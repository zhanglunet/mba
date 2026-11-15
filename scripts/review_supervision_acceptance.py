# -*- coding: utf-8 -*-
"""PRD-449/T5（trend issue #2169 的 T5 环节）：评审监督台验收试运行。

按 T1 设计（docs/plans/2026-11-15-prd-449-review-supervision-bench-design.md）§4
验收标准，把 T2 最小实现（review_supervision_bench.py）、T3 闸门
（review_supervision_gate.py）、T4 划界断言（review_supervision_boundary.py）
串起来全链跑一遍端到端验证，不改前几步的设计与代码，只新增本验收脚本：

  - 全链：可疑评分出炉 → 人看 → 批注（锚定打分步骤）→ 一键发回重评 →
    agent 改完回来（版本 +1、重新待审）→ 人点头 → 过闸 → 划界证明 →
    进品牌审计报告；三件套（进度/批注/发回反馈）全程落账可查；
  - 反例：待审/发回中/已否决/草稿四种未点头状态一律拦在下游之外；
  - 旧裁决不放行新版：v1 的放行裁决对 v2 失效，须重新点头、重新过闸；
  - 划界：监督记录含越界声称即拒绝；人直接改内容（版本不动）即越界。

运行：python3 scripts/review_supervision_acceptance.py（仓库根执行；
只跑内存里的合成占位数据，零网络零子进程，退出码 0 即全链跑通）。
测试：tests/unit/test_prd449_t5_review_supervision_acceptance.py
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from review_supervision_bench import (  # noqa: E402
    SupervisionBenchError, SupervisionBenchLedger, add_annotation, decide,
    downstream_outlet, get_detail, mark_viewed, new_item, resubmit, submit,
)
from review_supervision_boundary import (  # noqa: E402
    SupervisionBoundaryError, assert_no_human_direct_edit,
    assert_supervision_only, audit_batch, boundary_report,
    certify_gate_verdict,
)
from review_supervision_gate import GateBlockedError, SupervisionGate  # noqa: E402

SCHEMA = "review-supervision-acceptance/v1"
NOW = "2026-11-16T09:00:00Z"
LATER = "2026-11-16T10:00:00Z"
CONTENT_V1 = {"subject": "品牌（占位）", "scores": {"视角A（占位）": 8, "视角B（占位）": 6}, "total": 7}
CONTENT_V2 = {"subject": "品牌（占位）", "scores": {"视角A（占位）": 7, "视角B（占位）": 6}, "total": 6.5}
PROCESS_V1 = [{"step": "视角A打分（占位）", "at": NOW, "detail": "理由（占位）", "status": "ok"},
              {"step": "汇总（占位）", "at": NOW, "detail": "取舍（占位）", "status": "ok"}]
PROCESS_V2 = [{"step": "视角A打分（占位）", "at": LATER, "detail": "重评理由（占位）", "status": "ok"},
              {"step": "汇总（占位）", "at": LATER, "detail": "重算取舍（占位）", "status": "ok"}]


def _scenario(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def happy_path() -> tuple[dict[str, Any], dict[str, Any]]:
    """全链主场景：出炉 → 看 → 批注 → 发回 → 改回 → 点头 → 过闸 → 入账。

    返回（最终评分对象，场景小结）。
    """
    gate = SupervisionGate()
    ledger = SupervisionBenchLedger()
    item = new_item("sc-001", CONTENT_V1, PROCESS_V1, at=NOW)
    submit(item, at=NOW)
    mark_viewed(item, at=NOW)
    ann = add_annotation(item, step="视角A打分（占位）", text="8 分偏高，请重评（占位）", at=NOW)
    decide(item, "send-back", reason="视角A分数存疑（占位）",
           feedback_type="re-score", text="请按批注重评视角A（占位）",
           annotation_ids=[ann["annotation_id"]], at=NOW)
    assert item["status"] == "sent-back" and item["version"] == 1
    resubmit(item, content=CONTENT_V2, process=PROCESS_V2,
             diff_summary="视角A 8→7 分，总分 7→6.5（占位）", at=LATER)
    assert item["status"] == "in-review" and item["version"] == 2
    decide(item, "approve", at=LATER)
    assert item["status"] == "approved"
    verdict = gate.admit(item, at=LATER)
    stmt = certify_gate_verdict(item, verdict)
    rep = boundary_report(item, verdict)
    ledger.record(item)
    outlet = downstream_outlet([item])
    detail = get_detail(item)
    kinds = sorted({row["kind"] for row in detail["timeline"]})
    assert outlet["passed"] and outlet["blocked_count"] == 0
    assert kinds == ["annotation", "feedback", "progress"]
    assert stmt["certifies"] == "supervision-approved-only"
    assert rep["in_boundary"] is True
    return item, _scenario(
        "happy-path-full-chain", True,
        "sc-001：出炉→看→批注→发回→改回v2→点头→过闸→入账→进品牌审计报告；"
        f"进度{len(item['progress'])}条/批注{len(item['annotations'])}条/反馈"
        f"{len(item['feedbacks'])}条，时间线三类齐全")


def unapproved_blocked() -> dict[str, Any]:
    """反例：四种未点头状态一律拦在下游之外（闸门抛错 + 出口拦下留痕）。"""
    gate = SupervisionGate()
    items: list[dict[str, Any]] = []
    draft = new_item("sc-draft", CONTENT_V1, PROCESS_V1, at=NOW)
    items.append(draft)
    in_review = new_item("sc-review", CONTENT_V1, PROCESS_V1, at=NOW)
    submit(in_review, at=NOW)
    items.append(in_review)
    sent_back = new_item("sc-back", CONTENT_V1, PROCESS_V1, at=NOW)
    submit(sent_back, at=NOW)
    ann = add_annotation(sent_back, text="请重评（占位）", at=NOW)
    decide(sent_back, "send-back", reason="存疑（占位）", feedback_type="re-score",
           text="请重评（占位）", annotation_ids=[ann["annotation_id"]], at=NOW)
    items.append(sent_back)
    rejected = new_item("sc-rej", CONTENT_V1, PROCESS_V1, at=NOW)
    submit(rejected, at=NOW)
    decide(rejected, "reject", reason="不采纳（占位）", at=NOW)
    items.append(rejected)
    blocked_states = []
    for it in items:
        try:
            gate.admit(it, at=NOW)
        except GateBlockedError:
            blocked_states.append(it["status"])
        else:  # pragma: no cover - 闸门漏放即验收失败
            raise AssertionError(f"闸门放行了未点头的 {it['score_id']}")
    outlet = downstream_outlet(items)
    assert blocked_states == ["draft", "in-review", "sent-back", "rejected"]
    assert outlet["passed"] == [] and outlet["blocked_count"] == 4
    return _scenario(
        "unapproved-blocked", True,
        "draft/in-review/sent-back/rejected 四态：闸门各抛 GATE_BLOCKED 一次，"
        "出口 passed 为空、blocked_count=4")


def old_verdict_does_not_admit_new_version() -> dict[str, Any]:
    """旧裁决不放行新版：v1 放行裁决对 v2 失效，划界证明亦拒绝。"""
    gate = SupervisionGate()
    item = new_item("sc-002", CONTENT_V1, PROCESS_V1, at=NOW)
    submit(item, at=NOW)
    decide(item, "approve", at=NOW)
    verdict_v1 = gate.admit(item, at=NOW)
    assert gate.is_verdict_current(item, verdict_v1) is True
    v2 = copy.deepcopy(item)
    v2["version"] = 2
    assert gate.is_verdict_current(v2, verdict_v1) is False
    try:
        certify_gate_verdict(v2, verdict_v1)
    except SupervisionBoundaryError:
        pass
    else:  # pragma: no cover - 旧裁决被当成新版点头即验收失败
        raise AssertionError("v1 放行裁决被划界证明接受为 v2 的点头")
    return _scenario(
        "old-verdict-does-not-admit-new-version", True,
        "v1 放行裁决对 v1 有效、对 v2 失效；划界证明拒绝把 v1 裁决当 v2 点头")


def boundary_holds() -> dict[str, Any]:
    """划界：越界声称拒绝入界；人直接改内容（版本不动）即越界。"""
    item, _ = happy_path()
    assert_supervision_only(item)
    crossed = copy.deepcopy(item)
    crossed["verified"] = True
    try:
        assert_supervision_only(crossed)
    except SupervisionBoundaryError:
        pass
    else:  # pragma: no cover - 越界声称未被拒绝即验收失败
        raise AssertionError("含 verified 声称的记录通过了划界断言")
    before = copy.deepcopy(item)
    edited = copy.deepcopy(item)
    edited["content"] = dict(CONTENT_V1)
    try:
        assert_no_human_direct_edit(before, edited)
    except SupervisionBoundaryError:
        pass
    else:  # pragma: no cover - 人直接改内容未被拒绝即验收失败
        raise AssertionError("版本不动改内容通过了人不下场改断言")
    batch = audit_batch([item, crossed])
    assert batch["in_boundary_count"] == 1 and batch["crossed_count"] == 1
    return _scenario(
        "boundary-holds", True,
        "已点头记录在界内；含 verified 声称的记录越界拒绝；版本不动改内容越界"
        "拒绝；批量划界 1 条在界内、1 条越界")


def three_records_complete() -> dict[str, Any]:
    """三件套落账：进度/批注/反馈缺一不可，账本缺件拒绝入账。"""
    item, _ = happy_path()
    assert item["progress"] and item["annotations"] and item["feedbacks"]
    assert item["versions"] and len(item["versions"]) == 2
    ledger = SupervisionBenchLedger()
    ledger.record(item)
    assert ledger.latest_for("sc-001")["status"] == "approved"
    broken = copy.deepcopy(item)
    broken["progress"] = []
    try:
        ledger.record(broken)
    except SupervisionBenchError:
        pass
    else:  # pragma: no cover - 缺进度仍入账即验收失败
        raise AssertionError("进度为空的记录进了账本")
    return _scenario(
        "three-records-complete", True,
        "sc-001 进度/批注/反馈/双版本齐全；账本入账成功、最新一条为 approved v2；"
        "进度为空的记录拒绝入账")


def run_acceptance() -> dict[str, Any]:
    """跑完全部验收场景，返回验收报告（全过 verdict 为“全链跑通”）。"""
    scenarios = [
        happy_path()[1],
        unapproved_blocked(),
        old_verdict_does_not_admit_new_version(),
        boundary_holds(),
        three_records_complete(),
    ]
    passed = sum(1 for s in scenarios if s["passed"])
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "verdict": "全链跑通" if passed == len(scenarios) else "验收失败",
        "scenarios": scenarios,
        "passed_count": passed,
        "total_count": len(scenarios),
    }
    return report


def main() -> int:
    report = run_acceptance()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "全链跑通" else 1


if __name__ == "__main__":
    raise SystemExit(main())
