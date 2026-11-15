# -*- coding: utf-8 -*-
"""PRD-449/T4（trend issue #2168 的 T4 环节）：评审监督台划界断言。

按 T1 设计（docs/plans/2026-11-15-prd-449-review-supervision-bench-design.md）§2.7 与 PRD「非目标」落地，建在 T2 最小实现
（review_supervision_bench.py）与 T3 闸门（review_supervision_gate.py）之上：
  - 管什么：监督回路管评分出炉的全程——人看没看（进度）、批没批
    （批注）、裁决没裁决、发回 agent 改没改、改回版本重审；
  - 不管什么：评审报告评审（PRD-426）、结论真假验证（PRD-380）、待办收发（PRD-366）、协同会话（人不下场改评分）、事后审计链；
  - 断言是可执行的：监督记录里一旦出现真假/评审/收件箱的越界声称即
    显形拒绝；闸门放行裁决只证明"监督点头"，绝不证明真假、评审通过
    或收件箱已处理；人直接改内容（版本不动）即越界，改内容只能由
    agent 经 resubmit 改回、版本 +1。
零网络零子进程；示例全虚构占位。
测试：tests/unit/test_prd449_t4_review_supervision_boundary.py
"""
from __future__ import annotations

import copy
from typing import Any

from review_supervision_bench import (STATUSES, SupervisionBenchError)
from review_supervision_gate import SupervisionGate

SCHEMA = "review-supervision-boundary/v1"
ID_KEY = "score_id"
DOWNSTREAM = "品牌审计报告"
ERROR_CODES = ("BOUNDARY_CROSSED", "BOUNDARY_INCOMPLETE")

# 监督回路管辖内（T1 §2.7：事中监督 + 反馈回 agent）。
IN_SCOPE = ("viewed", "annotated", "decided", "sent-back", "resubmitted")
# 监督回路管辖外：邻域 PRD + 形态禁区（T1 §2.7 / PRD 非目标）。
OUT_OF_SCOPE = (
    {"prd": "PRD-426", "topic": "评审报告评审", "reason": "评审流水线审报告，与监督回路无关"},
    {"prd": "PRD-380", "topic": "评审结论验证", "reason": "验结论真假，监督台只管监督流程本身"},
    {"prd": "PRD-366", "topic": "收件箱待办收发", "reason": "管待办收发，监督台只管未点头的评分不进品牌审计报告"},
    {"prd": "COLLAB", "topic": "协同会话", "reason": "人只批注和裁决，不下场改评分内容"},
    {"prd": "AUDIT", "topic": "事后审计链", "reason": "监督台是事中监督 + 反馈回 agent，不是事后留痕"},
)
# 越界声称键：监督记录里一旦出现，即有人把监督台当成了验真/评审/收件箱。
FORBIDDEN_CLAIM_KEYS = ("verified", "truth_verified", "truth_score",
                        "review_passed", "reviewed", "inbox_handled")
DOES_NOT_CERTIFY = ("truth", "review-passed", "inbox-handled")


class SupervisionBoundaryError(SupervisionBenchError):
    """划界断言失败——显形拒绝：监督台不管这件事。"""


def classify_neighbour(prd_id: str) -> dict[str, Any] | None:
    """邻域 PRD 划界：返回其在监督回路外的定位；未知编号返回 None。"""
    for entry in OUT_OF_SCOPE:
        if entry["prd"] == prd_id:
            return {"prd": entry["prd"], "topic": entry["topic"],
                    "in_scope": False, "reason": entry["reason"]}
    return None


def out_of_scope_prds() -> list[str]:
    """所有已划界在外的邻域 PRD 编号。"""
    return [e["prd"] for e in OUT_OF_SCOPE if e["prd"].startswith("PRD-")]


