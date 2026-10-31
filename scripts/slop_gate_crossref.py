#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-206/T3（trend #1032）：slop 门条目与 PRD-205 设计语言条目互引。

按 PRD-206/T1 设计 §七（docs/plans/2026-10-26-anti-slop-gate.md）实现 T3 范围：
  只引编号，不抄内容：门条目登记 design_refs（指向 design/design-language.json 的 DL 编号）；
  悬空引用报错（编号必须在 205 条目表中真实存在，fail-closed）；
  口径冲突检查（Floor 拦截级不得引用 DL 侧 soft/建议级条目；冲突登记裁决，不单方面改口径）；
  反向索引：DL 编号 → 引用它的门条目，两边可互相定位。
登记原则：DL 1.0.0 仅覆盖视觉 token（5 条）；门条目在 DL 无对应条目时显式登记空表 + 理由，
不杜撰编号（T1 §七.1）。纯 stdlib，零网络；示例全虚构。
"""
from __future__ import annotations

from typing import Any

from slop_gate_floor import GATE_VERSION

# T2 已实现的 Floor 五条（与 scripts/slop_gate_floor.py 的 rule_id 一致）
GATE_FLOOR_ENTRIES = ("SLOP-T-02", "SLOP-G-01", "SLOP-S-01", "SLOP-S-02", "SLOP-C-01")

# 门条目 → 设计语言条目互引登记表（T1 §七.2：回填须附"条目 ↔ DL 编号"对照全表）
GATE_DESIGN_REFS: dict[str, dict[str, Any]] = {
    "SLOP-T-02": {
        "tier": "floor",
        "design_refs": [],
        "note": "文案品牌专属性域：DL 1.0.0 仅登记视觉 token 条目，暂无对应条目（不杜撰编号）",
    },
    "SLOP-G-01": {
        "tier": "floor",
        "design_refs": ["DL-C01"],
        "note": "色板外色值拦截 ↔ DL-C01 品牌色必须取自登记 token：同向约束，"
                "口径一致（门 floor ↔ DL hard，两侧都强制）",
    },
    "SLOP-S-01": {
        "tier": "floor",
        "design_refs": [],
        "note": "空洞断言为文案语气域：DL 1.0.0 暂无对应条目（不杜撰编号）",
    },
    "SLOP-S-02": {
        "tier": "floor",
        "design_refs": [],
        "note": "无来源量化指标为事实核查域：DL 1.0.0 暂无对应条目（不杜撰编号）",
    },
    "SLOP-C-01": {
        "tier": "floor",
        "design_refs": [],
        "note": "构图同构为骨架指纹域：DL 1.0.0 暂无版式/构图条目（不杜撰编号）",
    },
}

# 已裁决的互引冲突登记（T1 §七.3：冲突不许任何一方单方面改口径消解，
# 提交两 PRD 维护人裁决后在此登记；当前为空）
CONFLICT_REGISTRY: list[dict[str, str]] = []


def design_refs_for(slop_id: str, registry: dict[str, dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """正向定位：门条目编号 → 互引登记（tier/design_refs/note）。"""
    reg = registry if registry is not None else GATE_DESIGN_REFS
    return reg.get(slop_id)


def check_crossref(dl: dict[str, Any], registry: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """互引校验：悬空引用 / deprecated 引用 / 口径冲突。

    返回 {"ok", "dangling", "conflicts", "checked"}：
    - dangling：design_refs 中不存在（或已 deprecated）的 DL 编号——fail-closed 报错；
    - conflicts：口径冲突（Floor 拦截级引用 DL soft/建议级条目）+ 已裁决登记表；
    - checked：逐条对照全表（条目 ↔ DL 编号）。
    """
    reg = registry if registry is not None else GATE_DESIGN_REFS
    dl_rules = {r.get("id"): r for r in dl.get("rules", []) if isinstance(r, dict)}
    dangling: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = list(CONFLICT_REGISTRY)
    checked: list[dict[str, Any]] = []

    for slop_id, entry in reg.items():
        tier = entry.get("tier")
        if tier not in ("floor", "reflex", "finish"):
            dangling.append({"entry_id": slop_id, "ref": None,
                             "reason": f"tier 不在词表: {tier!r}"})
        for ref in entry.get("design_refs", []):
            rule = dl_rules.get(ref)
            if rule is None:
                dangling.append({"entry_id": slop_id, "ref": ref, "reason": "编号在 DL 条目表中不存在"})
                continue
            if rule.get("status") == "deprecated":
                dangling.append({"entry_id": slop_id, "ref": ref, "reason": "DL 条目已 deprecated"})
                continue
            if tier == "floor" and rule.get("severity") == "soft":
                conflicts.append({
                    "entry_id": slop_id, "ref": ref,
                    "reason": "口径冲突：门为 Floor 拦截级，DL 侧为 soft/建议级——须两 PRD 维护人裁决",
                })
        checked.append({
            "entry_id": slop_id,
            "tier": tier,
            "design_refs": list(entry.get("design_refs", [])),
            "note": entry.get("note", ""),
        })

    return {
        "ok": not dangling and not conflicts,
        "dangling": dangling,
        "conflicts": conflicts,
        "checked": checked,
    }


def reverse_index(dl: dict[str, Any], registry: dict[str, dict[str, Any]] | None = None) -> dict[str, list[str]]:
    """反向定位：DL 编号 → 引用它的门条目列表（只收录真实存在的 DL 编号）。"""
    reg = registry if registry is not None else GATE_DESIGN_REFS
    dl_ids = {r.get("id") for r in dl.get("rules", []) if isinstance(r, dict)}
    index: dict[str, list[str]] = {}
    for slop_id, entry in reg.items():
        for ref in entry.get("design_refs", []):
            if ref in dl_ids:
                index.setdefault(ref, []).append(slop_id)
    return index


def crossref_report(dl: dict[str, Any], registry: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """互引报告：两版版本号 + 对照全表 + 正反向定位 + 校验结果（互相定位的机读落点）。"""
    check = check_crossref(dl, registry)
    return {
        "gate_version": GATE_VERSION,
        "dl_version": dl.get("meta", {}).get("version"),
        "entries": check["checked"],
        "dangling": check["dangling"],
        "conflicts": check["conflicts"],
        "reverse_index": reverse_index(dl, registry),
        "ok": check["ok"],
    }
