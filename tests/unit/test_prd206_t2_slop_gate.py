# -*- coding: utf-8 -*-
"""PRD-206/T2 自测（trend #1031）：反 AI 味 Floor 门——违规样本拦截/正常不误伤。"""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from slop_gate_floor import gate_floors  # noqa: E402


class TestFloorGate(unittest.TestCase):
    def test_hollow_assertion_blocked(self):
        r = gate_floors("引领未来新篇章，带来极致体验")
        self.assertEqual(r["decision"], "blocked")
        self.assertEqual(r["hits"][0]["rule_id"], "SLOP-S-01")

    def test_no_brand_blocked(self):
        r = gate_floors("该产品为用户提供优质服务", brand_known=True)
        self.assertEqual(r["decision"], "blocked")
        self.assertEqual(r["hits"][0]["rule_id"], "SLOP-T-02")

    def test_unsourced_metric_blocked(self):
        r = gate_floors("DemoBrand 效率提升 300%", source_annotated=False)
        self.assertEqual(r["decision"], "blocked")
        self.assertEqual(r["hits"][0]["rule_id"], "SLOP-S-02")

    def test_gradient_blocked(self):
        r = gate_floors("DemoBrand 视觉升级", colors=["#ff00ff", "#00ff00", "#ff69b4"],
                         brand_palette={"#1a73e8", "#34a853"})
        self.assertEqual(r["decision"], "blocked")
        self.assertEqual(r["hits"][0]["rule_id"], "SLOP-G-01")

    def test_structure_collision_blocked(self):
        prev = {hashlib_md5("DemoBrand 示例文本内容")}
        r = gate_floors("DemoBrand 示例文本内容", prev_asset_hashes=prev)
        self.assertEqual(r["decision"], "blocked")
        self.assertEqual(r["hits"][0]["rule_id"], "SLOP-C-01")

    def test_clean_copy_passes(self):
        r = gate_floors("DemoBrand 推出数据核对功能，来源：内部审计报告",
                         source_annotated=True, colors=["#1a73e8"],
                         brand_palette={"#1a73e8"})
        self.assertEqual(r["decision"], "passed_with_warnings")
        self.assertEqual(r["hits"], [])

    def test_multiple_hits(self):
        r = gate_floors("最好的产品引领未来新篇章")
        self.assertGreater(len(r["hits"]), 1)


def hashlib_md5(text):
    import hashlib
    return hashlib.md5(text.encode()).hexdigest()[:16]


if __name__ == "__main__":
    unittest.main()
