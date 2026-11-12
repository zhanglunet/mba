# -*- coding: utf-8 -*-
"""PRD-380/T2（trend issue #1884 的 T2 环节）：评审结论验证台最小实现。

按 T1 设计（docs/plans/2026-11-12-prd-380-review-verification-bench-design.md）
§4 落地：

  - verify_score(review, work_snapshots, recheck_fn)：逐条结论快照重放
    验证——recheck_fn 注入式重跑同一评分推导（作品快照只读深拷贝，零新增
    评分逻辑 R2）；重算分数与结论分数一致 → VERIFIED，否则 UNVERIFIED
    （词表封闭）；作品快照指纹与 PRD-352 work_snapshots_digest 同族口径
    （sha16: 前缀规范化摘要）；
  - verify_scores(reviews, work_snapshots, recheck_fn)：复核收件箱来源
    包装（接入点：评分推导产物之后、verify_inbox.collect(low_confidence)
    之前）——UNVERIFIED 拦下不进复核收件箱（R1）；
  - ReviewBenchLedger：机器可读 JSONL 落账（路径注入，append-only R3/R4）；
    八件套缺一 BENCH_INCOMPLETE 拒绝入账；
  - reverify：作品快照/评委包变更二次验证——指纹不符 → BENCH_STALE 拒绝
    复用旧验证（R4 关闭以最新 VERIFIED 为准）。

零 LLM 零网络零子进程零改分词面（R2 不碰分数红线不变）；示例全虚构占位。
测试：tests/unit/test_prd380_t2_review_verify_bench.py
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

BENCH_SCHEMA = "review-verify-bench/v1"
VERDICTS = ("VERIFIED", "UNVERIFIED")
ERROR_CODES = ("BENCH_INCOMPLETE", "BENCH_REPRO_MISMATCH", "BENCH_STALE")


class ReviewBenchError(ValueError):
    """验证台违规——显形拒绝。"""


def snapshots_fingerprint(work_snapshots: list[dict[str, Any]]) -> str:
    """作品快照指纹（sha16: 前缀，与 352 work_snapshots_digest 同族口径）。"""
    canon = json.dumps(work_snapshots, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return "sha16:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def _recusal(code: str, detail: str) -> dict[str, Any]:
    return {"schema": BENCH_SCHEMA, "refused": code, "detail": detail,
            "verdict": None}


def verify_score(review: dict[str, Any],
                 work_snapshots: list[dict[str, Any]],
                 recheck_fn: Callable[[list], list[dict[str, Any]]],
                 *, at: str = "") -> dict[str, Any]:
    """逐条结论快照重放验证（R1/R2）：重算分数与结论一致 → VERIFIED。"""
    if not isinstance(review, dict):
        return _recusal("BENCH_INCOMPLETE", "review 非对象")
    missing = [k for k in ("review_id", "work_id", "kind", "source_ref",
                           "score") if review.get(k) in (None, "")]
    if missing:
        return _recusal("BENCH_INCOMPLETE", f"八件套缺 {missing}")
    if not callable(recheck_fn):
        return _recusal("BENCH_INCOMPLETE", "recheck_fn 未注入")
    rerun = recheck_fn(copy.deepcopy(work_snapshots)) or []
    hit = next((r for r in rerun
                if str(r.get("work_id")) == str(review.get("work_id"))), None)
    score_match = bool(hit and str(hit.get("score")) ==
                       str(review.get("score")))
    return {
        "schema": BENCH_SCHEMA,
        "review_id": review["review_id"],
        "work_id": review["work_id"],
        "kind": review["kind"],
        "source_ref": review["source_ref"],
        "snapshots_fingerprint": snapshots_fingerprint(work_snapshots),
        "review": copy.deepcopy(review),
        "reproduce": {"score_match": score_match,
                      "detail": f"重算 {len(rerun)} 条（占位）"},
        "verdict": "VERIFIED" if score_match else "UNVERIFIED",
        "at": at,
    }


def verify_scores(reviews: list[dict[str, Any]],
                  work_snapshots: list[dict[str, Any]],
                  recheck_fn: Callable[[list], list[dict[str, Any]]],
                  *, at: str = "") -> dict[str, Any]:
    """复核收件箱来源包装（接入点）：UNVERIFIED 拦下不进复核收件箱（R1）。"""
    verified: list[dict[str, Any]] = []
    unverified: list[dict[str, Any]] = []
    for r in reviews or []:
        out = verify_score(r, work_snapshots, recheck_fn, at=at)
        if out.get("refused") or out["verdict"] == "UNVERIFIED":
            unverified.append(out)
        else:
            verified.append(out)
    return {"schema": BENCH_SCHEMA, "verified": verified,
            "unverified": unverified, "unverified_count": len(unverified)}


class ReviewBenchLedger:
    """验证账本（R3/R4）：JSONL append-only；八件套缺一拒绝入账。"""

    _REQUIRED = ("review_id", "work_id", "kind", "source_ref",
                 "snapshots_fingerprint", "review", "verdict")

    def __init__(self, path: str | Path | None = None) -> None:
        self._records: list[dict[str, Any]] = []
        self._path = Path(path) if path else None

    def record(self, out: dict[str, Any], *, at: str = "") -> dict[str, Any]:
        if out.get("refused"):
            raise ReviewBenchError(f"{out['refused']}：{out['detail']}")
        rec = dict(out, at=at)
        missing = [k for k in self._REQUIRED if rec.get(k) in (None, "")]
        if missing:
            raise ReviewBenchError(f"BENCH_INCOMPLETE：账目缺 {missing}")
        if rec["verdict"] not in VERDICTS:
            raise ReviewBenchError(f"BENCH_INCOMPLETE：verdict 词表外 "
                                   f"{rec['verdict']!r}")
        if rec["verdict"] == "VERIFIED" and not rec["reproduce"]["score_match"]:
            raise ReviewBenchError("BENCH_REPRO_MISMATCH：声称 VERIFIED 但"
                                   "重算分数与结论不一致——验证结论与复现"
                                   "证据不一致")
        self._records.append(copy.deepcopy(rec))
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False,
                                    sort_keys=True) + "\n")
        return dict(rec)

    def entries(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._records]

    def latest_for(self, review_id: str) -> dict[str, Any] | None:
        found = [r for r in self._records if r["review_id"] == review_id]
        return dict(found[-1]) if found else None

    def reverify(self, review_id: str,
                 work_snapshots: list[dict[str, Any]],
                 recheck_fn: Callable[[list], list[dict[str, Any]]],
                 *, at: str = "") -> dict[str, Any]:
        """作品快照变更二次验证（R4）：指纹不符 → BENCH_STALE 拒绝复用。"""
        prior = self.latest_for(review_id)
        fp_now = snapshots_fingerprint(work_snapshots)
        if prior and prior["snapshots_fingerprint"] != fp_now:
            return _recusal("BENCH_STALE",
                            f"{review_id} 旧验证作品快照指纹与当前不符——"
                            "快照/评委包变更后须重新验证，旧 VERIFIED 不复用")
        base = {"review_id": review_id,
                "work_id": (prior or {}).get("work_id") or "",
                "kind": (prior or {}).get("kind") or "",
                "source_ref": (prior or {}).get("source_ref") or "",
                "score": ((prior or {}).get("review") or {}).get("score")}
        return self.record(verify_score(base, work_snapshots, recheck_fn,
                                        at=at), at=at)
