# -*- coding: utf-8 -*-
"""PRD-465/T3（trend issue #2247 的 T3 环节）：mba skill 发现层 发现回路闸门。

在 T2 最小实现（scripts/skill_discovery.py）之上加闸门层，不改 T2
代码、不改 T1 设计：
  - 推荐可溯源 verify_trace（T1 §6.2–§6.3）：每条候选须有非空 matched
    与 reason；recommendation.trace 须等于首位候选的 reason、
    recommendation.skill 须等于首位候选；分数须在 [0, 1]；无候选时
    recommendation 须为 None。溯源断了的推荐记录不许入账、不许复核；
  - 推荐可复核 review_recommendation（T1 §6.3）：人对一条 pending
    推荐接受（accepted）或否决（rejected），只可复核一次；接受/否决
    均须留 reviewer；否决须写 note（推错可纠：否决原因回流，供后续
    调关键词权重）；否决后 recommendation 保留 trace 备查，但置
    effective=False（该推荐不再生效），接受则 effective=True；
  - 入账闸门 GatedDiscoveryLedger：继承 T2 DiscoveryLedger，入账时
    先验 trace（DISCOVERY_TRACE_MISMATCH），再验复核记录一致性
    （已复核的须有 reviewer、否决的须有 note 且 effective=False）；
    否决记录入账即记一条纠正（按需求原文归一化键），供后续重推排除；
  - 纠正重推 recommend_corrected：同一需求重推时排除已被否决的
    skill，次位候选顶上；新记录 request.supersedes 指向上一次
    request_id；全部候选都被否决则返回空推荐（不硬推）。
不碰 mba 现有评审流程与分数（R1）：本模块只读推荐记录，不写评审分数。
零网络零子进程；示例全虚构占位。ASPIRE（Apache-2.0）只作形态借鉴，
本模块为原创实现，未复用其代码。
测试：tests/unit/test_prd465_t3_discovery_gate.py
"""
from __future__ import annotations

import copy
from typing import Any

from skill_discovery import (  # noqa: E402
    SCHEMA, DiscoveryError, DiscoveryLedger, recommend,
)

ERROR_CODES = ("DISCOVERY_INCOMPLETE", "DISCOVERY_SCORE_MISMATCH",
               "DISCOVERY_TRACE_MISMATCH", "DISCOVERY_INVALID_REVIEW")
REVIEW_VERDICTS = ("pending", "accepted", "rejected")


def _refused(code: str, detail: str) -> dict[str, Any]:
    return {"schema": SCHEMA, "refused": code, "detail": detail,
            "verdict": None}


def _norm_text(text: str) -> str:
    return " ".join(str(text or "").split())


def verify_trace(record: dict[str, Any]) -> dict[str, Any]:
    """溯源校验：候选须有 matched/reason，推荐须与首位候选一致。"""
    problems: list[str] = []
    candidates = record.get("candidates") or []
    for cand in candidates:
        skill = cand.get("skill")
        if not cand.get("matched"):
            problems.append(f"候选 {skill} 无 matched（不知因何命中）")
        if not str(cand.get("reason") or "").strip():
            problems.append(f"候选 {skill} 无 reason（不知为何推荐）")
        score = cand.get("score")
        if not isinstance(score, (int, float)) or not 0 <= score <= 1:
            problems.append(f"候选 {skill} 分数 {score!r} 不在 [0, 1]")
    top = candidates[0] if candidates else None
    recommendation = record.get("recommendation")
    if top is None:
        if recommendation is not None:
            problems.append("无候选却有推荐")
    else:
        if recommendation is None:
            problems.append("有候选无推荐")
        else:
            if recommendation.get("skill") != top.get("skill"):
                problems.append(
                    f"推荐 skill {recommendation.get('skill')!r} 不是首位"
                    f"候选 {top.get('skill')!r}")
            if not str(recommendation.get("trace") or "").strip():
                problems.append("推荐无 trace（溯源缺失）")
            elif recommendation.get("trace") != top.get("reason"):
                problems.append("推荐 trace 与首位候选 reason 不一致")
    return {"schema": SCHEMA, "ok": not problems, "problems": problems}


