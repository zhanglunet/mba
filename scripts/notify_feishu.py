#!/usr/bin/env python3
"""notify_feishu.py — 把「品牌监控 / 舆情信号」的变化推送到飞书群。

在 CI(push 到 main)里跑:比较 base..head 两个提交,聚合出**三类值得推**的变化,
拼成一张飞书交互卡片 POST 到自定义机器人 webhook。内容全部来自仓库文件里的真实
数据(事件标题/引用/URL、真实评分),不做任何 LLM 生成 —— 反捏造红线。

推送门槛(2026-07-13 与用户确认,与首页卡片「建议重审」同口径):
  1. 新增 **P0/P1** 舆情事件(P2/P3 不单独刷群,docs/15 §5.2)
  2. 品牌**新命中「建议重审」**触发规则(evaluate_triggers 单一真源:R1 P0≥1 / R2 P1≥3
     / R3 加权 4·2·0.5 ≥6;只数未消费事件)——base 未命中、head 命中才推
  3. **评分变动**(site/reports-meta.yaml 的 score_normalized 变化)

用法:
  python3 scripts/notify_feishu.py --base <sha> --head <sha>     # CI 模式
  python3 scripts/notify_feishu.py --base <sha> --head <sha> --dry-run   # 只打印卡片,不 POST

环境变量:
  FEISHU_WEBHOOK       飞书自定义机器人 webhook URL(必需,缺失则跳过)
  FEISHU_SIGN_SECRET   机器人「签名校验」密钥(可选,配了才加签)

退出码:0 = 成功推送 / 无变化可推 / 无 webhook(非阻断);1 = POST 失败(飞书返回错误)。
"""
import argparse, base64, datetime, hashlib, hmac, json, os, subprocess, sys, time, urllib.request, urllib.error
import pathlib, yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "watch-tools"))
from evaluate_triggers import evaluate  # 单一真源:触发规则  # noqa: E402

WDIM_NAME = {
    "W1": "媒体报道", "W2": "社交声量", "W3": "招投标采购", "W4": "监管司法",
    "W5": "资本市场", "W6": "产品口碑", "W7": "人事组织", "W8": "技术知产", "W9": "供应链生态",
}
SEV_MARK = {"P0": "🔴 P0", "P1": "🟠 P1"}
DIR_MARK = {"pos": "利好 ▲", "neg": "利空 ▼", "neu": "中性 ▬", "neutral": "中性 ▬"}
SITE = "https://mbabrand.com"
BIG_WINDOW = 100000  # 关掉 evaluate 的 30 天窗口 → 与首页「未消费全量」口径一致

# ── 分层预警(Phase 2,docs/20)──────────────────────────────────────────────
# L3 高层预警 = P0 事件 / 建议重审;L2 专项协同 = P1 事件;L1 日常 = 评分变动/其余。
# 事件可用 alert_tier 覆写;各层可配独立 webhook(FEISHU_WEBHOOK_L{1,2,3}),
# 未配则回落 FEISHU_WEBHOOK;解析到同一 webhook 的层合并成一张卡(单群仍一张)。
TIERS = ("L3", "L2", "L1")
TIER_META = {
    "L3": {"template": "red", "label": "高层预警", "emoji": "🚨"},
    "L2": {"template": "orange", "label": "专项协同", "emoji": "📣"},
    "L1": {"template": "blue", "label": "日常监测", "emoji": "📊"},
}


# ── git 取历史版本 ───────────────────────────────────────────────────────────
def git_show(ref, path):
    """git show <ref>:<path> → 文本;文件在该 ref 不存在时返回 None。"""
    try:
        out = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT,
                             capture_output=True, text=True, check=True)
        return out.stdout
    except subprocess.CalledProcessError:
        return None


def git_changed(base, head, pathspec):
    try:
        out = subprocess.run(["git", "diff", "--name-only", f"{base}..{head}", "--", pathspec],
                             cwd=ROOT, capture_output=True, text=True, check=True)
        return [l.strip() for l in out.stdout.splitlines() if l.strip()]
    except subprocess.CalledProcessError:
        return []


def resolve_base(base, head):
    """base 无效(空/全 0/解析不了)时退回 head^;再不行返回 None(无从 diff)。"""
    def valid(ref):
        if not ref or set(ref) <= {"0"}:
            return False
        return subprocess.run(["git", "cat-file", "-e", f"{ref}^{{commit}}"], cwd=ROOT,
                              capture_output=True).returncode == 0
    if valid(base):
        return base
    parent = f"{head}^"
    return parent if valid(parent) else None


def load_yaml(text, default):
    if not text:
        return default
    try:
        return yaml.safe_load(text)
    except Exception:
        return default


