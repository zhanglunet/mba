# -*- coding: utf-8 -*-
"""PRD-352/T2（trend issue #1631 的 T2 环节）：评审结论重放包最小实现。

按 T1 设计（docs/plans/2026-11-11-prd-352-review-replay-design.md）
§3.1/§3.2/§4 实现：

  - make_pack(reviews, work_snapshots, *, judgepack_version)：从评审决策
    记录构建重放包（R1 三件套）——input_fingerprint（作品快照 digest +
    评委包版本）、decisions（评分与理由逐条，分数原字符串零格式化 R4），
    output（findings 状态汇总）；缺任一 PACK_INCOMPLETE；
  - replay(pack, work_snapshots, score_fn, *, judgepack_version)：重放三步
    （§3.2）——①指纹复核（作品快照 digest 或评委包版本不符 →
    REPLAY_INPUT_DRIFT 拒绝）②注入式 score_fn 深拷贝复算评分推导
    （规则可判定部分；重放不改分零人工改分入口 R2——结果只做比对）
    ③decisions 逐字节比对 → REPLAY_OK / REPLAY_MISMATCH（首分歧条显形，
    R3 零静默换新评分）；
  - ReplayLedger：append-only（R4）；
  - **零改分**（R2）：本模块零分数写入（T4 AST 预埋：零评分写导入）。

零网络；示例全虚构占位。
测试：tests/unit/test_prd352_t2_review_replay.py
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Callable

PACK_SCHEMA = "review-replay-pack/v1"
ERROR_CODES = ("REPLAY_INPUT_DRIFT", "REPLAY_MISMATCH", "PACK_INCOMPLETE")
_DECISION_KEYS = ("work_id", "score", "why")


def _digest(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"))
    return "sha16:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def work_snapshots_digest(snapshots: list[dict[str, Any]]) -> str:
    return _digest(snapshots)


def make_pack(reviews: list[dict[str, Any]],
              work_snapshots: list[dict[str, Any]], *,
              judgepack_version: str) -> dict[str, Any]:
    """从评审决策记录构建重放包（R1 三件套）。"""
    clean = []
    for r in reviews or []:
        if not all(r.get(k) is not None for k in _DECISION_KEYS):
            return {"schema": PACK_SCHEMA, "refused": "PACK_INCOMPLETE",
                    "detail": f"评审缺 {_DECISION_KEYS} 任一——拒绝入账"}
        clean.append({k: r.get(k) for k in ("work_id", "score", "why")})
    if not clean or not work_snapshots or not judgepack_version:
        return {"schema": PACK_SCHEMA, "refused": "PACK_INCOMPLETE",
                "detail": "reviews/work_snapshots/judgepack_version 缺失"}
    return {
        "schema": PACK_SCHEMA,
        "input_fingerprint": {
            "work_snapshots_digest": work_snapshots_digest(work_snapshots),
            "judgepack_version": judgepack_version},
        "decisions": clean,
        "output": {"scores": [c["score"] for c in clean]},
    }


def _refusal(code: str, detail: str) -> dict[str, Any]:
    return {"schema": PACK_SCHEMA, "refused": code, "detail": detail,
            "verdict": None}


def replay(pack: dict[str, Any], work_snapshots: list[dict[str, Any]],
           score_fn: Callable[[list], list[dict[str, Any]]], *,
           judgepack_version: str) -> dict[str, Any]:
    """重放三步（§3.2）：评分推导复算（R2 零改分——结果只比对），对不上
    显形（R3）。"""
    fp = pack.get("input_fingerprint") or {}
    if (not fp or pack.get("refused") or not pack.get("decisions")
            or not pack.get("output")):
        return _refusal("PACK_INCOMPLETE", "重放包三件套不齐")
    if (work_snapshots_digest(work_snapshots)
            != fp.get("work_snapshots_digest")
            or judgepack_version != fp.get("judgepack_version")):
        return _refusal("REPLAY_INPUT_DRIFT",
                        "作品快照指纹或评委包版本与包不符——拒绝重放"
                        "（防新快照冒充当时）")
    rerun = score_fn(copy.deepcopy(work_snapshots)) or []
    norm = [{k: r.get(k) for k in ("work_id", "score", "why")} for r in rerun]
    for i, want in enumerate(pack["decisions"]):
        got = norm[i] if i < len(norm) else None
        if got != want:
            return {"schema": PACK_SCHEMA, "refused": None,
                    "verdict": "REPLAY_MISMATCH",
                    "evidence": {"first_divergence_index": i,
                                 "want": want, "got": got},
                    "rerun_count": len(norm)}
    if len(norm) != len(pack["decisions"]):
        return {"schema": PACK_SCHEMA, "refused": None,
                "verdict": "REPLAY_MISMATCH",
                "evidence": {"first_divergence_index": len(norm),
                             "why": "决策条数不一致"},
                "rerun_count": len(norm)}
    return {"schema": PACK_SCHEMA, "refused": None, "verdict": "REPLAY_OK",
            "evidence": None, "rerun_count": len(norm)}


class ReplayLedger:
    """重放账本（R4）：append-only 只增不删。"""

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    def record(self, pack: dict[str, Any], verdict: dict[str, Any], *,
               at: str) -> dict[str, Any]:
        entry = {"at": at,
                 "pack_fingerprint": copy.deepcopy(pack.get("input_fingerprint")),
                 "verdict": verdict.get("verdict") or verdict.get("refused"),
                 "evidence": copy.deepcopy(verdict.get("evidence"))}
        self._entries.append(entry)
        return dict(entry)

    @property
    def entries(self) -> list[dict[str, Any]]:
        return [dict(e) for e in self._entries]
