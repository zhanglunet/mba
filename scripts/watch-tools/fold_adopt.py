#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fold_adopt.py — 把前台 triage「提 PR」产生的暂存文件折进正式事件流。

前台 triage 页(site/watch/triage.html)的「提 PR」按钮,用 GitHub 预填新文件深链创建
`watch/_adopt/<date>-triage.yaml`:一个**扁平事件列表**,每条带 `slug:`(标明入哪个品牌)。
本脚本把这些暂存事件**按 slug 追加进 `watch/<slug>/events.yaml`**(文本追加,保留原文件注释/格式)、
**重算 id 尾号防撞号**,然后删掉暂存文件。运行后跑 validate_watch 即可。

反捏造边界不变:标题/日期/URL 来自源 feed(triage 页原样带过来);dim/severity/direction/lens
是人工在 triage 页判定的;本脚本只做**搬运 + 重编号**,不改任何字段值、不打分。

用法:
  python3 scripts/watch-tools/fold_adopt.py            # 折叠所有 watch/_adopt/*.yaml
  python3 scripts/watch-tools/fold_adopt.py --check    # 只校验暂存文件合法(不写),CI 用
  python3 scripts/watch-tools/fold_adopt.py --selftest # 自测
退出码:成功 0;暂存文件非法(缺字段/slug 未发布/无未处理项)1。
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WATCH = os.path.join(ROOT, "watch")
ADOPT = os.path.join(WATCH, "_adopt")

try:
    import yaml
