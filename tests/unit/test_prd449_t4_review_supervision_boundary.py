# -*- coding: utf-8 -*-
"""PRD-449/T4 测试（trend #2168 的 T4 环节）：评审监督台划界断言。
运行：python3 -m pytest tests/unit/test_prd449_t4_review_supervision_boundary.py -q
（仓库根执行；纯 unittest 用例，python3 -m unittest 亦可）
覆盖（T1 §2.7 + PRD 非目标 + T4 issue）：管辖内全程（看/批注/裁决/发回/
改回重审）落界内/邻域 PRD（["PRD-426", "PRD-380", "PRD-366"]）逐项划界在外/监督记录含越界
声称即拒绝/闸门放行只证监督点头、不证真假·评审·收件箱/人不下场改内容
（版本不动改内容即越界，resubmit 版本 +1 通过）/批量划界留痕/AST 零网络
/监督台全程不改分数。零网络；全合成占位。
"""
import ast
import copy
import json
import sys
import unittest
from pathlib import Path

MOD_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(MOD_DIR))
from review_supervision_bench import (  # noqa: E402
    STATUSES, SupervisionBenchError, can_enter_downstream, decide,
    new_item, resubmit, send_back, submit,
)
from review_supervision_gate import SupervisionGate  # noqa: E402
from review_supervision_boundary import (  # noqa: E402
    DOES_NOT_CERTIFY, ERROR_CODES, FORBIDDEN_CLAIM_KEYS, IN_SCOPE,
    OUT_OF_SCOPE, SCHEMA, SupervisionBoundaryError, assert_no_human_direct_edit,
    assert_supervision_only, audit_batch, boundary_report,
    certify_gate_verdict, classify_neighbour, out_of_scope_prds,
)

NOW = "2026-11-15T09:00:00Z"
LATER = "2026-11-15T10:00:00Z"
CONTENT = {"subject": "品牌（占位）", "scores": {"视角A（占位）": 8, "视角B（占位）": 6}, "total": 7}
PROCESS = [{"step": "视角A打分（占位）", "at": NOW, "detail": "理由（占位）", "status": "ok"}, {"step": "汇总（占位）", "at": NOW, "detail": "取舍（占位）", "status": "ok"}]
NEIGHBOUR_PRDS = ["PRD-426", "PRD-380", "PRD-366"]


def fresh():
    it = new_item("sc-001", CONTENT, PROCESS, at=NOW)
    return submit(it, at=NOW)


def approved():
    it = fresh()
    decide(it, "approve", at=LATER)
    return it


def sent_back():
    it = fresh()
    send_back(it, feedback_type="re-score", text="改（占位）", reason="r", at=NOW)
    return it


class TestInScope(unittest.TestCase):
    def test_supervision_record_is_in_scope(self):
        stmt = assert_supervision_only(approved())
        self.assertTrue(stmt["in_scope"])
        self.assertEqual(stmt["item_id"], "sc-001")
        self.assertEqual(stmt["status"], "approved")
        self.assertEqual(stmt["version"], 1)
        self.assertEqual(stmt["schema"], SCHEMA)

    def test_every_status_is_supervision_governed(self):
        for it in (fresh(), approved(), sent_back()):
            self.assertTrue(assert_supervision_only(it)["in_scope"])

    def test_in_scope_covers_full_loop(self):
        for ev in ("viewed", "annotated", "decided", "sent-back", "resubmitted"):
            self.assertIn(ev, IN_SCOPE)

    def test_boundary_report_lists_governs(self):
        rep = boundary_report(approved())
        self.assertTrue(rep["in_boundary"])
        self.assertEqual(rep["item_id"], "sc-001")
        self.assertTrue(rep["checks"]["has_progress"])
        self.assertTrue(rep["checks"]["has_annotations_ledger"])
        self.assertTrue(rep["checks"]["has_feedbacks_ledger"])
        self.assertTrue(rep["checks"]["has_versions"])
        self.assertTrue(rep["checks"]["process_visible"])

    def test_boundary_report_after_full_loop(self):
        it = fresh()
        decide(it, "send-back", reason="r", feedback_type="re-score",
               text="改（占位）", at=NOW)
        resubmit(it, content=CONTENT, process=PROCESS,
                 diff_summary="改完回来（占位）", at=LATER)
        decide(it, "approve", at=LATER)
        rep = boundary_report(it)
        self.assertTrue(rep["in_boundary"])
        self.assertEqual(rep["version"], 2)
        self.assertEqual(rep["status"], "approved")


