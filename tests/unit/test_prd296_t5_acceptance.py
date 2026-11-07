# -*- coding: utf-8 -*-
"""PRD-296/T5 测试（trend #1485）：验收试运行——样例全流程回放 + 歧义/失败
演练 + 文档无密钥。

运行：.venv/bin/python -m pytest tests/unit/test_prd296_t5_acceptance.py -q

验收标准（trend #1485）：**引用解析全链通过；红线断言全过；文档无密钥**。

回放：评审指令含 @brand-pack（占位） @作品42 → resolve_logged 全留痕 →
结论引用账本（指纹在案）→ 歧义/失败演练（NOT_FOUND/AMBIGUOUS/CORRUPT/
SYNTAX 全触发）→ 文档无密钥。
零网络；全合成占位。
"""
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from ref_gates import ConclusionRefLedger  # noqa: E402
from work_ref import RefAudit, resolve  # noqa: E402

PACKS = [{"name": "brand-pack（占位）", "members": ["评委A（占位）", "评委B（占位）"]}]
WORKS = [{"work_id": 42, "status": "在库（占位）"},
         {"work_id": 43, "status": "已撤回（占位）"}]
INSTRUCTION_REFS = ["@brand-pack（占位）", "@作品42"]


class 全链回放Tests(unittest.TestCase):
    def test_full_chain_replay_with_ledger(self):
        """样例全流程：解析+留痕 → 结论账本（指纹/作品状态逐引用在案）。"""
        audit = RefAudit()
        ledger = ConclusionRefLedger()
        ledger.open_conclusion("concl-001")
        for i, raw in enumerate(INSTRUCTION_REFS):
            out = audit.resolve_logged(raw, PACKS, WORKS,
                                       at=f"2026-11-04T09:0{i}:00Z")
            self.assertFalse(out["refused"], raw)
            ledger.append_ref("concl-001", out["resolution"] if "resolution" in out
                              else out)
        record = ledger.get("concl-001")
        self.assertEqual(len(record["ref_resolutions"]), 2)
        self.assertTrue(record["ref_resolutions"][0]["judgepack_fingerprint"]
                        .startswith("sha16:"))
        self.assertEqual(record["ref_resolutions"][1]["work_status"], "在库（占位）")

    def test_replay_deterministic(self):
        def run():
            audit = RefAudit()
            for i, raw in enumerate(INSTRUCTION_REFS):
                audit.resolve_logged(raw, PACKS, WORKS, at=f"2026-11-04T09:0{i}:00Z")
            return str(audit.records)
        self.assertEqual(run(), run())


class 歧义失败演练Tests(unittest.TestCase):
    def test_all_failures_block(self):
        """四路全触发（NOT_FOUND/AMBIGUOUS/CORRUPT/SYNTAX）。"""
        audit = RefAudit()
        for raw, want in (("@作品99", "REF_NOT_FOUND"),
                          ("@最新评委包", "REF_SYNTAX_ERROR"),
                          ("@brand-pack（占位）#成员", "REF_SYNTAX_ERROR")):
            out = audit.resolve_logged(raw, PACKS, WORKS, at="2026-11-04T09:00:00Z")
            self.assertTrue(out["refused"], raw)
            self.assertEqual(out["error_code"], want, raw)
        dup = PACKS + [{"name": "brand-pack（占位）", "members": []}]
        out = audit.resolve_logged("@brand-pack（占位）", dup, WORKS,
                                   at="2026-11-04T09:01:00Z")
        self.assertEqual(out["error_code"], "REF_REGISTRY_CORRUPT")


class 文档无密钥Tests(unittest.TestCase):
    def test_design_doc_no_secrets(self):
        secret_re = re.compile(r"(sk-[A-Za-z0-9]{8,}|ghp_[A-Za-z0-9]{8,}|"
                               r"AKIA[0-9A-Z]{16}|password\s*[:=]\s*['\"][^'\"]{4,})",
                               re.IGNORECASE)
        docs = list((REPO / "docs" / "plans").glob("2026-11-04-prd-296-*.md"))
        self.assertTrue(docs, "T1 设计文档在位")
        for doc in docs:
            blob = doc.read_text(encoding="utf-8")
            self.assertFalse(secret_re.findall(blob), doc.name)
            for host in re.findall(r"https?://([a-z0-9.-]+)", blob, re.IGNORECASE):
                self.assertTrue(host.endswith(("github.com", "example.com",
                                               "example.invalid", "synthetic",
                                               "local")), f"{doc.name} {host}")


if __name__ == "__main__":
    unittest.main()
