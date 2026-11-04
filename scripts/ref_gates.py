# -*- coding: utf-8 -*-
"""PRD-296/T3（trend issue #1483）：评审引用歧义闸门与结论引用字段。

按 T1 设计（docs/plans/2026-11-04-prd-296-at-judgepack-work-ref-design.md）
§5/§6 实现，叠加 T2 work_ref（解析器不变，闸门消费其产物）：

  - gate_review_start(resolutions)：评审开始闸（§5）——任一引用 refused →
    一票否决（NOT_FOUND 停下问、AMBIGUOUS 停下问、REGISTRY_CORRUPT 数据
    异常显形交人工，不静默糊弄）；
  - ConclusionRefLedger：评审结论引用字段账本（§6）——append_ref 把解析
    产物挂到结论（judgepack_fingerprint/work_id/work_status 逐引用可溯源）；
    **只记录用了哪一版，不改口径**（R1：PRD-282 快照口径文件零触碰——
    本模块零快照写导入，AST 断言）；
  - 错误码封闭：REF_* 三码穷举。

零网络；示例全虚构占位。
测试：tests/unit/test_prd296_t3_gates.py
"""
from __future__ import annotations

import ast
import copy
from pathlib import Path
from typing import Any

from work_ref import resolve  # noqa: F401  (词表供封闭断言)

ERROR_CODES = ("REF_SYNTAX_ERROR", "REF_NOT_FOUND", "REF_AMBIGUOUS",
               "REF_REGISTRY_CORRUPT")


def gate_review_start(resolutions: list[dict[str, Any]]) -> dict[str, Any]:
    """评审开始闸（§5）：任一引用 refused → 一票否决。"""
    for out in resolutions:
        if out.get("resolution", {}).get("status") == "refused":
            code = out["resolution"].get("error_code")
            return {"allow": False, "error_code": code,
                    "detail": out["resolution"].get("detail", "")}
    return {"allow": True, "error_code": None, "detail": None}


class ConclusionRefLedger:
    """结论引用字段账本（§6）：append-only、逐引用可溯源、零口径修改。"""

    def __init__(self) -> None:
        self._conclusions: dict[str, dict[str, Any]] = {}

    def open_conclusion(self, conclusion_id: str) -> None:
        if conclusion_id in self._conclusions:
            raise ValueError(f"结论 id 重复：{conclusion_id!r}")
        self._conclusions[conclusion_id] = {"ref_resolutions": []}

    def append_ref(self, conclusion_id: str, resolution: dict[str, Any]) -> dict:
        record = self._conclusions.get(conclusion_id)
        if record is None:
            raise KeyError(f"结论不存在：{conclusion_id!r}")
        if resolution.get("resolution", {}).get("status") != "resolved":
            raise ValueError("refused 解析不进结论引用字段（闸门已挡）")
        entry = {
            "judgepack_fingerprint": (resolution.get("judgepack") or {}).get("fingerprint"),
            "work_id": resolution.get("work_id"),
            "work_status": (resolution.get("meta_summary") or {}).get("work_status"),
        }
        record["ref_resolutions"].append(entry)
        return copy.deepcopy(entry)

    def get(self, conclusion_id: str) -> dict[str, Any]:
        return copy.deepcopy(self._conclusions[conclusion_id])


if __name__ == "__main__":  # pragma: no cover
    tree = ast.parse(Path(__file__).resolve().read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        mods = []
        if isinstance(node, ast.Import):
            mods = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods = [node.module.split(".")[0]]
        for mod in mods:
            assert mod not in {"config_snapshot"}, "引用账本导入了快照写面"
    print("AST 红线自检通过（零口径修改）")
