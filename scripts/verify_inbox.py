# -*- coding: utf-8 -*-
"""PRD-366/T2（trend issue #1645 的 T2 环节）：评审复核收件箱最小实现。

按 T1 设计（docs/plans/2026-11-11-prd-366-verify-inbox-design.md）
§3.1/§3.2/§4 实现：

  - collect(*, low_confidence=None, withdraw_confirms=None,
    slides_gate_reviews=None, external_ref_reviews=None)：四源只读汇聚（R2）
    → 条目 {item_id, kind, source_ref, work_snapshot_digest,
    judgepack_version, reason, state} 缺一 INBOX_ITEM_INCOMPLETE 拒绝入箱
    （R3；work_snapshot_digest 与 PRD-352 重放包同源）；
  - approve(item, *, by, at, verdict)："撤回确认"类 approve 必带人工定性
    verdict（§6.1 裁决：approve 仅记「确认撤回动议」，实际撤回走既有流程）；
  - InboxLedger：append-only（R4）——approve/reject 人批留痕；重复裁决
    INBOX_DOUBLE_DECIDE、未知 id、携带撤回/重转换/改分载荷
    INBOX_AUTO_EXEC_ATTEMPT（R1 零分数写零撤回触发零重转换——动作走既有
    流程）显形拒绝；
  - view(kind)：kind 过滤视图。

kind 词表封闭：low_confidence_score / withdraw_confirm /
slides_gate_review / external_ref_review。零网络；示例全虚构占位。
测试：tests/unit/test_prd366_t2_verify_inbox.py
"""
from __future__ import annotations

import copy
from typing import Any

INBOX_SCHEMA = "review-verify-inbox/v1"
ITEM_KINDS = ("low_confidence_score", "withdraw_confirm",
              "slides_gate_review", "external_ref_review")
ERROR_CODES = ("INBOX_ITEM_INCOMPLETE", "INBOX_DOUBLE_DECIDE",
               "INBOX_AUTO_EXEC_ATTEMPT")
_EXEC_KEYS = ("action", "withdraw", "execute", "rescore", "reconvert")


class InboxError(ValueError):
    """收件箱违规——显形拒绝。"""


def _item(item_id: str, kind: str, source_ref: str, work_snapshot_digest: str,
          judgepack_version: str, reason: str) -> dict[str, Any]:
    return {"item_id": item_id, "kind": kind, "source_ref": source_ref,
            "work_snapshot_digest": work_snapshot_digest,
            "judgepack_version": judgepack_version, "reason": reason,
            "state": "pending", "decided_by": None, "decided_at": None,
            "reject_reason": None, "human_verdict": None}


def collect(*, low_confidence: list[dict[str, Any]] | None = None,
            withdraw_confirms: list[dict[str, Any]] | None = None,
            slides_gate_reviews: list[dict[str, Any]] | None = None,
            external_ref_reviews: list[dict[str, Any]] | None = None,
            fingerprint: str = "sha16:none（占位）",
            judgepack_version: str = "v1（占位）",
            at: str = "") -> list[dict[str, Any]]:
    """四源只读汇聚（R2）；条目缺一拒绝入箱并显形。"""
    items: list[dict[str, Any]] = []
    incomplete: list[str] = []
    n = 0

    def _add(kind: str, source_ref: str, reason: str):
        nonlocal n
        n += 1
        it = _item(f"item-{n:03d}", kind, source_ref, fingerprint,
                   judgepack_version, reason)
        missing = [k for k in ("item_id", "kind", "source_ref", "reason")
                   if not it.get(k)]
        if missing or kind not in ITEM_KINDS:
            incomplete.append(f"{kind or '(空 kind)'} 缺 {missing or 'kind 非法'}")
            return
        items.append(it)

    for lc in low_confidence or []:
        _add("low_confidence_score",
             str(lc.get("source_ref") or "review-replay-pack/v1（占位）"),
             str(lc.get("reason") or "低置信评分项（占位）"))
    for w in withdraw_confirms or []:
        _add("withdraw_confirm", str(w.get("source_ref") or "withdraw-motion"),
             str(w.get("reason") or ""))   # reason 必填
    for sg in slides_gate_reviews or []:
        _add("slides_gate_review",
             f"slides-gate/v1#{sg.get('check', 'page_mapping')}",
             str(sg.get("reason") or "verify_gate 失败复核（占位）"))
    for er in external_ref_reviews or []:
        _add("external_ref_review", str(er.get("source_ref") or "verify-gate"),
             str(er.get("reason") or "外链检出处置（占位）"))
    if incomplete:
        raise InboxError(f"INBOX_ITEM_INCOMPLETE：{'；'.join(incomplete)}")
    return items


class InboxLedger:
    """收件箱账本（R4）：append-only；approve/reject 只改状态零动作（R1）。"""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []

    def add(self, items: list[dict[str, Any]]) -> list[str]:
        added = []
        for it in items:
            if it["item_id"] in self._items:
                raise InboxError(f"INBOX_DOUBLE_DECIDE：{it['item_id']} 已在箱")
            self._items[it["item_id"]] = copy.deepcopy(it)
            self._events.append({"op": "add", "item_id": it["item_id"]})
            added.append(it["item_id"])
        return added

    def _decide(self, item_id: str, state: str, *, by: str, at: str,
                reason: str = "", verdict: str | None = None,
                payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if payload and any(k in payload for k in _EXEC_KEYS):
            raise InboxError("INBOX_AUTO_EXEC_ATTEMPT：裁决携带撤回/重转换/"
                             "改分载荷——收件箱零自动执行（R1），动作走既有流程")
        it = self._items.get(item_id)
        if not it:
            raise InboxError(f"未知 item_id：{item_id!r}")
        if it["state"] != "pending":
            raise InboxError(f"INBOX_DOUBLE_DECIDE：{item_id} 已裁决"
                             f"（{it['state']}）——重复裁决显形拒绝")
        if state == "approved" and it["kind"] == "withdraw_confirm":
            if not verdict:
                raise InboxError("撤回确认 approve 必带人工定性 verdict"
                                 "（§6.1 裁决：仅记「确认撤回动议」，实际撤回"
                                 "走既有流程）")
            it["human_verdict"] = verdict
        it["state"] = state
        it["decided_by"] = by
        it["decided_at"] = at
        if reason:
            it["reject_reason"] = reason
        self._events.append({"op": state.lower(), "item_id": item_id,
                             "by": by, "at": at})
        return dict(it)

    def approve(self, item_id: str, *, by: str, at: str,
                verdict: str | None = None,
                payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._decide(item_id, "approved", by=by, at=at, verdict=verdict,
                            payload=payload)

    def reject(self, item_id: str, *, by: str, at: str, reason: str = "",
              payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._decide(item_id, "rejected", by=by, at=at, reason=reason,
                            payload=payload)

    def view(self, kind: str | None = None) -> list[dict[str, Any]]:
        return [copy.deepcopy(it) for it in self._items.values()
                if kind is None or it["kind"] == kind]

    @property
    def events(self) -> list[dict[str, Any]]:
        return [dict(e) for e in self._events]
