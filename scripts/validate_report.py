#!/usr/bin/env python3
"""
validate_report.py — MBA report.md structural validator.

Checks that a brand report.md meets the required schema:
  - Title heading with version number
  - Score Matrix with 5 lenses and numeric scores
  - Dissent Heatmap section
  - Final Verdict section
  - Legal / Disclaimer section
  - Sources section

Usage:
  python scripts/validate_report.py                        # all in published/reports/
  python scripts/validate_report.py path/to/report.md     # one file
  python scripts/validate_report.py --dir path/to/dir/    # all report.md under dir

Exit code: 0 = all pass, 1 = one or more failures.
"""

import re
import sys
from pathlib import Path

LENS_PATTERNS = [
    r"Origin",
    r"Cat(?:egory)?\.?",
    r"Lev(?:erage)?\.?",
    r"ID|Ident(?:ity)?",
    r"Signal",
]


# Score Matrix heading, bilingual (English canonical + Chinese 评分矩阵)
MATRIX_HEADING = r"(?:Score Matrix|评分矩阵)"


def _check_score_rows(text: str) -> tuple:
    """Return (errors, warnings). errors block CI; warnings are advisory."""
    errors, warnings = [], []
    matrix_m = re.search(
        r"^##\s+" + MATRIX_HEADING + r"(.+?)^##",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not matrix_m:
        return (
            ["Score Matrix / 评分矩阵 section not found or not closed by a following ## heading"],
            warnings,
        )

    block = matrix_m.group(1)

    for pat in LENS_PATTERNS:
        # Use a sentinel split: match the whole row, then grab everything after first |
        row_m = re.search(
            r"^\|[^|]*(?:" + pat + r")[^|]*\|(.*)",
            block,
            re.MULTILINE | re.IGNORECASE,
        )
        if not row_m:
            errors.append(f"  Score Matrix missing lens matching '{pat}'")
            continue
        row_text = row_m.group(row_m.lastindex) or ""
        scores = re.findall(r"(?<!\d)([1-9]|10)(?!\d)", row_text)
        if not scores:
            errors.append(f"  Lens '{pat}' row has no numeric scores 1-10")

    # Total row is advisory. MBA matrices label it variously: 'Total' / 'Judge
    # Total' / 'Score Total' / '总分' / '总计', sometimes with a 'Normalized'
    # line right below. Accept any of these anywhere in the matrix block.
    if not re.search(r"(Total|总分|总计|归一化|Normalized)", block, re.IGNORECASE):
        warnings.append("  Score Matrix has no Total / 总分 row (advisory)")

    return errors, warnings


def validate_file(path: Path) -> tuple:
    """Validate one report.md. Returns (errors, warnings).

    Hard requirements (block CI): an MBA report title, a Score Matrix with all 5
    lenses carrying numeric scores, and a Legal / Disclaimer section.

    Advisory (warn only): Final Verdict, Dissent Heatmap, and Sources — these
    vary across bilingual report formats and some legitimate pipeline outputs
    omit them; they are surfaced but do not fail the build.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"Cannot read file: {e}"], []

    errors, warnings = [], []

    # Hard rules — every published report must satisfy these.
    hard_rules = [
        (
            r"^#\s+.+(?:Brand Influence Review \(v\d+\)|Brand Influence Audit|品牌影响力审计)",
            "Missing MBA report title (e.g. '# {Brand} — Brand Influence Review (v{N})' or 'MBA 品牌影响力审计报告')",
        ),
        (
            r"^##\s+" + MATRIX_HEADING,
            "Missing '## Score Matrix' / '## 评分矩阵' section",
        ),
        (
            r"(Legal|Disclaimer|免责声明)",
            "Missing Legal / Disclaimer / 免责声明 section",
        ),
    ]

    # Advisory rules — surfaced as warnings, do not fail CI. Anchors cover the
    # real MBA section-naming variants: dissent may be a "Dissent Heatmap" or a
    # "最大分歧" / "核心张力" discussion; the verdict may be "Final Verdict",
    # "TL;DR", "Core Insight", "总评", "结论", or the "品牌行动建议" close.
    soft_rules = [
        (
            r"(Dissent Heatmap|异议热力图|最大分歧|核心张力|分歧|张力|Divergence)",
            "No Dissent Heatmap / 异议热力图 / 分歧 section (advisory)",
        ),
        (
            r"(Final Verdict|Final Assessment|Verdict|总评|总结论|总结|Core Insight|TL;?DR|品牌行动|Brand Action|^##[^\n]*结论)",
            "No Final Verdict / TL;DR / 总评 / 结论 section (advisory)",
        ),
        (
            r"^##\s+(?:Sources|来源|参考(?:文献|资料)?)",
            "No '## Sources' / '## 来源' section (advisory) — backfill real public sources when available",
        ),
    ]

    for pattern, message in hard_rules:
        if not re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            errors.append(message)

    for pattern, message in soft_rules:
        if not re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            warnings.append(message)

    matrix_errors, matrix_warnings = _check_score_rows(text)
    errors.extend(matrix_errors)
    warnings.extend(matrix_warnings)

    return errors, warnings


def find_reports(root: Path) -> list:
    return sorted(root.rglob("report.md"))


def main() -> int:
    args = sys.argv[1:]

    if "--dir" in args:
        idx = args.index("--dir")
        targets = find_reports(Path(args[idx + 1]))
    elif args and not args[0].startswith("-"):
        targets = [Path(a) for a in args]
    else:
        repo_root = Path(__file__).resolve().parent.parent
        targets = find_reports(repo_root / "published" / "reports")

    if not targets:
        print("No report.md files found — nothing to validate.")
        return 0

    repo_root = Path(__file__).resolve().parent.parent
    total, failed, warned = len(targets), 0, 0

    for path in targets:
        errs, warns = validate_file(path)
        try:
            rel = path.resolve().relative_to(repo_root)
        except ValueError:
            rel = path
        if errs:
            failed += 1
            print(f"FAIL  {rel}")
            for e in errs:
                print(f"      {e}")
            for w in warns:
                print(f"      warn: {w}")
        elif warns:
            warned += 1
            print(f"ok    {rel}")
            for w in warns:
                print(f"      warn: {w}")
        else:
            print(f"ok    {rel}")

    print(f"\n{total - failed}/{total} passed", end="")
    if warned:
        print(f"  ({warned} with advisory warnings)", end="")
    if failed:
        print(f"  ({failed} failed)")
        return 1
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
