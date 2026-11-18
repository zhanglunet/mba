"""PRD-485/T3（trend issue #2347 的 T3 环节）：评委技能评估 监督回路闸门。

按 T1 设计（docs/plans/2026-11-17-prd-485-mba-skill-evaluation-design.md）落地：把"评估未过关的技能不得进入评审复核收件箱"做成
强制检查。T2 只产出评估报告（静态完整性结论 + 行为待补测 + 重叠候选），没有
任何东西拦住未过关技能的产物进评审复核收件箱；T3 只加检查，不改 T2 的评估逻辑与
报告格式，按技能过闸：
  - check_gate(report, skill_id)：纯函数；以 T2 报告的 skills 行为准重新推导
    "该技能是否可进评审复核收件箱"——行为结论为"过关"且不在疑似重叠对里且静态无缺项，
    三项缺一不可；只认清单或只认历史通过的一律拦下，并逐条给出拦截原因
    （code + target + detail）。
  - enforce_gate：不通过即显形拒绝（GateError，GATE_BLOCKED）。
  - admit_to_downstream：评审复核收件箱唯一允许的入口——先过闸，再把放行/拦截的
    审计条目写进 SkillEvaluationLedger（拦截也留痕，绕关尝试有据可查）；静态
    缺项或行为未过关而被拦的技能，另追加一条整改条目（append-only，原因/证据/
    整改期限/复测结果齐全，期限待人填、不编造）。
  - gate_outlet：加固版批量出口，逐技能过闸；未知/残缺技能按拦截处理，
    永不抛错漏放。
  - 整改清单 append-only：SkillEvaluationLedger 只追加、不改历史条目。

口径（按 T1 设计"评委技能包定期体检，坏技能进清单修，评审复核收件箱只审评估过关的评委技能打出的分。"）：
  - 行为结论"过关"才可放行；"待补测"拦下但不进整改清单（待补测不是失效，
    等对照跑分补测）；"未过关/不过关/待整改/失效"拦下并进整改
    清单；疑似重叠拦下待人确认（合并/拆分/保留由人决定）。
  - 今天全部技能行为结论都是"待补测"，闸门会把它们全拦下——这是实情，不是
    闸门太严：真实对照跑分在 T5 补，跑分出来重评"过关"后才能放行。

本模块不重跑评估、不改报告、不碰技能包——只有检查与审计，没有放行的后门；
评估结论的改动仍走 T2 的评估流程；发布仍人工确认。零网络零子进程；示例全
虚构占位。
测试：tests/unit/test_skill_evaluation_gate.py
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from skill_evaluation import SCHEMA, evaluate  # noqa: E402

GATE_SCHEMA = "skill-evaluation-gate/v1"
GATE_PRD = 485
GATE_REPO = "mba"
BEHAVIOR_PASS = "过关"
BEHAVIOR_PENDING = ("待补测", "待复核")
BEHAVIOR_FAIL = ("未过关", "不过关", "待整改", "失效")
STATIC_OK = "静态完整"
STATIC_GAP = "待整改-静态缺项"
BLOCK_REASON_CODES = ("BAD_REPORT", "UNKNOWN_SKILL", "REMEDIATE",
                      "INSUFFICIENT_EVIDENCE", "SUSPECTED_OVERLAP")
GATE_AUDIT_KINDS = ("gate_passed", "gate_blocked", "remediation")


class GateError(ValueError):
    """评估闸门违规——显形拒绝。"""


def _now(at: str) -> str:
    return at or "1970-01-01T00:00:00Z"


def _reason(code: str, target: Any, detail: str) -> dict[str, Any]:
    return {"code": code, "target": target, "detail": detail}


def _row_for(report: dict[str, Any], skill_id: str) -> dict[str, Any] | None:
    for row in report.get("skills") or []:
        if isinstance(row, dict) and row.get("name") == skill_id:
            return row
    return None


def _overlapped(report: dict[str, Any], row: dict[str, Any]) -> bool:
    vals: list[Any] = []
    for pair in report.get("overlap_candidates") or []:
        if isinstance(pair, dict):
            vals.extend([pair.get("a"), pair.get("b")])
    return (row.get("path") in vals or row.get("name") in vals
            or row.get("id") in vals)


def check_gate(report: dict[str, Any] | None,
               skill_id: str) -> dict[str, Any]:
    """强制复核：以 T2 报告为准重新推导"该技能是否可进评审复核收件箱"。

    返回 {"allowed": bool, "reasons": [...]}；报告残缺时只拦下不抛错；
    技能不在报告里则显形拒绝（UNKNOWN_SKILL）。
    """
    if not isinstance(report, dict):
        return {"allowed": False,
                "reasons": [_reason("BAD_REPORT", None, "评估报告不是 dict")]}
    if report.get("schema") != SCHEMA:
        return {"allowed": False,
                "reasons": [_reason(
                    "BAD_REPORT", report.get("schema"),
                    f"评估报告 schema 非 {SCHEMA}"
                    f"（PRD-{GATE_PRD}，{GATE_REPO}）")]}
    if not isinstance(report.get("skills"), list):
        return {"allowed": False,
                "reasons": [_reason("BAD_REPORT", skill_id, "报告无 skills 列表")]}
    if not isinstance(report.get("overlap_candidates"), list):
        return {"allowed": False,
                "reasons": [_reason("BAD_REPORT", skill_id,
                                    "报告无 overlap_candidates 列表——缺重叠结果不得放行")]}
    row = _row_for(report, skill_id)
    if row is None:
        raise GateError(f"UNKNOWN_SKILL：报告里无此技能 skill_id={skill_id!r}")
    reasons: list[dict[str, Any]] = []
    static = row.get("static_verdict")
    if static == STATIC_GAP:
        reasons.append(_reason(
            "REMEDIATE", skill_id,
            f"技能 {skill_id!r} 静态缺项：{','.join(row.get('missing') or []) or '见报告'}"))
    elif static != STATIC_OK:
        reasons.append(_reason(
            "BAD_REPORT", skill_id,
            f"技能 {skill_id!r} 静态结论词表外 static_verdict={static!r}"))
    behavior = row.get("behavior_verdict")
    if behavior == BEHAVIOR_PASS:
        pass
    elif behavior in BEHAVIOR_PENDING:
        reasons.append(_reason(
            "INSUFFICIENT_EVIDENCE", skill_id,
            f"技能 {skill_id!r} 行为结论={behavior!r}，未过关：{row.get('behavior_reason')}"))
    elif behavior in BEHAVIOR_FAIL:
        reasons.append(_reason(
            "REMEDIATE", skill_id,
            f"技能 {skill_id!r} 行为未过关（{behavior}）：{row.get('behavior_reason')}"))
    else:
        reasons.append(_reason(
            "BAD_REPORT", skill_id,
            f"技能 {skill_id!r} 行为结论词表外 behavior_verdict={behavior!r}"))
    if _overlapped(report, row):
        reasons.append(_reason(
            "SUSPECTED_OVERLAP", skill_id,
            f"技能 {skill_id!r} 在疑似重叠对里，待人确认（不自动合并）"))
    return {"allowed": not reasons, "reasons": reasons}


def enforce_gate(report: dict[str, Any] | None,
                 skill_id: str) -> dict[str, Any]:
    """过闸：不通过即显形拒绝；通过返回 check_gate 的裁决。"""
    verdict = check_gate(report, skill_id)
    if not verdict["allowed"]:
        codes = "; ".join(
            f"{r['code']}({r['target']})" for r in verdict["reasons"])
        raise GateError(f"GATE_BLOCKED：评估未过关不进评审复核收件箱——{codes}")
    return verdict


def _record_decision(ledger: Any, report: dict[str, Any] | None,
                     skill_id: str, verdict: dict[str, Any],
                     by: str, at: str) -> None:
    """记一条闸门审计；静态缺项或行为未过关被拦时，另追加一条整改条目。"""
    entry = {"kind": "gate_passed" if verdict["allowed"] else "gate_blocked",
             "skill_id": skill_id, "by": by, "at": _now(at),
             "reasons": [r["code"] for r in verdict["reasons"]],
             "targets": [r["target"] for r in verdict["reasons"]]}

    ledger.record(report if isinstance(report, dict) else {}, entry)
    if verdict["allowed"]:
        return
    if not any(r["code"] == "REMEDIATE" for r in verdict["reasons"]):
        return
    reason = next((r["detail"] for r in verdict["reasons"]
                   if r["code"] == "REMEDIATE"), "")
    ledger.record(report if isinstance(report, dict) else {}, {
        "kind": "remediation", "skill_id": skill_id, "by": by,
        "at": _now(at), "reason": reason,
        "evidence": "评估报告（schema 见条目）",
        "due": "待定", "action": "修", "retest": None})


def admit_to_downstream(report: dict[str, Any] | None, skill_id: str, *,
                        ledger: Any = None, by: str,
                        at: str = "") -> dict[str, Any]:
    """评审复核收件箱唯一允许的入口：先过闸，再把裁决写进账本留痕。

    放行返回 {"admitted": 技能准入记录, "verdict": 裁决}；拦截时先记一条
    gate_blocked 审计（绕关尝试有据可查），再显形拒绝。未知技能也先记账
    再拒绝。ledger 给了就必须给 by（审计须署名），否则拒绝入账。
    """
    try:
        verdict = check_gate(report, skill_id)
    except GateError as exc:
        verdict = {"allowed": False,
                   "reasons": [_reason("UNKNOWN_SKILL", skill_id, str(exc))]}
    if ledger is not None:
        if not by:
            raise GateError("GATE_BLOCKED：审计留痕须 by（裁决人必填）")
        _record_decision(ledger, report, skill_id, verdict, by, at)
    if not verdict["allowed"]:
        codes = "; ".join(
            f"{r['code']}({r['target']})" for r in verdict["reasons"])
        raise GateError(f"GATE_BLOCKED：评估未过关不进评审复核收件箱——{codes}")
    row = _row_for(report, skill_id) if isinstance(report, dict) else None
    return {"admitted": {
        "skill_id": skill_id,
        "static_verdict": row.get("static_verdict") if row else None,
        "behavior_verdict": row.get("behavior_verdict") if row else None},
        "verdict": verdict}


def gate_outlet(report: dict[str, Any] | None,
                skill_ids: list[str] | None, *,
                ledger: Any = None, by: str,
                at: str = "") -> dict[str, Any]:
    """加固版批量出口：逐技能过闸，只放行 check_gate 通过的技能。"""
    passed, blocked = [], []
    for skill_id in skill_ids or []:
        try:
            verdict = check_gate(report, skill_id)
        except GateError as exc:
            verdict = {"allowed": False,
                       "reasons": [_reason("UNKNOWN_SKILL", skill_id, str(exc))]}
        if ledger is not None:
            if not by:
                raise GateError("GATE_BLOCKED：审计留痕须 by（裁决人必填）")
            _record_decision(ledger, report, skill_id, verdict, by, at)
        row = _row_for(report, skill_id) if isinstance(report, dict) else None
        if verdict["allowed"]:
            passed.append({
                "skill_id": skill_id,
                "static_verdict": row.get("static_verdict") if row else None,
                "behavior_verdict": row.get("behavior_verdict") if row else None})
        else:
            blocked.append({"skill_id": skill_id, "reasons": verdict["reasons"]})
    return {"schema": GATE_SCHEMA, "passed": passed, "blocked": blocked,
            "blocked_count": len(blocked)}


def format_remediation_line(entry: dict[str, Any]) -> str:
    """整改条目 → remediation 清单的行格式（只渲染，不改历史条目）。"""
    date = str(entry.get("at") or "")[:10] or "未知日期"
    retest = entry.get("retest")
    return (f"- {date} 技能 {entry.get('skill_id')}：{entry.get('reason')} / "
            f"证据（{entry.get('evidence')}）/ 整改期限 {entry.get('due')} / "
            f"建议动作 {entry.get('action')} / 复测结果 {retest or '待复测'}")


class SkillEvaluationLedger:
    """评估闸门留痕账本：JSONL append-only（路径注入），缺件拒绝入账。

    三种条目：gate_passed / gate_blocked（闸门审计）、remediation（整改条目）。
    只追加、不改历史条目；entries() 返回深拷贝，改返回结果不污染账本。
    """

    _REQUIRED = ("skill_id", "kind", "by", "at")

    def __init__(self, path: str | Path | None = None) -> None:
        self._records: list[dict[str, Any]] = []
        self._path = Path(path) if path else None

    def record(self, report: dict[str, Any] | None,
               entry: dict[str, Any]) -> dict[str, Any]:
        report = report if isinstance(report, dict) else {}
        rec = {"schema": GATE_SCHEMA, "prd": report.get("prd"),
               **copy.deepcopy(entry)}
        missing = [k for k in self._REQUIRED
                   if k not in rec or rec.get(k) in (None, "")]
        if missing:
            raise GateError(f"GATE_BLOCKED：账目缺 {missing}")
        self._records.append(copy.deepcopy(rec))
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False,
                                    sort_keys=True) + "\n")
        return dict(rec)

    def entries(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._records)

    def latest_for(self, skill_id: str) -> dict[str, Any] | None:
        found = [r for r in self._records if r.get("skill_id") == skill_id]
        return copy.deepcopy(found[-1]) if found else None
