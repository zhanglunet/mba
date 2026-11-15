# -*- coding: utf-8 -*-
"""PRD-449/T5 测试（trend #2169 的 T5 环节）：评审监督台验收试运行。
运行：python3 -m pytest tests/unit/test_prd449_t5_review_supervision_acceptance.py -q
（仓库根执行；纯 unittest 用例，python3 -m unittest 亦可）
覆盖（T1 §4 验收标准 + T5 issue）：全链跑通（出炉→看→批注→发回→改回
v2→点头→过闸→划界证明→进品牌审计报告，三件套齐全）/四种未点头状态
一律拦在下游之外/旧裁决不放行新版/划界断言全程成立/三件套缺件拒绝
入账/验收脚本本身标准库-only、零网络零子进程。零网络；全合成占位。
"""
import ast
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

MOD_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(MOD_DIR))
from review_supervision_acceptance import (  # noqa: E402
    CONTENT_V1, PROCESS_V1, SCHEMA, boundary_holds, happy_path,
    old_verdict_does_not_admit_new_version, run_acceptance,
    three_records_complete, unapproved_blocked,
)
from review_supervision_bench import (  # noqa: E402
    decide, downstream_outlet, new_item, submit,
)
from review_supervision_gate import SupervisionGate  # noqa: E402

NOW = "2026-11-16T09:00:00Z"
ACC_PATH = MOD_DIR / "review_supervision_acceptance.py"
STDLIB_ALLOW = {"__future__", "copy", "json", "pathlib", "sys", "typing"}


class TestAcceptanceVerdict(unittest.TestCase):
    def test_run_acceptance_all_scenarios_pass(self):
        """验收总 verdict 为“全链跑通”，5 个场景全过。"""
        report = run_acceptance()
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["verdict"], "全链跑通")
        self.assertEqual(report["passed_count"], report["total_count"])
        self.assertEqual(report["total_count"], 5)
        self.assertEqual(
            [s["name"] for s in report["scenarios"]],
            ["happy-path-full-chain", "unapproved-blocked",
             "old-verdict-does-not-admit-new-version", "boundary-holds",
             "three-records-complete"])
        self.assertTrue(all(s["passed"] for s in report["scenarios"]))

    def test_acceptance_script_exits_zero(self):
        """验收脚本直接跑：退出码 0，stdout 是全链跑通的 JSON 报告。"""
        proc = subprocess.run(
            [sys.executable, str(ACC_PATH)], capture_output=True, text=True,
            cwd=str(Path(__file__).resolve().parents[2]), timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual(report["verdict"], "全链跑通")


class TestHappyPath(unittest.TestCase):
    def test_full_chain_states_and_versions(self):
        """全链状态与版本：v1 发回、v2 改回重审、点头后 approved。"""
        item, sc = happy_path()
        self.assertTrue(sc["passed"])
        self.assertEqual(item["score_id"], "sc-001")
        self.assertEqual(item["status"], "approved")
        self.assertEqual(item["version"], 2)
        self.assertEqual(len(item["versions"]), 2)
        self.assertEqual(item["versions"][1]["diff_summary"],
                         "视角A 8→7 分，总分 7→6.5（占位）")
        events = [p["event"] for p in item["progress"]]
        self.assertEqual(events, ["created", "submitted", "viewed",
                                  "annotated", "sent-back", "resubmitted",
                                  "approved"])

    def test_annotation_anchored_and_feedback_linked(self):
        """批注锚定到打分步骤；反馈单含类型、正文、理由与关联批注。"""
        item, _ = happy_path()
        self.assertEqual(len(item["annotations"]), 1)
        ann = item["annotations"][0]
        self.assertEqual(ann["step"], "视角A打分（占位）")
        self.assertEqual(len(item["feedbacks"]), 1)
        fb = item["feedbacks"][0]
        self.assertEqual(fb["type"], "re-score")
        self.assertEqual(fb["annotation_ids"], [ann["annotation_id"]])
        self.assertEqual(fb["version"], 1)
        self.assertTrue(fb["reason"])

    def test_approved_only_enters_downstream(self):
        """只有点头的进品牌审计报告：出口 passed 恰为已点头那一条。"""
        item, _ = happy_path()
        other = new_item("sc-003", CONTENT_V1, PROCESS_V1, at=NOW)
        submit(other, at=NOW)
        outlet = downstream_outlet([other, item])
        self.assertEqual([p["score_id"] for p in outlet["passed"]], ["sc-001"])
        self.assertEqual(outlet["blocked_count"], 1)

    def test_gate_verdict_current_only_for_approved_version(self):
        """闸门放行裁决只对点头当时的版本有效。"""
        item, _ = happy_path()
        gate = SupervisionGate()
        verdict = gate.admit(item, at=NOW)
        self.assertTrue(gate.is_verdict_current(item, verdict))
        self.assertEqual(gate.report()["allowed"], 1)


class TestNegativePaths(unittest.TestCase):
    def test_unapproved_blocked(self):
        """四种未点头状态：闸门拦截 + 出口拦下。"""
        sc = unapproved_blocked()
        self.assertTrue(sc["passed"])
        self.assertIn("blocked_count=4", sc["detail"])

    def test_old_verdict_does_not_admit_new_version(self):
        """v1 裁决不对 v2 有效。"""
        sc = old_verdict_does_not_admit_new_version()
        self.assertTrue(sc["passed"])

    def test_rejected_never_enters_downstream(self):
        """已否决的评分不进品牌审计报告，只留档备查。"""
        item = new_item("sc-rej", CONTENT_V1, PROCESS_V1, at=NOW)
        submit(item, at=NOW)
        decide(item, "reject", reason="不采纳（占位）", at=NOW)
        self.assertEqual(item["status"], "rejected")
        outlet = downstream_outlet([item])
        self.assertEqual(outlet["passed"], [])
        self.assertEqual(outlet["blocked"][0]["status"], "rejected")


class TestBoundaryAndLedger(unittest.TestCase):
    def test_boundary_holds(self):
        """划界断言全程成立。"""
        self.assertTrue(boundary_holds()["passed"])

    def test_three_records_complete(self):
        """三件套落账齐全，缺件拒绝入账。"""
        self.assertTrue(three_records_complete()["passed"])

    def test_bench_content_unchanged_by_supervision(self):
        """监督台不碰分数：批注与裁决不改动评分内容与过程。"""
        before = copy.deepcopy(CONTENT_V1)
        item, _ = happy_path()
        self.assertEqual(item["versions"][0]["content"], before)
        self.assertEqual(item["versions"][0]["process"], PROCESS_V1)


class TestAcceptanceModuleHygiene(unittest.TestCase):
    def test_stdlib_only_and_no_network_or_subprocess(self):
        """验收脚本标准库-only；零网络零子进程。"""
        tree = ast.parse(ACC_PATH.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertLessEqual(imported, STDLIB_ALLOW | {"review_supervision_bench", "review_supervision_boundary", "review_supervision_gate"})
        self.assertFalse(imported & {"urllib", "requests", "socket",
                                     "http", "subprocess"}, ACC_PATH.name)

    def test_no_real_host_or_secret_placeholders(self):
        """验收脚本无真实内部主机名/IP/账号/密钥字面量（只用占位）。"""
        text = ACC_PATH.read_text(encoding="utf-8")
        for bad in ("10.", "192.168.", "api_key", "password", "token="):
            self.assertNotIn(bad, text)


if __name__ == "__main__":
    unittest.main()