# ── 变化检测 ─────────────────────────────────────────────────────────────────
def detect_changes(base, head):
    """返回 dict(new_events:[...], rec_brands:[...], score_changes:[...])。"""
    meta_head = load_yaml(git_show(head, "site/reports-meta.yaml"), {"reports": []}) or {"reports": []}
    brand_cn = {r["slug"]: r.get("brand_cn", r["slug"]) for r in meta_head.get("reports", [])}
    as_of = datetime.date.today()

    new_events, rec_brands = [], []
    for path in git_changed(base, head, "watch/"):
        if not path.endswith("events.yaml"):
            continue
        slug = pathlib.PurePosixPath(path).parent.name
        head_ev = load_yaml(git_show(head, path), []) or []
        base_ev = load_yaml(git_show(base, path), []) or []
        base_ids = {str(e.get("id")) for e in base_ev if isinstance(e, dict)}
        # 1) 新增 P0/P1 事件
        for e in head_ev:
            if not isinstance(e, dict):
                continue
            if str(e.get("id")) in base_ids:
                continue
            if e.get("severity") in ("P0", "P1"):
                new_events.append({"slug": slug, "brand": brand_cn.get(slug, slug), **e})
        # 2) 新命中「建议重审」
        head_hit = evaluate(head_ev, as_of, window_days=BIG_WINDOW)
        base_hit = evaluate(base_ev, as_of, window_days=BIG_WINDOW)
        if head_hit["hit"] and not base_hit["hit"]:
            rec_brands.append({"slug": slug, "brand": brand_cn.get(slug, slug),
                               "p0": head_hit["p0"], "p1": head_hit["p1"],
                               "rules": head_hit["rules_hit"]})

    # 3) 评分变动
    score_changes = []
    if git_changed(base, head, "site/reports-meta.yaml"):
        meta_base = load_yaml(git_show(base, "site/reports-meta.yaml"), {"reports": []}) or {"reports": []}
        base_score = {r["slug"]: r.get("score_normalized") for r in meta_base.get("reports", [])}
        for r in meta_head.get("reports", []):
            slug = r["slug"]
            new = r.get("score_normalized")
            old = base_score.get(slug)
            if new is None:
                continue
            if slug not in base_score:  # 新品牌首审
                score_changes.append({"slug": slug, "brand": brand_cn.get(slug, slug),
                                      "old": None, "new": new, "version": r.get("version", "")})
            elif old is not None and abs(float(new) - float(old)) >= 0.005:
                score_changes.append({"slug": slug, "brand": brand_cn.get(slug, slug),
                                      "old": old, "new": new, "version": r.get("version", "")})

    new_events.sort(key=lambda e: (e.get("severity"), e.get("date", "")))
    return {"new_events": new_events, "rec_brands": rec_brands, "score_changes": score_changes}


# ── 飞书卡片 ─────────────────────────────────────────────────────────────────
def esc_md(s):
    # lark_md 里的正文;去掉可能破坏 markdown 的裸字符
    return str(s).replace("*", "＊").replace("[", "【").replace("]", "】").strip()


def event_tier(e):
    """单条舆情事件的层级:alert_tier 覆写优先,否则按 severity 派生。"""
    t = e.get("alert_tier")
    if t in TIERS:
        return t
    if e.get("severity") == "P0":
        return "L3"
    if e.get("severity") == "P1":
        return "L2"
    return "L1"


def split_tiers(ch):
    """把变化按层拆分。返回 {tier: {rec_brands, new_events, score_changes}}。
    建议重审 → L3;事件按 event_tier;评分变动 → L1。"""
    out = {t: {"rec_brands": [], "new_events": [], "score_changes": []} for t in TIERS}
    for b in ch["rec_brands"]:
        out["L3"]["rec_brands"].append(b)
    for e in ch["new_events"]:
        out[event_tier(e)]["new_events"].append(e)
    for s in ch["score_changes"]:
        out["L1"]["score_changes"].append(s)
    return out


def _rec_element(rb):
    lines = []
    for b in rb:
        rules = "、".join(b["rules"]) or "触发规则命中"
        lines.append(f"• **{esc_md(b['brand'])}** — 未消费 P0×{b['p0']} / P1×{b['p1']}("
                     f"{esc_md(rules)}) [信号 →]({SITE}/watch/{b['slug']}/)")
    return {"tag": "div", "text": {"tag": "lark_md", "content": "**🔁 建议重审**\n" + "\n".join(lines)}}


