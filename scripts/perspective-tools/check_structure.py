#!/usr/bin/env python3
"""Validate that every <slug>-perspective/SKILL.md has the H2 sections required
by metric-brand-auditor/references/perspective-structure-spec.md.

Required logical sections (any of the listed aliases satisfies):

  - Core Mental Models  : "## Core Mental Models" | "## 核心心智模型"
  - Honest Boundary     : "## Honest Boundary"    | "## 诚实边界"
  - Anti-Fabrication    : "## Anti-Fabrication Red Lines" | "## Anti-Fabrication 红线"
                          | "## Anti-Fabrication Guard"
  - Self-Conflict Rule  : "## Self-Conflict Rule"
  - Sources             : "## Sources" | "## 附录：调研来源"

Exit codes:
  0  all perspectives PASS
  1  one or more perspectives FAIL
  2  invocation / IO error

Usage:
  python3 scripts/perspective-tools/check_structure.py
  python3 scripts/perspective-tools/check_structure.py --perspective fusheng
  python3 scripts/perspective-tools/check_structure.py --root /path/to/mba

Designed to run in CI alongside scripts/validate_panels.py. No external deps.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = [
    ("Core Mental Models", ["Core Mental Models", "核心心智模型"]),
    ("Honest Boundary", ["Honest Boundary", "诚实边界"]),
    (
        "Anti-Fabrication",
        ["Anti-Fabrication Red Lines", "Anti-Fabrication 红线", "Anti-Fabrication Guard"],
    ),
    ("Self-Conflict Rule", ["Self-Conflict Rule"]),
    ("Sources", ["Sources", "附录：调研来源"]),
]


def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(8):
        if (cur / "metric-brand-auditor" / "SKILL.md").is_file():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise SystemExit(
        "check_structure.py: could not locate repo root (no metric-brand-auditor/ "
        "above this script). Pass --root explicitly."
    )


def h2_headings(skill_md: Path) -> list[str]:
    out = []
    for line in skill_md.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## +(.+?)\s*$", line)
        if m:
            out.append(m.group(1).strip())
        elif re.match(r"^##[^#]", line):  # malformed "##Foo" without space
            out.append(line[2:].strip())
    return out


def list_perspective_dirs(root: Path) -> list[Path]:
    return sorted(p for p in root.glob("*-perspective") if (p / "SKILL.md").is_file())


def check_one(skill_md: Path) -> list[str]:
    """Return list of missing-section error strings (empty = PASS)."""
    headings = h2_headings(skill_md)
    missing = []
    for label, aliases in REQUIRED_SECTIONS:
        if not any(any(alias in h for alias in aliases) for h in headings):
            missing.append(f"  - missing `## {aliases[0]}` (or alias: {' / '.join(aliases[1:])})")
    return missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=None,
                        help="Repo root (auto-detected if omitted).")
    parser.add_argument("--perspective", default=None,
                        help="Check only this slug (e.g. fusheng).")
    args = parser.parse_args()

    root = args.root or find_repo_root(Path(__file__).resolve().parent)

    dirs = list_perspective_dirs(root)
    if args.perspective:
        wanted = root / f"{args.perspective}-perspective"
        dirs = [d for d in dirs if d == wanted]
        if not dirs:
            print(f"check_structure.py: no such perspective '{args.perspective}'", file=sys.stderr)
            return 2

    if not dirs:
        print("check_structure.py: no *-perspective/ dirs found", file=sys.stderr)
        return 2

    fail_count = 0
    for d in dirs:
        slug = d.name[: -len("-perspective")]
        skill_md = d / "SKILL.md"
        missing = check_one(skill_md)
        if missing:
            fail_count += 1
            print(f"FAIL {slug}")
            for line in missing:
                print(line)
        else:
            print(f"OK   {slug}")

    print(f"\n{len(dirs) - fail_count}/{len(dirs)} perspectives pass structure spec")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
