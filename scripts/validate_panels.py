#!/usr/bin/env python3
"""Lightweight validator for MBA panel YAML files.

This intentionally avoids PyYAML so it works in the default macOS / Codex
runtime. It understands the small subset of YAML used by panels/*.yaml:
top-level scalar fields and judges entries with scalar fields.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PANELS_DIR = ROOT / "metric-brand-auditor" / "panels"
PERSPECTIVE_ROOTS = [
    ROOT / "perspectives",   # canonical layout since 2026-06
    ROOT,                    # legacy: <slug>-perspective/ at repo root
    Path.home() / ".claude" / "skills",
    Path.home() / "skills",
    Path.home() / ".codex" / "skills",
]


def strip_comment(line: str) -> str:
    return line.split("#", 1)[0].rstrip()


def parse_panel(path: Path) -> dict:
    data: dict[str, object] = {"judges": []}
    current_judge: dict[str, str] | None = None
    in_judges = False

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = strip_comment(raw)
        if not line.strip():
            continue

        top = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if top and not raw.startswith(" "):
            key, value = top.groups()
            if key == "judges":
                in_judges = True
                continue
            if value not in {"|", ">"}:
                data[key] = value.strip().strip('"').strip("'")
            continue

        if in_judges:
            start = re.match(r"^\s*-\s+slug:\s*([\w-]+)\s*$", line)
            if start:
                current_judge = {"slug": start.group(1)}
                data["judges"].append(current_judge)
                continue

            field = re.match(r"^\s+([A-Za-z_][\w-]*):\s*(.*)$", line)
            if field and current_judge is not None:
                key, value = field.groups()
                if value not in {"|", ">"}:
                    current_judge[key] = value.strip().strip('"').strip("'")

    return data


def parse_industries(path: Path) -> dict[str, str]:
    mappings: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = strip_comment(raw)
        match = re.match(r"^([\w-]+):\s*([\w-]+)\s*$", line)
        if match:
            mappings[match.group(1)] = match.group(2)
    return mappings


def perspective_exists(slug: str) -> bool:
    return any((root / f"{slug}-perspective" / "SKILL.md").is_file() for root in PERSPECTIVE_ROOTS)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    if not PANELS_DIR.is_dir():
        print(f"ERROR: panels dir not found: {PANELS_DIR}", file=sys.stderr)
        return 2

    panel_files = sorted(p for p in PANELS_DIR.glob("*.yaml") if p.name != "industries.yaml")
    panel_names = {p.stem for p in panel_files}

    for path in panel_files:
        data = parse_panel(path)
        name = data.get("name")
        status = data.get("status", "active")
        judges = data.get("judges") or []

        if name != path.stem:
            errors.append(f"{path.name}: name={name!r} does not match filename {path.stem!r}")
        if not judges:
            errors.append(f"{path.name}: judges must contain at least one entry")

        seen: set[str] = set()
        missing: list[str] = []
        for judge in judges:
            slug = judge.get("slug", "")
            if slug in seen:
                errors.append(f"{path.name}: duplicate judge slug {slug!r}")
            seen.add(slug)

            language = judge.get("language", "zh")
            if language not in {"zh", "en"}:
                errors.append(f"{path.name}: judge {slug!r} has unsupported language {language!r}")

            weight = judge.get("weight", "1.0")
            try:
                if float(weight) <= 0:
                    errors.append(f"{path.name}: judge {slug!r} weight must be > 0")
            except ValueError:
                errors.append(f"{path.name}: judge {slug!r} weight is not numeric: {weight!r}")

            if slug and not perspective_exists(slug):
                missing.append(slug)

        if missing and status != "skeleton":
            # 硬错误(E2-6):非 skeleton panel 引用了不存在的 perspective slug =
            # 面板不可用,必须 CI 红(此前仅 WARN 会放行断链面板)。
            errors.append(f"{path.name}: missing perspective skills: {', '.join(missing)}")
        if status == "skeleton":
            print(f"OK skeleton: {path.name} ({len(judges)} judges, {len(missing)} missing skills)")
        else:
            print(f"OK panel: {path.name} ({len(judges)} judges)")

    industries_path = PANELS_DIR / "industries.yaml"
    if industries_path.is_file():
        mappings = parse_industries(industries_path)
        for industry, panel in mappings.items():
            if panel not in panel_names:
                # 硬错误(E2-6):活跃 industry 别名指向不存在的 panel 文件 =
                # `--industry <x>` 会 ABORT,属真实断链,必须 CI 红。
                errors.append(f"industries.yaml: {industry!r} maps to missing panel {panel!r}")
        print(f"OK industries.yaml ({len(mappings)} mappings)")
    else:
        warnings.append("industries.yaml is missing")

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
