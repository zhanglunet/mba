# -*- coding: utf-8 -*-
"""PRD-338/T3 测试（trend #1617 的 T3 环节）：幻灯片逐页对应闸门。

运行：.venv/bin/python -m pytest tests/unit/test_prd338_t3_slides_gate.py -q

覆盖（T1 设计 §4/R1/R2/R3）：ERROR_CODES 三码封闭；conversion_gate（干净
记录 allow 带产物/缺评委条目 CONCLUSION_INCOMPLETE 拒绝零产物/页面断裂
SLIDES_PAGE_MISMATCH/外链注入 EXTERNAL_REF_FOUND 归因）；verify_gate 双机
判之二独立复核（页对应重算/评语分数逐字在位 R2/外链探测 R3）；与 T2 串联
（真实产物过双闸）。零网络；全合成占位。
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from slides import render_slides, slides_from_conclusions  # noqa: E402
from slides_gate import (  # noqa: E402
    ERROR_CODES,
    conversion_gate,
    verify_gate,
)

GOOD = [
    {"work_id": 42, "work_title": "作品42（占位）",
     "evaluations": [{"evaluator": "评委甲（占位）", "verdict": "入围",
                      "score": "92.5（原样）", "comment": "逻辑清晰（占位评语）"}]},
    {"work_id": 43, "work_title": "作品43（占位）",
     "evaluations": [{"evaluator": "评委乙（占位）", "verdict": "入围",
                      "score": "88", "comment": "论证扎实（占位评语）"}]},
]
INCOMPLETE = [{"work_id": 44, "work_title": "作品44（占位）", "evaluations": []}]


class TestCodes(unittest.TestCase):
    def test_three_codes_closed(self):
        self.assertEqual(set(ERROR_CODES),
                         {"CONCLUSION_INCOMPLETE", "SLIDES_PAGE_MISMATCH",
                          "EXTERNAL_REF_FOUND"})


class TestConversionGate(unittest.TestCase):
    def test_clean_record_allows_with_artifact(self):
        out = conversion_gate(GOOD)
        self.assertEqual(out["gate"], "allow")
        self.assertIsNone(out["error_code"])
        self.assertIn("<h2>", out["artifact"])
        self.assertEqual(out["pages"], 4)   # 封面+2 作品+汇总

    def test_incomplete_rejected_zero_artifact(self):
        """CONCLUSION_INCOMPLETE：缺评委条目显形拒绝，零半成品。"""
        out = conversion_gate(INCOMPLETE)
        self.assertEqual(out["gate"], "reject")
        self.assertEqual(out["error_code"], "CONCLUSION_INCOMPLETE")
        self.assertIsNone(out["artifact"])

    def test_page_mismatch_mapped(self):
        good_gate = conversion_gate(GOOD)
        self.assertEqual(good_gate["gate"], "allow")
        # 抹掉一个作品页标题 → T2 自检拒绝（外链探测不命中）
        doc = slides_from_conclusions(GOOD)
        html_text = render_slides(doc["pages"]).replace("<h2>", "", 1)
        from slides import self_check, SlidesMismatch
        with self.assertRaises(SlidesMismatch):
            self_check(doc["pages"], html_text)   # T2 自检拒绝（闸门同源）
        # 双机判之二独立复核同样归因 SLIDES_PAGE_MISMATCH
        out = verify_gate(GOOD, html_text)
        self.assertEqual(out["gate"], "reject")
        self.assertEqual(out["error_code"], "SLIDES_PAGE_MISMATCH")

    def test_external_ref_mapped(self):
        """EXTERNAL_REF_FOUND 归因：注入外链的记录触发三码之第三。"""
        poisoned = [dict(GOOD[0], evaluations=[
            dict(GOOD[0]["evaluations"][0],
                 comment="详见 https://cdn.example.invalid/x.js（占位注入）")])]
        doc = slides_from_conclusions(poisoned)
        html_text = render_slides(doc["pages"])
        gate = verify_gate(poisoned, html_text)
        self.assertEqual(gate["gate"], "reject")
        self.assertEqual(gate["error_code"], "EXTERNAL_REF_FOUND")


class TestVerifyGate(unittest.TestCase):
    def test_independent_recompute_allows(self):
        """双机判之二：从结论记录直接重算，页对应/逐字/零外链三查过。"""
        doc = slides_from_conclusions(GOOD)
        html_text = render_slides(doc["pages"])
        out = verify_gate(GOOD, html_text)
        self.assertEqual(out["gate"], "allow")
        self.assertTrue(all(c["ok"] for c in out["checks"]))

    def test_paraphrase_detected_by_verbatim_check(self):
        """R2 复核：页面被改写（评语替换）→ verbatim 查不通过。"""
        doc = slides_from_conclusions(GOOD)
        html_text = render_slides(doc["pages"]).replace(
            "逻辑清晰（占位评语）", "改写过的评语（占位）")
        out = verify_gate(GOOD, html_text)
        self.assertEqual(out["gate"], "reject")
        verbatim = next(c for c in out["checks"] if c["check"] == "verbatim_r2")
        self.assertFalse(verbatim["ok"])


class TestChainAndRedline(unittest.TestCase):
    def test_t2_chain_through_both_gates(self):
        """与 T2 串联：转换闸 → 独立复核闸，双机判一致 allow。"""
        first = conversion_gate(GOOD)
        second = verify_gate(GOOD, first["artifact"])
        self.assertEqual((first["gate"], second["gate"]), ("allow", "allow"))

    def test_gate_module_zero_network(self):
        import ast
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        tree = ast.parse((REPO / "scripts" / "slides_gate.py").read_text(
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
