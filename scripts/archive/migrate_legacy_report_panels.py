#!/usr/bin/env python3
"""Bind legacy MBA reports to a named panel.

Reports are intentionally git-ignored because they may contain sensitive brand
material. This helper performs the one-time local migration described in
metric-brand-auditor/SKILL.md Phase 0.5: any report directory with report.md
but no panel.yaml gets a default panel binding.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "metric-brand-auditor" / "reports"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", default="default", help="panel name to bind legacy reports to")
    parser.add_argument("--mba-version", default="0.2.18", help="MBA version to record")
    parser.add_argument("--date", default=date.today().isoformat(), help="locked_at date")
    parser.add_argument("--dry-run", action="store_true", help="show what would be written")
    args = parser.parse_args()

    if not REPORTS_DIR.is_dir():
        print(f"No reports directory found: {REPORTS_DIR}")
        return 0

    migrated = 0
    for report_dir in sorted(p for p in REPORTS_DIR.iterdir() if p.is_dir()):
        report_md = report_dir / "report.md"
        panel_yaml = report_dir / "panel.yaml"
        if not report_md.is_file() or panel_yaml.exists():
            continue

        content = (
            "# Generated during panel-system legacy migration\n"
            f"panel: {args.panel}\n"
            f"locked_at: {args.date}\n"
            f"mba_version: {args.mba_version}\n"
            "overrides:\n"
            "  add: []\n"
            "  drop: []\n"
        )
        if args.dry_run:
            print(f"DRY RUN would write {panel_yaml}")
        else:
            panel_yaml.write_text(content, encoding="utf-8")
            print(f"Wrote {panel_yaml}")
        migrated += 1

    print(f"{'Would migrate' if args.dry_run else 'Migrated'} {migrated} report(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
