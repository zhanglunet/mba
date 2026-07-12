#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evaluate_triggers.py — Brand Watch 触发规则**运行时**评估器(W7,docs/15 §5.3)。

规则(滚动 30 天窗口内,三条任一命中 → 建议重审):
  R1  P0 ≥ 1
  R2  P1 ≥ 2
  R3  加权计数 4×P0 + 2×P1 + 0.5×P2 ≥ 5

与首页徽章(build_home_cards.py)的分工——两者口径**故意不同**,docs/16 §6.2 记录在案:
  - 徽章是**生成物**,必须确定性(--check 漂移 gate),所以数「未消费」、不看日期窗;
  - 本评估器是**运行时工具**(不产生入库产物),恢复 PRD 的 30 天滚动窗语义。
  默认只数未消费事件(consumed_by 已进审计的信号不再重复催审),--include-consumed
  可切回 PRD 严格口径。

边界(不可妥协):评估器**只建议、不改分**——输出是 EVOLUTION 建议,不是任何分数。

用法:
  python3 scripts/watch-tools/evaluate_triggers.py                 # 全部品牌
  python3 scripts/watch-tools/evaluate_triggers.py --brand spacex  # 单品牌
  python3 scripts/watch-tools/evaluate_triggers.py --json          # 机器输出
  python3 scripts/watch-tools/evaluate_triggers.py --as-of 2026-07-12 --window-days 30
  python3 scripts/watch-tools/evaluate_triggers.py --selftest
