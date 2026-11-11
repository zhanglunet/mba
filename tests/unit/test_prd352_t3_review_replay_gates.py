# -*- coding: utf-8 -*-
"""PRD-352/T3 测试（trend #1631 的 T3 环节）：评审结论重放闸门。

运行：.venv/bin/python -m pytest tests/unit/test_prd352_t3_review_replay_gates.py -q

覆盖（T1 §4 + R2/R3/R4）：ledger_gate（一致 pass/verdict 或 evidence 或指纹
错位 VERDICT_MISMATCH 显形/空账本显形）；append_only_gate（无基线形态过/
mark_baseline 后追加 pass/删除或首条改写 LEDGER_DRIFT 显形）；pack_gate（一致
pass/别包冒充 PACK_STALE 显形）；gate_summary 一票否决；与 T2 串联（真实
make_pack+replay+ReplayLedger 产物三闸全过）；AST 零评分写导入零网络零子进程
+闸门只读。零网络；全合成占位。
"""
import ast
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from review_replay import ReplayLedger, make_pack, replay  # noqa: E402
from review_replay_gates import (  # noqa: E402
    ERROR_CODES,
    append_only_gate,
    gate_summary,
    ledger_gate,
    mark_baseline,
    pack_gate,
)

NOW = "2026-11-11T09:00:00Z"
WORKS = [{"work_id": 42, "work_title": "作品42（占位）",
          "snapshot_digest": "sha16:w42（占位）"}]
REVIEWS = [{"work_id": 42, "score": "88（原样）", "why": "论证扎实（占位）"}]


def score_fn(work_snapshots):
    return [dict(r) for r in REVIEWS]


class TestLedgerGate(unittest.TestCase):
    def setUp(self):
        self.pack = make_pack(REVIEWS, WORKS, judgepack_version="v1")
        self.verdict = replay(self.pack, WORKS, score_fn,
                              judgepack_version="v1")
        self.ledger = ReplayLedger()
        self.ledger.record(self.pack, self.verdict, at=NOW)

    def test_consistent_record_passes(self):
        self.assertEqual(ledger_gate(self.pack, self.verdict,
                                     self.ledger)["gate"], "pass")

    def test_forged_verdict_mismatch(self):
        """verdict 与账本不一致 → VERDICT_MISMATCH 显形。"""
        forged = {"verdict": "REPLAY_MISMATCH", "evidence": None}
        out = ledger_gate(self.pack, forged, self.ledger)
        self.assertEqual(out["gate"], "VERDICT_MISMATCH")
        self.assertTrue(any("不一致" in r for r in out["reasons"]))

    def test_tampered_evidence_mismatch(self):
        forged = {"verdict": "REPLAY_OK",
                  "evidence": {"fake": "证据改写（占位）"}}
        out = ledger_gate(self.pack, forged, self.ledger)
        self.assertEqual(out["gate"], "VERDICT_MISMATCH")

    def test_empty_ledger_visible(self):
        pack = make_pack(REVIEWS, WORKS, judgepack_version="v1")
        out = ledger_gate(pack, {"verdict": "REPLAY_OK", "evidence": None},
                          ReplayLedger())
        self.assertEqual(out["gate"], "VERDICT_MISMATCH")
        self.assertIn("账本为空", out["reasons"][0])


