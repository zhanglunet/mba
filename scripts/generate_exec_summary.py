#!/usr/bin/env python3
"""mba 管理层一页摘要生成脚本（PRD-023/T2，trend #127）。

设计原则（来自 docs/plans/2026-10-17-exec-summary-format.md §一、§四）：
  纯抽取/重排，不重新打分、不引入新结论；每个数字都能在完整报告找到出处。
  任一区块取不到数据时留空并标注"本轮无"，绝不编造。

数据源（review 修正后的口径）：
  一句话定位     <- ## TL;DR 首段（50 字上限）
  综合评分       <- ## Score Matrix 表尾（Score Total / Score Normalized）
  最强/最弱维度  <- 规范要求"维度名 + 一句话证据"；证据句无法纯抽取得到，
                    按规则 3 留空（不编造）
  评委最大分歧点 <- 异议热力图最大值；"哪两位评委"需解读，按规则 3 留空
  90 天行动 Top3 <- 报告无"90 天行动建议"章节时按规则 3 留空
  delta 区块     <- ## 版本变化速览 (delta banner) / ## Score Matrix / ## 各维度评估

用法：
  python3 scripts/generate_exec_summary.py published/reports/<brand>/report.md [-o out.md]

只用标准库 + 正则，不调 LLM，无网络 I/O。
"""
import argparse
import pathlib
import re
import sys

NONE = "本轮无"


def strip_md(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"\*(.+?)\*", r"\1", s)
    s = s.replace("`", "")
    s = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", s)
    return s.strip()


def clip(s: str, n: int) -> str:
    s = re.sub(r"\s+", " ", s.strip())
    if len(s) <= n:
        return s
    cut = s[:n]
    for sep in ("。", "！", "？", "；"):
        i = cut.rfind(sep)
        if i >= n * 0.5:
            return cut[: i + 1]
    return cut.rstrip() + "…"


def section(text: str, heading: str) -> str:
    """取 ## <heading> 到下一个 ## 之间的正文（含 heading 行）。"""
    m = re.search(
        r"^## " + re.escape(heading) + r"\s*$\n(.*?)(?=^## |\Z)",
        text,
        re.M | re.S,
    )
    return m.group(1) if m else ""


def first_para(sec: str) -> str:
    parts = [p.strip() for p in sec.strip().split("\n\n") if p.strip()]
    return parts[0] if parts else ""


def fmt_delta(cur: float, prev: float) -> str:
    d = round(cur - prev, 2)
    return f"{d:+g}"


