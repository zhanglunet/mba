# -*- coding: utf-8 -*-
"""PRD-366/T5 测试（trend #1645 的 T5 环节）：复核收件箱验收试运行。

运行：uv run --with pytest python -m pytest tests/unit/test_prd366_t5_verify_inbox.py -q
（仓库根执行）

验收（T1 §5 T5 行「样例回放+文档无密钥」）：
  全链周期演练：四源只读汇聚 → 入箱 → 人批（定性）→ 人拒留痕 → 重复
  裁决演练（INBOX_DOUBLE_DECIDE 显形）→ AUTO_EXEC 演练（withdraw/
  rescore 载荷 INBOX_AUTO_EXEC_ATTEMPT 显形拒绝——零分数写零撤回零转换
  重跑）；两遍全链周期产物逐字节一致（确定性可复现）；work_snapshot_
  digest 与 PRD-352 同族复验；账本 append-only；零动作触发行为复验
  （批/拒返回值零动作载荷键）；链复跑：T2/T3/T4 测试子进程复跑 exit 0
  （链上仍绿实测，含 T3 ERROR_CODES 订正后全链）；文档无密钥：T1 设计
  文档拼接 needle 扫描+占位符纪律。零网络；全合成占位。
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from verify_inbox import InboxError, InboxLedger, collect  # noqa: E402

NOW = "2026-11-11T09:00:00Z"
FP = "sha16:work42（占位）"
LOW = [{"source_ref": "review-replay-pack/v1（占位）",
        "reason": "低置信评分项（占位）"}]
WITHDRAW = [{"source_ref": "withdraw-motion#42（占位）",
             "reason": "撤回动议（占位）"}]
SLIDES = [{"check": "page_mapping", "reason": "SLIDES_PAGE_MISMATCH 复核（占位）"}]
EXTERNAL = [{"source_ref": "verify-gate/v1（占位）",
             "reason": "外链检出处置（占位）"}]


def _fresh_cycle():
    items = collect(low_confidence=LOW, withdraw_confirms=WITHDRAW,
                    slides_gate_reviews=SLIDES, external_ref_reviews=EXTERNAL,
                    fingerprint=FP, at=NOW)
    led = InboxLedger()
    led.add(items)
    led.approve(items[0]["item_id"], by="复核人（占位）", at=NOW,
                verdict="低置信维持原判（占位）")
    led.reject(items[1]["item_id"], by="复核人（占位）", at=NOW,
               reason="撤回不成立（占位）")
    return items, led


class TestFullCycleDrill(unittest.TestCase):
    def test_cycle_deterministic_twice(self):
        """全链周期（收→批→拒）两遍：条目/events/状态逐字节一致。"""
        items1, led1 = _fresh_cycle()
        items2, led2 = _fresh_cycle()
        self.assertEqual(json.dumps(items1, sort_keys=True),
                         json.dumps(items2, sort_keys=True))
        self.assertEqual(json.dumps(led1.events, sort_keys=True),
                         json.dumps(led2.events, sort_keys=True))
        states = [it["state"] for it in led1.view()]
        self.assertEqual(sorted(states), ["approved", "pending", "pending",
                                          "rejected"])

    def test_fingerprint_family_with_352(self):
        """work_snapshot_digest 与 PRD-352 重放包同族复验（sha16 口径）。"""
        items, _ = _fresh_cycle()
        for it in items:
            self.assertTrue(it["work_snapshot_digest"].startswith("sha16:"))

    def test_reject_trace_and_zero_action_keys(self):
        """拒也留痕；批/拒返回值零动作载荷键（R1 零动作触发行为复验）。"""
        items, led = _fresh_cycle()
        rejected = next(it for it in led.view()
                        if it["item_id"] == items[1]["item_id"])
        self.assertEqual(rejected["reject_reason"], "撤回不成立（占位）")
        fresh = InboxLedger()
        fresh.add(collect(low_confidence=LOW, fingerprint=FP, at=NOW))
        approved = fresh.approve(items[0]["item_id"], by="复核人（占位）",
                                 at=NOW)
        for key in ("withdrawn", "rescored", "reconverted"):
            self.assertNotIn(key, approved)


class TestFailureDrills(unittest.TestCase):
    def test_double_decide_visible(self):
        """重复裁决演练：INBOX_DOUBLE_DECIDE 显形拒绝。"""
        items, led = _fresh_cycle()
        with self.assertRaisesRegex(InboxError, "INBOX_DOUBLE_DECIDE"):
            led.approve(items[0]["item_id"], by="复核人（占位）", at=NOW)

    def test_auto_exec_payload_rejected(self):
        """AUTO_EXEC 演练：withdraw/rescore 载荷 → INBOX_AUTO_EXEC_ATTEMPT
        显形拒绝（复核结论是人定性，动作走既有流程）。"""
        items, led = _fresh_cycle()
        with self.assertRaisesRegex(InboxError, "INBOX_AUTO_EXEC_ATTEMPT"):
            led.approve(items[2]["item_id"], by="复核人（占位）", at=NOW,
                        payload={"withdraw": True})
        with self.assertRaisesRegex(InboxError, "INBOX_AUTO_EXEC_ATTEMPT"):
            led.reject(items[2]["item_id"], by="复核人（占位）", at=NOW,
                       payload={"rescore": True})

    def test_ledger_append_only_through_drills(self):
        """账本 append-only：全演练流程后 events 只增不删。"""
        _, led1 = _fresh_cycle()
        n0 = len(led1.events)
        items2, led2 = _fresh_cycle()
        try:
            led2.approve(items2[0]["item_id"], by="复核人（占位）", at=NOW)
        except InboxError:
            pass   # 重复裁决被拒——events 不增
        self.assertEqual(len(led2.events), n0)


class TestChainRerun(unittest.TestCase):
    def test_t2_t3_t4_rerun_green(self):
        """链复跑：T2/T3/T4 测试子进程复跑 exit 0（链上仍绿实测，含 T3
        订正后全链）。"""
        for test_file in ("test_prd366_t2_verify_inbox.py",
                          "test_prd366_t3_verify_inbox_gates.py",
                          "test_prd366_t4_verify_inbox_boundary.py"):
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q",
                 str(REPO / "tests" / "unit" / test_file)],
                capture_output=True, timeout=300)
            self.assertEqual(proc.returncode, 0,
                             f"{test_file} 复跑失败：{proc.stdout[-400:]}")


class TestDocNoSecrets(unittest.TestCase):
    def test_t1_design_doc_no_secrets(self):
        """文档无密钥：T1 设计文档拼接 needle 扫描+占位符纪律。"""
        doc = next(REPO.glob("docs/plans/2026-11-11-prd-366-*.md"))
        text = doc.read_text(encoding="utf-8").lower()
        for needle in ("sk-" + "live", "passw" + "ord", "api_k" + "ey"):
            self.assertNotIn(needle, text, f"设计文档出现密钥词 {needle}")
        self.assertIn("占位", text)


if __name__ == "__main__":
    unittest.main()