class TestOutOfScopeNeighbours(unittest.TestCase):
    def test_each_neighbour_is_out_of_scope(self):
        for prd in NEIGHBOUR_PRDS:
            got = classify_neighbour(prd)
            self.assertIsNotNone(got, prd)
            self.assertFalse(got["in_scope"])
            self.assertEqual(got["prd"], prd)
            self.assertTrue(got["reason"])

    def test_out_of_scope_prds_lists_all(self):
        self.assertEqual(sorted(out_of_scope_prds()), sorted(NEIGHBOUR_PRDS))

    def test_unknown_neighbour_unclassified(self):
        self.assertIsNone(classify_neighbour("PRD-9999"))

    def test_boundary_report_lists_out_of_scope(self):
        rep = boundary_report(fresh())
        listed = [o["prd"] for o in rep["out_of_scope"]]
        self.assertEqual(sorted(listed), sorted(NEIGHBOUR_PRDS))
        for o in rep["out_of_scope"]:
            self.assertFalse(o["in_scope"])


class TestForbiddenClaims(unittest.TestCase):
    def test_each_forbidden_key_crosses_boundary(self):
        for key in FORBIDDEN_CLAIM_KEYS:
            it = approved()
            it[key] = True
            with self.assertRaisesRegex(SupervisionBoundaryError,
                                        "BOUNDARY_CROSSED", msg=key):
                assert_supervision_only(it)

    def test_truth_claim_rejected(self):
        it = approved()
        it["truth_verified"] = True
        with self.assertRaisesRegex(SupervisionBoundaryError, "BOUNDARY_CROSSED"):
            assert_supervision_only(it)
        with self.assertRaisesRegex(SupervisionBoundaryError, "BOUNDARY_CROSSED"):
            boundary_report(it)

    def test_review_claim_rejected(self):
        it = approved()
        it["review_passed"] = True
        with self.assertRaisesRegex(SupervisionBoundaryError, "BOUNDARY_CROSSED"):
            assert_supervision_only(it)
        self.assertEqual(audit_batch([it])["crossed_count"], 1)

    def test_non_dict_or_incomplete_rejected(self):
        for bad in (None, "sig", ["x"], 42):
            with self.assertRaisesRegex(SupervisionBoundaryError, "BOUNDARY_INCOMPLETE"):
                assert_supervision_only(bad)
        it = approved()
        del it["progress"]
        with self.assertRaisesRegex(SupervisionBoundaryError, "BOUNDARY_INCOMPLETE"):
            assert_supervision_only(it)
        bad_status = approved()
        bad_status["status"] = "no-such-status"
        with self.assertRaisesRegex(SupervisionBoundaryError, "BOUNDARY_INCOMPLETE"):
            assert_supervision_only(bad_status)

    def test_boundary_error_is_bench_error(self):
        self.assertTrue(issubclass(SupervisionBoundaryError, SupervisionBenchError))

    def test_audit_batch_does_not_raise(self):
        good, bad = approved(), approved()
        bad["verified"] = True
        out = audit_batch([good, bad, None])
        self.assertEqual(out["in_boundary_count"], 1)
        self.assertEqual(out["crossed_count"], 2)
        self.assertEqual(len(out["crossed"]), 2)
        self.assertEqual(out["schema"], SCHEMA)


