# -*- coding: utf-8 -*-
"""PRD-449/T2 测试（trend #2166 的 T2 环节）：评审监督台。
运行：uv run --with pytest python -m pytest tests/unit/test_prd449_t2_review_supervision_bench.py -q
（仓库根执行；纯 unittest 用例，python3 -m unittest 亦可）
覆盖（T1 §2 + §4）：出炉→待审→点头全程三件套落账/批注锚定步骤/发回打包
反馈单/改回新版本重新待审不继承点头/硬关口（未点头不进下游）/JSONL 落库/
查询清单与详情/AST 零网络/监督台全程不改分数。零网络；全合成占位。
"""
import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

MOD_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from review_supervision_bench import (  # noqa: E402
    DECISIONS, ERROR_CODES, FEEDBACK_TYPES, SCHEMA, STATUSES,
    SupervisionBenchError, SupervisionBenchLedger, add_annotation,
    can_enter_downstream, decide, downstream_outlet, get_detail, list_items,
    mark_viewed, new_item, resubmit, send_back, submit, timeline,
)

NOW = "2026-11-15T09:00:00Z"
LATER = "2026-11-15T10:00:00Z"
CONTENT = {"subject": "品牌（占位）", "scores": {"视角A（占位）": 8, "视角B（占位）": 6}, "total": 7}
PROCESS = [{"step": "视角A打分（占位）", "at": NOW, "detail": "理由（占位）", "status": "ok"}, {"step": "汇总（占位）", "at": NOW, "detail": "取舍（占位）", "status": "ok"}]


def fresh():
    it = new_item("sc-001", CONTENT, PROCESS, at=NOW)
    return submit(it, at=NOW)


class TestLifecycle(unittest.TestCase):
    def test_new_item_draft_version_1(self):
        it = new_item("sc-001", CONTENT, PROCESS, at=NOW)
        self.assertEqual(it["status"], "draft")
        self.assertEqual(it["version"], 1)
        self.assertEqual(it["progress"][0]["event"], "created")
        self.assertEqual(it["annotations"], [])
        self.assertEqual(it["feedbacks"], [])

    def test_submit_draft_to_in_review(self):
        it = submit(new_item("sc-001", CONTENT, PROCESS, at=NOW), at=LATER)
        self.assertEqual(it["status"], "in-review")
        self.assertEqual(it["progress"][-1]["event"], "submitted")

    def test_submit_twice_refused(self):
        it = fresh()
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_BAD_TRANSITION"):
            submit(it, at=LATER)

    def test_approve_from_draft_refused(self):
        it = new_item("sc-001", CONTENT, PROCESS, at=NOW)
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_BAD_TRANSITION"):
            decide(it, "approve", at=NOW)

    def test_mark_viewed_only_logs_progress(self):
        it = fresh()
        before = copy.deepcopy(it["content"])
        mark_viewed(it, at=LATER)
        self.assertEqual(it["progress"][-1]["event"], "viewed")
        self.assertEqual(it["content"], before)
        self.assertEqual(it["status"], "in-review")

    def test_bad_process_step_refused(self):
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_INCOMPLETE"):
            new_item("sc-001", CONTENT, [{"detail": "缺 step 名"}], at=NOW)

    def test_vocab_closed(self):
        self.assertEqual(set(STATUSES), set(("draft", "in-review", "approved", "sent-back", "rejected")))
        self.assertEqual(set(DECISIONS), set(("approve", "send-back", "reject")))
        self.assertEqual(set(FEEDBACK_TYPES), set(("re-score", "change-judge-pack", "add-basis")))


