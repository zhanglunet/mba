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


def _check_score_rows(text: str) -> list:
    """Return list of error strings; empty list = pass."""
    errors = []
    matrix_m = re.search(
        r"^##\s+Score Matrix(.+?)^##",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not matrix_m:
        return ["Score Matrix section not found or not closed by a following ## heading"]

    block = matrix_m.group(1)

    lens_found = 0
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
        lens_found += 1
        row_text = row_m.group(row_m.lastindex) or ""
        scores = re.findall(r"(?<!\d)([1-9]|10)(?!\d)", row_text)
        if not scores:
            errors.append(f"  Lens '{pat}' row has no numeric scores 1-10")

    if not re.search(r"\|\s*\*?\*?Total", block, re.IGNORECASE):
        errors.append("  Score Matrix missing 'Total' row")

    return errors


def validate_file(path: Path) -> list:
    """Validate one report.md. Returns list of error strings (empty = pass)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"Cannot read file: {e}"]

    errors = []

    rules = [
        (
            r"^#\s+.+Brand Influence Review \(v\d+\)",
            "Missing title: '# {Brand} — Brand Influence Review (v{N})'",
        ),
        (
            r"^##\s+Score Matrix",
            "Missing '## Score Matrix' section",
        ),
        (
            r"(Dissent Heatmap|异议热力图)",
            "Missing Dissent Heatmap / 异议热力图 section",
        ),
        (
            r"Final Verdict",
            "Missing 'Final Verdict' section",
        ),
        (
            r"(Legal|Disclaimer|免责声明)",
            "Missing Legal / Disclaimer / 免责声明 section",
        ),
        (
            r"^##\s+Sources",
            "Missing '## Sources' section",
        ),
    ]

    for pattern, message in rules:
        if not re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            errors.append(message)

    errors.extend(_check_score_rows(text))

    return errors


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
    total, failed = len(targets), 0

    for path in targets:
        errs = validate_file(path)
        try:
            rel = path.resolve().relative_to(repo_root)
        except ValueError:
            rel = path
        if errs:
            failed += 1
            print(f"FAIL  {rel}")
            for e in errs:
                print(f"      {e}")
        else:
            print(f"ok    {rel}")

    print(f"\n{total - failed}/{total} passed", end="")
    if failed:
        print(f"  ({failed} failed)")
        return 1
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
