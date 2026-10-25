#!/usr/bin/env python3
"""消费者评委输出适配层：Consumer Answers 答卷 → 三态 findings.json 投影
（PRD-178/T3，trend #892）。

PRD-178/T1 §六.1 的落地：消费者评委（role=consumer，C1–C5 题组）的结论逐条进
findings.json，`lens` 使用 PRD-177/T1 已预留的 `c1`–`c5` 枚举（题号 Cn ↔ lens cn
咬合）。本工具是 scripts/adapt_findings.py（PRD-177/T2，专家评委）的消费者域姊妹
实现——**不改动专家适配层**，投影纪律与其同款：

  - **默认落 needs_validation，绝不默认 confirmed**——evidence 不足时宁可三态
    降级，不造假确认；confirmed / rejected 由评委或下一轮复核判定（T1 §2.3）；
  - 每个答卷数据行至多一条 finding：claim 取 Key phrase（缺则取 Answer），
    evidence.quote 取 Why 原文（缺则取 Answer，逐字子串，永远能在源文件命中）；
  - C2 购买意愿是消费者域唯一数值分：按 T1 §六.1「C2 低分主因」只投影答案
    ≤5（0–10 中位以下）的数据行；>5 视为无复核事项，跳过并记 note；
  - `## One-liner verdict` / `## Would I share it?` 不入 findings（C1–C5 已覆盖，
    重复计数会污染三态对账），记 note；
  - evidence kind 沿 PRD-177 schema 现有枚举：本工具只引答卷原文（kind=review）；
    scenario.md（人设语料）引用为 kind=research（perspectives 语料，见 fixture
    README 的 T3 定稿说明），由人工/复核在判定 confirmed 时补充。

确定性：无随机、无时间戳、无未排序字典遍历；同一输入重复运行输出逐字节一致。
本工具不判三态升级，不把消费者结论与专家分数换算、平均。

用法（在仓库根）：
  python3 scripts/adapt_consumer_findings.py \\
    published/reports/<brand>/versions/v1/reviews/<consumer-slug>.md [更多 reviews...]
  python3 scripts/adapt_consumer_findings.py <reviews...> -o <findings.json> \\
    [--panel consumer-mixed]
  python3 scripts/adapt_consumer_findings.py <reviews...> --root <repo-root>

reviews 路径需包含
`published/reports/<brand>/versions/<v>/reviews/<slug>.md` 段（从中推导 brand_slug /
judge_slug / report_ref）；不匹配时用 --brand-slug / --report-ref 显式给出。
输出默认 stdout（-o 落盘）。退出码：0 = 已产出；2 = 用法 / IO 错误。
产出文件建议随后跑 `python3 scripts/validate_findings.py <findings.json>` 验收
（该校验器属 PRD-177/T2，合入后即可全量 R-1…R-7 验收）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = "prd-177-v1"
CLAIM_MAX_CHARS = 80
DEFAULT_PANEL = "consumer-mixed"
# C2 低分阈值（0–10 中位以下）；T1 §六.1「C2 低分主因」的 T3 落地口径，可随
# 评审复盘调整，调整不影响 schema（只影响适配层投影范围）。
C2_LOW_MAX = 5

REVIEWS_RE = re.compile(
    r"published/reports/([A-Za-z0-9][A-Za-z0-9_-]*)/versions/([A-Za-z0-9][A-Za-z0-9_-]*)"
    r"/reviews/([A-Za-z0-9][A-Za-z0-9_-]*)\.md"
)
JUDGE_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$|^lead$")
QUESTION_RE = re.compile(r"^C([1-5])\b")

DEFAULT_UNRESOLVED = (
    "适配层默认降级：该结论仅引用消费者评委落笔原文单条依据，未满足 confirmed 进入"
    "条件（evidence ≥2 条且覆盖 ≥2 种 kind，或含 synthesis 逐字引用）；消费者结论是"
    "模拟人设视角信号、不代表市场调研，需评委复核或下一轮 synthesis 交叉验证后定三态。"
)


def clean_cell(cell: str) -> str:
    return cell.replace("**", "").strip().strip("\"'“”「」").strip()


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


def adapt_review(md: str, reviews_rel: str, judge_slug: str
                 ) -> tuple[list[dict], list[str], list[str]]:
    """投影单个消费者答卷。返回 (findings, notes, skips)。确定性。"""
    lines = md.splitlines()
    findings: list[dict] = []
    notes: list[str] = []
    skips: list[str] = []
    seq = 0

    def emit(lens: str | None, claim_src: str, quote: str, line_no: int) -> None:
        nonlocal seq
        seq += 1
        claim = clean_cell(claim_src)
        if len(claim) > CLAIM_MAX_CHARS:
            claim = claim[:CLAIM_MAX_CHARS]
            notes.append(f"{judge_slug} L{line_no}: claim 超 {CLAIM_MAX_CHARS} 字，"
                         "已截断（逐字原文见 evidence.quote）")
        findings.append({
            "id": f"F-{judge_slug}-{seq:03d}",
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

    for title, start, end in split_sections(md):
        if not title.startswith("Consumer Answers"):
            if title.startswith(("One-liner verdict", "Would I share it")):
                notes.append(f"{judge_slug}: 「{title}」为总结性表态，C1–C5 已覆盖，"
                             "不入 findings（避免重复计数）")
            continue
        body = lines[start:end]
        for offset, raw in enumerate(body):
            line_no = start + offset + 1
            stripped = raw.strip()
            if not stripped.startswith("|"):
                continue
            cells = stripped.strip("|").split("|")
            if all(re.fullmatch(r":?-+:?", c.strip()) for c in cells):
                continue  # 分隔行
            head = cells[0].strip().lower()
            if head == "question" or head.startswith("question"):
                continue  # 表头行
            if len(cells) < 4:
                skips.append(f"{judge_slug} L{line_no}: 数据行少于 4 列"
                             "（Question/Answer/Key phrase/Why），跳过")
                continue
            q_cell, answer, key_phrase, why = (cells[0].strip(), cells[1].strip(),
                                               cells[2].strip(), cells[3].strip())
            m = QUESTION_RE.match(q_cell)
            if m:
                lens = f"c{m.group(1)}"
            else:
                lens = None
                notes.append(f"{judge_slug} L{line_no}: 题号 {q_cell!r} 不在 C1–C5，"
                             "lens 落 null（跨口径）")
            if lens == "c2":
                num = re.search(r"\d+", answer)
                if num and int(num.group()) > C2_LOW_MAX:
                    notes.append(f"{judge_slug} L{line_no}: C2 购买意愿={num.group()}"
                                 f"（>{C2_LOW_MAX} 非低分），按 T1 §六.1 只投影低分主因，"
                                 "跳过")
                    continue
                if not num:
                    notes.append(f"{judge_slug} L{line_no}: C2 答案无数值（{answer!r}），"
                                 "保守投影")
            claim_src = key_phrase or answer
            quote_src = why or answer
            if not quote_src:
                skips.append(f"{judge_slug} L{line_no}: Answer/Why 全空，"
                             "无法构成合法 evidence，跳过")
                continue
            emit(lens, claim_src, quote_src, line_no)
    return findings, notes, skips


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="消费者答卷 → 三态 findings.json 投影（PRD-178/T3，lens=c1–c5，"
                    "默认 needs_validation）")
    parser.add_argument("reviews_md", nargs="+", help="消费者答卷 markdown 路径（1 个以上）")
    parser.add_argument("--root", type=Path, default=None,
                        help="仓库根（默认本脚本所在仓库根）")
    parser.add_argument("--panel", default=DEFAULT_PANEL,
                        help=f"panel 名（写入 findings.panel，默认 {DEFAULT_PANEL}）")
    parser.add_argument("--brand-slug", default=None,
                        help="品牌 slug（默认从首个路径的 published/reports 段推导）")
    parser.add_argument("--report-ref", default=None,
                        help="report.md 仓库相对路径（默认从首个路径推导）")
    parser.add_argument("-o", "--out", type=Path, default=None,
                        help="输出文件（默认 stdout）")
    args = parser.parse_args(argv)

    root = (args.root or Path(__file__).resolve().parents[1]).resolve()
    brand_slug = args.brand_slug
    report_ref = args.report_ref
    jobs: list[tuple[str, str, str]] = []  # (abs_path, reviews_rel, judge_slug)
    for raw in args.reviews_md:
        p = Path(raw)
        if not p.is_absolute():
            p = root / p
        if not p.is_file():
            print(f"ERROR: 文件不存在: {p}", file=sys.stderr)
            return 2
        try:
            rel = p.resolve().relative_to(root).as_posix()
        except ValueError:
            print(f"ERROR: reviews 路径不在 --root 下: {p}；"
                  "请用 --root 指到仓库根，或显式给 --brand-slug / --report-ref",
                  file=sys.stderr)
            return 2
        m = REVIEWS_RE.search(rel)
        if m:
            brand_slug = brand_slug or m.group(1)
            report_ref = report_ref or (
                "published/reports/%s/versions/%s/report.md" % (m.group(1), m.group(2)))
        judge_slug = m.group(3) if m else p.stem
        if not JUDGE_SLUG_RE.fullmatch(judge_slug):
            print(f"ERROR: judge_slug 非法（须为小写字母/数字/连字符或 lead）: "
                  f"{judge_slug!r}", file=sys.stderr)
            return 2
        jobs.append((p, rel, judge_slug))

    if not (brand_slug and report_ref):
        print("ERROR: 无法推导 brand_slug / report_ref（路径中无 "
              "published/reports/<brand>/versions/<v>/reviews/<slug>.md 段）；"
              "请显式给 --brand-slug / --report-ref", file=sys.stderr)
        return 2

    findings: list[dict] = []
    notes: list[str] = []
    skips: list[str] = []
    for p, rel, judge_slug in jobs:  # 按 CLI 顺序，确定性
        try:
            md = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            print(f"ERROR: 无法读取文件 {p}: {e}", file=sys.stderr)
            return 2
        fs, ns, ss = adapt_review(md, rel, judge_slug)
        findings.extend(fs)
        notes.extend(ns)
        skips.extend(ss)

    doc = {
        "findings_version": SCHEMA_VERSION,
        "brand_slug": brand_slug,
        "panel": args.panel,
        "report_ref": report_ref,
        "counts": {
            "confirmed": 0,
            "needs_validation": len(findings),
            "rejected": 0,
        },
        "findings": findings,
    }
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
        target = str(args.out)
    else:
        sys.stdout.write(payload)
        target = None

    # 人类可读摘要走 stderr（stdout 只载 JSON，方便管道）
    print(f"== adapt_consumer_findings ({SCHEMA_VERSION}) ==", file=sys.stderr)
    print(f"输入: {len(jobs)} 份答卷（{', '.join(j[2] for j in jobs)}）", file=sys.stderr)
    print(f"投影: {len(doc['findings'])} 条 findings（全部 needs_validation，"
          f"confirmed=0 / rejected=0——适配层不判三态升级；C2 只投影 ≤{C2_LOW_MAX} 低分）",
          file=sys.stderr)
    for n in notes:
        print(f"note: {n}", file=sys.stderr)
    for s in skips:
        print(f"skip: {s}", file=sys.stderr)
    if target is not None:
        print(f"落盘: {target}", file=sys.stderr)
        print("下一步: python3 scripts/validate_findings.py "
              f"{target}（PRD-177/T2 校验器合入后）", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
