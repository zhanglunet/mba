# -*- coding: utf-8 -*-
"""PRD-449/T3 测试（trend #2167 的 T3 环节）：评审监督台监督回路闸门。
运行：uv run --with pytest python -m pytest tests/unit/test_prd449_t3_review_supervision_gate.py -q
（仓库根执行；纯 unittest 用例，python3 -m unittest 亦可）
覆盖（T1 §2.3 + §4）：已点头放行、未点头（draft / in-review / sent-back / rejected）一律拦截且留痕/
放行裁决绑定版本、改回重审不继承点头/批量过闸只放行 approved 且与 T2 出口一致/
无放行开关参数/闸门不改对象/裁决日志 JSONL/AST 零网络/监督台全程不改分数。零网络；全合成占位。
"""
import ast
import copy
import inspect
import json
import sys
import tempfile
import unittest
from pathlib import Path

MOD_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(MOD_DIR))
from review_supervision_bench import (  # noqa: E402
    STATUSES, SupervisionBenchError, can_enter_downstream, decide,
    downstream_outlet, new_item, resubmit, send_back, submit,
)
from review_supervision_gate import (  # noqa: E402
    ERROR_CODES, SCHEMA, GateBlockedError, SupervisionGate,
)

NOW = "2026-11-15T09:00:00Z"
LATER = "2026-11-15T10:00:00Z"
CONTENT = {"subject": "品牌（占位）", "scores": {"视角A（占位）": 8, "视角B（占位）": 6}, "total": 7}
PROCESS = [{"step": "视角A打分（占位）", "at": NOW, "detail": "理由（占位）", "status": "ok"}, {"step": "汇总（占位）", "at": NOW, "detail": "取舍（占位）", "status": "ok"}]
BLOCKED_STATUSES = ["draft", "in-review", "sent-back", "rejected"]


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


def blocked_item(status):
    """造一个处于指定未点头状态的对象（改回/否决走真实流转，其余直接置状态）。"""
    if status == "draft":
        return new_item("sc-001", CONTENT, PROCESS, at=NOW)
    if status == "in-review":
        return fresh()
    if status == "sent-back":
        return sent_back()
    if status == "rejected":
        it = fresh()
        decide(it, "reject", reason="可疑评分（占位）", at=LATER)
        return it
    raise AssertionError(f"unknown blocked status {status!r}")



class TestAdmitAllowed(unittest.TestCase):
    def test_approved_admitted(self):
        gate = SupervisionGate()
        it = approved()
        verdict = gate.admit(it, at=LATER)
        self.assertEqual(verdict["decision"], "allowed")
        self.assertEqual(verdict["item_id"], "sc-001")
        self.assertEqual(verdict["status"], "approved")
        self.assertEqual(verdict["version"], 1)
        self.assertIn("品牌审计报告", verdict["reason"])
        self.assertEqual(verdict["schema"], SCHEMA)

    def test_allowed_attempt_is_logged(self):
        gate = SupervisionGate()
        gate.admit(approved(), by="gate", at=LATER)
        self.assertEqual(len(gate.decisions()), 1)
        self.assertEqual(gate.allowed_decisions()[0]["decision"], "allowed")
        self.assertEqual(gate.allowed_decisions()[0]["by"], "gate")