class TestAnnotations(unittest.TestCase):
    def test_add_annotation_anchored_to_step(self):
        it = fresh()
        ann = add_annotation(it, step="视角A打分（占位）", text="来源存疑（占位）", at=LATER)
        self.assertEqual(ann["step"], "视角A打分（占位）")
        self.assertEqual(ann["annotation_id"], "an-001")
        self.assertEqual(it["progress"][-1]["event"], "annotated")

    def test_annotation_does_not_change_content(self):
        it = fresh()
        before = copy.deepcopy(it["content"])
        add_annotation(it, text="整条批注（占位）", at=LATER)
        self.assertEqual(it["content"], before)

    def test_annotation_unknown_step_refused(self):
        it = fresh()
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_BAD_ANNOTATION"):
            add_annotation(it, step="不存在的步骤", text="x", at=LATER)

    def test_annotation_empty_text_refused(self):
        it = fresh()
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_BAD_ANNOTATION"):
            add_annotation(it, text="  ", at=LATER)

    def test_annotation_after_approve_refused(self):
        it = fresh()
        decide(it, "approve", at=LATER)
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_BAD_TRANSITION"):
            add_annotation(it, text="太晚了（占位）", at=LATER)


class TestSendBackResubmit(unittest.TestCase):
    def test_send_back_packs_feedback(self):
        it = fresh()
        ann = add_annotation(it, step="视角A打分（占位）", text="请换源（占位）", at=NOW)
        fb = send_back(it, feedback_type="re-score", text="换一个来源重跑（占位）",
                       reason="来源不可靠（占位）", annotation_ids=[ann["annotation_id"]],
                       at=LATER)
        self.assertEqual(it["status"], "sent-back")
        self.assertEqual(fb["type"], "re-score")
        self.assertEqual(fb["annotation_ids"], [ann["annotation_id"]])
        self.assertEqual(fb["version"], 1)

    def test_send_back_bad_type_refused(self):
        it = fresh()
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_BAD_FEEDBACK"):
            send_back(it, feedback_type="no-such-type", text="x", reason="r", at=LATER)

    def test_send_back_no_reason_refused(self):
        it = fresh()
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_BAD_FEEDBACK"):
            send_back(it, feedback_type="re-score", text="x", reason="  ", at=LATER)

    def test_send_back_unknown_annotation_refused(self):
        it = fresh()
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_BAD_FEEDBACK"):
            send_back(it, feedback_type="re-score", text="x", reason="r",
                      annotation_ids=["an-999"], at=LATER)

    def test_decide_send_back_delegates(self):
        it = fresh()
        decide(it, "send-back", reason="请改（占位）", feedback_type="re-score",
               text="改一下（占位）", at=LATER)
        self.assertEqual(it["status"], "sent-back")
        self.assertEqual(len(it["feedbacks"]), 1)

    def test_resubmit_new_version_back_to_review(self):
        it = fresh()
        send_back(it, feedback_type="re-score", text="改（占位）", reason="r", at=NOW)
        out = resubmit(it, content={"subject": "品牌（占位）", "scores": {"视角A（占位）": 8, "视角B（占位）": 7}, "total": 7}, process=PROCESS,
                       diff_summary="换了来源（占位）", at=LATER)
        self.assertEqual(out["version"], 2)
        self.assertEqual(out["status"], "in-review")
        self.assertFalse(can_enter_downstream(out))
        self.assertEqual(len(out["versions"]), 2)
        self.assertEqual(out["versions"][0]["version"], 1)

    def test_resubmit_without_send_back_refused(self):
        it = fresh()
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_BAD_TRANSITION"):
            resubmit(it, content=CONTENT, process=PROCESS,
                     diff_summary="x", at=LATER)

    def test_resubmit_without_diff_refused(self):
        it = fresh()
        send_back(it, feedback_type="re-score", text="改（占位）", reason="r", at=NOW)
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_INCOMPLETE"):
            resubmit(it, content=CONTENT, process=PROCESS, diff_summary=" ", at=LATER)


class TestDecisions(unittest.TestCase):
    def test_approve_enters_downstream(self):
        it = fresh()
        decide(it, "approve", at=LATER)
        self.assertEqual(it["status"], "approved")
        self.assertTrue(can_enter_downstream(it))

    def test_unknown_decision_refused(self):
        it = fresh()
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_BAD_TRANSITION"):
            decide(it, "whatever", at=LATER)

    def test_reject_needs_reason(self):
        it = fresh()
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_BAD_TRANSITION"):
            decide(it, "reject", reason="  ", at=LATER)
        decide(it, "reject", reason="评分失真（占位）", at=LATER)
        self.assertEqual(it["status"], "rejected")
        self.assertFalse(can_enter_downstream(it))


