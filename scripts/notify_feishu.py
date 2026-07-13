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


def build_card(ch):
    ne, rb, sc = ch["new_events"], ch["rec_brands"], ch["score_changes"]
    if not (ne or rb or sc):
        return None
    today = datetime.date.today().isoformat()
    urgent = bool(rb) or any(e.get("severity") == "P0" for e in ne)
    template = "red" if urgent else "orange"
    n = len(ne) + len(rb) + len(sc)

    elements = []

    if rb:
        lines = []
        for b in rb:
            rules = "、".join(b["rules"]) or "触发规则命中"
            lines.append(f"• **{esc_md(b['brand'])}** — 未消费 P0×{b['p0']} / P1×{b['p1']}("
                         f"{esc_md(rules)}) [信号 →]({SITE}/watch/{b['slug']}/)")
        elements.append({"tag": "div", "text": {"tag": "lark_md",
                        "content": "**🔁 建议重审**\n" + "\n".join(lines)}})

    if ne:
        lines = []
        for e in ne:
            mark = SEV_MARK.get(e.get("severity"), e.get("severity", ""))
            d = DIR_MARK.get(str(e.get("direction", "neu")).lower(), "")
            dim = e.get("dim", "")
            dim_txt = f"{dim} {WDIM_NAME.get(dim, '')}".strip()
            title = esc_md(e.get("title", e.get("id", "事件")))
            url = e.get("url", "")
            date = e.get("date", "")
            head = f"• {mark} {d} · {esc_md(e['brand'])} · {esc_md(dim_txt)} · {date}"
            body = f"[{title}]({url})" if url else title
            lines.append(f"{head}\n  {body}")
        elements.append({"tag": "div", "text": {"tag": "lark_md",
                        "content": "**📮 新增舆情信号(P0/P1)**\n" + "\n".join(lines)}})

    if sc:
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
        elements.append({"tag": "div", "text": {"tag": "lark_md",
                        "content": "**📈 评分变动**\n" + "\n".join(lines)}})

    elements.append({"tag": "hr"})
    elements.append({"tag": "note", "elements": [{"tag": "lark_md",
                    "content": f"MBA 品牌监控 · 评分为 AI 评委模拟,非本人观点,不构成投资建议 · [{SITE}]({SITE})"}]})

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {"template": template,
                       "title": {"tag": "plain_text", "content": f"MBA 品牌监控更新 · {today} · {n} 项"}},
            "elements": elements,
        },
    }


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--dry-run", action="store_true", help="只打印卡片 JSON,不 POST")
    args = ap.parse_args()

    base = resolve_base(args.base, args.head)
    if base is None:
        print("[feishu] 无有效 base 提交可 diff — 跳过")
        return 0

    changes = detect_changes(base, args.head)
    card = build_card(changes)
    if card is None:
        print("[feishu] 本次无 P0/P1 事件 / 建议重审 / 评分变动 — 无需推送")
        return 0

    n = sum(len(changes[k]) for k in ("new_events", "rec_brands", "score_changes"))
    if args.dry_run:
        print(f"[feishu] DRY-RUN — {n} 项变化,卡片如下:\n")
        print(json.dumps(card, ensure_ascii=False, indent=2))
        return 0

    webhook = os.environ.get("FEISHU_WEBHOOK", "").strip()
    if not webhook:
        print("[feishu] 未设置 FEISHU_WEBHOOK — 跳过(非阻断)")
        return 0
    ok, detail = post_feishu(webhook, card, os.environ.get("FEISHU_SIGN_SECRET", "").strip() or None)
    print(f"[feishu] 推送 {n} 项变化:{'成功' if ok else '失败'}（{detail}）")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
