"""PRD-485/T3 测试（trend #2347 的 T3 环节）：评委技能评估监督回路闸门。
运行：uv run --with pytest python -m pytest tests/unit/test_skill_evaluation_gate.py -q
覆盖（T1 红线）：只放行行为"过关"且静态完整且非重叠的技能/静态缺项拦下并
追加整改条目/待补测拦下但不进整改清单/未过关拦下进清单/疑似重叠拦下待人
确认/未知技能先记账再拒绝/放行与拦截审计留痕/加固出口批量过闸/整改清单
append-only/词表封闭/AST 零网络/无发布路径/闸门自身不授予通过/真实技能包
只读断言。零网络；全合成占位。
"""
import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path

MOD_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(MOD_DIR))
MODULE_DIR = MOD_DIR

from skill_evaluation import SCHEMA, evaluate  # noqa: E402
from skill_evaluation_gate import (  # noqa: E402
    BEHAVIOR_FAIL, BEHAVIOR_PASS, BEHAVIOR_PENDING, BLOCK_REASON_CODES,
    GATE_AUDIT_KINDS, GATE_SCHEMA, GateError, SkillEvaluationLedger,
    admit_to_downstream, check_gate, enforce_gate, format_remediation_line,
    gate_outlet)

NOW = "2026-11-17T09:00:00Z"
BY = "reviewer（占位）"


def make_report(specs):
    """合成 T2 报告：specs = [(skill_id, static_verdict, behavior_verdict, overlapped)]。"""
    skills = []
    overlapped = []
    for i, spec in enumerate(specs):
        sid, static, behavior = spec[0], spec[1], spec[2]
        skills.append({"name": sid, "path": f"skills/{sid}/SKILL.md",
                       "checks": {}, "missing": [] if static == "静态完整"
                       else ["description（占位）"],
                       "static_verdict": static,
                       "behavior_verdict": behavior,
                       "behavior_reason": "合成占位"})
        if len(spec) > 3 and spec[3]:
            overlapped.append({"a": f"skills/{sid}/SKILL.md",
                                "b": f"skills/other-{i}/SKILL.md",
                                "similarity": 0.9})
    return {"schema": SCHEMA, "skill_count": len(skills),
            "static_complete": sum(1 for s in skills
                                   if s["static_verdict"] == "静态完整"),
            "static_gap": sum(1 for s in skills
                              if s["static_verdict"] != "静态完整"),
            "overlap_candidates": overlapped, "skills": skills}


def codes(verdict):
    return [r["code"] for r in verdict["reasons"]]


OK_ROW = ("skill-a", "静态完整", "过关")
GAP_ROW = ("skill-b", "待整改-静态缺项", "过关")
PENDING_ROW = ("skill-c", "静态完整", "待补测")
FAIL_ROW = ("skill-d", "静态完整", "未过关")


