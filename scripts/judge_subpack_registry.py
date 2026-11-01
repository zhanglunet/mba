#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-233/T2（trend #1166）：评委包四维度分包落地。

按 T1 设计（docs/plans/2026-10-26-judge-pack-layering.md §五）实现：
  JUDGE_SUBPACKS：43+3 位评委 → 四维度 sub-pack（brand 26 / copy 8 / visual 4 /
  compliance 5）+ consumer 横切组（3，非 sub-pack）；每包一句话定位。
  build_registry(skills_root)：扫 eval 评委数据 → 总登记册（机读 JSON）。
只读；零网络。

测试：tests/unit/test_prd233_t2_subpacks.py
"""
from __future__ import annotations

import json
from pathlib import Path

SUBPACK_INFO = {
    "brand": {"one_line": "先回答「这个品牌是谁、占什么位置」——看定位、心智占领与长期品牌资产的评委组。", "expected": 26},
    "copy": {"one_line": "看品牌怎么说——名字、话术、发布会与内容表达能否把定位说清、说动人。", "expected": 8},
    "visual": {"one_line": "看品牌长什么样——产品与视觉识别是否配得上定位，第一眼是否成立。", "expected": 4},
    "compliance": {"one_line": "看品牌经不经得起查——安全、监管、危机与信任治理视角下的品牌成色。", "expected": 5},
}

CROSSCUT = {"consumer": {"one_line": "受众侧的一面镜子——第一印象、购买意愿、价格直觉、信任犹豫与表达欲。", "expected": 3}}


class SubpackError(ValueError):
    """分包不一致。"""


def build_registry(judges: list[dict[str, Any]]) -> dict:
    """judges 列表每条含 {slug, name_cn, sub_pack}。"""
    errors: list[str] = []
    subpacks: dict[str, list[str]] = {}
    registry: dict[str, Any] = {"schema": "judge-subpack-registry/v1", "subpacks": {}, "judges": {}}
    crosscut_members: list[str] = []
    for j in judges:
        slug = j.get("slug", "")
        sub = j.get("sub_pack", "")
        if sub in CROSSCUT:
            crosscut_members.append(slug)
            registry["judges"][slug] = {"sub_pack": sub, "name_cn": j.get("name_cn", "")}
            continue
        if sub not in SUBPACK_INFO:
            errors.append(f"{slug}: 未知 sub_pack {sub!r}")
            continue
        subpacks.setdefault(sub, []).append(slug)
        registry["judges"][slug] = {"sub_pack": sub, "name_cn": j.get("name_cn", "")}
    for sub, info in SUBPACK_INFO.items():
        members = sorted(subpacks.get(sub, []))
        actual = len(members)
        if actual != info["expected"]:
            errors.append(f"{sub}: 实际 {actual} 人 ≠ 设计 {info['expected']} 人")
        registry["subpacks"][sub] = {
            "one_line": info["one_line"],
            "count": actual,
            "members": members,
        }
    registry["crosscut"] = {
        "consumer": {"one_line": CROSSCUT["consumer"]["one_line"],
                     "members": sorted(crosscut_members)},
    }
    registry["errors"] = errors
    registry["ok"] = not errors
    return registry