class TestAdmitBlocked(unittest.TestCase):
    def test_every_non_approved_status_blocked(self):
        for st in BLOCKED_STATUSES:
            gate = SupervisionGate()
            with self.assertRaisesRegex(GateBlockedError, "GATE_BLOCKED", msg=st):
                gate.admit(blocked_item(st), at=LATER)

    def test_blocked_reason_names_status(self):
        gate = SupervisionGate()
        with self.assertRaisesRegex(GateBlockedError, "in-review"):
            gate.admit(fresh(), at=LATER)

    def test_blocked_attempt_is_logged(self):
        gate = SupervisionGate()
        with self.assertRaises(GateBlockedError):
            gate.admit(fresh(), at=LATER)
        self.assertEqual(len(gate.decisions()), 1)
        self.assertEqual(gate.blocked_decisions()[0]["decision"], "blocked")
        self.assertEqual(gate.blocked_decisions()[0]["status"], "in-review")
        self.assertIn("GATE_BLOCKED", gate.blocked_decisions()[0]["reason"])

    def test_non_dict_blocked(self):
        gate = SupervisionGate()
        for bad in (None, "sig", ["x"], 42):
            with self.assertRaisesRegex(GateBlockedError, "GATE_BLOCKED"):
                gate.admit(bad, at=LATER)
        self.assertEqual(len(gate.blocked_decisions()), 4)

    def test_missing_id_or_status_blocked(self):
        gate = SupervisionGate()
        no_id = approved()
        del no_id["score_id"]
        with self.assertRaisesRegex(GateBlockedError, "GATE_BLOCKED"):
            gate.admit(no_id, at=LATER)
        no_status = approved()
        del no_status["status"]
        with self.assertRaisesRegex(GateBlockedError, "GATE_BLOCKED"):
            gate.admit(no_status, at=LATER)
        bad_status = approved()
        bad_status["status"] = "no-such-status"
        with self.assertRaisesRegex(GateBlockedError, "词表外"):
            gate.admit(bad_status, at=LATER)

    def test_gate_error_is_bench_error(self):
        self.assertTrue(issubclass(GateBlockedError, SupervisionBenchError))


class TestNoMutation(unittest.TestCase):
    def test_admit_does_not_mutate_item(self):
        gate = SupervisionGate()
        for it in (approved(), fresh()):
            before = copy.deepcopy(it)
            try:
                gate.admit(it, at=LATER)
            except GateBlockedError:
                pass
            self.assertEqual(it, before)

    def test_batch_does_not_mutate_items(self):
        gate = SupervisionGate()
        items = [approved(), fresh()]
        before = copy.deepcopy(items)
        gate.admit_batch(items, at=LATER)
        self.assertEqual(items, before)

    def test_gate_never_touches_scores(self):
        gate = SupervisionGate()
        it = approved()
        gate.admit(it, at=LATER)
        self.assertEqual(it["content"]["scores"], {"视角A（占位）": 8, "视角B（占位）": 6})
        self.assertEqual(it["content"]["total"], 7)



class TestBatch(unittest.TestCase):
    def test_mixed_batch_only_approved_pass(self):
        gate = SupervisionGate()
        ok, wait, back = approved(), fresh(), sent_back()
        out = gate.admit_batch([ok, wait, back], at=LATER)
        self.assertEqual(out["admitted_count"], 1)
        self.assertEqual(out["blocked_count"], 2)
        self.assertEqual(out["admitted"][0]["score_id"], "sc-001")
        self.assertEqual({b["status"] for b in out["blocked"]},
                         {"in-review", "sent-back"})
        self.assertEqual(len(gate.decisions()), 3)

    def test_empty_batch(self):
        gate = SupervisionGate()
        out = gate.admit_batch([], at=LATER)
        self.assertEqual(out["admitted_count"], 0)
        self.assertEqual(out["blocked_count"], 0)
        self.assertEqual(gate.decisions(), [])

    def test_batch_agrees_with_t2_outlet(self):
        gate = SupervisionGate()
        ok, wait = approved(), fresh()
        out = gate.admit_batch([ok, wait], at=LATER)
        outlet = downstream_outlet([ok, wait])
        self.assertEqual([a["score_id"] for a in out["admitted"]],
                         [p["score_id"] for p in outlet["passed"]])
        self.assertEqual(out["blocked_count"], outlet["blocked_count"])



