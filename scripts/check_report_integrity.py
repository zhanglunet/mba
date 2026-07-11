#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_report_integrity.py — F1:报告"数字自洽"守卫。

`validate_report.py` 只查结构(章节/标题在不在);本脚本查**算术**:published 报告的
Score Matrix 里,分数矩阵必须自洽——否则一个 metric 品牌审计工具的招牌数字就是错的。

对每份 `published/reports/*/report.md` 的 `## Score Matrix` 表校验:
  A. 每个维度行:声明的 Mean == 该行 N 位评委单元格的均值(四舍五入到 1 位,容差 0.05)。
  B. Judge Total 行:每位评委的总分 == 其所在列 5 个维度单元格之和。
  C. Score Total / 总分 == 全表单元格之和 == 各评委总分之和。
  D. Normalized / 归一化 == Score Total / 满分 × 10(容差 0.05)。

设计原则(和 firewall/consistency 一样**不误伤**):能可靠解析到的才校验,解析不出的
**跳过并标注**(不判负);只有**明确的算术对不上**才 FAIL。单元格含 v2 delta 标注
(如 `7→6 ↓1` / `9 ↔` / `8↓1`)时取**当前值**(有 `→` 取箭头后的数,否则取首个整数)。

退出码:任一报告有明确算术错误 → 1;否则 0。
用法:`check_report_integrity.py [report.md ...]`(默认全部 published 报告)。
"""
import os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOL = 0.05  # 均值/归一化四舍五入容差

def _clean(s):
    return s.replace("*", "").replace("`", "").strip()

def cell_int(s):
    """从单元格取当前整数分:有 `→`/`->` 取箭头后的数;否则取首个整数。"""
    s = _clean(s)
    if not s or s in {"—", "-", "–", "N/A"}:
        return None
    for arrow in ("→", "->", "➜", "⟶"):
        if arrow in s:
            s = s.split(arrow)[-1]
            break
    m = re.search(r"-?\d+", s)
    return int(m.group()) if m else None

def cell_float(s):
    s = _clean(s)
    if not s or s in {"—", "-", "–", "N/A"}:
        return None
    for arrow in ("→", "->", "➜", "⟶"):
        if arrow in s:
            s = s.split(arrow)[-1]
            break
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None

def matrix_section(md):
    m = re.search(r"^##\s+.*(?:Score Matrix|评分矩阵).*$", md, re.M | re.I)
    if not m:
        return None
    start = m.end()
    nxt = re.search(r"^##\s+", md[start:], re.M)
    return md[start:start + nxt.start()] if nxt else md[start:]

def parse_rows(section):
    rows = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) or c == "" for c in cells):
            continue  # 分隔行
        rows.append(cells)
    return rows

def _is_summary_row(label):
    """任何汇总行(Total / 总 / 纯 Mean 行)——都不是维度行。"""
    n = _clean(label).lower()
    return "total" in n or "总" in n or n in {"mean", "均值"}

def _is_primary_total_row(label):
    """评委总分(原始 /50)行,用于 B 校验——排除 /10 归一化那一行。"""
    n = _clean(label).lower()
    return ("total" in n or "总" in n) and "/10" not in n

def check_report(path):
    rel = os.path.relpath(path, ROOT)
    md = open(path, encoding="utf-8").read()
    sec = matrix_section(md)
    problems, skips = [], []
    if not sec:
        return rel, [], ["无 Score Matrix 段(跳过)"]
    rows = parse_rows(sec)
    if len(rows) < 3:
        return rel, [], ["Score Matrix 表无法解析(跳过)"]

    header = rows[0]
    # 判定列角色:0=Lens;含 mean/均=均值列;σ/std/Δ/空=忽略;其余=评委列
    judge_cols, mean_col = [], None
    for i, h in enumerate(header):
        if i == 0:
            continue
        nh = _clean(h).lower()
        if "mean" in nh or "均值" in nh:
            if mean_col is None:
                mean_col = i
            continue
        if nh in {"σ", "std", "标准差", ""} or "σ" in h or "δ" in nh or "/10" in nh:
            continue
        judge_cols.append(i)
    if len(judge_cols) < 3:
        return rel, [], [f"评委列解析异常(判到 {len(judge_cols)} 列,跳过)"]

    # 数据行(维度) vs 总分行
    lens_rows, total_row = [], None
    for r in rows[1:]:
        if not r:
            continue
        if _is_summary_row(r[0]):
            # 汇总行:不算维度;第一条原始 /50 总分行留作 B 校验
            if total_row is None and _is_primary_total_row(r[0]):
                total_row = r
            continue
        # 维度行:该行评委单元格都能取到整数
        vals = [cell_int(r[c]) if c < len(r) else None for c in judge_cols]
        if all(v is not None for v in vals):
            lens_rows.append((r, vals))

    if len(lens_rows) < 3:
        return rel, [], [f"可解析维度行不足({len(lens_rows)},跳过)"]

    # A. 每维度 Mean == 评委均值
    if mean_col is not None:
        for r, vals in lens_rows:
            stated = cell_float(r[mean_col]) if mean_col < len(r) else None
            if stated is None:
                skips.append(f"维度 {_clean(r[0])[:16]} 均值列空(跳过均值校验)")
                continue
            computed = round(sum(vals) / len(vals), 2)
            if abs(stated - computed) > TOL + 0.005:
                problems.append(f"维度「{_clean(r[0])[:20]}」Mean 声明 {stated} != 评委均值 {computed}({'+'.join(map(str,vals))})/{len(vals)}")
    else:
        skips.append("无 Mean 列(跳过维度均值校验)")

    # B. Judge Total == 各评委列之和
    col_sums = {c: sum(vals[j] for _, vals in lens_rows for j in [judge_cols.index(c)]) for c in judge_cols}
    grand_from_cells = sum(col_sums.values())
    if total_row is not None:
        for c in judge_cols:
            stated = cell_int(total_row[c]) if c < len(total_row) else None
            if stated is None:
                skips.append(f"评委列 {header[c][:10]} 总分空(跳过)")
                continue
            if stated != col_sums[c]:
                problems.append(f"评委「{_clean(header[c])[:12]}」Total 声明 {stated} != 列和 {col_sums[c]}")
    else:
        skips.append("无 Judge Total 行(跳过评委总分校验)")

    # C. Score Total == 全表之和
    mtot = re.search(r"(?:Score Total|总分)[^\d]*([\d]+)\s*/\s*(\d+)", sec, re.I)
    max_pts = None
    if mtot:
        stated_total = int(mtot.group(1)); max_pts = int(mtot.group(2))
        if stated_total != grand_from_cells:
            problems.append(f"Score Total 声明 {stated_total} != 全表单元格之和 {grand_from_cells}")
    else:
        skips.append("未找到 'Score Total/总分 N / M' 行(跳过总分校验)")

    # D. Normalized == total / max * 10
    mnorm = re.search(r"(?:Normalized|归一化)[^\d]*([\d]+(?:\.\d+)?)\s*/\s*10", sec, re.I)
    if mnorm and max_pts:
        stated_norm = float(mnorm.group(1))
        computed_norm = round(grand_from_cells / max_pts * 10, 2)
        if abs(stated_norm - computed_norm) > TOL + 0.005:
            problems.append(f"Normalized 声明 {stated_norm} != {grand_from_cells}/{max_pts}×10 = {computed_norm}")
    elif not mnorm:
        skips.append("未找到 Normalized/归一化 行(跳过)")

    return rel, problems, skips

def main(argv):
    targets = argv or sorted(glob.glob(os.path.join(ROOT, "published", "reports", "*", "report.md")))
    print("报告数字自洽守卫(check_report_integrity.py)")
    print("=" * 64)
    hard = 0
    for path in targets:
        rel, problems, skips = check_report(path)
        if problems:
            hard += 1
            print(f"❌ FAIL  {rel}")
            for p in problems:
                print(f"         · {p}")
        else:
            note = f"  ({len(skips)} 跳过)" if skips else ""
            print(f"✅ OK    {rel}{note}")
        for s in skips:
            print(f"         ~ {s}")
    print("=" * 64)
    if hard:
        print(f"❌ {hard} 份报告存在明确算术不一致。")
        return 1
    print("✅ 全部报告 Score Matrix 数字自洽。")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