class TestGate(unittest.TestCase):
    def test_passing_skill_allowed(self):
        report = make_report([OK_ROW])
        d = check_gate(report, "skill-a")
        self.assertTrue(d["allowed"])

    def test_static_gap_blocked_with_remediation_code(self):
        report = make_report([GAP_ROW])
        d = check_gate(report, "skill-b")
        self.assertFalse(d["allowed"])
        self.assertIn("REMEDIATE", codes(d))

    def test_behavior_pending_blocked_without_remediation(self):
        report = make_report([PENDING_ROW])
        d = check_gate(report, "skill-c")
        self.assertFalse(d["allowed"])
        self.assertIn("INSUFFICIENT_EVIDENCE", codes(d))
        self.assertNotIn("REMEDIATE", codes(d))

    def test_behavior_fail_blocked_with_remediation(self):
        report = make_report([FAIL_ROW])
        d = check_gate(report, "skill-d")
        self.assertFalse(d["allowed"])
        self.assertIn("REMEDIATE", codes(d))

    def test_overlap_blocked_even_if_passing(self):
        report = make_report([("skill-a", "静态完整", "过关")])
        report["overlap_candidates"] = [
            {"a": "skills/skill-a/SKILL.md", "b": "skills/skill-x/SKILL.md",
             "similarity": 0.9}]
        d = check_gate(report, "skill-a")
        self.assertFalse(d["allowed"])
        self.assertIn("SUSPECTED_OVERLAP", codes(d))

    def test_unknown_skill_raises(self):
        report = make_report([OK_ROW])
        with self.assertRaisesRegex(GateError, "UNKNOWN_SKILL"):
            check_gate(report, "nope")

    def test_bad_reports_blocked(self):
        for bad in [None, "x", {}, {"schema": "other/v1"},
                    {"schema": SCHEMA, "skills": "x"},
                    {"schema": SCHEMA, "skills": []}]:
            d = check_gate(bad, "skill-a")
            self.assertFalse(d["allowed"])
            self.assertIn("BAD_REPORT", codes(d))

    def test_verdict_out_of_vocab_is_bad_report(self):
        report = make_report([("skill-a", "静态完整", "瞎编结论")])
        d = check_gate(report, "skill-a")
        self.assertFalse(d["allowed"])
        self.assertIn("BAD_REPORT", codes(d))

    def test_per_skill_verdict_does_not_leak(self):
        # 按技能认结论：skill-b 静态缺项拦下，不影响 skill-a 放行。
        report = make_report([GAP_ROW, OK_ROW])
        self.assertFalse(check_gate(report, "skill-b")["allowed"])
        self.assertTrue(check_gate(report, "skill-a")["allowed"])

    def test_enforce_gate_raises_and_passes(self):
        with self.assertRaisesRegex(GateError, "GATE_BLOCKED"):
            enforce_gate(make_report([PENDING_ROW]), "skill-c")
        self.assertEqual(
            enforce_gate(make_report([OK_ROW]), "skill-a")["allowed"], True)


class TestLedger(unittest.TestCase):
    def test_admit_records_audit_and_blocks_with_remediation(self):
        with tempfile.TemporaryDirectory() as td:
            led = SkillEvaluationLedger(Path(td) / "gate.jsonl")
            with self.assertRaisesRegex(GateError, "GATE_BLOCKED"):
                admit_to_downstream(make_report([FAIL_ROW]), "skill-d",
                                    ledger=led, by=BY, at=NOW)
            kinds = [e["kind"] for e in led.entries()]
            self.assertEqual(kinds.count("gate_blocked"), 1)
            self.assertEqual(kinds.count("remediation"), 1)
            self.assertEqual(led.latest_for("skill-d")["kind"], "remediation")

    def test_pending_block_records_audit_without_remediation(self):
        with tempfile.TemporaryDirectory() as td:
            led = SkillEvaluationLedger(Path(td) / "gate.jsonl")
            with self.assertRaises(GateError):
                admit_to_downstream(make_report([PENDING_ROW]), "skill-c",
                                    ledger=led, by=BY, at=NOW)
            kinds = [e["kind"] for e in led.entries()]
            self.assertIn("gate_blocked", kinds)
            self.assertNotIn("remediation", kinds)

    def test_pass_records_audit(self):
        with tempfile.TemporaryDirectory() as td:
            led = SkillEvaluationLedger(Path(td) / "gate.jsonl")
            out = admit_to_downstream(make_report([OK_ROW]), "skill-a",
                                      ledger=led, by=BY, at=NOW)
            self.assertTrue(out["verdict"]["allowed"])
            self.assertEqual([e["kind"] for e in led.entries()],
                             ["gate_passed"])

    def test_ledger_requires_by(self):
        led = SkillEvaluationLedger(None)
        with self.assertRaisesRegex(GateError, "by"):
            admit_to_downstream(make_report([OK_ROW]), "skill-a",
                                ledger=led, by="", at=NOW)

    def test_ledger_append_only_and_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "gate.jsonl"
            led = SkillEvaluationLedger(path)
            led.record({"prd": 485}, {"kind": "gate_passed",
                                          "skill_id": "s", "by": BY, "at": NOW})
            led.record({"prd": 485}, {"kind": "gate_blocked",
                                          "skill_id": "s2", "by": BY, "at": NOW})
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)
            snapshot = led.entries()
            snapshot[0]["kind"] = "改（占位）"
            self.assertEqual(led.entries()[0]["kind"], "gate_passed")

    def test_unknown_skill_recorded_then_refused(self):
        with tempfile.TemporaryDirectory() as td:
            led = SkillEvaluationLedger(Path(td) / "gate.jsonl")
            with self.assertRaisesRegex(GateError, "GATE_BLOCKED"):
                admit_to_downstream(make_report([OK_ROW]), "ghost",
                                    ledger=led, by=BY, at=NOW)
            self.assertEqual(led.latest_for("ghost")["kind"], "gate_blocked")

    def test_format_remediation_line(self):
        line = format_remediation_line({"skill_id": "s", "at": NOW,
                                        "reason": "静态缺项", "evidence": "报告",
                                        "due": "待定", "action": "修"})
        self.assertIn("技能 s", line)
        self.assertIn("整改期限 待定", line)


