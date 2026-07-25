#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L1 预筛:哪些「建议重审」的品牌**真的值得**跑全量重审?

## 为什么要这个

每日流水线(discover → classify → fold)天天往 events.yaml 堆事件,触发器(P0≥1 / P1≥3 /
加权≥6)很快就被顶过,于是首页常年一片「建议重审」。但 2026-07 那轮 15 家全量重审的实测
结果是:**净持平 1 家、其余多为 ±1~3 分**——大量事件是「方向价」(券商观点 / 预览 /
洽谈 / 同一件事的多家转载),**根本不该改分**。

全量重审(L2)每家要读 report.md 全文 + 全部未消费事件 ≈ 25k token 输入。若天天全量跑,
绝大多数 token 花在得出「↔ 不动」上。**L1 就是那道便宜的闸**:只看事件标题 + severity
(~2k token),判断这批里有没有**已落地的硬事实**;没有就不必惊动 L2。

## 边界(与本项目的反捏造原则一致)

- L1 **只判断「值不值得人去重审」,绝不建议加减分**——分数只在评委 in-character 重打时变。
- 判断是 **model-judged**,输出里如实标注,并要求模型**引用具体事件 id** 以便复核。
- 产出是**建议数据**(`watch/prescreen.json`),给人看 / 给后续消费;**不自动改任何已发布内容**。
- 没有 API key 时**优雅跳过**(退出 0,不写文件),与 classify_candidates 的行为一致。

## 用法

    python3 scripts/watch-tools/prescreen_reaudit.py                # 跑(需 key)
    python3 scripts/watch-tools/prescreen_reaudit.py --dry-run      # 只打印将发给模型的输入 + token 估算,不花钱
    python3 scripts/watch-tools/prescreen_reaudit.py --selftest     # 离线自检(mock 模型返回)
    python3 scripts/watch-tools/prescreen_reaudit.py --brand apple  # 只看一个品牌