class TestGateOutlet(unittest.TestCase):
    def test_gate_blocks_every_non_approved_status(self):
        for st in ["draft", "in-review", "sent-back", "rejected"]:
            self.assertFalse(can_enter_downstream({"status": st}), st)
        self.assertTrue(can_enter_downstream({"status": "approved"}))

    def test_outlet_only_passes_approved(self):
        ok = fresh()
        decide(ok, "approve", at=LATER)
        wait = fresh()
        out = downstream_outlet([ok, wait])
        self.assertEqual(len(out["passed"]), 1)
        self.assertEqual(out["blocked_count"], 1)
        self.assertEqual(out["blocked"][0]["status"], "in-review")


class TestLedger(unittest.TestCase):
    def test_record_and_jsonl_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bench" / "log.jsonl"
            led = SupervisionBenchLedger(path)
            it = fresh()
            decide(it, "approve", at=LATER)
            led.record(it)
            self.assertEqual(len(led.entries()), 1)
            self.assertEqual(led.latest_for("sc-001")["status"], "approved")
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["score_id"], "sc-001")

    def test_record_missing_field_refused(self):
        led = SupervisionBenchLedger(None)
        bad = fresh()
        del bad["feedbacks"]
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_INCOMPLETE"):
            led.record(bad)

    def test_record_bad_status_refused(self):
        led = SupervisionBenchLedger(None)
        bad = fresh()
        bad["status"] = "no-such-status"
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_BAD_STATUS"):
            led.record(bad)

    def test_record_empty_progress_refused(self):
        led = SupervisionBenchLedger(None)
        bad = fresh()
        bad["progress"] = []
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_INCOMPLETE"):
            led.record(bad)


class TestQuery(unittest.TestCase):
    def test_list_items_filters_by_status(self):
        ok = fresh()
        decide(ok, "approve", at=LATER)
        wait = fresh()
        self.assertEqual(len(list_items([ok, wait], status="approved")), 1)
        self.assertEqual(len(list_items([ok, wait])), 2)
        self.assertEqual(list_items([ok, wait], status="approved")[0]["score_id"], "sc-001")

    def test_list_items_bad_status_refused(self):
        with self.assertRaisesRegex(SupervisionBenchError, "BENCH_BAD_STATUS"):
            list_items([], status="no-such-status")

    def test_detail_timeline_covers_all_three(self):
        it = fresh()
        add_annotation(it, step="视角A打分（占位）", text="批注（占位）", at=NOW)
        send_back(it, feedback_type="re-score", text="改（占位）", reason="r", at=LATER)
        det = get_detail(it)
        kinds = {r["kind"] for r in det["timeline"]}
        self.assertEqual(kinds, {"progress", "annotation", "feedback"})
        self.assertEqual(det["item"]["score_id"], "sc-001")
        self.assertEqual(timeline(it)[0]["at"], NOW)


class TestRedline(unittest.TestCase):
    def test_ast_zero_network_zero_subprocess(self):
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        src = MOD_DIR / "review_supervision_bench.py"
        tree = ast.parse(src.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse(imported & banned, imported & banned)

    def test_error_codes_closed(self):
        self.assertEqual(set(ERROR_CODES), {
            "BENCH_INCOMPLETE", "BENCH_BAD_STATUS", "BENCH_BAD_TRANSITION",
            "BENCH_BAD_FEEDBACK", "BENCH_BAD_ANNOTATION"})

class TestScoresUntouched(unittest.TestCase):
    def test_full_cycle_leaves_scores_untouched(self):
        it = fresh()
        before = copy.deepcopy(it["content"])
        add_annotation(it, step="视角A打分（占位）", text="分存疑（占位）", at=NOW)
        send_back(it, feedback_type="re-score", text="重评（占位）", reason="r",
                  at=NOW)
        resubmit(it, content=CONTENT, process=PROCESS,
                 diff_summary="重评（占位）", at=LATER)
        decide(it, "approve", at=LATER)
        self.assertEqual(it["content"]["scores"], before["scores"])
        self.assertEqual(it["content"]["total"], before["total"])


if __name__ == "__main__":
    unittest.main()
