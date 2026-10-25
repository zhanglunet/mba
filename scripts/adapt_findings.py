#!/usr/bin/env python3
"""评委输出适配层：reviews/<slug>.md → 三态 findings.json 投影（PRD-177/T2，trend #886）。

PRD-177 风险「评委拒改输出 → 适配层兼容旧格式」的落地（T1 §3.3）：评委原始结论仍是
自然语言 `reviews/<slug>.md`（judge-prompt-template STEP 5 形态），本工具把它**确定性投影**
为 `findings.json`（schema `prd-177-v1`），供校验器（scripts/validate_findings.py R-1…R-7）
与下游消费。findings 是评委结论的机读投影，**不替代** reviews/<slug>.md。

投影纪律（T1 §3.3，一字不差）：
  - `## Scores` 的 Why 段 + `## Verdict` / `## Critical gap` 映射为 finding 候选；
  - **默认落 needs_validation，绝不默认 confirmed**——evidence 不足时宁可三态降级，
    不造假确认；每条附 unresolved_fact（未决事实 = 待复核）；
  - `## Brand action` 不入 findings（是建议不是结论）；
  - evidence 只引评委落笔原文（kind=review，逐字子串），quote 永远能在源文件命中；
  - claim >80 字时截断到 80 字（claim 是结论摘要，逐字原文保留在 evidence.quote）；
  - Why / Tooltip 全空的 Scores 行跳过（无法构成合法 evidence，宁缺勿造）。

确定性：无随机、无时间戳、无未排序字典遍历；同一输入重复运行输出逐字节一致。
本工具不判三态升级（confirmed / rejected 需评委或下一轮复核，见 T1 §2.3）。

用法（在仓库根）：
  python3 scripts/adapt_findings.py published/reports/<brand>/versions/v1/reviews/<slug>.md
  python3 scripts/adapt_findings.py <reviews.md> -o <findings.json> [--panel default]
  python3 scripts/adapt_findings.py <reviews.md> --root <repo-root>   # 测试 fixture 用

reviews 路径需匹配 `published/reports/<brand>/versions/<v>/reviews/<slug>.md`（从中推导
brand_slug / judge_slug / report_ref）；不匹配时用 --brand-slug / --report-ref / --judge-slug
显式给出。输出默认 stdout（-o 落盘）。退出码：0 = 已产出；2 = 用法 / IO 错误。
产出文件建议随后跑 `python3 scripts/validate_findings.py <findings.json>` 验收。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = "prd-177-v1"
CLAIM_MAX_CHARS = 80
DEFAULT_UNRESOLVED = (
    "适配层默认降级：该结论仅引用评委落笔原文单条依据，未满足 confirmed 进入条件"
    "（evidence ≥2 条且覆盖 ≥2 种 kind，或含 synthesis 逐字引用），"
    "需评委复核或下一轮 synthesis 交叉验证后定三态。"
)

REVIEWS_RE = re.compile(
    r"^published/reports/([A-Za-z0-9][A-Za-z0-9_-]*)/versions/([A-Za-z0-9][A-Za-z0-9_-]*)"
    r"/reviews/([A-Za-z0-9][A-Za-z0-9_-]*)\.md$"
)
JUDGE_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$|^lead$")

# reviews Scores 表 Lens 列 → findings lens 枚举（Score Matrix 行短名，T1 §2.2）。
# 取首段小写匹配；中英两种落笔都认；未识别 → null（跨口径结论）。
LENS_MAP = {
    "origin": "origin", "起源叙事": "origin",
    "category": "category", "品类定义": "category",
    "leverage": "leverage", "杠杆点": "leverage",
    "identity": "identity", "身份系统": "identity",
    "real-world": "signal", "real world": "signal", "signal": "signal", "真实信号": "signal",
}


def map_lens(label: str) -> str | None:
    head = re.split(r"[\s/（(]", label.strip(), maxsplit=1)[0].strip().lower()
    if head in LENS_MAP:
        return LENS_MAP[head]
    for k, val in LENS_MAP.items():
        if k in label.lower():
            return val
    return None


def split_sections(md: str) -> list[tuple[str, int, int]]:
    """返回 [(标题, 起始行号 1-based, 结束行号 exclusive)]，H2 驱动，顺序保留。"""
    marks = []
    for n, line in enumerate(md.splitlines(), 1):
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            marks.append((m.group(1).strip(), n))
    out = []
    total = md.count("\n") + 1
    for idx, (title, start) in enumerate(marks):
        end = marks[idx + 1][1] - 1 if idx + 1 < len(marks) else total
        out.append((title, start, end))
    return out


def clean_cell(cell: str) -> str:
    return cell.replace("**", "").strip().strip("\"'“”「」").strip()


def cell_quote(cell: str) -> str:
    """表格单元格的逐字引用：只去首尾空白（保持与源文件逐字可命中）。"""
    return cell.strip()


def section_first_line(lines: list[str]) -> str | None:
    """区段内首个非空行（去 `>` 前缀后的逐字文本）。区段为空返回 None。"""
    for line in lines:
        if not line.strip():
            continue
        return re.sub(r"^>\s?", "", line).strip()
    return None


def adapt(md: str, reviews_rel: str, brand_slug: str, panel: str,
          judge_slug: str, report_ref: str) -> tuple[dict, list[str], list[str]]:
    """投影。返回 (findings_doc, notes, skips)。notes/skips 供 stdout 报告，确定性。"""
    lines = md.splitlines()
    findings: list[dict] = []
    notes: list[str] = []
    skips: list[str] = []
    seq = 0

    def next_id() -> str:
        nonlocal seq
        seq += 1
        return f"F-{judge_slug}-{seq:03d}"

    def emit(lens: str | None, claim_src: str, quote: str, line_no: int,
             where: str) -> None:
        claim = clean_cell(claim_src)
        if len(claim) > CLAIM_MAX_CHARS:
            claim = claim[:CLAIM_MAX_CHARS]
            notes.append(f"{where}: claim 超 {CLAIM_MAX_CHARS} 字，已截断（逐字原文见 evidence.quote）")
        findings.append({
            "id": next_id(),
            "status": "needs_validation",
            "judge_slug": judge_slug,
            "lens": lens,
            "claim": claim,
            "evidence": [{
                "source_ref": f"{reviews_rel}#L{line_no}",
                "quote": quote,
                "kind": "review",
            }],
            "unresolved_fact": DEFAULT_UNRESOLVED,
        })

    sections = split_sections(md)
    scored_rows = 0

    for title, start, end in sections:
        if title.startswith("Scores"):
            body = lines[start:end]  # start 是 ## 行（1-based）→ lines[start] 即表头下一行
            for offset, raw in enumerate(body):
                line_no = start + offset + 1  # lines[start+offset] 的 1-based 行号
                stripped = raw.strip()
                if not stripped.startswith("|"):
                    continue
                cells = [c for c in stripped.strip("|").split("|")]
                if len(cells) < 3:
                    continue
                if all(re.fullmatch(r":?-+:?", c.strip()) for c in cells):
                    continue  # 分隔行
                head = cells[0].strip().lower()
                if head == "lens" or head.startswith("lens "):
                    continue  # 表头行
                scored_rows += 1
                lens_label = cells[0]
                why = cells[-1].strip()
                tooltip = cells[2].strip() if len(cells) >= 4 else ""
                src_text, src_cell = (why, cells[-1]) if why else (tooltip, cells[2])
                if not src_text:
                    skips.append(f"Scores 第 {scored_rows} 数据行（{lens_label.strip()}）: "
                                 f"Why/Tooltip 全空，无法构成合法 evidence，跳过")
                    continue
                lens = map_lens(lens_label)
                if lens is None:
                    notes.append(f"Scores 行 {lens_label.strip()!r}: lens 未识别，落 null（跨口径）")
                emit(lens, src_text, cell_quote(src_cell), line_no, f"Scores 行 {line_no}")
        elif title.startswith("Verdict") or title.lower().startswith("critical gap"):
            where = "Verdict" if title.startswith("Verdict") else "Critical gap"
            body = lines[start:end]
            text = section_first_line(body)
            if not text:
                skips.append(f"{where}: 区段为空，跳过")
                continue
            # 该行在文件中的真实 1-based 行号（区段头往下第一个非空行）
            line_no = None
            for offset, raw in enumerate(body):
                if raw.strip():
                    line_no = start + offset + 1
                    break
            quote = re.sub(r"^>\s?", "", text).strip() or text.strip()
            emit(None, text, quote, line_no, where)
        elif title.startswith("Brand action"):
            notes.append("Brand action 是建议不是结论（T1 §3.3），不入 findings")

    doc = {
        "findings_version": SCHEMA_VERSION,
        "brand_slug": brand_slug,
        "panel": panel,
        "report_ref": report_ref,
        "counts": {
            "confirmed": 0,
            "needs_validation": len(findings),
            "rejected": 0,
        },
        "findings": findings,
    }
    return doc, notes, skips


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="reviews/<slug>.md → 三态 findings.json 投影（PRD-177/T2，默认 needs_validation）")
    parser.add_argument("reviews_md", help="reviews markdown 路径")
    parser.add_argument("--root", type=Path, default=None,
                        help="仓库根（默认本脚本所在仓库根）")
    parser.add_argument("--panel", default="default", help="panel 名（写入 findings.panel）")
    parser.add_argument("--judge-slug", default=None,
                        help="评委 slug（默认从文件名推导；Lead 聚合层用 lead）")
    parser.add_argument("--brand-slug", default=None, help="品牌 slug（默认从路径推导）")
    parser.add_argument("--report-ref", default=None,
                        help="report.md 仓库相对路径（默认从路径推导）")
    parser.add_argument("-o", "--out", type=Path, default=None,
                        help="输出文件（默认 stdout）")
    args = parser.parse_args(argv)

    root = (args.root or Path(__file__).resolve().parents[1]).resolve()
    path = Path(args.reviews_md)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        print(f"ERROR: 文件不存在: {path}", file=sys.stderr)
        return 2
    try:
        md = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        print(f"ERROR: 无法读取文件: {e}", file=sys.stderr)
        return 2

    rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else None
    brand_slug = args.brand_slug
    judge_slug = args.judge_slug
    report_ref = args.report_ref
    if rel and REVIEWS_RE.match(rel):
        m = REVIEWS_RE.match(rel)
        brand_slug = brand_slug or m.group(1)
        report_ref = report_ref or f"published/reports/{m.group(1)}/versions/{m.group(2)}/report.md"
        judge_slug = judge_slug or m.group(3)
    reviews_rel = rel
    if not reviews_rel:
        print("ERROR: reviews 路径不在 --root 下，且未提供推导基准；"
              "请用 --root 指到仓库根，或显式给 --brand-slug / --report-ref", file=sys.stderr)
        return 2
    judge_slug = judge_slug or path.stem
    if not JUDGE_SLUG_RE.fullmatch(judge_slug or ""):
        print(f"ERROR: judge_slug 非法（须为小写字母/数字/连字符或 lead）: {judge_slug!r}；"
              "可用 --judge-slug 显式指定", file=sys.stderr)
        return 2
    if not (brand_slug and report_ref):
        print("ERROR: 无法推导 brand_slug / report_ref（路径不符合 "
              "published/reports/<brand>/versions/<v>/reviews/<slug>.md）；"
              "请显式给 --brand-slug / --report-ref", file=sys.stderr)
        return 2

    doc, notes, skips = adapt(md, reviews_rel, brand_slug, args.panel,
                              judge_slug, report_ref)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
        target = args.out
    else:
        sys.stdout.write(payload)
        target = None

    # 人类可读摘要走 stderr（stdout 只载 JSON，方便管道）
    print(f"== adapt_findings ({SCHEMA_VERSION}) ==", file=sys.stderr)
    print(f"输入: {reviews_rel}", file=sys.stderr)
    print(f"投影: {len(doc['findings'])} 条 findings（全部 needs_validation，"
          f"confirmed=0 / rejected=0——适配层不判三态升级）", file=sys.stderr)
    for n in notes:
        print(f"note: {n}", file=sys.stderr)
    for s in skips:
        print(f"skip: {s}", file=sys.stderr)
    if target is not None:
        print(f"落盘: {target}", file=sys.stderr)
        print("下一步: python3 scripts/validate_findings.py "
              f"{target if target.is_absolute() else target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