退出码恒为 0(--selftest 失败除外):这是建议工具,不是 gate。
"""
import argparse
import datetime
import glob
import json
import os
import sys

try:
    import yaml
except ImportError:
    print("evaluate_triggers: 需要 PyYAML(pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WATCH_DIR = os.path.join(ROOT, "watch")

WEIGHTS = {"P0": 4.0, "P1": 2.0, "P2": 0.5, "P3": 0.0}
WEIGHTED_THRESHOLD = 5.0


def as_date(v):
    if isinstance(v, datetime.date):
        return v
    if isinstance(v, str):
        try:
            return datetime.date.fromisoformat(v)
        except ValueError:
            return None
    return None


def evaluate(events, as_of, window_days=30, include_consumed=False):
    """对单品牌事件列表评估触发规则。返回 dict(counts / weighted / rules_hit / hit)。"""
    counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    window_start = as_of - datetime.timedelta(days=window_days)
    considered = []
    for e in events or []:
        if not isinstance(e, dict):
            continue
        d = as_date(e.get("date"))
        if d is None or not (window_start <= d <= as_of):
            continue
        if not include_consumed and e.get("consumed_by"):
            continue
        sev = e.get("severity")
        if sev in counts:
            counts[sev] += 1
            considered.append(str(e.get("id")))
    weighted = sum(WEIGHTS[s] * n for s, n in counts.items())
    rules_hit = []
    if counts["P0"] >= 1:
        rules_hit.append("R1:P0≥1")
    if counts["P1"] >= 2:
        rules_hit.append("R2:P1≥2")
    if weighted >= WEIGHTED_THRESHOLD:
        rules_hit.append(f"R3:加权{weighted:g}≥{WEIGHTED_THRESHOLD:g}")
    return {
        "p0": counts["P0"], "p1": counts["P1"], "p2": counts["P2"], "p3": counts["P3"],
        "weighted": weighted, "rules_hit": rules_hit, "hit": bool(rules_hit),
        "considered_ids": considered,
    }


def load_events(watch_dir, brand=None):
    out = {}
    for path in sorted(glob.glob(os.path.join(watch_dir, "*", "events.yaml"))):
        slug = os.path.basename(os.path.dirname(path))
        if brand and slug != brand:
            continue
        out[slug] = yaml.safe_load(open(path, encoding="utf-8")) or []
    return out


def main(argv):
    ap = argparse.ArgumentParser(description="Brand Watch 触发规则运行时评估(只建议、不改分)")
    ap.add_argument("--brand", help="只评估该品牌 slug")
    ap.add_argument("--as-of", help="评估基准日 YYYY-MM-DD(默认今天;定基准日可复现)")
    ap.add_argument("--window-days", type=int, default=30, help="滚动窗口天数(默认 30)")
    ap.add_argument("--include-consumed", action="store_true",
                    help="窗口内已消费(consumed_by)事件也计数(PRD 严格口径;默认只数未消费)")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv)

    as_of = as_date(args.as_of) if args.as_of else datetime.date.today()
    if as_of is None:
        print(f"evaluate_triggers: --as-of `{args.as_of}` 不是合法 YYYY-MM-DD", file=sys.stderr)
        return 2

    all_events = load_events(WATCH_DIR, args.brand)
    if args.brand and not all_events:
        print(f"evaluate_triggers: watch/{args.brand}/events.yaml 不存在", file=sys.stderr)
        return 2

    results = {slug: evaluate(ev, as_of, args.window_days, args.include_consumed)
               for slug, ev in all_events.items()}

    if args.json:
        print(json.dumps({
            "as_of": as_of.isoformat(), "window_days": args.window_days,
            "include_consumed": args.include_consumed,
            "brands": {s: {k: v for k, v in r.items() if k != "considered_ids"}
                       for s, r in results.items()},
        }, ensure_ascii=False, indent=2))
        return 0

    scope = "含已消费" if args.include_consumed else "仅未消费"
    print(f"触发规则评估 · 基准日 {as_of} · 窗口 {args.window_days} 天 · {scope}"
          f"(规则:P0≥1 / P1≥2 / 加权 4·2·0.5 ≥5)")
    print("-" * 72)
    hits = 0
    for slug, r in sorted(results.items()):
        mark = "⚡ 建议重审" if r["hit"] else "—"
        rules = ",".join(r["rules_hit"]) if r["rules_hit"] else "无"
        print(f"{slug:<14} P0×{r['p0']} P1×{r['p1']} P2×{r['p2']} "
              f"加权={r['weighted']:g}  命中:{rules:<24} {mark}")
        hits += r["hit"]
    print("-" * 72)
    print(f"{hits}/{len(results)} 品牌命中触发规则。评估仅作建议——改分只能来自评委重审(docs/15 §5.3)。")
    return 0


# ------------------------------------------------------------- selftest ----

def selftest():
    as_of = datetime.date(2026, 7, 12)

    def ev(days_ago, sev, consumed=None):
        d = as_of - datetime.timedelta(days=days_ago)
        e = {"id": f"{d.isoformat()}-t-001", "date": d, "severity": sev}
        if consumed:
            e["consumed_by"] = consumed
        return e

    cases = [
        ("空事件不命中", [], False, {}),
        ("窗口内 1×P0 命中 R1", [ev(5, "P0")], True, {}),
        ("窗口内 1×P1 不命中", [ev(5, "P1")], False, {}),
        ("窗口内 2×P1 命中 R2", [ev(5, "P1"), ev(9, "P1")], True, {}),
        ("P1+6×P2 加权 5.0 命中 R3", [ev(3, "P1")] + [ev(i + 4, "P2") for i in range(6)], True, {}),
        ("5×P2 加权 2.5 不命中", [ev(i + 1, "P2") for i in range(5)], False, {}),
        ("P0 在窗口外(31 天前)不命中", [ev(31, "P0")], False, {}),
        ("P0 恰在窗口沿(30 天前)命中", [ev(30, "P0")], True, {}),
        ("已消费 P0 默认不计", [ev(5, "P0", consumed="v2")], False, {}),
        ("已消费 P0 在 include_consumed 下计入", [ev(5, "P0", consumed="v2")], True,
         {"include_consumed": True}),
        ("未来日期事件不计", [ev(-3, "P0")], False, {}),
        ("P3 不参与任何规则", [ev(2, "P3")] * 20, False, {}),
    ]
    failed = []
    for name, events, expect_hit, kw in cases:
        r = evaluate(events, as_of, 30, kw.get("include_consumed", False))
        if r["hit"] != expect_hit:
            failed.append(f"{name}: 期望 hit={expect_hit},实得 {r}")
    if failed:
        print("evaluate_triggers --selftest: ❌", file=sys.stderr)
        for f in failed:
            print("  - " + f, file=sys.stderr)
        return 1
    print(f"evaluate_triggers --selftest: ✅ {len(cases)} 组断言全部通过(评估器有牙)。")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv[1:] else main(sys.argv[1:]))