except ImportError:
    print("fold_adopt: 需要 PyYAML(pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

REQUIRED = ["slug", "date", "dim", "severity", "direction", "title", "quote", "url", "lens_map"]
DIMS = {f"W{i}" for i in range(1, 10)}
SEVS = {"P0", "P1", "P2", "P3"}
DIRS = {"pos", "neg", "neutral", "mixed"}
LENSES = {"origin", "category", "leverage", "identity", "signal"}


def _published_slugs():
    path = os.path.join(ROOT, "site", "published-reports.txt")
    out = set()
    if os.path.exists(path):
        for ln in open(path, encoding="utf-8"):
            s = ln.strip()
            if s and not s.startswith("#"):
                out.add(s)
    return out


def _max_seq(slug):
    """该品牌 events.yaml 已用 id 的最大 NNN 尾号(重编号基准)。"""
    path = os.path.join(WATCH, slug, "events.yaml")
    mx = 0
    if os.path.exists(path):
        for e in (yaml.safe_load(open(path, encoding="utf-8")) or []):
            if isinstance(e, dict) and e.get("id"):
                m = re.search(r"-(\d+)$", str(e["id"]))
                if m:
                    mx = max(mx, int(m.group(1)))
    return mx


def _yesc(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def render_event(ev, eid):
    lens = ev.get("lens_map") or ["signal"]
    if isinstance(lens, str):
        lens = [lens]
    return (
        f"- id: {eid}\n"
        f"  date: {ev['date']}\n"
        f"  dim: {ev['dim']}\n"
        f"  severity: {ev['severity']}\n"
        f"  direction: {ev['direction']}\n"
        f"  direction_by: {ev.get('direction_by', 'model-judged')}\n"
        f"  title: \"{_yesc(ev['title'])}\"\n"
        f"  quote: \"{_yesc(ev['quote'])}\"\n"
        f"  quote_type: {ev.get('quote_type', 'title')}\n"
        f"  url: {ev['url']}\n"
        f"  fetched_at: \"{ev.get('fetched_at', '')}\"\n"
        f"  lens_map: [{', '.join(lens)}]\n"
        f"  source_type: {ev.get('source_type', 'media')}\n"
        f"  note: \"{_yesc(ev.get('note', '前台 triage 采纳;标题/日期/URL 取自源 feed,判断字段人工定。'))}\"\n"
    )


def validate_adopt(events, published, ctx):
    """校验一个暂存文件的事件列表;返回错误清单。"""
    errs = []
    for i, ev in enumerate(events):
        if not isinstance(ev, dict):
            errs.append(f"{ctx}[{i}]: 不是映射")
            continue
        for k in REQUIRED:
            if not ev.get(k):
                errs.append(f"{ctx}[{i}]: 缺字段 `{k}`")
        slug = ev.get("slug")
        if slug and published and slug not in published:
            errs.append(f"{ctx}[{i}]: slug `{slug}` 不在已发布白名单")
        if ev.get("dim") and ev["dim"] not in DIMS:
            errs.append(f"{ctx}[{i}]: dim `{ev['dim']}` 非法(W1..W9)")
        if ev.get("severity") and ev["severity"] not in SEVS:
            errs.append(f"{ctx}[{i}]: severity `{ev['severity']}` 非法(P0..P3)")
        if ev.get("direction") and ev["direction"] not in DIRS:
            errs.append(f"{ctx}[{i}]: direction `{ev['direction']}` 非法")
        lm = ev.get("lens_map") or []
        if isinstance(lm, str):
            lm = [lm]
        for l in lm:
            if l not in LENSES:
                errs.append(f"{ctx}[{i}]: lens `{l}` 非法")
    return errs


def load_adopt_files():
    files = sorted(glob.glob(os.path.join(ADOPT, "*.yaml"))) + sorted(glob.glob(os.path.join(ADOPT, "*.yml")))
    out = []
    for f in files:
        try:
            doc = yaml.safe_load(open(f, encoding="utf-8"))
        except Exception as e:
            out.append((f, None, [f"{os.path.basename(f)}: YAML 解析失败:{e}"]))
            continue
        events = doc if isinstance(doc, list) else (doc.get("events") if isinstance(doc, dict) else None)
        if not isinstance(events, list) or not events:
            out.append((f, None, [f"{os.path.basename(f)}: 期望非空事件列表(或 {{events: [...]}})"]))
            continue
        out.append((f, events, []))
    return out


def main(argv):
    check = "--check" in argv
    if "--selftest" in argv:
        return _selftest()
    published = _published_slugs()
    batches = load_adopt_files()
    if not batches:
        print("fold_adopt: 无 watch/_adopt/*.yaml,跳过。")
        return 0
    all_errs, total = [], 0
    for f, events, errs in batches:
        rel = os.path.relpath(f, ROOT)
        all_errs += errs
        if events is None:
            continue
        all_errs += validate_adopt(events, published, rel)
        total += len(events)
    if all_errs:
        print("fold_adopt: ❌ 暂存文件校验失败:")
        for e in all_errs:
            print("  -", e)
        return 1
    if check:
        print(f"fold_adopt: ✅ --check 通过 —— {len(batches)} 文件 / {total} 条待折叠事件全部合法。")
        return 0

    # 真折叠:按 slug 追加、重算尾号、删暂存
    seqs, folded = {}, 0
    per_slug_blocks = {}
    for f, events, _ in batches:
        for ev in events:
            slug = ev["slug"]
            if slug not in seqs:
                seqs[slug] = _max_seq(slug)
            seqs[slug] += 1
            eid = f"{ev['date']}-{slug}-{seqs[slug]:03d}"
            per_slug_blocks.setdefault(slug, []).append(render_event(ev, eid))
            folded += 1
    for slug, blocks in sorted(per_slug_blocks.items()):
        path = os.path.join(WATCH, slug, "events.yaml")
        existing = ""
        if os.path.exists(path):
            existing = open(path, encoding="utf-8").read().rstrip("\n")
        header = f"\n\n# ── 前台 triage 采纳折入({len(blocks)} 条)──\n"
        open(path, "w", encoding="utf-8").write(existing + header + "\n".join(blocks) + "\n")
        print(f"fold_adopt: + {len(blocks)} 条 → watch/{slug}/events.yaml")
    for f, _, _ in batches:
        os.remove(f)
        print(f"fold_adopt: 删除暂存 {os.path.relpath(f, ROOT)}")
    print(f"fold_adopt: ✅ 折叠 {folded} 条 / {len(per_slug_blocks)} 品牌。跑 validate_watch.py 复核。")
    return 0


def _selftest():
    import tempfile, textwrap
    ev = {"slug": "spacex", "date": "2026-07-18", "dim": "W5", "severity": "P1",
          "direction": "pos", "title": '他说"上市"了', "quote": "SpaceX IPO",
          "url": "https://x/y", "lens_map": ["signal"]}
    errs = validate_adopt([ev], {"spacex"}, "t")
    assert not errs, errs
    assert validate_adopt([{**ev, "slug": "ghost"}], {"spacex"}, "t"), "should reject unknown slug"
    assert validate_adopt([{**ev, "dim": "W99"}], {"spacex"}, "t"), "should reject bad dim"
    blk = render_event(ev, "2026-07-18-spacex-009")
    assert 'title: "他说\\"上市\\"了"' in blk, blk
    assert yaml.safe_load(blk)[0]["id"] == "2026-07-18-spacex-009"
    print("fold_adopt selftest: ✅ 通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