def review_recommendation(record: dict[str, Any], *, verdict: str,
                          reviewer: str,
                          note: str = "") -> dict[str, Any]:
    """人工复核推荐（T1 §6.3）：接受则生效，否决则反馈回流、推荐失效。

    只可复核 pending 记录一次；接受/否决均须留 reviewer；否决须写 note。
    recommendation 保留 trace 备查，只改 effective 标志。
    """
    review = record.get("review") or {}
    if review.get("verdict") != "pending":
        return _refused("DISCOVERY_INVALID_REVIEW",
                        f"推荐已复核（verdict={review.get('verdict')}），"
                        "不可重复复核")
    if verdict not in ("accepted", "rejected"):
        return _refused("DISCOVERY_INVALID_REVIEW",
                        f"复核结论 {verdict!r} 词表外（只接受/否决）")
    if not str(reviewer or "").strip():
        return _refused("DISCOVERY_INVALID_REVIEW", "复核须留 reviewer")
    if not record.get("candidates"):
        return _refused("DISCOVERY_INVALID_REVIEW", "无候选，无可复核")
    if verdict == "rejected" and not str(note or "").strip():
        return _refused("DISCOVERY_INVALID_REVIEW",
                        "否决须写 note（推错可纠：否决原因须回流）")
    out = copy.deepcopy(record)
    out["review"] = {"verdict": verdict, "reviewer": str(reviewer),
                     "note": str(note)}
    if out.get("recommendation") is not None:
        out["recommendation"]["effective"] = verdict == "accepted"
    return out


class GatedDiscoveryLedger(DiscoveryLedger):
    """入账闸门：先验 trace，再验复核记录一致性；否决入账即记纠正。"""

    def __init__(self, path=None) -> None:
        super().__init__(path)
        self._corrections: dict[str, dict[str, str]] = {}

    def record(self, rec: dict[str, Any]) -> dict[str, Any]:
        trace = verify_trace(rec)
        if not trace["ok"]:
            raise DiscoveryError("DISCOVERY_TRACE_MISMATCH：推荐溯源不完整："
                                 + "；".join(trace["problems"]))
        review = rec.get("review") or {}
        verdict = review.get("verdict")
        if verdict in ("accepted", "rejected"):
            if not str(review.get("reviewer") or "").strip():
                raise DiscoveryError(
                    "DISCOVERY_INCOMPLETE：已复核记录无 reviewer")
            if verdict == "rejected" and not str(
                    review.get("note") or "").strip():
                raise DiscoveryError(
                    "DISCOVERY_INCOMPLETE：否决记录无 note（原因须回流）")
            effective = (rec.get("recommendation") or {}).get("effective")
            if verdict == "rejected" and effective is not False:
                raise DiscoveryError(
                    "DISCOVERY_INCOMPLETE：否决的推荐仍 effective")
            if verdict == "accepted" and effective is not True:
                raise DiscoveryError(
                    "DISCOVERY_INCOMPLETE：接受的推荐未置 effective")
        stored = super().record(rec)
        if verdict == "rejected":
            key = _norm_text((rec.get("request") or {}).get("text", ""))
            skill = (rec.get("recommendation") or {}).get("skill")
            if key and skill:
                self._corrections.setdefault(key, {})[skill] = \
                    str(review.get("note") or "")
        return stored

    def corrections_for(self, text: str) -> dict[str, str]:
        """某需求原文下已被否决的 skill → 否决原因（纠正表）。"""
        return dict(self._corrections.get(_norm_text(text), {}))

    def excluded_for(self, text: str) -> list[str]:
        return sorted(self.corrections_for(text))


def recommend_corrected(index: dict[str, Any], text: str,
                        ledger: GatedDiscoveryLedger, *,
                        request_id: str = "", supersedes: str = "",
                        top_n: int = 3) -> dict[str, Any]:
    """纠正重推：同一需求重推时排除已被否决的 skill，次位候选顶上。

    新记录 request.supersedes 指向上一次 request_id；全部候选都被否决
    则返回空推荐（不硬推）。未被否决过的需求与 T2 recommend() 一致。
    """
    rec = recommend(index, text, request_id=request_id, top_n=100)
    excluded = set(ledger.excluded_for(text))
    kept = [c for c in rec["candidates"] if c["skill"] not in excluded]
    kept = kept[:max(0, top_n)]
    top = kept[0] if kept else None
    rec["candidates"] = kept
    rec["recommendation"] = (
        {"skill": top["skill"], "trace": top["reason"]} if top else None)
    if supersedes:
        rec["request"] = dict(rec["request"], supersedes=supersedes)
    return rec
