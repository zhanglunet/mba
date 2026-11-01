# -*- coding: utf-8 -*-
"""PRD-233/T2 自测：评委包四维度分包。"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from judge_subpack_registry import SubpackError, build_registry  # noqa: E402

JUDGES = (
    [{"slug": f"brand-{i:02d}", "name_cn": f"品牌评委{i}", "sub_pack": "brand"} for i in range(26)]
    + [{"slug": f"copy-{i:02d}", "name_cn": f"文案评委{i}", "sub_pack": "copy"} for i in range(8)]
    + [{"slug": f"visual-{i:02d}", "name_cn": f"视觉评委{i}", "sub_pack": "visual"} for i in range(4)]
    + [{"slug": f"compliance-{i:02d}", "name_cn": f"合规评委{i}", "sub_pack": "compliance"} for i in range(5)]
    + [{"slug": f"consumer-{i:02d}", "name_cn": f"消费者{i}", "sub_pack": "consumer"} for i in range(3)]
)


class SubpackTests(unittest.TestCase):
    def test_all_46_judges_registered(self):
        r = build_registry(JUDGES)
        self.assertEqual(len(r["judges"]), 46)

    def test_four_subpack_counts_match_design(self):
        r = build_registry(JUDGES)
        for sub, info in r["subpacks"].items():
            expected = {"brand": 26, "copy": 8, "visual": 4, "compliance": 5}[sub]
            self.assertEqual(info["count"], expected, f"{sub} 人数不对")

    def test_every_pack_has_one_line(self):
        r = build_registry(JUDGES)
        for sub, info in r["subpacks"].items():
            self.assertTrue(info["one_line"].strip(), f"{sub} 缺定位")

    def test_unknown_subpack_reports_error(self):
        bad = [{"slug": "x", "name_cn": "x", "sub_pack": "unknown"}]
        r = build_registry(bad)
        self.assertFalse(r["ok"])

    def test_serializable(self):
        r = build_registry(JUDGES)
        json.dumps(r, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