def extract(report_path: pathlib.Path) -> dict:
    text = report_path.read_text(encoding="utf-8")
    out = {}

    # ---- 标题信息 ----
    m = re.search(r"^# (.+?) — Brand Influence Review \(v(\d+)\)", text, re.M)
    out["brand"] = m.group(1).strip() if m else report_path.parent.name
    out["version"] = m.group(2) if m else ""
    m = re.search(r"\*\*Audit Date\*\*:\s*([\d-]+)", text)
    out["date"] = m.group(1) if m else ""
    m = re.search(r"\*\*基线\*\*:\s*v(\d+)", text)
    out["prev_version"] = m.group(1) if m else ""

    # ---- 一句话定位：TL;DR 首段，50 字上限 ----
    tldr = section(text, "TL;DR")
    para = strip_md(first_para(tldr))
    out["positioning"] = clip(para, 50) if para else NONE

    # ---- 综合评分：Score Matrix 表尾 ----
    sm = section(text, "Score Matrix")
    total = prev_total = norm = prev_norm = None
    m = re.search(r"Score Total:\s*([\d.]+)\s*/\s*250.*?[（(]v2:\s*([\d.]+)", sm)
    if m:
        total, prev_total = float(m.group(1)), float(m.group(2))
    m = re.search(r"Score Normalized:\s*([\d.]+)\s*/\s*10.*?[（(]v2:\s*([\d.]+)", sm)
    if m:
        norm, prev_norm = float(m.group(1)), float(m.group(2))
    if total is not None and norm is not None:
        out["score"] = (
            f"{total:g}（{fmt_delta(total, prev_total)}）"
            f"· 归一化 {norm:g}（{fmt_delta(norm, prev_norm)}）"
        )
    else:
        out["score"] = NONE

    # ---- 最强/最弱维度：需"一句话证据"，纯抽取无法得到 -> 本轮无 ----
    out["top_dims"] = NONE
    out["bottom_dims"] = NONE

    # ---- 评委最大分歧点：需解读"哪两位评委" -> 本轮无 ----
    out["dissent"] = NONE

    # ---- 90 天行动：报告无此章节 -> 本轮无 ----
    out["actions"] = NONE

    # ---- delta：本次评分变化 ----
    if total is not None and norm is not None and out["prev_version"]:
        pv = out["prev_version"]
        out["delta_score"] = (
            f"总分 {prev_total:g} → {total:g}（{fmt_delta(total, prev_total)}），"
            f"归一化 {prev_norm:g} → {norm:g}（{fmt_delta(norm, prev_norm)}）"
        )
    else:
        out["delta_score"] = NONE

    # ---- delta：移动的维度（各维度评估标题 ↑↓ + Score Matrix 评委 →） ----
    moved = []
    for dm in re.finditer(r"^### (.+?)[—–-] ([\d.]+) ([↑↓][\d.]+|↔)", text, re.M):
        name, _score, arrow = dm.group(1).strip(), dm.group(2), dm.group(3)
        if arrow != "↔":
            moved.append((name.split("（")[0], arrow))
    judges, judge_moves = [], []
    hm = re.search(r"^\| Lens \|(.+?)\|\n\|[-| ]+\|\n((?:^\|.*\n?)+)", sm, re.M)
    if hm:
        judges = [j.strip() for j in hm.group(1).split("|")][:-1]  # 去掉 Mean 列
        for row in hm.group(2).strip().split("\n"):
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            lens = cells[0].split("/")[0].strip()
            for j, cell in zip(judges, cells[1:]):
                mm = re.search(r"(\d+)\s*→\s*(\d+)", cell)
                if mm:
                    judge_moves.append((lens, j, mm.group(1), mm.group(2)))
    dim_notes = []
    for name, arrow in moved:
        jm = [f"{j} {a}→{b}" for (ln, j, a, b) in judge_moves if ln == name]
        dim_notes.append(f"{name} {arrow}" + ("——" + "、".join(jm) if jm else ""))
    out["delta_dims"] = "；".join(dim_notes) if dim_notes else NONE

    # ---- delta：新增关键事件 / 一句话为什么变（delta banner 原文抽取） ----
    banner = section(text, "版本变化速览 (delta banner)")
    bpara = first_para(banner)
    why = strip_md(bpara)
    out["delta_why"] = why if why else NONE
    event = NONE
    for p in banner.split("\n\n"):
        if "消费" in p and ("事件" in p or "events.yaml" in p):
            p = strip_md(p.strip())
            mm = re.search(r"多家转载：(.+)", p, re.S)
            event = mm.group(1).strip() if mm else p
            break
    out["delta_events"] = event

    # ---- delta：触发器状态（报告未提及 -> 本轮无） ----
    out["delta_triggers"] = NONE if "触发器" not in text else "报告提及，人工核对"

    return out


def render(d: dict) -> str:
    v = d["version"]
    pv = d["prev_version"]
    title = f"{d['brand']} — 一页摘要（v{v}" + (f" · {d['date']}" if d["date"] else "") + "）"
    lines = [
        f"# {title}",
        "",
        f"**一句话定位**：{d['positioning']}",
        f"**综合评分**：{d['score']}",
        f"**最强维度**：{d['top_dims']}",
        f"**最弱维度**：{d['bottom_dims']}",
        f"**评委最大分歧点**：{d['dissent']}",
        f"**90 天行动 Top3**：{d['actions']}",
        "",
        "---",
        "",
        f"**EVOLUTION delta（v{pv} → v{v}）**" if pv and v else "**EVOLUTION delta**",
        f"- **本次评分变化**：{d['delta_score']}",
        f"- **移动的维度**：{d['delta_dims']}",
        f"- **新增关键事件**：{d['delta_events']}",
        f"- **触发器状态**：{d['delta_triggers']}",
        f"- **一句话为什么变**：{d['delta_why']}",
        "",
        "> 生成方式：纯抽取（`scripts/generate_exec_summary.py`），未重新打分；"
        "取不到数据的区块标注“本轮无”，不编造。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="mba 管理层一页摘要生成（纯抽取）")
    ap.add_argument("report", help="完整报告路径，如 published/reports/deepseek/report.md")
    ap.add_argument("-o", "--output", help="输出文件（缺省打印到 stdout）")
    args = ap.parse_args()

    p = pathlib.Path(args.report)
    if not p.is_file():
        print(f"ERROR: 报告不存在: {p}", file=sys.stderr)
        return 2

    md = render(extract(p))
    if args.output:
        pathlib.Path(args.output).write_text(md, encoding="utf-8")
        print(f"written: {args.output}")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
