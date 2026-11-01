#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-234/T2（trend #1171）：按共用标准（PRD-199 口径）重写技能文件。

T2 切片：审计全部品牌技能文件（judge pack 层面的标准模板对齐）——
  metadata.version 补齐 + description 触发式句式追加 + 标准字段校验。
幂等；只读模式报告差距；写模式落盘。零网络。
"""
from __future__ import annotations
import json
from pathlib import Path

STANDARD_VERSION = "agentskills-2026-10"
REQUIRED_FIELDS = ("name", "description")


def audit_pack(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    gaps = []
    if not data.get("name"):
        gaps.append("name 缺失")
    if not data.get("description", "").strip():
        gaps.append("description 为空")
    if not data.get("version"):
        gaps.append("version 缺失")
    if not data.get("standard"):
        gaps.append(f"standard（{STANDARD_VERSION}）缺失")
    return {"path": str(path), "name": data.get("name", "?"), "gaps": gaps}


def align_pack(path: Path, *, write: bool = False) -> dict:
    report = audit_pack(path)
    if not write or not report["gaps"]:
        return dict(report, changed=False)
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = False
    if not data.get("version"):
        data["version"] = "1.0.0"
        changed = True
    if not data.get("standard"):
        data["standard"] = STANDARD_VERSION
        changed = True
    if write and changed:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dict(audit_pack(path), changed=changed)


def audit_all(design_dir: Path) -> dict[str, dict]:
    return {str(p): audit_pack(p)
            for p in sorted(design_dir.glob("*.json")) if p.name != "package-lock.json"}
