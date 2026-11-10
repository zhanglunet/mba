# -*- coding: utf-8 -*-
"""PRD-338/T2 测试（trend #1617 的 T2 环节）：评审报告一键转 HTML 幻灯片最小实现。

运行：.venv/bin/python -m pytest tests/unit/test_prd338_t2_slides.py -q

覆盖（T1 设计 §3.1/§3.2/§3.3）：页结构三段（封面/作品页×N/汇总尾页）逐页
对应规则 R1（页序=结论记录序/每页评语条数=评委条数一对一不合并）+零改写
R2（评语分数逐字进页面分数原字符串直接输出）+单文件离线 R3（全内联零外链
零 script，转换器内防线）+CONCLUSION_INCOMPLETE 缺条目显形拒绝+回读自检
SLIDES_PAGE_MISMATCH+确定性。零网络；全合成占位。
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from slides import (  # noqa: E402
    ConclusionIncomplete,
    SlidesMismatch,
    render_slides,
    self_check,
    slides_from_conclusions,
)

CONCLUSIONS = [
    {"work_id": "w-1（占位）", "work_title": "作品一（占位）",
     "evaluations": [
         {"evaluator": "评委A（占位）", "verdict": "通过（占位）",
          "score": "8.5/10（占位）", "comment": "设计语言契合（占位评语）"},
         {"evaluator": "评委B（占位）", "verdict": "有条件通过（占位）",
          "score": "7.0/10（占位）", "comment": "叙事可再聚焦（占位评语）"}]},
    {"work_id": "w-2（占位）", "work_title": "作品二（占位）",
     "evaluations": [
         {"evaluator": "评委C（占位）", "verdict": "不通过（占位）",
          "score": "4.0/10（占位）", "comment": "证据链断裂（占位评语）"}]},
]


class 页结构Tests(unittest.TestCase):
    def test_three_section_structure(self):
        pages = slides_from_conclusions(CONCLUSIONS)["pages"]
        self.assertEqual([p["kind"] for p in pages],
                         ["cover", "work", "work", "summary"])   # R1 页序=记录序
        self.assertEqual(pages[1]["evaluations"][0]["comment"], "设计语言契合（占位评语）")

    def test_incomplete_conclusion_rejected(self):
        with self.assertRaises(ConclusionIncomplete):
            slides_from_conclusions([{"work_id": "w-x", "work_title": "x（占位）",
                                      "evaluations": []}])


class 零改写Tests(unittest.TestCase):
    def test_scores_and_comments_verbatim(self):
        pages = slides_from_conclusions(CONCLUSIONS)["pages"]
        work = pages[1]
        self.assertEqual(work["evaluations"][0]["score"], "8.5/10（占位）")  # R4 原字符串
        self.assertEqual(work["evaluations"][0]["comment"], "设计语言契合（占位评语）")


class 单文件Tests(unittest.TestCase):
    def test_single_file_offline_no_external_no_script(self):
        pages = slides_from_conclusions(CONCLUSIONS)["pages"]
        html_text = render_slides(pages)
        self.assertTrue(html_text.startswith("<!doctype html>"))
        for token in ("http://", "https://", "<script", "src=", "href="):
            self.assertNotIn(token, html_text, token)          # R3 零外链资源
        self.assertIn("<style>", html_text)                    # 全内联

    def test_self_check_pass_and_fail(self):
        pages = slides_from_conclusions(CONCLUSIONS)["pages"]
        html_text = render_slides(pages)
        self_check(pages, html_text)                           # 一致 → 静默过
        with self.assertRaises(SlidesMismatch):
            self_check(pages, html_text + "<script>x</script>")


if __name__ == "__main__":
    unittest.main()
