# -*- coding: utf-8 -*-
"""PRD-366/T2 测试（trend #1645 的 T2 环节）：评审复核收件箱。

运行：.venv/bin/python -m pytest tests/unit/test_prd366_t2_verify_inbox.py -q

覆盖（T1 §3.1/§3.2/§4 + R1–R4）：collect 四源只读汇聚（词表封闭+条目缺一
INBOX_ITEM_INCOMPLETE 显形拒绝入箱+fingerprint 与 PRD-352 重放包同源）；
InboxLedger 状态机（approve/reject 人批留痕/重复裁决/未知 id/AUTO_EXEC 携带
撤回/重转换/改分载荷拒绝——零分数写零撤回触发零重转换 R1 走既有流程/撤回
确认 approve 必带人工定性 verdict §6.1）；append-only；view kind 过滤；AST
零网络零子进程。零网络；全合成占位。
"""
import ast
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from verify_inbox import (  # noqa: E402
    ERROR_CODES,
    ITEM_KINDS,
    InboxError,
    InboxLedger,
    collect,
)

NOW = "2026-11-11T09:00:00Z"
FP = "sha16:work42（占位）"
LOW = [{"source_ref": "review-replay-pack/v1（占位）",
        "reason": "低置信评分项（占位）"}]
WITHDRAW = [{"source_ref": "withdraw-motion#42（占位）",
             "reason": "撤回动议（占位）"}]
SLIDES = [{"check": "page_mapping", "reason": "SLIDES_PAGE_MISMATCH 复核（占位）"}]
EXTERNAL = [{"source_ref": "verify-gate/v1（占位）",
             "reason": "外链检出处置（占位）"}]


class TestCollect(unittest.TestCase):
    def test_four_sources_closed_vocab(self):
        items = collect(low_confidence=LOW, withdraw_confirms=WITHDRAW,
                        slides_gate_reviews=SLIDES,
                        external_ref_reviews=EXTERNAL, fingerprint=FP,
                        at=NOW)
        self.assertEqual([it["kind"] for it in items],
                         ["low_confidence_score", "withdraw_confirm",
                          "slides_gate_review", "external_ref_review"])
        self.assertEqual(set(ITEM_KINDS),
                         {"low_confidence_score", "withdraw_confirm",
                          "slides_gate_review", "external_ref_review"})

    def test_fingerprint_same_source_as_352(self):
        """R3：work_snapshot_digest 与 PRD-352 重放包同源（调用方注入）。"""
        items = collect(low_confidence=LOW, fingerprint=FP, at=NOW)
        self.assertEqual(items[0]["work_snapshot_digest"], FP)

    def test_incomplete_raises_visible(self):
        """R3：reason 缺失 → INBOX_ITEM_INCOMPLETE 显形拒绝入箱。"""
        with self.assertRaisesRegex(InboxError, "INBOX_ITEM_INCOMPLETE"):
            collect(withdraw_confirms=[{"source_ref": "s"}], at=NOW)


class TestLedger(unittest.TestCase):
    def _ledger(self):
        led = InboxLedger()
        led.add(collect(low_confidence=LOW, withdraw_confirms=WITHDRAW,
                        slides_gate_reviews=SLIDES,
                        external_ref_reviews=EXTERNAL, fingerprint=FP,
                        at=NOW))
        return led

    def test_approve_reject_state_machine(self):
        led = self._ledger()
        a = led.approve("item-001", by="reviewer（占位）", at=NOW)
        self.assertEqual(a["state"], "approved")
        r = led.reject("item-003", by="reviewer（占位）", at=NOW,
                       reason="按规则重转换（占位）")
        self.assertEqual(r["state"], "rejected")

    def test_withdraw_confirm_requires_verdict(self):
        """§6.1：撤回确认 approve 必带人工定性 verdict。"""
        led = self._ledger()
        with self.assertRaisesRegex(InboxError, "必带人工定性"):
            led.approve("item-002", by="r（占位）", at=NOW)
        a = led.approve("item-002", by="r（占位）", at=NOW,
                        verdict="确认撤回动议（占位）")
        self.assertEqual(a["human_verdict"], "确认撤回动议（占位）")

    def test_double_and_unknown_visible(self):
        led = self._ledger()
        led.approve("item-001", by="r（占位）", at=NOW)
        with self.assertRaisesRegex(InboxError, "INBOX_DOUBLE_DECIDE"):
            led.reject("item-001", by="r（占位）", at=NOW)
        with self.assertRaisesRegex(InboxError, "未知"):
            led.approve("item-999", by="r（占位）", at=NOW)

    def test_auto_exec_disposal_payload_rejected(self):
        """R1：裁决携带撤回/重转换/改分载荷 → AUTO_EXEC 显形拒绝。"""
        led = self._ledger()
        with self.assertRaisesRegex(InboxError, "INBOX_AUTO_EXEC_ATTEMPT"):
            led.approve("item-002", by="r（占位）", at=NOW, verdict="v",
                        payload={"withdraw": 42})
        with self.assertRaisesRegex(InboxError, "INBOX_AUTO_EXEC_ATTEMPT"):
            led.reject("item-003", by="r（占位）", at=NOW,
                       payload={"reconvert": True})
        with self.assertRaisesRegex(InboxError, "INBOX_AUTO_EXEC_ATTEMPT"):
            led.reject("item-001", by="r（占位）", at=NOW,
                       payload={"rescore": 95})
        self.assertEqual(led.view()[0]["state"], "pending")   # 零状态变化

    def test_append_only_and_view_filter(self):
        led = self._ledger()
        led.approve("item-001", by="r（占位）", at=NOW)
        before = [dict(e) for e in led.events]
        led.reject("item-004", by="r（占位）", at=NOW, reason="r（占位）")
        self.assertEqual(led.events[:len(before)], before)
        self.assertEqual(len(led.events), len(before) + 1)
        self.assertEqual(len(led.view("external_ref_review")), 1)
        self.assertEqual(len(led.view()), 4)


class TestRedline(unittest.TestCase):
    def test_error_codes_closed(self):
        self.assertEqual(set(ERROR_CODES),
                         {"INBOX_ITEM_INCOMPLETE", "INBOX_DOUBLE_DECIDE",
                          "INBOX_AUTO_EXEC_ATTEMPT"})

    def test_ast_zero_network_zero_subprocess(self):
        """R1 AST：零网络零子进程（零分数写零撤回触发零重转换）。"""
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        tree = ast.parse((REPO / "scripts" / "verify_inbox.py").read_text(
            encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module.split(".")[0]]
            for mod in mods:
                self.assertNotIn(mod, banned)


if __name__ == "__main__":
    unittest.main()