def assert_supervision_only(item: Any) -> dict[str, Any]:
    """断言：这条记录是监督记录、且只含监督声称。

    监督记录须有三件套（进度/批注/反馈）+ 版本 + 合法状态；一旦出现
    真假、评审、收件箱的声称键，即越界，显形拒绝。
    """
    if not isinstance(item, dict):
        raise SupervisionBoundaryError("BOUNDARY_INCOMPLETE：入界对象不是监督记录")
    missing = [k for k in ("status", "version", "progress", "annotations",
                           "feedbacks", "versions") if k not in item]
    if missing:
        raise SupervisionBoundaryError(f"BOUNDARY_INCOMPLETE：监督记录缺 {missing}")
    if item.get("status") not in STATUSES:
        raise SupervisionBoundaryError(
            f"BOUNDARY_INCOMPLETE：状态 {item.get('status')!r} 词表外")
    if not isinstance(item.get("version"), int) or item["version"] < 1:
        raise SupervisionBoundaryError("BOUNDARY_INCOMPLETE：版本号非法")
    crossed = [k for k in FORBIDDEN_CLAIM_KEYS if k in item]
    if crossed:
        raise SupervisionBoundaryError(
            f"BOUNDARY_CROSSED：监督记录含越界声称 {crossed}，监督台不管真假/评审/收件箱")
    return {"schema": SCHEMA, "item_id": item.get(ID_KEY),
            "status": item.get("status"), "version": item.get("version"),
            "in_scope": True, "governs": list(IN_SCOPE)}


def certify_gate_verdict(item: Any, verdict: Any) -> dict[str, Any]:
    """断言：闸门放行裁决只证明"监督点头"，不证明其他任何事。

    放行裁决须与对象、版本、approved 状态三者对上（闸门 is_verdict_current
    的同一口径）；对上后返回的证明写明"只证监督点头"，并逐项列出不证明
    的事（真假/评审通过/收件箱处理）；对不上即越界拒绝。
    """
    gate = SupervisionGate()
    if not gate.is_verdict_current(item, verdict):
        raise SupervisionBoundaryError(
            "BOUNDARY_CROSSED：放行裁决与对象/版本/状态对不上，不能当作监督点头")
    stmt = {"schema": SCHEMA, "item_id": item.get(ID_KEY),
            "version": item.get("version"),
            "certifies": "supervision-approved-only",
            "certifies_text": f"仅证明该评分经监督回路点头、可进{DOWNSTREAM}",
            "does_not_certify": list(DOES_NOT_CERTIFY)}
    return stmt


def assert_no_human_direct_edit(before: Any, after: Any) -> dict[str, Any]:
    """断言：人不下场改内容。

    内容或过程变了、版本却没变，即人绕开 agent 改回回路直接改了内容，
    越界；版本 +1 的改回（resubmit）与原样不动都通过。
    """
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise SupervisionBoundaryError("BOUNDARY_INCOMPLETE：比对对象不是监督记录")
    changed = (before.get("content") != after.get("content")
               or before.get("process") != after.get("process"))
    if changed and before.get("version") == after.get("version"):
        raise SupervisionBoundaryError(
            "BOUNDARY_CROSSED：内容变了版本没变——人直接改内容，未走 agent 改回")
    return {"schema": SCHEMA, "item_id": after.get(ID_KEY),
            "version": after.get("version"), "direct_edit": False}


def boundary_report(item: Any, verdict: Any = None) -> dict[str, Any]:
    """划界报告：管什么 / 不管什么 / 这条记录与裁决落在界内还是界外。"""
    stmt = assert_supervision_only(item)
    checks = {"has_progress": bool(item.get("progress")),
              "has_annotations_ledger": "annotations" in item,
              "has_feedbacks_ledger": "feedbacks" in item,
              "has_versions": bool(item.get("versions")),
              "process_visible": bool(item.get("process"))}

    rep: dict[str, Any] = {"schema": SCHEMA, "item_id": item.get(ID_KEY),
                           "status": item.get("status"),
                           "version": item.get("version"),
                           "in_scope": stmt["governs"],
                           "out_of_scope": [classify_neighbour(p)
                                            for p in out_of_scope_prds()],
                           "checks": checks, "in_boundary": True}

    if verdict is not None:
        rep["gate_certification"] = certify_gate_verdict(item, verdict)
    return rep


def audit_batch(items: Any) -> dict[str, Any]:
    """批量划界：逐条断言，不抛错；越界的逐条留痕。"""
    in_boundary: list[dict[str, Any]] = []
    crossed: list[dict[str, Any]] = []
    for it in items or []:
        try:
            in_boundary.append(assert_supervision_only(it))
        except SupervisionBoundaryError as exc:
            crossed.append({"item_id": it.get(ID_KEY) if isinstance(it, dict) else None,
                            "reason": str(exc)})
    return {"schema": SCHEMA, "in_boundary_count": len(in_boundary),
            "crossed_count": len(crossed), "crossed": crossed}
