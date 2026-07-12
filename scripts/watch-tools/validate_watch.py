#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_watch.py — Brand Watch(舆情监控)数据静态硬 gate。

守三件事(docs/15 §3 三原则的机器化,docs/16 §2 是实现记录):

  A. 事件可溯源的**结构底线**:每条事件必须有 url / quote / fetched_at / date,
     quote ≤ 100 字(docs/15 §8.4),url 必须是 http(s)。
     (quote 是否逐字命中原文属抽检 SOP,不进 CI —— 网络校验会 flaky。)
  B. 判断字段与事实字段分列:direction_by 恒为 "model-judged";
     dim/severity/direction/lens_map 枚举合法;id 前缀与 date、目录 slug 一致且唯一。
  C. 适用性矩阵对齐:watch/matrix.yaml 的品牌集合 == site/published-reports.txt
     白名单(新发布品牌必须补矩阵行);事件的 dim 在该品牌上不得为 off
     (空维度诚实留空,不填噪音)。

用法:
  python3 scripts/watch-tools/validate_watch.py             # 校验全部 watch 数据
  python3 scripts/watch-tools/validate_watch.py --selftest  # 自测:证明每类违规都会被抓
退出码:有违规 → 1;否则 0。watch/ 不存在或无事件文件时通过(功能未启用不算错)。
"""
import datetime
import glob
import os
import re
import sys

try:
    import yaml
except ImportError:
    print("validate_watch: 需要 PyYAML(pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WATCH_DIR = os.path.join(ROOT, "watch")
MATRIX = os.path.join(WATCH_DIR, "matrix.yaml")
WHITELIST = os.path.join(ROOT, "site", "published-reports.txt")

DIMS = {f"W{i}" for i in range(1, 10)}
SEVERITIES = {"P0", "P1", "P2", "P3"}
DIRECTIONS = {"pos", "neg", "neutral", "mixed"}
LENSES = {"origin", "category", "leverage", "identity", "signal"}
QUOTE_TYPES = {"title", "body"}
QUOTE_MAX = 100
REQUIRED = ("id", "date", "dim", "severity", "direction", "direction_by",
            "title", "quote", "url", "fetched_at", "lens_map")
FETCHED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?Z$")


def read_whitelist(path=WHITELIST):
    slugs = []
    for line in open(path, encoding="utf-8"):
        t = line.strip()
        if t and not t.startswith("#"):
            slugs.append(t)
    return slugs


def as_date(v):
    """YAML 会把裸日期解析成 date;也接受 'YYYY-MM-DD' 字符串。非法返回 None。"""
    if isinstance(v, datetime.date):
        return v
    if isinstance(v, str):
        try:
            return datetime.date.fromisoformat(v)
        except ValueError:
            return None
    return None


def _norm_flag(v):
    """YAML 1.1 把 on/off 解析成布尔 —— 归一化回字符串(过程记录见 docs/16 §2)。"""
    if v is True:
        return "on"
    if v is False:
        return "off"
    return v


def validate_matrix(matrix, whitelist):
    """检查 C(矩阵对齐白名单)。返回 (errors, brands_dict)。"""
    errs = []
    brands = (matrix or {}).get("brands") or {}
    brands = {s: ({d: _norm_flag(v) for d, v in dims.items()} if isinstance(dims, dict) else dims)
              for s, dims in brands.items()}
    wl, mx = set(whitelist), set(brands)
    for miss in sorted(wl - mx):
        errs.append(f"matrix: 白名单品牌 `{miss}` 缺矩阵行(新发布品牌必须补 watch/matrix.yaml)")
    for extra in sorted(mx - wl):
        errs.append(f"matrix: 品牌 `{extra}` 不在发布白名单(下线品牌应删矩阵行)")
    for slug, dims in brands.items():
        if not isinstance(dims, dict):
            errs.append(f"matrix: `{slug}` 的维度配置不是映射")
            continue
        if set(dims) != DIMS:
            errs.append(f"matrix: `{slug}` 维度键应恰为 W1..W9,实际 {sorted(dims)}")
        for d, v in dims.items():
            if v not in ("core", "on", "off"):
                errs.append(f"matrix: `{slug}.{d}` 取值 `{v}` 非法(core/on/off)")
    return errs, brands


def validate_events(slug, events, brands, today):
    """检查 A + B(单品牌事件流)。"""
    errs = []
    ctx0 = f"watch/{slug}/events.yaml"
    if events is None:
        return [f"{ctx0}: 空文件(要么有事件,要么删文件)"]
    if not isinstance(events, list):
        return [f"{ctx0}: 顶层必须是事件列表"]
    if slug not in brands:
        errs.append(f"{ctx0}: 品牌 `{slug}` 不在矩阵(先补 matrix.yaml)")
    seen = set()
    for i, e in enumerate(events):
        ctx = f"{ctx0}[{i}]"
        if not isinstance(e, dict):
            errs.append(f"{ctx}: 事件必须是映射")
            continue
        missing = [f for f in REQUIRED if f not in e or e[f] in (None, "", [])]
        if missing:
            errs.append(f"{ctx}: 缺字段 {', '.join(missing)}")
            continue
        d = as_date(e["date"])
        if d is None:
            errs.append(f"{ctx}: date `{e['date']}` 不是合法 YYYY-MM-DD")
        elif d > today:
            errs.append(f"{ctx}: date {d} 在未来")
        eid = str(e["id"])
        if d and not re.fullmatch(rf"{d.isoformat()}-{re.escape(slug)}-\d{{3}}", eid):
            errs.append(f"{ctx}: id `{eid}` 应为 <date>-{slug}-NNN 且日期与 date 一致")
        if eid in seen:
            errs.append(f"{ctx}: id `{eid}` 重复")
        seen.add(eid)
        if e["dim"] not in DIMS:
            errs.append(f"{ctx}: dim `{e['dim']}` 非法(W1..W9)")
        elif slug in brands and isinstance(brands[slug], dict) \
                and brands[slug].get(e["dim"]) == "off":
            errs.append(f"{ctx}: dim {e['dim']} 在 `{slug}` 上为 off(空维度诚实留空,不许填事件)")
        if e["severity"] not in SEVERITIES:
            errs.append(f"{ctx}: severity `{e['severity']}` 非法(P0..P3)")
        if e["direction"] not in DIRECTIONS:
            errs.append(f"{ctx}: direction `{e['direction']}` 非法(pos/neg/neutral/mixed)")
        if e["direction_by"] != "model-judged":
            errs.append(f"{ctx}: direction_by 必须为 model-judged(判断字段不得伪装成事实)")
        q = str(e["quote"])
        if len(q) > QUOTE_MAX:
            errs.append(f"{ctx}: quote 超 {QUOTE_MAX} 字({len(q)})——只存短逐字引用 + 链接原文")
        if e.get("quote_type") not in (None, *QUOTE_TYPES):
            errs.append(f"{ctx}: quote_type `{e['quote_type']}` 非法(title/body)")
        if not str(e["url"]).startswith(("http://", "https://")):
            errs.append(f"{ctx}: url 必须是 http(s) 绝对地址")
        if not FETCHED_RE.match(str(e["fetched_at"])):
            errs.append(f"{ctx}: fetched_at `{e['fetched_at']}` 应为 ISO UTC(YYYY-MM-DDTHH:MM[:SS]Z)")
        lm = e["lens_map"]
        if not isinstance(lm, list) or not lm or not set(lm) <= LENSES:
            errs.append(f"{ctx}: lens_map 必须是非空列表且 ⊆ {sorted(LENSES)}")
    return errs


def main():
    if not os.path.isdir(WATCH_DIR):
        print("validate_watch: watch/ 不存在 —— 功能未启用,通过。")
        return 0
    whitelist = read_whitelist()
    if not os.path.isfile(MATRIX):
        print("validate_watch: ❌ watch/ 存在但缺 matrix.yaml(适用性矩阵是数据层前置)", file=sys.stderr)
        return 1
    matrix = yaml.safe_load(open(MATRIX, encoding="utf-8"))
    errs, brands = validate_matrix(matrix, whitelist)

    today = datetime.date.today()
    n_events = 0
    files = sorted(glob.glob(os.path.join(WATCH_DIR, "*", "events.yaml")))
    for path in files:
        slug = os.path.basename(os.path.dirname(path))
        try:
            events = yaml.safe_load(open(path, encoding="utf-8"))
        except yaml.YAMLError as ex:
            errs.append(f"watch/{slug}/events.yaml: YAML 解析失败 —— {ex}")
            continue
        errs.extend(validate_events(slug, events, brands, today))
        n_events += len(events) if isinstance(events, list) else 0

    if errs:
        print("validate_watch: ❌ 发现违规:", file=sys.stderr)
        for e in errs:
            print("  - " + e, file=sys.stderr)
        return 1
    print(f"validate_watch: ✅ 通过 —— 矩阵 {len(brands)} 品牌对齐白名单,"
          f"{len(files)} 个事件文件 / {n_events} 条事件全部合规。")
    return 0


# ------------------------------------------------------------- selftest ----

def selftest():
    """证明每类违规都会被抓(和 quality_check --selftest 同一哲学:门禁要自证有牙)。"""
    today = datetime.date.today()
    brands = {"demo": {f"W{i}": ("off" if i == 2 else "on") for i in range(1, 10)}}

    def ok_event(**over):
        e = {
            "id": "2026-01-02-demo-001", "date": datetime.date(2026, 1, 2),
            "dim": "W3", "severity": "P1", "direction": "neg",
            "direction_by": "model-judged", "title": "t", "quote": "q",
            "url": "https://example.com/x", "fetched_at": "2026-01-02T00:00:00Z",
            "lens_map": ["signal"],
        }
        e.update(over)
        return e

    cases = [
        ("合法事件应通过", [ok_event()], 0),
        ("缺 url 必抓", [{k: v for k, v in ok_event().items() if k != "url"}], 1),
        ("quote 超长必抓", [ok_event(quote="长" * 101)], 1),
        ("direction_by 非 model-judged 必抓", [ok_event(direction_by="human")], 1),
        ("dim=off 填事件必抓", [ok_event(dim="W2", id="2026-01-02-demo-002")], 1),
        ("未来日期必抓", [ok_event(date=today + datetime.timedelta(days=9),
                                   id=f"{(today + datetime.timedelta(days=9)).isoformat()}-demo-003")], 1),
        ("id 与 date 不一致必抓", [ok_event(id="2025-12-31-demo-004")], 1),
        ("id 重复必抓", [ok_event(), ok_event()], 1),
        ("severity 非法必抓", [ok_event(severity="P9")], 1),
        ("lens_map 越界必抓", [ok_event(lens_map=["signal", "vibe"])], 1),
        ("url 非 http 必抓", [ok_event(url="ftp://x")], 1),
    ]
    failed = []
    for name, events, expect_min in cases:
        errs = validate_events("demo", events, brands, today)
        got = len(errs)
        if (expect_min == 0 and got != 0) or (expect_min > 0 and got < expect_min):
            failed.append(f"{name}: 期望 {'0' if expect_min == 0 else '≥1'} 条违规,实得 {got} —— {errs}")

    m_errs, _ = validate_matrix({"brands": {"ghost": {f"W{i}": "on" for i in range(1, 10)}}}, ["real"])
    if len(m_errs) < 2:  # ghost 不在白名单 + real 缺矩阵行
        failed.append(f"矩阵对齐失衡应抓 2 类,实得 {m_errs}")

    if failed:
        print("validate_watch --selftest: ❌", file=sys.stderr)
        for f in failed:
            print("  - " + f, file=sys.stderr)
        return 1
    print(f"validate_watch --selftest: ✅ {len(cases) + 1} 组断言全部通过(门禁有牙)。")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv[1:] else main())
