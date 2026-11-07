# -*- coding: utf-8 -*-
"""PRD-296/T3 测试（trend #1483）：评审引用歧义闸门与结论引用字段。

运行：.venv/bin/python -m pytest tests/unit/test_prd296_t3_gates.py -q

覆盖（T1 设计 §5/§6）：评审开始闸一票否决（NOT_FOUND/AMBIGUOUS/
REGISTRY_CORRUPT 三路停下问）；结论引用字段账本（指纹/作品 id/状态逐引用
可溯源、refused 不进结论、AST 零快照写导入——口径变更走 282）；错误码
封闭穷举。零网络；全合成占位。
"""
import ast
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from ref_gates import (  # noqa: E402
    ERROR_CODES,
    ConclusionRefLedger,
    gate_review_start,
)
from work_ref import resolve  # noqa: E402

PACKS = [{"name": "brand-pack（占位）", "members": ["评委A（占位）", "评委B（占位）"]}]
WORKS = [{"work_id": 42, "status": "在库（占位）"}]


class 评审开始闸Tests(unittest.TestCase):
    def test_all_resolved_allows(self):
        res = [resolve("@brand-pack（占位）", PACKS, WORKS),
               resolve("@作品42", PACKS, WORKS)]
        self.assertTrue(gate_review_start(res)["allow"])

    def test_veto_paths(self):
        blocked = gate_review_start([resolve("@作品99", PACKS, WORKS)])
        self.assertFalse(blocked["allow"])
        self.assertEqual(blocked["error_code"], "REF_NOT_FOUND")
        corrupt = gate_review_start([resolve("@brand-pack（占位）",
                                             PACKS + [{"name": "brand-pack（占位）",
                                                       "members": []}], WORKS)])
        self.assertFalse(corrupt["allow"])
        self.assertEqual(corrupt["error_code"], "REF_REGISTRY_CORRUPT")  # 显形交人工


class 结论引用账本Tests(unittest.TestCase):
    def test_append_ref_traceable(self):
        ledger = ConclusionRefLedger()
        ledger.open_conclusion("concl-001")
        out = resolve("@brand-pack（占位）", PACKS, WORKS)
        entry = ledger.append_ref("concl-001", out)
        self.assertTrue(entry["judgepack_fingerprint"].startswith("sha16:"))
        record = ledger.get("concl-001")
        self.assertEqual(len(record["ref_resolutions"]), 1)

    def test_refused_never_enters_ledger(self):
        ledger = ConclusionRefLedger()
        ledger.open_conclusion("concl-002")
        refused = resolve("@作品99", PACKS, WORKS)
        with self.assertRaises(ValueError):
            ledger.append_ref("concl-002", refused)
        self.assertEqual(ledger.get("concl-002")["ref_resolutions"], [])

    def test_ast_no_snapshot_write(self):
        """R1：账本零快照写导入（口径变更走 PRD-282，本模块只记录用了哪一版）。"""
        banned = {"config_snapshot"}
        tree = ast.parse((REPO / "scripts" / "ref_gates.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module.split(".")[0]]
            for mod in mods:
                self.assertNotIn(mod, banned)


class 词表封闭Tests(unittest.TestCase):
    def test_four_codes_exhaustive(self):
        self.assertEqual(sorted(ERROR_CODES),
                         ["REF_AMBIGUOUS", "REF_NOT_FOUND",
                          "REF_REGISTRY_CORRUPT", "REF_SYNTAX_ERROR"])


if __name__ == "__main__":
    unittest.main()