def _events_element(ne):
    lines = []
    for e in ne:
        mark = SEV_MARK.get(e.get("severity"), e.get("severity", ""))
        d = DIR_MARK.get(str(e.get("direction", "neu")).lower(), "")
        dim = e.get("dim", "")
        dim_txt = f"{dim} {WDIM_NAME.get(dim, '')}".strip()
        title = esc_md(e.get("title", e.get("id", "事件")))
        url = e.get("url", "")
        date = e.get("date", "")
        persons = e.get("related_persons") or []
        who = f" · 关联 {esc_md('、'.join(persons))}" if persons else ""
        head = f"• {mark} {d} · {esc_md(e['brand'])} · {esc_md(dim_txt)}{who} · {date}"
        body = f"[{title}]({url})" if url else title
        act = e.get("suggested_action")
        tail = f"\n  建议:{esc_md(act)}" if act else ""
        lines.append(f"{head}\n  {body}{tail}")
    return {"tag": "div", "text": {"tag": "lark_md", "content": "**📮 新增舆情信号**\n" + "\n".join(lines)}}


def _scores_element(sc):
    lines = []
    for s in sc:
        if s["old"] is None:
            lines.append(f"• **{esc_md(s['brand'])}** {s.get('version','')} 首审 **{s['new']}**/10 "
                         f"[报告 →]({SITE}/reports/{s['slug']}/)")
        else:
            delta = round(float(s["new"]) - float(s["old"]), 2)
            arrow = "↑" if delta > 0 else "↓"
            lines.append(f"• **{esc_md(s['brand'])}** {s['old']} → **{s['new']}**/10 "
                         f"({arrow}{abs(delta):.2f}) [报告 →]({SITE}/reports/{s['slug']}/)")
    return {"tag": "div", "text": {"tag": "lark_md", "content": "**📈 评分变动**\n" + "\n".join(lines)}}


def _sections_elements(sec):
    """把一个 {rec_brands,new_events,score_changes} 子集渲染成 element 列表(仅非空段)。"""
    els = []
    if sec["rec_brands"]:
        els.append(_rec_element(sec["rec_brands"]))
    if sec["new_events"]:
        els.append(_events_element(sec["new_events"]))
    if sec["score_changes"]:
        els.append(_scores_element(sec["score_changes"]))
    return els


def _count(sec):
    return len(sec["rec_brands"]) + len(sec["new_events"]) + len(sec["score_changes"])


def build_card(ch):
    """兼容入口:把全部变化合成单卡(header 取最高层)。供单群/无分层 webhook 场景。"""
    tiers = split_tiers(ch)
    included = [t for t in TIERS if _count(tiers[t]) > 0]
    return build_card_for(included, tiers)


def build_card_for(tiers_included, tiers):
    """为给定层级集合建一张卡:按 L3→L2→L1 顺序拼各层分区,header 用最高层模板。"""
    tiers_included = [t for t in TIERS if t in tiers_included and _count(tiers[t]) > 0]
    if not tiers_included:
        return None
    top = tiers_included[0]  # TIERS 已按 L3→L1 排序
    today = datetime.date.today().isoformat()
    n = sum(_count(tiers[t]) for t in tiers_included)

    elements = []
    multi = len(tiers_included) > 1
    for t in tiers_included:
        if multi:
            m = TIER_META[t]
            elements.append({"tag": "div", "text": {"tag": "lark_md",
                            "content": f"{m['emoji']} **{m['label']}({t})**"}})
        elements.extend(_sections_elements(tiers[t]))
    elements.append({"tag": "hr"})
    elements.append({"tag": "note", "elements": [{"tag": "lark_md",
                    "content": f"MBA 品牌监控 · 评分为 AI 评委模拟,非本人观点,不构成投资建议 · [{SITE}]({SITE})"}]})

    meta = TIER_META[top]
    label = "" if multi else f" · {meta['label']}"
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {"template": meta["template"],
                       "title": {"tag": "plain_text",
                                 "content": f"{meta['emoji']} MBA 品牌监控更新{label} · {today} · {n} 项"}},
            "elements": elements,
        },
    }


def tier_webhook(tier):
    """层级 → webhook:FEISHU_WEBHOOK_L{n} 优先,回落 FEISHU_WEBHOOK。返回 '' 表示未配。"""
    return (os.environ.get(f"FEISHU_WEBHOOK_{tier}", "").strip()
            or os.environ.get("FEISHU_WEBHOOK", "").strip())