"""

import os, sys, json, glob, datetime, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import classify_candidates as cc          # 复用 provider 分派 / 退避重试 / JSON 抽取
import evaluate_triggers as et            # 复用 30 天窗口触发规则

OUT_PATH = os.path.join(ROOT, "watch", "prescreen.json")
WATCH_DIR = os.path.join(ROOT, "watch")

SYSTEM = (
    "你在给一个品牌影响力审计系统做**预筛**:判断某品牌积压的舆情信号里,有没有值得"
    "「请人类评委重新打分」的**已落地硬事实**。\n\n"
    "判定标准——\n"
    "substantive(值得重审):出现了**已经发生、可核验**的实质事件,例如:财报/营收/盈亏"
    "具体数字、完成融资(含估值)、产品正式发布并可用、裁员/高管变动落地、监管处罚或诉讼判决、"
    "重大合作签约完成、股价异动伴随明确事由。\n"
    "directional(不值得):只有**方向价**——券商评级/目标价/观点、'据报道/洽谈中/预计/"
    "拟/预览/即将'、分析文章、同一件事的多家转载、纯口号或愿景表述。\n\n"
    "重要:\n"
    "1. 你**不判断分数涨跌**,也不建议加减分——只回答「值不值得人去重审」。\n"
    "2. 同一件事被多家转载,算**一件**;若该事件本身只是观点,再多转载也仍是 directional。\n"
    "3. reason 必须**引用具体事件 id**(取自输入),不要泛泛而谈。\n\n"
    '只输出 JSON 数组,每项:{"slug":"...","verdict":"substantive|directional",'
    '"reason":"...(≤80字,含事件 id)","key_event_ids":["..."]}。不要任何解释性散文。'
)


def _events_digest(events, window_days=30, as_of=None):
    """取窗口内未消费事件的 (id, date, severity, title) —— 只给标题,不给正文/URL,省 token。"""
    dates = [et.as_date(e.get("date")) for e in events if isinstance(e, dict)]
    dates = [d for d in dates if d]
    if as_of is None:
        as_of = max(dates) if dates else datetime.date.today()
    start = as_of - datetime.timedelta(days=window_days)
    out = []
    for e in events:
        if not isinstance(e, dict) or e.get("consumed_by"):
            continue
        d = et.as_date(e.get("date"))
        if d is None or not (start <= d <= as_of):
            continue
        out.append({"id": e.get("id"), "date": str(e.get("date")),
                    "sev": e.get("severity"), "title": (e.get("title") or "")[:110]})
    return out


def build_payload(brand=None, window_days=30):
    """→ [{slug, triggered_by, events:[...]}] ,只含**触发了**重审规则的品牌。"""
    feeds = et.load_events(WATCH_DIR, brand=brand)
    items = []
    for slug, events in sorted(feeds.items()):
        res = et.evaluate(events, as_of=None) if _accepts_none(et.evaluate) else None
        if res is None:  # evaluate 需要显式 as_of
            dates = [et.as_date(e.get("date")) for e in events if isinstance(e, dict)]
            dates = [d for d in dates if d]
            as_of = max(dates) if dates else datetime.date.today()
            res = et.evaluate(events, as_of, window_days)
        if not res.get("hit"):
            continue
        digest = _events_digest(events, window_days)
        if not digest:
            continue
        items.append({"slug": slug, "triggered_by": res.get("rules") or res.get("hit"),
                      "events": digest})
    return items


def _accepts_none(fn):
    return False  # evaluate 需要显式 as_of;保留分支以便将来放宽


def _clean(rows, wanted_slugs):
    """规范化模型返回:verdict 只允许两值;未覆盖的品牌降级为 directional 并标注。"""
    by = {}
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict):
            continue
        slug = r.get("slug")
        if slug not in wanted_slugs:
            continue
        v = r.get("verdict")
        if v not in ("substantive", "directional"):
            v = "directional"
        by[slug] = {"verdict": v, "reason": str(r.get("reason") or "")[:160],
                    "key_event_ids": [str(i) for i in (r.get("key_event_ids") or [])][:6]}
    for slug in wanted_slugs:
        by.setdefault(slug, {"verdict": "directional",
                             "reason": "模型未覆盖该品牌 —— 保守判为无实质变化(需人工复核)",
                             "key_event_ids": []})
    return by


def run(items, prov):
    payload = [{"slug": it["slug"], "events": it["events"]} for it in items]
    rows = cc.call_llm(payload, prov)
    return _clean(rows, {it["slug"] for it in items})


def render_md(result):
    """人可读摘要(给 PR body / 终端)。"""
    sub = [s for s, r in result["brands"].items() if r["verdict"] == "substantive"]
    dirn = [s for s, r in result["brands"].items() if r["verdict"] == "directional"]
    lines = [f"L1 预筛 · {result['generated_at']} · model={result['model']}",
             f"触发品牌 {len(result['brands'])} 家 → **值得重审 {len(sub)} 家** / 仅方向价 {len(dirn)} 家", ""]
    for slug in sub:
        r = result["brands"][slug]
        lines.append(f"  ⚡ {slug}: {r['reason']}  [{', '.join(r['key_event_ids'])}]")
    for slug in dirn:
        lines.append(f"  · {slug}: {result['brands'][slug]['reason']}")
    return "\n".join(lines)


def main(argv):
    ap = argparse.ArgumentParser(description="L1:预筛哪些触发品牌真的值得全量重审")
    ap.add_argument("--brand", help="只看一个品牌")
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true", help="只打印将发给模型的输入 + token 估算,不调用")
    ap.add_argument("--selftest", action="store_true", help="离线自检(mock 模型返回)")
    ap.add_argument("-o", "--out", default=OUT_PATH)
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    items = build_payload(args.brand, args.window_days)
    if not items:
        print("prescreen: 无触发品牌 —— 无需预筛。")
        return 0

    if args.dry_run:
        payload = [{"slug": it["slug"], "events": it["events"]} for it in items]
        blob = json.dumps(payload, ensure_ascii=False)
        n_ev = sum(len(it["events"]) for it in items)
        print(f"prescreen --dry-run:{len(items)} 个触发品牌 / {n_ev} 条未消费事件")
        print(f"  输入 ≈ {len(blob)} 字符 + system {len(SYSTEM)} 字符 "
              f"≈ {(len(blob) + len(SYSTEM)) // 2} token(粗估,中文 ~2 字符/token)")
        print(f"  品牌:{', '.join(it['slug'] for it in items)}")
        return 0

    prov = cc._provider()
    if not prov:
        print("prescreen: 未配置 GLM_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY —— 优雅跳过。")
        return 0

    brands = run(items, prov)
    result = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": prov[3],
        "window_days": args.window_days,
        "note": ("L1 预筛:判断「值不值得请评委重审」,**不判断分数涨跌**。verdict 为 model-judged,"
                 "reason 引用事件 id 供复核;分数只在评委 in-character 重打时变。"),
        "brands": brands,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(render_md(result))
    print(f"\nprescreen: 已写 {os.path.relpath(args.out, ROOT)}")
    return 0


def _selftest():
    """离线断言:不碰网络,验证摘要/规范化/降级/窗口这几处易错的地方。"""
    checks, fails = 0, []

    def ok(cond, name):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(name)

    today = datetime.date(2026, 7, 25)
    ev = [
        {"id": "a-1", "date": today, "severity": "P1", "title": "完成 B 轮融资 10 亿美元"},
        {"id": "a-2", "date": today, "severity": "P2", "title": "券商上调评级", "consumed_by": "v3"},
        {"id": "a-3", "date": datetime.date(2026, 1, 1), "severity": "P0", "title": "很久以前的事"},
    ]
    d = _events_digest(ev, 30, as_of=today)
    ok(len(d) == 1 and d[0]["id"] == "a-1", "digest:只取窗口内未消费")
    ok("title" in d[0] and "url" not in d[0], "digest:不含 URL(省 token)")

    cleaned = _clean([{"slug": "x", "verdict": "substantive", "reason": "见 a-1", "key_event_ids": ["a-1"]}],
                     {"x", "y"})
    ok(cleaned["x"]["verdict"] == "substantive", "clean:保留合法 verdict")
    ok(cleaned["y"]["verdict"] == "directional", "clean:未覆盖品牌保守降级")
    ok("需人工复核" in cleaned["y"]["reason"], "clean:降级理由写明需复核")

    bad = _clean([{"slug": "x", "verdict": "涨分!", "reason": "r"}], {"x"})
    ok(bad["x"]["verdict"] == "directional", "clean:非法 verdict 降级(模型不能自创判定)")

    ok("不判断分数" in SYSTEM and "directional" in SYSTEM, "prompt:明确禁止判断分数涨跌")
    ok("转载" in SYSTEM, "prompt:明确同一事多家转载算一件")

    r = {"generated_at": "t", "model": "m",
         "brands": {"a": {"verdict": "substantive", "reason": "见 a-1", "key_event_ids": ["a-1"]},
                    "b": {"verdict": "directional", "reason": "只有观点", "key_event_ids": []}}}
    md = render_md(r)
    ok("值得重审 1 家" in md and "⚡ a" in md, "render:摘要区分两类")

    print(f"prescreen --selftest: {'✅ ' + str(checks) + ' 组断言全部通过(门禁有牙)' if not fails else '❌ 失败: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
