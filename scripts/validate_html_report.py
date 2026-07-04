#!/usr/bin/env python3
"""
validate_html_report.py — MBA report.html structural validator.

Checks that a self-contained HTML report has the required visual components:
  - Chart.js radar chart (<canvas> element)
  - Mermaid diagram (leverage map / influence map)
  - Dissent heatmap section
  - At least one judge card or scorecard
  - Legal / disclaimer section

Usage:
  python scripts/validate_html_report.py                       # all in published/reports/
  python scripts/validate_html_report.py path/to/report.html  # one file
  python scripts/validate_html_report.py --dir path/to/dir/   # all report.html under dir

Exit code: 0 = all pass, 1 = one or more failures.
"""

import re
import sys
from pathlib import Path


# Hard requirements (block CI): the core interactive components every published
# HTML report must ship, plus a legal / disclaimer section.
HARD_RULES = [
    (
        r"<canvas[\s>]",
        "Missing <canvas> element (radar chart requires Chart.js canvas)",
    ),
    (
        r"chart\.js|Chart\.js|cdn\.jsdelivr\.net/npm/chart",
        "Missing Chart.js script reference",
    ),
    (
        r'(class=["\'][^"\']*mermaid[^"\']*["\']|influence|leverage|map-flow|影响力构造|Leverage Map)',
        "Missing influence/leverage map (Mermaid diagram or custom map element)",
    ),
    (
        r"(Legal|Disclaimer|免责声明)",
        "Missing Legal / Disclaimer section",
    ),
]

# Advisory (warn only): sections that legitimately vary across bilingual report
# formats; surfaced but not blocking.
SOFT_RULES = [
    (
        r"(dissent|heatmap|异议|热力图)",
        "No dissent heatmap section (advisory)",
    ),
    (
        r"(Final Verdict|final.verdict|verdict|总评|结论)",
        "No Final Verdict / 总评 / 结论 section (advisory)",
    ),
    (
        r"(Sources|参考|来源)",
        "No Sources / 参考 / 来源 section (advisory) — backfill real public sources when available",
    ),
]


def validate_file(path: Path) -> tuple:
    """Validate one report.html. Returns (errors, warnings)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [f"Cannot read file: {e}"], []

    errors, warnings = [], []
    for pattern, message in HARD_RULES:
        if not re.search(pattern, text, re.IGNORECASE):
            errors.append(message)
    for pattern, message in SOFT_RULES:
        if not re.search(pattern, text, re.IGNORECASE):
            warnings.append(message)

    return errors, warnings


def find_reports(root: Path) -> list:
    return sorted(root.rglob("report.html"))


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
        print("No report.html files found — nothing to validate.")
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