# ── 发送(含飞书签名)──────────────────────────────────────────────────────────
def sign(secret, timestamp):
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(string_to_sign.encode("utf-8"), b"", digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def post_feishu(url, card, secret=None, timeout=10):
    body = dict(card)
    if secret:
        ts = str(int(time.time()))
        body = {"timestamp": ts, "sign": sign(secret, ts), **body}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        return False, f"network error: {e}"
    try:
        j = json.loads(raw)
    except Exception:
        return False, f"non-JSON response: {raw[:200]}"
    # 飞书成功:{"code":0,...} 或旧格式 {"StatusCode":0,...}
    if j.get("code") == 0 or j.get("StatusCode") == 0:
        return True, "ok"
    return False, f"feishu error: {raw[:200]}"


def build_test_card():
    """一张明确标注为「测试」的连通性卡片 —— 手动触发用,验证 webhook / 签名 / 进群是否 OK。
    不含任何品牌数据,不冒充真实变化。"""
    today = datetime.date.today().isoformat()
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {"template": "turquoise",
                       "title": {"tag": "plain_text", "content": f"🔧 MBA 飞书推送 · 连通性测试 · {today}"}},
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md",
                 "content": "**如果你在群里看到这条,说明配置成功 ✅**\n"
                            "webhook 可达、签名(若配)正确、机器人已进群。\n\n"
                            "之后每当合并涉及 **舆情事件 / 评分** 的 PR 到 main,"
                            "就会自动推送「新增 P0/P1 事件 / 建议重审 / 评分变动」的真实变化卡片。"}},
                {"tag": "hr"},
                {"tag": "note", "elements": [{"tag": "lark_md",
                 "content": f"MBA 品牌监控 · 手动测试消息(非真实告警)· [{SITE}]({SITE})"}]},
            ],
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--dry-run", action="store_true", help="只打印卡片 JSON,不 POST")
    ap.add_argument("--test", action="store_true", help="发一张「连通性测试」卡片(不 diff,手动验证用)")
    ap.add_argument("--tier", choices=TIERS, help="只处理指定层级(L1/L2/L3),便于测试")
    args = ap.parse_args()
    secret = os.environ.get("FEISHU_SIGN_SECRET", "").strip() or None
    only = [args.tier] if args.tier else list(TIERS)

    # 手动连通性测试:发测试卡片即返回(--tier 指定发到哪层的 webhook)
    if args.test:
        card = build_test_card()
        if args.dry_run:
            print(f"[feishu] DRY-RUN(--test tier={args.tier or 'L1'})测试卡片如下:\n")
            print(json.dumps(card, ensure_ascii=False, indent=2))
            return 0
        webhook = tier_webhook(args.tier or "L1")
        if not webhook:
            print("[feishu] 未设置 FEISHU_WEBHOOK — 无法发测试卡片")
            return 1
        ok, detail = post_feishu(webhook, card, secret)
        print(f"[feishu] 测试卡片({args.tier or 'L1'}):{'成功' if ok else '失败'}（{detail}）")
        return 0 if ok else 1

    base = resolve_base(args.base, args.head)
    if base is None:
        print("[feishu] 无有效 base 提交可 diff — 跳过")
        return 0

    changes = detect_changes(base, args.head)
    tiers = split_tiers(changes)
    active = [t for t in only if _count(tiers[t]) > 0]
    if not active:
        print("[feishu] 本次无 P0/P1 事件 / 建议重审 / 评分变动 — 无需推送")
        return 0

    # 按解析后的 webhook 分组:同一 webhook 的层合并成一张卡(单群一张,多群分流)
    groups = {}  # webhook(或占位) → [tiers]
    for t in active:
        wh = tier_webhook(t) or "<unset>"
        groups.setdefault(wh, []).append(t)

    if args.dry_run:
        total = sum(_count(tiers[t]) for t in active)
        print(f"[feishu] DRY-RUN — {total} 项变化,{len(groups)} 张卡(层→webhook 分组):")
        for wh, ts in groups.items():
            card = build_card_for(ts, tiers)
            print(f"\n─── webhook={'(未配)' if wh=='<unset>' else wh[:48]+'…'} · 层 {'/'.join(ts)} ───")
            print(json.dumps(card, ensure_ascii=False, indent=2))
        return 0

    if list(groups) == ["<unset>"]:
        print("[feishu] 未设置 FEISHU_WEBHOOK — 跳过(非阻断)")
        return 0

    rc = 0
    for wh, ts in groups.items():
        if wh == "<unset>":
            print(f"[feishu] 层 {'/'.join(ts)} 无对应 webhook — 跳过")
            continue
        card = build_card_for(ts, tiers)
        n = sum(_count(tiers[t]) for t in ts)
        ok, detail = post_feishu(wh, card, secret)
        print(f"[feishu] 推送层 {'/'.join(ts)}({n} 项):{'成功' if ok else '失败'}（{detail}）")
        if not ok:
            rc = 1
    return rc
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