class TestAppendOnlyGate(unittest.TestCase):
    def setUp(self):
        self.pack = make_pack(REVIEWS, WORKS, judgepack_version="v1")
        self.ledger = ReplayLedger()
        self.ledger.record(self.pack, {"verdict": "REPLAY_OK",
                                       "evidence": None}, at=NOW)
        self.ledger.record(self.pack, {"verdict": "REPLAY_OK",
                                       "evidence": None}, at=NOW)

    def test_no_baseline_form_check_passes(self):
        self.assertEqual(append_only_gate(self.ledger)["gate"], "pass")

    def test_mark_baseline_then_append_passes(self):
        mark_baseline(self.ledger)
        self.ledger.record(self.pack, {"verdict": "REPLAY_OK",
                                       "evidence": None}, at=NOW)
        self.assertEqual(append_only_gate(self.ledger)["gate"], "pass")

    def test_deletion_detected(self):
        mark_baseline(self.ledger)
        self.ledger._entries.pop()
        self.assertEqual(append_only_gate(self.ledger)["gate"], "LEDGER_DRIFT")

    def test_first_entry_rewrite_detected(self):
        mark_baseline(self.ledger)
        self.ledger._entries[0]["verdict"] = "REPLAY_OK（篡改）（占位）"
        self.assertEqual(append_only_gate(self.ledger)["gate"], "LEDGER_DRIFT")

    def test_non_ledger_object_visible(self):
        self.assertEqual(append_only_gate(object())["gate"], "LEDGER_DRIFT")


class TestPackGate(unittest.TestCase):
    def setUp(self):
        self.pack = make_pack(REVIEWS, WORKS, judgepack_version="v1")
        self.ledger = ReplayLedger()
        self.ledger.record(self.pack, {"verdict": "REPLAY_OK",
                                       "evidence": None}, at=NOW)

    def test_matching_pack_passes(self):
        self.assertEqual(pack_gate(self.pack, self.ledger)["gate"], "pass")

    def test_wrong_pack_stale(self):
        """别包冒充 → PACK_STALE 显形（不同作品快照 → 不同指纹）。"""
        other = make_pack(REVIEWS, [dict(WORKS[0],
                                         snapshot_digest="sha16:changed")],
                          judgepack_version="v1")
        self.assertEqual(pack_gate(other, self.ledger)["gate"], "PACK_STALE")

    def test_empty_ledger_visible(self):
        pack = make_pack(REVIEWS, WORKS, judgepack_version="v1")
        self.assertEqual(pack_gate(pack, ReplayLedger())["gate"], "PACK_STALE")


class TestSummaryAndChain(unittest.TestCase):
    def test_summary_one_block_votes_all(self):
        pack = make_pack(REVIEWS, WORKS, judgepack_version="v1")
        ledger = ReplayLedger()
        ledger.record(pack, {"verdict": "REPLAY_OK", "evidence": None},
                      at=NOW)
        forged = {"verdict": "REPLAY_OK", "evidence": {"fake": 1}}
        out = gate_summary([append_only_gate(ledger),
                            ledger_gate(pack, forged, ledger)])
        self.assertEqual(out["gate"], "block")
        self.assertEqual(out["gates_checked"], 2)

    def test_chain_with_real_t2_products(self):
        """与 T2 串联：真实 make_pack+replay+ReplayLedger 产物三闸全过。"""
        pack = make_pack(REVIEWS, WORKS, judgepack_version="v1")
        verdict = replay(pack, WORKS, score_fn, judgepack_version="v1")
        ledger = ReplayLedger()
        ledger.record(pack, verdict, at=NOW)
        mark_baseline(ledger)
        results = [append_only_gate(ledger), ledger_gate(pack, verdict, ledger),
                   pack_gate(pack, ledger)]
        self.assertTrue(all(r["gate"] == "pass" for r in results))
        self.assertEqual(gate_summary(results)["gate"], "pass")

    def test_error_codes_closed(self):
        self.assertEqual(set(ERROR_CODES),
                         {"VERDICT_MISMATCH", "LEDGER_DRIFT", "PACK_STALE"})


class TestRedline(unittest.TestCase):
    def test_ast_zero_score_write_zero_network_readonly(self):
        """R2 AST：零评分写导入零网络零子进程+闸门只读（零账本写调用）。"""
        banned = {"urllib", "requests", "socket", "http", "subprocess",
                  "score_write", "scoring"}
        src = (REPO / "scripts" / "review_replay_gates.py").read_text(
            encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module.split(".")[0]]
            for mod in mods:
                self.assertNotIn(mod, banned)
        for call in (".record(", ".add(", ".append("):
            self.assertNotIn(call, src, f"闸门出现账本写调用 {call}")


if __name__ == "__main__":
    unittest.main()
