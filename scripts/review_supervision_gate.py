# -*- coding: utf-8 -*-
"""PRD-449/T3（trend issue #2167 的 T3 环节）：评审监督台监督回路闸门。

按 T1 设计（docs/plans/2026-11-15-prd-449-review-supervision-bench-design.md）§2.3 落地，建在 T2 最小实现（review_supervision_bench.py）之上：
  - 闸门是下游的唯一入口：只有 approved 能进品牌审计报告；draft / in-review / sent-back / rejected一律拦下；
  - 每次放行与拦截都记一条闸门裁决（对象标识、状态、版本、裁决、原因、时间、
    操作人），拦截也留痕；裁决日志 JSONL append-only（路径注入）；
  - 改回的新版本重新待审、不继承上一轮点头：放行裁决只对裁决当时的版本有效，
    版本变了旧裁决即失效，须重新点头、重新过闸；
  - 不设例外通道：admit / admit_batch 没有任何放行开关参数；闸门本身不改对象
    内容、不改状态、不改分数。
零网络零子进程；示例全虚构占位。
测试：tests/unit/test_prd449_t3_review_supervision_gate.py
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from review_supervision_bench import STATUSES, SupervisionBenchError, can_enter_downstream

SCHEMA = "review-supervision-gate/v1"
ID_KEY = "score_id"
DOWNSTREAM = "品牌审计报告"
ERROR_CODES = ("GATE_BLOCKED", "GATE_INCOMPLETE")


class GateBlockedError(SupervisionBenchError):
    """闸门拦截——显形拒绝：未点头不进下游。"""


def _judge(item: Any, *, by: str, at: str) -> dict[str, Any]:
    """判一次：返回裁决（不抛错）；拦下的原因写明状态。"""
    verdict: dict[str, Any] = {"schema": SCHEMA, "decision": "blocked",
                               "item_id": None, "status": None, "version": None,
                               "reason": "", "by": by, "at": at}
    if not isinstance(item, dict):
        verdict["reason"] = "GATE_BLOCKED：入闸对象不是监督记录"
        return verdict
    verdict["item_id"] = item.get(ID_KEY)
    verdict["status"] = item.get("status")
    verdict["version"] = item.get("version")
    if verdict["item_id"] in (None, ""):
        verdict["reason"] = "GATE_BLOCKED：缺对象标识，不进下游"
        return verdict
    if verdict["status"] not in STATUSES:
        verdict["reason"] = f"GATE_BLOCKED：状态 {verdict['status']!r} 词表外，不进下游"
        return verdict
    if not can_enter_downstream(item):
        verdict["reason"] = f"GATE_BLOCKED：状态 {verdict['status']} 未点头，不进{DOWNSTREAM}"
        return verdict
    verdict["decision"] = "allowed"
    verdict["reason"] = f"已点头，放行进{DOWNSTREAM}"
    return verdict


class SupervisionGate:
    """监督回路闸门：下游唯一入口；每次裁决都留痕；不改对象。"""

    def __init__(self, path: str | Path | None = None) -> None:
        self._decisions: list[dict[str, Any]] = []
        self._path = Path(path) if path else None

    def _log(self, verdict: dict[str, Any]) -> dict[str, Any]:
        rec = copy.deepcopy(verdict)
        self._decisions.append(rec)
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
        return dict(rec)

    def admit(self, item: Any, *, by: str = "gate", at: str = "") -> dict[str, Any]:
        """单件过闸：已点头放行（返回放行裁决），未点头抛 GateBlockedError。"""
        verdict = _judge(item, by=by, at=at)
        self._log(verdict)
        if verdict["decision"] != "allowed":
            raise GateBlockedError(verdict["reason"])
        return dict(verdict)

    def admit_batch(self, items: Any, *, by: str = "gate", at: str = "") -> dict[str, Any]:
        """批量过闸：只放行 approved；其余拦下留痕，不抛错。"""
        admitted: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        for it in items or []:
            verdict = _judge(it, by=by, at=at)
            self._log(verdict)
            if verdict["decision"] == "allowed":
                admitted.append(copy.deepcopy(it))
            else:
                blocked.append(dict(verdict))
        out: dict[str, Any] = {"schema": SCHEMA, "admitted": admitted,
                               "blocked": blocked,
                               "admitted_count": len(admitted),
                               "blocked_count": len(blocked)}
        return out

    def is_verdict_current(self, item: Any, verdict: Any) -> bool:
        """放行裁决是否仍有效：对象、版本、approved 状态三者须同时对上。"""
        if not isinstance(item, dict) or not isinstance(verdict, dict):
            return False
        return (verdict.get("decision") == "allowed"
                and verdict.get("item_id") == item.get(ID_KEY)
                and verdict.get("version") == item.get("version")
                and item.get("status") == "approved")

    def decisions(self) -> list[dict[str, Any]]:
        return [dict(d) for d in self._decisions]

    def allowed_decisions(self) -> list[dict[str, Any]]:
        return [d for d in self.decisions() if d["decision"] == "allowed"]

    def blocked_decisions(self) -> list[dict[str, Any]]:
        return [d for d in self.decisions() if d["decision"] == "blocked"]

    def report(self) -> dict[str, Any]:
        """闸门裁决汇总：总数、放行/拦截数、按状态分桶。"""
        by_status: dict[str, int] = {}
        for d in self._decisions:
            by_status[str(d.get("status"))] = by_status.get(str(d.get("status")), 0) + 1
        return {"schema": SCHEMA, "total": len(self._decisions),
                "allowed": len(self.allowed_decisions()),
                "blocked": len(self.blocked_decisions()),
                "by_status": by_status}
