#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-205/T2（trend #1026）：生成器接入——加载共享设计语言文件。

按 PRD-205/T1 设计（docs/plans/2026-10-28-prd-205-design-language.md）实现 T2 范围：
  加载 design-language.yaml → 生成器读取同一份 token/规则 → 产物可被检查清单核对。
  纯 Python（无 yaml 库时用内置子集解析——顶层键 + 嵌套一层 + 列表）。
  零网络；示例全虚构。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_design_language(path: Path) -> dict[str, Any]:
    """加载设计语言 JSON（与 YAML 同构，但用 stdlib json 解析）。"""
    return json.loads(path.read_text(encoding="utf-8"))


def get_token(dl: dict[str, Any], path: str) -> Any:
    """按点分路径取 token 值。如 tokens.color.primary。"""
    parts = path.split(".")
    obj = dl
    for part in parts:
        if isinstance(obj, dict):
            obj = obj.get(part)
        else:
            return None
    return obj


def build_prompt_section(dl: dict[str, Any]) -> str:
    """从设计语言生成系统提示词的设计语言段（给 LLM 的约束文本）。"""
    lines = ["## 设计语言约束（必须遵守）\n"]
    tokens = dl.get("tokens", {})
    if isinstance(tokens, dict):
        for key, val in tokens.items():
            if isinstance(val, dict):
                for sk, sv in val.items():
                    lines.append(f"- {key}.{sk}: {sv}")
            elif isinstance(val, str):
                lines.append(f"- {key}: {val}")
    rules = dl.get("rules", [])
    if isinstance(rules, list):
        lines.append("\n### 规则\n")
        for r in rules:
            if isinstance(r, dict):
                rid = r.get("id", "?")
                desc = r.get("description", "")
                lines.append(f"- [{rid}] {desc}")
    return "\n".join(lines)
