# -*- coding: utf-8 -*-
"""PRD-449/T2（trend issue #2166 的 T2 环节）：评审监督台最小实现。

按 T1 设计（docs/plans/2026-11-15-prd-449-review-supervision-bench-design.md）§2 落地：
  - 三件套落账：进度记录 + 批注记录 + 发回反馈记录，统一用 score_id 串联；
  - 状态机：出炉（draft）→ 待审（in-review）→ 已点头（approved）→ 进入品牌审计报告；发回（sent-back）→ 改完 → 回到待审；否决（rejected）→ 归档；只有 approved 能进下游（品牌审计报告），
    发回后 agent 改回的新版本重新待审、不继承上一轮点头；
  - 批注锚定到具体打分步骤，只附加不覆盖原文；发回反馈单含类型、
    正文与关联批注；人只批注和裁决，不下场改内容。
  - 监督台不碰分数：只做呈现、批注、裁决与发回，不修改任何分数，不改动
    评委包与评审流程；分数的改动只能由 agent 在发回回路里完成、再回来重审。
零网络零子进程；示例全虚构占位。
测试：tests/unit/test_prd449_t2_review_supervision_bench.py
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

SCHEMA = "review-supervision-bench/v1"
STATUSES = ("draft", "in-review", "approved", "sent-back", "rejected")
DECISIONS = ("approve", "send-back", "reject")
FEEDBACK_TYPES = ("re-score", "change-judge-pack", "add-basis")
ERROR_CODES = ("BENCH_INCOMPLETE", "BENCH_BAD_STATUS", "BENCH_BAD_TRANSITION",
               "BENCH_BAD_FEEDBACK", "BENCH_BAD_ANNOTATION")


class SupervisionBenchError(ValueError):
    """监督台违规——显形拒绝。"""


def _validate_process(process: Any) -> list[dict[str, Any]]:
    """过程步骤校验：每步须有 step 名；步状态只认 ok / refused。"""
    steps: list[dict[str, Any]] = []
    for i, st in enumerate(process or []):
        if not isinstance(st, dict) or not str(st.get("step", "")):
            raise SupervisionBenchError(f"BENCH_INCOMPLETE：过程第 {i} 步缺 step")
        status = st.get("status", "ok")
        if status not in ("ok", "refused"):
            raise SupervisionBenchError(f"BENCH_BAD_STATUS：过程步状态 {status!r} 词表外")
        steps.append({"step": str(st["step"]), "at": str(st.get("at", "")),
                      "detail": str(st.get("detail", "")), "status": status})
    return steps


def _progress(item: dict[str, Any], event: str, *, by: str, at: str) -> None:
    item["progress"].append({"event": event, "by": by, "at": at})


def new_item(item_id: str, content: dict[str, Any], process: Any, *, at: str = "") -> dict[str, Any]:
    """新建一条监督对象：出炉，状态 draft，版本 1。"""
    steps = _validate_process(process)
    item: dict[str, Any] = {
        "schema": SCHEMA, "score_id": str(item_id),
        "content": copy.deepcopy(content), "process": steps,
        "status": "draft", "version": 1,
        "versions": [{"version": 1, "content": copy.deepcopy(content),
                      "process": copy.deepcopy(steps), "at": at}],
        "progress": [], "annotations": [], "feedbacks": [],
    }
    _progress(item, "created", by="agent", at=at)
    return item


def submit(item: dict[str, Any], *, by: str = "agent", at: str = "") -> dict[str, Any]:
    """出炉 → 待审。"""
    if item["status"] != "draft":
        raise SupervisionBenchError(f"BENCH_BAD_TRANSITION：{item['status']} 不能提交待审")
    item["status"] = "in-review"
    _progress(item, "submitted", by=by, at=at)
    return dict(item)


def mark_viewed(item: dict[str, Any], *, by: str = "human", at: str = "") -> dict[str, Any]:
    """人查看：只记进度，不改状态、不改内容。"""
    if item["status"] in ("rejected", "closed"):
        raise SupervisionBenchError(f"BENCH_BAD_TRANSITION：{item['status']} 已归档，不可再看")
    _progress(item, "viewed", by=by, at=at)
    return dict(item)


def add_annotation(item: dict[str, Any], *, step: str | None = None, text: str,
                   by: str = "human", at: str = "") -> dict[str, Any]:
    """批注：锚定到具体过程步骤（step 缺省为整条），只附加不覆盖原文。"""
    if item["status"] in ("approved", "rejected", "closed"):
        raise SupervisionBenchError(f"BENCH_BAD_TRANSITION：{item['status']} 状态不可再批注")
    if not str(text or "").strip():
        raise SupervisionBenchError("BENCH_BAD_ANNOTATION：批注文本为空")
    if step is not None and step not in [s["step"] for s in item["process"]]:
        raise SupervisionBenchError(f"BENCH_BAD_ANNOTATION：锚定步骤 {step!r} 不存在")
    ann: dict[str, Any] = {"annotation_id": f"an-{len(item['annotations']) + 1:03d}",
                          "step": step, "text": str(text), "by": by, "at": at}
    item["annotations"].append(ann)
    _progress(item, "annotated", by=by, at=at)
    return dict(ann)


def send_back(item: dict[str, Any], *, feedback_type: str, text: str, reason: str,
              annotation_ids: Any = (), by: str = "human", at: str = "") -> dict[str, Any]:
    """一键发回：批注与反馈单打包发回 agent；状态 → sent-back。"""
    if item["status"] != "in-review":
        raise SupervisionBenchError(f"BENCH_BAD_TRANSITION：{item['status']} 状态不可发回")
    if feedback_type not in FEEDBACK_TYPES:
        raise SupervisionBenchError(f"BENCH_BAD_FEEDBACK：反馈类型 {feedback_type!r} 词表外")
    if not str(text or "").strip():
        raise SupervisionBenchError("BENCH_BAD_FEEDBACK：反馈正文为空")
    if not str(reason or "").strip():
        raise SupervisionBenchError("BENCH_BAD_FEEDBACK：发回必须写理由")
    known = {a["annotation_id"] for a in item["annotations"]}
    for aid in annotation_ids or []:
        if aid not in known:
            raise SupervisionBenchError(f"BENCH_BAD_FEEDBACK：关联批注 {aid!r} 不存在")
    fb: dict[str, Any] = {"feedback_id": f"fb-{len(item['feedbacks']) + 1:03d}",
                          "type": feedback_type, "text": str(text),
                          "reason": str(reason),
                          "annotation_ids": list(annotation_ids or []),
                          "version": item["version"], "by": by, "at": at}
    item["feedbacks"].append(fb)
    item["status"] = "sent-back"
    _progress(item, "sent-back", by=by, at=at)
    return dict(fb)


def decide(item: dict[str, Any], decision: str, *, reason: str = "", by: str = "human",
           at: str = "", feedback_type: str | None = None, text: str | None = None,
           annotation_ids: Any = ()) -> dict[str, Any]:
    """裁决：点头 / 发回 / 否决。发回走 send_back（一点发回即打包反馈单）。"""
    if decision not in DECISIONS:
        raise SupervisionBenchError(f"BENCH_BAD_TRANSITION：裁决 {decision!r} 词表外")
    if item["status"] != "in-review":
        raise SupervisionBenchError(f"BENCH_BAD_TRANSITION：{item['status']} 状态不可裁决")
    if decision == "approve":
        item["status"] = "approved"
        _progress(item, "approved", by=by, at=at)
        return dict(item)
    if decision == "reject":
        if not str(reason or "").strip():
            raise SupervisionBenchError("BENCH_BAD_TRANSITION：否决必须写理由")
        item["status"] = "rejected"
        _progress(item, "rejected", by=by, at=at)
        return dict(item)
    send_back(item, feedback_type=feedback_type or "", text=text or "",
              reason=reason, annotation_ids=annotation_ids, by=by, at=at)
    return dict(item)


def resubmit(item: dict[str, Any], *, content: dict[str, Any], process: Any,
             diff_summary: str, by: str = "agent", at: str = "") -> dict[str, Any]:
    """agent 改完回来：新版本挂在同一条下，重新待审，不继承上一轮点头。"""
    if item["status"] != "sent-back":
        raise SupervisionBenchError("BENCH_BAD_TRANSITION：只有发回中的可改回")
    if not str(diff_summary or "").strip():
        raise SupervisionBenchError("BENCH_INCOMPLETE：改回须附差异摘要")
    steps = _validate_process(process)
    new_version = item["version"] + 1
    item["version"] = new_version
    item["content"] = copy.deepcopy(content)
    item["process"] = steps
    item["versions"].append({"version": new_version,
                             "content": copy.deepcopy(content),
                             "process": copy.deepcopy(steps), "at": at,
                             "diff_summary": str(diff_summary)})
    item["status"] = "in-review"
    _progress(item, "resubmitted", by=by, at=at)
    return dict(item)


def can_enter_downstream(item: Any) -> bool:
    """硬关口：只有 approved 能进下游；其余一律拦下。"""
    return isinstance(item, dict) and item.get("status") == "approved"


def downstream_outlet(items: Any) -> dict[str, Any]:
    """下游出口包装：只放行 approved；其余拦下留痕（带状态与原因）。"""
    passed, blocked = [], []
    for it in items or []:
        if can_enter_downstream(it):
            passed.append(copy.deepcopy(it))
        else:
            blocked.append({"score_id": it.get("score_id"), "status": it.get("status"),
                            "reason": "未点头，不进下游"})
    out: dict[str, Any] = {"schema": SCHEMA, "passed": passed, "blocked": blocked,
                           "blocked_count": len(blocked)}
    return out


def list_items(items: Any, *, status: str | None = None) -> list[dict[str, Any]]:
    """查询清单：按状态过滤（只读，不改原表）。"""
    if status is not None and status not in STATUSES:
        raise SupervisionBenchError(f"BENCH_BAD_STATUS：状态 {status!r} 词表外")
    return [copy.deepcopy(it) for it in (items or [])
            if status is None or it.get("status") == status]


def timeline(item: dict[str, Any]) -> list[dict[str, Any]]:
    """三件套时间线：进度 + 批注 + 发回反馈，按 at 排序（同 at 保序）。"""
    rows = ([dict(r, kind="progress") for r in item.get("progress", [])]
            + [dict(a, kind="annotation") for a in item.get("annotations", [])]
            + [dict(f, kind="feedback") for f in item.get("feedbacks", [])])
    rows.sort(key=lambda r: str(r.get("at", "")))
    return rows


def get_detail(item: dict[str, Any]) -> dict[str, Any]:
    """查询详情：对象 + 过程 + 批注 + 反馈时间线（深拷贝只读）。"""
    return {"item": copy.deepcopy(item), "timeline": timeline(item)}


class SupervisionBenchLedger:
    """三件套账本：JSONL append-only（路径注入），缺件拒绝入账。"""

    _REQUIRED = ("score_id", "status", "version", "progress", "annotations",
                 "feedbacks", "versions")

    def __init__(self, path: str | Path | None = None) -> None:
        self._records: list[dict[str, Any]] = []
        self._path = Path(path) if path else None

    def record(self, item: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(item, dict) or item.get("refused"):
            raise SupervisionBenchError("BENCH_INCOMPLETE：入账对象不是监督记录")
        missing = [k for k in self._REQUIRED if k not in item]
        if missing:
            raise SupervisionBenchError(f"BENCH_INCOMPLETE：账目缺 {missing}")
        if item.get("status") not in STATUSES:
            raise SupervisionBenchError("BENCH_BAD_STATUS：状态词表外")
        if not isinstance(item.get("version"), int) or item["version"] < 1:
            raise SupervisionBenchError("BENCH_INCOMPLETE：版本号非法")
        if not item.get("progress"):
            raise SupervisionBenchError("BENCH_INCOMPLETE：进度记录为空")
        rec = copy.deepcopy(item)
        self._records.append(rec)
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
        return dict(rec)

    def entries(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._records]

    def latest_for(self, item_id: str) -> dict[str, Any] | None:
        found = [r for r in self._records if r.get("score_id") == item_id]
        return dict(found[-1]) if found else None
