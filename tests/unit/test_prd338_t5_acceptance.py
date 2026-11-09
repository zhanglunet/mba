# -*- coding: utf-8 -*-
"""PRD-338/T5 测试（trend #1617 的 T5 环节）：幻灯片转换验收试运行。

运行：.venv/bin/python -m pytest tests/unit/test_prd338_t5_acceptance.py -q

覆盖（T1 §5 验收「样例记录全链回放 + 逐页比对演练 + 文档无密钥」）：
① 样例记录全链回放——三作品×多评委结论记录 → 转换闸 → 独立复核闸 →
  HTML 产物（单文件离线）；回放可复现逐字节一致；评语/分数逐字在位；
② 逐页比对演练——页数=作品数（<h2> 钉值）/每页评语条数=评委条数/页序=
  结论序；篡改产物页数 → SLIDES_PAGE_MISMATCH 拒绝；
③ 文档无密钥——T1 设计文档（T1 分支）零密钥/零 IP/外链仅 github 与
  example 域。
零网络；全合成占位。
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from slides import render_slides, slides_from_conclusions  # noqa: E402
from slides_gate import conversion_gate, verify_gate  # noqa: E402

GOOD = [
    {"work_id": 42, "work_title": "作品42（占位）",
     "evaluations": [
         {"evaluator": "评委甲（占位）", "verdict": "入围", "score": "92.5",
          "comment": "逻辑清晰（占位评语）"},
         {"evaluator": "评委乙（占位）", "verdict": "入围", "score": "88",
          "comment": "论证扎实（占位评语）"}]},
    {"work_id": 43, "work_title": "作品43（占位）",
     "evaluations": [{"evaluator": "评委丙（占位）", "verdict": "备选",
                      "score": "81", "comment": "完成度尚可（占位评语）"}]},
    {"work_id": 44, "work_title": "作品44（占位）",
     "evaluations": [{"evaluator": "评委甲（占位）", "verdict": "入围",
                      "score": "90", "comment": "演示流畅（占位评语）"}]},
]


class TestFullReplay(unittest.TestCase):
    def test_full_chain_to_artifact(self):
        """① 全链回放：转换闸 → 独立复核闸 → 单文件离线产物。"""
        gate = conversion_gate(GOOD)
        self.assertEqual(gate["gate"], "allow")
        html_text = gate["artifact"]
        self.assertEqual(gate["pages"], 5)   # 封面 + 3 作品 + 汇总
        second = verify_gate(GOOD, html_text)
        self.assertEqual(second["gate"], "allow")
        for token in ("逻辑清晰（占位评语）", "92.5", "演示流畅（占位评语）"):
            self.assertIn(token, html_text)
        self.assertNotIn("http://", html_text)
        self.assertNotIn("<script", html_text)

    def test_replay_reproducible(self):
        """① 回放可复现：同记录重放逐字节一致。"""
        a = conversion_gate(GOOD)
        b = conversion_gate(GOOD)
        self.assertEqual(a, b)


class TestPageMappingDrill(unittest.TestCase):
    def test_page_mapping_nailed(self):
        """② 逐页比对钉值：<h2> 数=作品数；页序=结论序。"""
        doc = slides_from_conclusions(GOOD)
        html_text = render_slides(doc["pages"])
        self.assertEqual(html_text.count("<h2>"), 3)
        kinds = [p["kind"] for p in doc["pages"]]
        self.assertEqual(kinds, ["cover", "work", "work", "work", "summary"])
        self.assertEqual([p["work_id"] for p in doc["pages"][1:4]],
                         [42, 43, 44])

    def test_per_page_evaluation_counts(self):
        """② 每页评语条数=评委条数（42 页 2 条，43/44 页各 1 条）。"""
        html_text = conversion_gate(GOOD)["artifact"]
        self.assertEqual(html_text.count("评委甲（占位）"), 2)
        self.assertEqual(html_text.count("评委乙（占位）"), 1)
        self.assertEqual(html_text.count("评委丙（占位）"), 1)

    def test_tampered_pages_rejected(self):
        """② 演练：抹掉一页标题 → SLIDES_PAGE_MISMATCH 拒绝。"""
        html_text = render_slides(slides_from_conclusions(GOOD)["pages"])
        broken = html_text.replace("<h2>", "", 1)
        out = verify_gate(GOOD, broken)
        self.assertEqual(out["gate"], "reject")
        self.assertEqual(out["error_code"], "SLIDES_PAGE_MISMATCH")


class TestDocNoSecrets(unittest.TestCase):
    def test_design_doc_no_secrets(self):
        """③ 文档无密钥：T1 设计文档（T1 分支）零密钥/零 IP/外链仅
        github 与 example 域。"""
        doc = subprocess.run(
            ["git", "show", "origin/trend/prd-338-t1-slides-design:docs/plans/"
             "2026-11-09-prd-338-slides-design.md"],
            capture_output=True, text=True, check=True).stdout
        for token in ("password", "secret", "api_key", "AKIA", "Bearer ",
                      "BEGIN RSA"):
            self.assertNotIn(token.lower(), doc.lower(), token)
        self.assertEqual(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", doc), [])
        # 只匹配真实主机形态（红线声明里的裸 scheme token 不是链接）
        for m in re.findall(r"https?://[A-Za-z0-9.\-]+", doc):
            self.assertTrue(any(ok in m for ok in
                                ("github.com", "example.invalid",
                                 "example.com")), m)


if __name__ == "__main__":
    unittest.main()