class TestVersionBinding(unittest.TestCase):
    def test_verdict_current_for_approved(self):
        gate = SupervisionGate()
        it = approved()
        verdict = gate.admit(it, at=LATER)
        self.assertTrue(gate.is_verdict_current(it, verdict))

    def test_resubmit_does_not_inherit_approval(self):
        gate = SupervisionGate()
        it = fresh()
        send_back(it, feedback_type="re-score", text="改（占位）", reason="r",
                  at=NOW)
        resubmit(it, content=CONTENT, process=PROCESS,
                 diff_summary="换了来源（占位）", at=LATER)
        self.assertEqual(it["version"], 2)
        self.assertEqual(it["status"], "in-review")
        with self.assertRaisesRegex(GateBlockedError, "GATE_BLOCKED"):
            gate.admit(it, at=LATER)
        decide(it, "approve", at=LATER)
        verdict = gate.admit(it, at=LATER)
        self.assertEqual(verdict["version"], 2)
        self.assertTrue(gate.is_verdict_current(it, verdict))

    def test_verdict_stale_after_version_change(self):
        gate = SupervisionGate()
        it = approved()
        verdict = gate.admit(it, at=LATER)
        self.assertTrue(gate.is_verdict_current(it, verdict))
        it["version"] = 2  # 模拟新版本到达：旧放行裁决即失效，须重新点头
        self.assertFalse(gate.is_verdict_current(it, verdict))

    def test_verdict_current_rejects_blocked_and_mismatched(self):
        gate = SupervisionGate()
        it = approved()
        verdict = gate.admit(it, at=LATER)
        other = approved()
        other["score_id"] = "sc-001-other"
        self.assertFalse(gate.is_verdict_current(other, verdict))
        self.assertFalse(gate.is_verdict_current(it, {"decision": "blocked"}))
        self.assertFalse(gate.is_verdict_current(None, verdict))
        self.assertFalse(gate.is_verdict_current(it, None))


class TestNoBypass(unittest.TestCase):
    def test_no_switch_parameter(self):
        banned = {"force", "bypass", "override", "skip_gate", "allow_all"}
        for fn in (SupervisionGate.admit, SupervisionGate.admit_batch):
            params = set(inspect.signature(fn).parameters)
            self.assertFalse(params & banned, (fn.__name__, params & banned))

    def test_switch_kwarg_rejected(self):
        gate = SupervisionGate()
        with self.assertRaises(TypeError):
            gate.admit(fresh(), force=True, at=LATER)

    def test_no_switch_identifier_in_source(self):
        src = (MOD_DIR / "review_supervision_gate.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.arg):
                names.add(node.arg)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
        self.assertFalse(names & {"force", "bypass", "override", "skip_gate"},
                         names & {"force", "bypass", "override", "skip_gate"})


class TestGateLog(unittest.TestCase):
    def test_jsonl_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "gate" / "decisions.jsonl"
            gate = SupervisionGate(path)
            gate.admit(approved(), at=LATER)
            with self.assertRaises(GateBlockedError):
                gate.admit(fresh(), at=LATER)
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)
            rows = [json.loads(x) for x in lines]
            self.assertEqual([r["decision"] for r in rows], ["allowed", "blocked"])
            self.assertEqual(rows[0]["item_id"], "sc-001")

    def test_decisions_returns_copies(self):
        gate = SupervisionGate()
        gate.admit(approved(), at=LATER)
        rows = gate.decisions()
        rows[0]["decision"] = "tampered"
        self.assertEqual(gate.decisions()[0]["decision"], "allowed")

    def test_report_counts(self):
        gate = SupervisionGate()
        gate.admit(approved(), at=LATER)
        with self.assertRaises(GateBlockedError):
            gate.admit(fresh(), at=LATER)
        with self.assertRaises(GateBlockedError):
            gate.admit(sent_back(), at=LATER)
        rep = gate.report()
        self.assertEqual(rep["total"], 3)
        self.assertEqual(rep["allowed"], 1)
        self.assertEqual(rep["blocked"], 2)
        self.assertEqual(rep["by_status"]["approved"], 1)
        self.assertEqual(rep["by_status"]["in-review"], 1)
        self.assertEqual(rep["by_status"]["sent-back"], 1)


class TestRedline(unittest.TestCase):
    def test_ast_zero_network_zero_subprocess(self):
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        for mod in ("review_supervision_gate.py", "review_supervision_bench.py"):
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
        self.assertEqual(set(ERROR_CODES), {"GATE_BLOCKED", "GATE_INCOMPLETE"})



if __name__ == "__main__":
    unittest.main()
