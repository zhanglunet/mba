# -*- coding: utf-8 -*-
"""PRD-296/T2 测试（trend #1482）：@评委包/@作品引用解析最小实现。

运行：.venv/bin/python -m pytest tests/unit/test_prd296_t2_ref.py -q

覆盖（T1 设计 §3/§4/§5/§6）：parse 两形态与禁止形态（成员后缀/子对象/相对词/
双写）；指纹 canonical SHA-256 前 16；resolve 精确匹配→包指纹/作品 id、
撤回作品显形寻址、候选 0/多裁决、REGISTRY_CORRUPT；二值返回；RefAudit
append-only 成败都记。零网络；全合成占位。
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from work_ref import (  # noqa: E402
    RefAudit,
    RefSyntaxError,
    pack_fingerprint,
    parse,
    resolve,
)

PACKS = [{"name": "brand-pack（占位）", "members": ["评委A（占位）", "评委B（占位）"]}]
WORKS = [{"work_id": 42, "status": "在库（占位）"},
         {"work_id": 43, "status": "已撤回（占位）"}]


class TestParse(unittest.TestCase):
    def test_two_forms(self):
        self.assertEqual(parse("@brand-pack（占位）"),
                         {"kind": "judgepack", "name": "brand-pack（占位）",
                          "work_number": None})
        self.assertEqual(parse("@作品42"),
                         {"kind": "work", "name": None, "work_number": 42})

    def test_prohibited_forms(self):
        for bad in ("@brand-pack（占位）#成员", "@作品42/评论", "@最新评委包",
                    "@@双写", "@包 名"):
            with self.assertRaises(RefSyntaxError):
                parse(bad)


class TestResolve(unittest.TestCase):
    def test_pack_resolves_with_fingerprint(self):
        out = resolve("@brand-pack（占位）", PACKS, WORKS)
        self.assertEqual(out["resolution"]["status"], "resolved")
        self.assertEqual(out["judgepack"]["member_count"], 2)
        want = pack_fingerprint(["评委A（占位）", "评委B（占位）"])
        self.assertEqual(out["judgepack"]["fingerprint"], want)
        # 指纹确定性：成员顺序无关
        self.assertEqual(want, pack_fingerprint(["评委B（占位）", "评委A（占位）"]))

    def test_work_resolves_with_status_visible(self):
        out = resolve("@作品43", PACKS, WORKS)
        self.assertEqual(out["work_id"], 43)
        self.assertEqual(out["meta_summary"]["work_status"], "已撤回（占位）")  # 显形不拦截

    def test_not_found_and_corrupt(self):
        out = resolve("@作品99", PACKS, WORKS)
        self.assertEqual(out["resolution"]["error_code"], "REF_NOT_FOUND")
        dup = PACKS + [{"name": "brand-pack（占位）", "members": []}]
        out2 = resolve("@brand-pack（占位）", dup, WORKS)
        self.assertEqual(out2["resolution"]["error_code"], "REF_REGISTRY_CORRUPT")

    def test_binary_return(self):
        for raw in ("@brand-pack（占位）", "@作品42", "@作品99"):
            out = resolve(raw, PACKS, WORKS)
            self.assertIn(out["resolution"]["status"], ("resolved", "refused"))


class TestRefAudit(unittest.TestCase):
    def test_success_logged_with_fingerprint(self):
        audit = RefAudit()
        audit.resolve_logged("@brand-pack（占位）", PACKS, WORKS,
                             at="2026-11-04T09:00:00Z")
        audit.resolve_logged("@作品43", PACKS, WORKS, at="2026-11-04T09:01:00Z")
        self.assertEqual(audit.records[0]["resolved"]["judgepack_fingerprint"],
                         pack_fingerprint(["评委A（占位）", "评委B（占位）"]))
        self.assertEqual(audit.records[1]["resolved"]["work_status"],
                         "已撤回（占位）")

    def test_refused_and_syntax_logged(self):
        audit = RefAudit()
        audit.resolve_logged("@作品99", PACKS, WORKS, at="2026-11-04T09:00:00Z")
        audit.resolve_logged("@最新评委包", PACKS, WORKS, at="2026-11-04T09:01:00Z")
        self.assertEqual([r["error_code"] for r in audit.records],
                         ["REF_NOT_FOUND", "REF_SYNTAX_ERROR"])

    def test_append_only(self):
        audit = RefAudit()
        audit.resolve_logged("@作品42", PACKS, WORKS, at="2026-11-04T09:00:00Z")
        before = list(audit.records)
        audit.resolve_logged("@作品99", PACKS, WORKS, at="2026-11-04T09:01:00Z")
        self.assertEqual(audit.records[:len(before)], before)


if __name__ == "__main__":
    unittest.main()