class TestOutlet(unittest.TestCase):
    def test_gate_outlet_blocks_all_pending(self):
        out = gate_outlet(make_report([PENDING_ROW, OK_ROW]),
                          ["skill-c", "skill-a", "ghost"], by=BY, at=NOW)
        self.assertEqual([p["skill_id"] for p in out["passed"]], ["skill-a"])
        self.assertEqual(out["blocked_count"], 2)
        self.assertIn("UNKNOWN_SKILL",
                      codes({"reasons": out["blocked"][1]["reasons"]}) if False else
                      [r["code"] for r in out["blocked"][1]["reasons"]])

    def test_gate_outlet_with_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            led = SkillEvaluationLedger(Path(td) / "g.jsonl")
            out = gate_outlet(make_report([OK_ROW, GAP_ROW]),
                              ["skill-a", "skill-b"], ledger=led, by=BY, at=NOW)
            self.assertEqual(len(out["passed"]), 1)
            self.assertEqual(len(out["blocked"]), 1)
            kinds = [e["kind"] for e in led.entries()]
            self.assertEqual(kinds.count("gate_passed"), 1)
            self.assertEqual(kinds.count("gate_blocked"), 1)
            self.assertEqual(kinds.count("remediation"), 1)


class TestRealInventory(unittest.TestCase):
    def test_real_pack_all_pending_blocked(self):
        # 今天的实情：真实技能包行为结论全是"待补测"，闸门全拦——不是闸门严，
        # 是对照跑分还没补（T5 补，重评"过关"后才能放行）。
        report = evaluate(Path("."))
        self.assertEqual(report["skill_count"], 54)
        self.assertTrue(all(s["behavior_verdict"] in BEHAVIOR_PENDING
                            for s in report["skills"]))
        for row in report["skills"]:
            d = check_gate(report, row["name"])
            self.assertFalse(d["allowed"])
            self.assertIn("INSUFFICIENT_EVIDENCE", codes(d))


class TestRedlines(unittest.TestCase):
    def test_vocab_closed(self):
        self.assertEqual(BEHAVIOR_PASS, "过关")
        for w in BEHAVIOR_PENDING + BEHAVIOR_FAIL:
            self.assertIsInstance(w, str)
        self.assertEqual(set(BLOCK_REASON_CODES),
                         {"BAD_REPORT", "UNKNOWN_SKILL", "REMEDIATE",
                           "INSUFFICIENT_EVIDENCE", "SUSPECTED_OVERLAP"})
        self.assertEqual(set(GATE_AUDIT_KINDS),
                         {"gate_passed", "gate_blocked", "remediation"})

    def test_no_publish_path(self):
        # 评估不碰发布：闸门模块不得含发布/删除技能的函数名。
        src = (MODULE_DIR / "skill_evaluation_gate.py").read_text(encoding="utf-8")
        for word in ("publish", "delete_skill", "remove_skill", "merge_skill"):
            self.assertNotIn(word, src.lower())

    def test_ast_zero_network(self):
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        for name in ("skill_evaluation.py", "skill_evaluation_gate.py"):
            src = (MODULE_DIR / name).read_text(encoding="utf-8")
            imported = set()
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, ast.Import):
                    imported.update(a.name.split(".")[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            self.assertFalse(imported & banned, name)


if __name__ == "__main__":
    unittest.main()
