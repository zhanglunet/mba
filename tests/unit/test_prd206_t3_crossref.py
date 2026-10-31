# -*- coding: utf-8 -*-
"""PRD-206/T3 自测（trend #1032）：门条目与设计语言互引——悬空报错/口径不冲突/正反向定位。"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from slop_gate_crossref import (  # noqa: E402
    GATE_DESIGN_REFS,
    GATE_FLOOR_ENTRIES,
    check_crossref,
    crossref_report,
    design_refs_for,
    reverse_index,
)
from slop_gate_floor import GATE_VERSION  # noqa: E402

DL_PATH = Path(__file__).resolve().parents[2] / "design" / "design-language.json"


def load_dl():
    return json.loads(DL_PATH.read_text(encoding="utf-8"))


class TestRegistryCoverage(unittest.TestCase):
    def test_registry_covers_t2_floor_entries(self):
        # T2 实现的 Floor 五条：SLOP-S-01/T-02/S-02/G-01/C-01
        self.assertEqual(set(GATE_DESIGN_REFS), set(GATE_FLOOR_ENTRIES))
        self.assertEqual(
            set(GATE_FLOOR_ENTRIES),
            {"SLOP-T-02", "SLOP-G-01", "SLOP-S-01", "SLOP-S-02", "SLOP-C-01"},
        )

    def test_registry_entry_shape(self):
        for slop_id, entry in GATE_DESIGN_REFS.items():
            self.assertEqual(entry["tier"], "floor")
            self.assertIsInstance(entry["design_refs"], list)
            # 空表必须留理由（不杜撰编号的诚实登记）
            self.assertTrue(entry.get("note"), f"{slop_id} 缺 note")

    def test_forward_locate(self):
        entry = design_refs_for("SLOP-G-01")
        self.assertEqual(entry["design_refs"], ["DL-C01"])
        self.assertIsNone(design_refs_for("SLOP-N-99"))


class TestCrossrefCheck(unittest.TestCase):
    def test_no_dangling_no_conflict(self):
        result = check_crossref(load_dl())
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["dangling"], [])
        self.assertEqual(result["conflicts"], [])

    def test_dangling_ref_detected(self):
        bad = {"SLOP-X-99": {"tier": "floor", "design_refs": ["DL-Z99"], "note": "坏例"}}
        result = check_crossref(load_dl(), registry=bad)
        self.assertFalse(result["ok"])
        self.assertEqual(result["dangling"][0]["entry_id"], "SLOP-X-99")
        self.assertEqual(result["dangling"][0]["ref"], "DL-Z99")
        self.assertIn("不存在", result["dangling"][0]["reason"])

    def test_deprecated_ref_detected(self):
        dl = load_dl()
        dl["rules"][0]["status"] = "deprecated"  # DL-C01
        result = check_crossref(dl)
        self.assertFalse(result["ok"])
        self.assertTrue(any(d["ref"] == "DL-C01" and "deprecated" in d["reason"]
                            for d in result["dangling"]))

    def test_floor_referencing_soft_is_conflict(self):
        bad = {"SLOP-Y-99": {"tier": "floor", "design_refs": ["DL-S01"], "note": "坏例"}}
        result = check_crossref(load_dl(), registry=bad)  # DL-S01 severity=soft
        self.assertFalse(result["ok"])
        self.assertTrue(any(c["entry_id"] == "SLOP-Y-99" and "口径冲突" in c["reason"]
                            for c in result["conflicts"]))

    def test_unknown_tier_fail_closed(self):
        bad = {"SLOP-Z-01": {"tier": "mega", "design_refs": [], "note": "坏例"}}
        result = check_crossref(load_dl(), registry=bad)
        self.assertFalse(result["ok"])
        self.assertIn("tier 不在词表", result["dangling"][0]["reason"])

    def test_reflex_referencing_soft_allowed(self):
        ok_reg = {"SLOP-R-01": {"tier": "reflex", "design_refs": ["DL-S01"], "note": "警告级引建议级"}}
        result = check_crossref(load_dl(), registry=ok_reg)
        self.assertTrue(result["ok"], result)


class TestMutualLocation(unittest.TestCase):
    def test_reverse_index(self):
        index = reverse_index(load_dl())
        self.assertIn("DL-C01", index)
        self.assertIn("SLOP-G-01", index["DL-C01"])

    def test_forward_and_reverse_consistent(self):
        dl = load_dl()
        index = reverse_index(dl)
        for slop_id, entry in GATE_DESIGN_REFS.items():
            for ref in entry["design_refs"]:
                # 正向登记的每个引用，反向都能定位回来
                self.assertIn(slop_id, index.get(ref, []),
                              f"{ref} 反向索引缺 {slop_id}")
        # 反向索引里的每个编号在 DL 条目表中真实存在
        dl_ids = {r["id"] for r in dl["rules"]}
        for ref in index:
            self.assertIn(ref, dl_ids)

    def test_report_versions_and_ok(self):
        report = crossref_report(load_dl())
        self.assertEqual(report["gate_version"], GATE_VERSION)
        self.assertEqual(report["dl_version"], "1.0.0")
        self.assertTrue(report["ok"])
        self.assertEqual(len(report["entries"]), 5)
        self.assertTrue(report["reverse_index"])


if __name__ == "__main__":
    unittest.main()
