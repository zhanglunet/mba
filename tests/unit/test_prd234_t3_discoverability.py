# -*- coding: utf-8 -*-
"""PRD-234/T3 自测：品牌技能跨工具加载验证（trend #1172）。

运行：uv run --with pytest python -m pytest tests/unit/test_prd234_t3_discoverability.py -q

覆盖：真实 46 技能包全量检查（验收「验证记录齐全，失败项有原因说明」——失败
类型精确对账：metadata×46×2 / description 超长×9 / 触发式句式缺×9，每条失败
带 reason）；误报防线（musk-perspective 的 sk- 子串、公开引文 URL 不在违规面、
长度原因含实际字数与处置建议）；失败路径 fixture（缺 SKILL.md/name 不一致/
超长/越权密钥/内网地址/重复名）；落盘验证记录与重跑一致；确定性。零网络。
"""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from check_perspective_discoverability import (  # noqa: E402
    DESCRIPTION_MAX,
    PERSPECTIVES_DIR,
    check_all,
    check_skill,
)

REPORT_PATH = REPO / "docs" / "plans" / "prd234-t3-discoverability-report.json"


class 真实全量验证Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = check_all()

    def test_covers_all_46_packs(self):
        self.assertEqual(self.report["summary"]["total"], 46)
        self.assertEqual(len(self.report["results"]), 46)

    def test_failure_kinds_exact_ledger(self):
        """验收核心：失败项有原因说明——失败类型精确对账（当前出厂状态如实记录）。"""
        self.assertEqual(self.report["summary"]["failure_kinds"], {
            "metadata.version 在位": 46,
            "metadata.standard 对齐声明": 46,
            "description 长度": 9,
            "触发式句式（Use as / Explicit triggers）": 9,
        })

    def test_every_failure_has_reason(self):
        """每条失败必须带 reason（验收口径），metadata 类指明 T4 处置去向。"""
        reasons = self.report["summary"]["failure_reasons"]
        self.assertTrue(reasons)
        for failure in reasons:
            self.assertTrue(failure["reason"].strip())
        metadata_reasons = [r["reason"] for r in reasons
                            if r["item"] == "metadata.version 在位"]
        self.assertTrue(all("T4" in r for r in metadata_reasons))

    def test_overlength_reason_reports_actual_length(self):
        """description 超长：reason 含实际字数与上限（可核对）。"""
        overlength = [r for r in self.report["summary"]["failure_reasons"]
                      if r["item"] == "description 长度"]
        self.assertEqual(len(overlength), 9)
        for failure in overlength:
            self.assertRegex(failure["reason"], r"\d+ 字 > 1024")

    def test_no_false_positive_on_repo_naming_and_public_citations(self):
        """误报防线：musk-perspective 的 sk- 子串、公开引文 URL 不产生失败。"""
        musk = next(r for r in self.report["results"] if r["skill"] == "musk-perspective")
        items = {c["item"] for c in musk["checks"] if not c["ok"]}
        self.assertNotIn("无密钥字面量", items)
        for result in self.report["results"]:
            items = {c["item"] for c in result["checks"] if not c["ok"]}
            self.assertNotIn("无密钥字面量", items)
            self.assertNotIn("无内网主机/凭据", items)

    def test_schema_and_scope_statement(self):
        self.assertEqual(self.report["schema"], "perspective-discoverability-report/v1")
        self.assertIn("结构级", self.report["scope"])
        self.assertIn("T5", self.report["scope"])  # 真实工具实测归 T5，诚实声明


class 失败路径FixtureTests(unittest.TestCase):
    def _write(self, tmp: Path, dirname: str, content: str) -> Path:
        d = tmp / dirname
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(content, encoding="utf-8")
        return d

    VALID = """---
name: test-perspective
description: |
  测试评委（占位人设）——默认怀疑的求证型视角。

  Use as: MBA `test` panel judge — 测试镜头。

  Explicit triggers: "用测试视角看"。
metadata:
  version: 1.0.0
  standard: agentskills-2026-10
---
# 测试评委正文（占位）

按指令执行（非空正文）。
"""

    def test_valid_fixture_passes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self._write(Path(tmp), "test-perspective", self.VALID)
            report = check_all(Path(tmp))
            self.assertEqual(report["summary"]["failed"], 0)

    def test_metadata_gap_flagged_with_reason(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            content = self.VALID.replace("metadata:\n  version: 1.0.0"
                                         "\n  standard: agentskills-2026-10\n", "")
            self._write(Path(tmp), "test-perspective", content)
            report = check_all(Path(tmp))
            bad = report["summary"]["failure_reasons"]
            self.assertTrue(any("metadata.version" in b["item"] for b in bad))
            self.assertTrue(all(b["reason"] for b in bad))

    def test_overlength_flagged_with_counts(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            content = self.VALID.replace("测试镜头。", "测试镜头。" + "长" * 1100)
            self._write(Path(tmp), "test-perspective", content)
            report = check_all(Path(tmp))
            bad = [b for b in report["summary"]["failure_reasons"]
                   if b["item"] == "description 长度"]
            self.assertEqual(len(bad), 1)

    def test_real_secret_flagged_but_name_substring_not(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            secret = "sk-" + "Ab12Cd34Ef56Gh78"  # 16 位随机形态（合成，非真实密钥）
            content = self.VALID.replace("按指令执行", f"token={secret} 仅为触发检查的合成串")
            self._write(Path(tmp), "test-perspective", content)
            report = check_all(Path(tmp))
            self.assertTrue(any("密钥" in b["item"]
                                for b in report["summary"]["failure_reasons"]))

    def test_internal_host_flagged(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            content = self.VALID.replace("按指令执行",
                                         "回调地址 https://10.0.0.1/hook（占位内网）")
            self._write(Path(tmp), "test-perspective", content)
            report = check_all(Path(tmp))
            self.assertTrue(any("内网" in b["item"]
                                for b in report["summary"]["failure_reasons"]))

    def test_public_citation_url_not_flagged(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            content = self.VALID.replace("按指令执行",
                                         "引文：https://news.qq.com/rain/a/20260214A05TA000（公开报道）")
            self._write(Path(tmp), "test-perspective", content)
            report = check_all(Path(tmp))
            self.assertEqual(report["summary"]["failed"], 0)

    def test_duplicate_names_flagged(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self._write(Path(tmp), "dup-a-perspective", self.VALID)
            self._write(Path(tmp), "dup-b-perspective", self.VALID)
            report = check_all(Path(tmp))
            self.assertEqual(report["summary"]["failed"], 2)


class 验证记录与确定性Tests(unittest.TestCase):
    def test_committed_record_matches_fresh_run(self):
        """落盘验证记录（docs/plans/prd234-t3-discoverability-report.json）
        与重跑结果一致——验证记录齐全且可复现。"""
        committed = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        fresh = check_all()
        self.assertEqual(committed, fresh)

    def test_deterministic(self):
        one = json.dumps(check_all(), ensure_ascii=False, sort_keys=True)
        two = json.dumps(check_all(), ensure_ascii=False, sort_keys=True)
        self.assertEqual(one, two)


if __name__ == "__main__":
    unittest.main()
