#!/usr/bin/env python3
"""mba EVOLUTION delta 摘要脚本（PRD-023/T3，trend #128）。

从 `published/reports/<brand>/report.md` 抽取 EVOLUTION delta 版 5 个固定区块
（规范见 docs/plans/2026-10-17-exec-summary-format.md §二，review 修正版）：
  本次评分变化 <- ## Score Matrix 表尾（Score Total / Score Normalized，v2 对比数）
  移动的维度   <- ## 各维度评估标题（↑↓）+ Score Matrix 表"评委 →"（谁推动的）
  新增关键事件 <- ## 版本变化速览 (delta banner)（watch 事件流本轮消费的核心事实）
  触发器状态   <- 报告未提及触发器时按规则 3 标"本轮无"
  一句话为什么变 <- delta banner 原文，不改写

抽取逻辑复用 scripts/generate_exec_summary.py（T2，trend #127）的 extract()，
本脚本只做"delta 区块独立渲染"。

设计原则：纯抽取/重排，不重新打分、不引入新结论；取不到数据的区块
标注"本轮无"，绝不编造。

用法：
  python3 scripts/generate_delta_summary.py published/reports/<brand>/report.md [-o out.md]

只用标准库 + 正则，不调 LLM，无网络 I/O。
"""
import argparse
import importlib.util
import pathlib
import sys


def _load_gen_exec():
    here = pathlib.Path(__file__).resolve().parent
    mod_path = here / "generate_exec_summary.py"
    spec = importlib.util.spec_from_file_location("gen_exec_summary", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def render_delta(d: dict) -> str:
    v = d["version"]
    pv = d["prev_version"]
    header = f"**EVOLUTION delta（v{pv} → v{v}）**" if pv and v else "**EVOLUTION delta**"
    lines = [
        header,
        f"- **本次评分变化**：{d['delta_score']}",
        f"- **移动的维度**：{d['delta_dims']}",
        f"- **新增关键事件**：{d['delta_events']}",
        f"- **触发器状态**：{d['delta_triggers']}",
        f"- **一句话为什么变**：{d['delta_why']}",
        "",
        "> 生成方式：纯抽取（`scripts/generate_delta_summary.py` 复用 "
        "`generate_exec_summary.py` 抽取函数），未重新打分；"
        "取不到数据的区块标注“本轮无”，不编造。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="mba EVOLUTION delta 摘要（纯抽取）")
    ap.add_argument("report", help="完整报告路径，如 published/reports/deepseek/report.md")
    ap.add_argument("-o", "--output", help="输出文件（缺省打印到 stdout）")
    args = ap.parse_args()

    p = pathlib.Path(args.report)
    if not p.is_file():
        print(f"ERROR: 报告不存在: {p}", file=sys.stderr)
        return 2

    gen = _load_gen_exec()
    md = render_delta(gen.extract(p))
    if args.output:
        pathlib.Path(args.output).write_text(md, encoding="utf-8")
        print(f"written: {args.output}")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
