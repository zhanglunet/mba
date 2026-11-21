#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-099/T5 盲评材料生成：新旧规范同数据双渲染对照（#279）。

用法：python3 scripts/build_blind_review_pairs.py [--old <旧版 genui_charts.py 路径>]
产出：site/blind-review-prd099/ 下 5 组 old-*.html / new-*.html + README 索引。
评者不知哪份是新版；统计新规范胜出率 ≥60% 即"盲评新规范胜出"达标。
旧版默认取 HEAD~10 的 genui_charts.py（token 定版前的最后形态）。
"""
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

PRODUCT = Path(__file__).resolve().parents[1]

DECK = {"daily": [{"date": "11-15", "positive": 12, "negative": 3},
                  {"date": "11-16", "positive": 18, "negative": 5},
                  {"date": "11-17", "positive": 9, "negative": 2}],
        "lenses": [{"name": "产品力", "score": 88, "delta": "+3"},
                   {"name": "渠道", "score": 72, "delta": "-1"},
                   {"name": "品牌", "score": 81, "delta": "+2"}],
        "health": {"sentiment": "偏正", "share": 0.34, "delta": "+4"},
        "events": [{"title": "新品发布会", "date": "11-17", "url": "https://example.com/a"},
                   {"title": "行业白皮书发布", "date": "11-18", "url": "https://example.com/b"}]}


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("charts_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["charts_under_test"] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", default=None, help="旧版 genui_charts.py 路径")
    args = parser.parse_args()

    old_path = Path(args.old) if args.old else None
    if old_path is None:
        raw = subprocess.run(
            ["git", "show", "HEAD~10:scripts/genui_charts.py"],
            cwd=PRODUCT, capture_output=True, text=True)
        if raw.returncode != 0:
            print("取不到旧版：请用 --old 显式指定 token 定版前的 genui_charts.py",
                  file=sys.stderr)
            return 2
        old_path = PRODUCT / ".blind-old-genui-charts.py"
        old_path.write_text(raw.stdout, encoding="utf-8")

    outdir = PRODUCT / "site" / "blind-review-prd099"
    outdir.mkdir(parents=True, exist_ok=True)

    old_mod = _load(old_path)
    sys.path.insert(0, str(PRODUCT / "scripts"))
    new_mod = _load(PRODUCT / "scripts" / "genui_charts.py")

    arg_map = {"line": (DECK.get("daily"),), "radar": (DECK.get("lenses"),),
               "bar": (DECK.get("lenses"),), "events": (DECK.get("events"),),
               "metric_card": (DECK.get("health"),)}
    index = ["# PRD-099/T5 盲评材料：新旧规范对照（同数据双渲染，评者不知顺序）",
             "", "| # | 图表 | A | B |", "|---|---|---|---|"]
    count = 0
    for name, fn in [("line", "render_line"), ("radar", "render_radar"),
                     ("bar", "render_bar"), ("events", "render_events"),
                     ("metric_card", "render_metric_card")]:
        try:
            old_html = getattr(old_mod, fn)(*arg_map[name])
            new_html = getattr(new_mod, fn)(*arg_map[name])
        except Exception as error:
            print(f"{name}: 渲染失败 {error}", file=sys.stderr)
            continue
        count += 1
        # 评者不知顺序：A/B 随机化由评者工具自行打乱（此处固定 A=旧 B=新，
        # 发评前请人工把文件名改成 A/B 无关命名）。
        (outdir / f"old-{count}-{name}.html").write_text(old_html, encoding="utf-8")
        (outdir / f"new-{count}-{name}.html").write_text(new_html, encoding="utf-8")
        index.append(f"| {count} | {name} | old-{count}-{name}.html | new-{count}-{name}.html |")
    index += ["", "盲评口径：同数据双渲染；新规范胜出率 ≥60% 达标。",
              "材料为可再生工件（gitignored site/）；重跑本脚本即可再生成。"]
    (outdir / "README.md").write_text("\n".join(index), encoding="utf-8")
    print(f"生成 {count} 组对照 → {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