class TestGateCertification(unittest.TestCase):
    def test_allowed_verdict_certifies_supervision_only(self):
        gate = SupervisionGate()
        it = approved()
        verdict = gate.admit(it, at=LATER)
        stmt = certify_gate_verdict(it, verdict)
        self.assertEqual(stmt["certifies"], "supervision-approved-only")
        self.assertIn("品牌审计报告", stmt["certifies_text"])
        self.assertEqual(stmt["item_id"], "sc-001")
        self.assertEqual(stmt["version"], 1)

    def test_certification_lists_what_it_does_not_certify(self):
        self.assertIn("truth", " ".join(DOES_NOT_CERTIFY).lower())
        gate = SupervisionGate()
        stmt = certify_gate_verdict(approved(), gate.admit(approved(), at=LATER))
        self.assertEqual(stmt["does_not_certify"], list(DOES_NOT_CERTIFY))

    def test_stale_verdict_cannot_certify(self):
        gate = SupervisionGate()
        it = approved()
        verdict = gate.admit(it, at=LATER)
        it["version"] = 2
        with self.assertRaisesRegex(SupervisionBoundaryError, "BOUNDARY_CROSSED"):
            certify_gate_verdict(it, verdict)

    def test_blocked_verdict_cannot_certify(self):
        with self.assertRaisesRegex(SupervisionBoundaryError, "BOUNDARY_CROSSED"):
            certify_gate_verdict(fresh(), {"decision": "blocked"})

    def test_boundary_report_carries_certification(self):
        gate = SupervisionGate()
        it = approved()
        verdict = gate.admit(it, at=LATER)
        rep = boundary_report(it, verdict=verdict)
        self.assertEqual(rep["gate_certification"]["certifies"],
                         "supervision-approved-only")

    def test_gate_and_boundary_agree_on_downstream(self):
        gate = SupervisionGate()
        ok, wait = approved(), fresh()
        self.assertTrue(can_enter_downstream(ok))
        self.assertFalse(can_enter_downstream(wait))
        self.assertIsNotNone(certify_gate_verdict(ok, gate.admit(ok, at=LATER)))
        with self.assertRaisesRegex(SupervisionBoundaryError, "BOUNDARY_CROSSED"):
            certify_gate_verdict(wait, {"decision": "blocked"})


class TestNoHumanDirectEdit(unittest.TestCase):
    def test_direct_content_edit_same_version_crosses(self):
        before = approved()
        after = copy.deepcopy(before)
        after["content"] = dict(after["content"])
        after["content"]["_edited"] = "人直接改（占位）"
        with self.assertRaisesRegex(SupervisionBoundaryError, "BOUNDARY_CROSSED"):
            assert_no_human_direct_edit(before, after)

    def test_direct_process_edit_same_version_crosses(self):
        before = approved()
        after = copy.deepcopy(before)
        after["process"] = [{"step": "人改的步骤（占位）", "at": LATER,
                             "detail": "（占位）", "status": "ok"}]
        with self.assertRaisesRegex(SupervisionBoundaryError, "BOUNDARY_CROSSED"):
            assert_no_human_direct_edit(before, after)

    def test_agent_resubmit_version_bump_passes(self):
        before = sent_back()
        after = copy.deepcopy(before)
        resubmit(after, content=CONTENT, process=PROCESS,
                 diff_summary="换了来源（占位）", at=LATER)
        out = assert_no_human_direct_edit(before, after)
        self.assertFalse(out["direct_edit"])
        self.assertEqual(out["version"], 2)

    def test_unchanged_passes(self):
        it = approved()
        out = assert_no_human_direct_edit(it, copy.deepcopy(it))
        self.assertFalse(out["direct_edit"])

    def test_non_dict_rejected(self):
        with self.assertRaisesRegex(SupervisionBoundaryError, "BOUNDARY_INCOMPLETE"):
            assert_no_human_direct_edit(None, approved())


class TestRedline(unittest.TestCase):
    def test_ast_zero_network_zero_subprocess(self):
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        for mod in ("review_supervision_boundary.py", "review_supervision_bench.py", "review_supervision_gate.py"):
            src = MOD_DIR / mod
            tree = ast.parse(src.read_text(encoding="utf-8"))
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(a.name.split(".")[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            self.assertFalse(imported & banned, (mod, imported & banned))

    def test_error_codes_closed(self):
        self.assertEqual(set(ERROR_CODES), {"BOUNDARY_CROSSED", "BOUNDARY_INCOMPLETE"})

    def test_boundary_never_touches_scores(self):
        it = approved()
        boundary_report(it)
        self.assertEqual(it["content"]["scores"], {"视角A（占位）": 8, "视角B（占位）": 6})
        self.assertEqual(it["content"]["total"], 7)



if __name__ == "__main__":
    unittest.main()
