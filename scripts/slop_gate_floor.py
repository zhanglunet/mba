#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-206/T2（trend #1031）：mba 反 AI 味 Floor 门最小实现。"""
from __future__ import annotations
import hashlib, re
from typing import Any

GATE_VERSION = "slop-floor-0.1.0"
_HOLLOW_PATTERNS = (
    re.compile(r"(?:引领|开启|赋能|定义|重新定义|革命性|颠覆)(?:了?)?(?:未来|新时代|新篇章|新纪元)"),
    re.compile(r"(?:卓越|极致|非凡|超凡)(?:的|之)?(?:体验|品质|性能|表现)"),
)
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?(?:%|万|亿|倍|x)?")
_BRAND_MARKERS = ("DemoBrand", "示例品牌", "mba", "MBA")
_GENERIC_MARKERS = ("产品", "服务", "品牌", "方案", "平台", "系统", "用户", "客户")


def gate_floors(copy_text, *, brand_known=True, source_annotated=None,
                colors=None, brand_palette=None, prev_asset_hashes=None):
    hits = []
    text = copy_text or ""
    has_brand = any(b in text for b in _BRAND_MARKERS)
    if not has_brand and any(m in text for m in _GENERIC_MARKERS):
        hits.append({"rule_id": "SLOP-T-02", "evidence": "整稿不含品牌/产品专名——换名测试不过"})
    for pat in _HOLLOW_PATTERNS:
        if pat.search(text):
            hits.append({"rule_id": "SLOP-S-01", "evidence": f"空洞断言: {pat.pattern[:30]}"})
            break
    nums = _NUMBER_RE.findall(text)
    if nums and source_annotated is not True:
        hits.append({"rule_id": "SLOP-S-02", "evidence": f"量化指标 {nums[:3]} 无来源标注"})
    if colors and brand_palette:
        outside = [c for c in colors if c.lower() not in brand_palette]
        if len(outside) >= 2:
            hits.append({"rule_id": "SLOP-G-01", "evidence": f"色板外色值: {outside[:3]}"})
    if prev_asset_hashes:
        ch = hashlib.md5(re.sub(r"\s+", " ", text).encode()).hexdigest()[:16]
        if ch in prev_asset_hashes:
            hits.append({"rule_id": "SLOP-C-01", "evidence": "与已审资产构图同构"})
    decision = "blocked" if hits else "passed_with_warnings"
    return {"decision": decision, "hits": hits, "version": GATE_VERSION}
