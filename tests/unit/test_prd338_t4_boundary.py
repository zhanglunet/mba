# -*- coding: utf-8 -*-
"""PRD-338/T4 测试（trend #1617 的 T4 环节）：幻灯片转换划界断言。

运行：.venv/bin/python -m pytest tests/unit/test_prd338_t4_boundary.py -q

覆盖（T1 §0 R1–R4 + §2 划界）：R2 零改写字面断言（评语/分数逐字进页面——
字面集合一致：每条评语/分数的转义形态在 HTML 中恰好在位）；R4 分数只展示
不改写（分数原字符串逐字在位 + 零计算符号——模块零 sum/avg 排名逻辑对
evaluations 数值运算 AST 断言 + 汇总尾页只计数条数零平均）；R3 离线可用
（产物零外链 URL/零 src=/零 @import/零 <link）；R1 页对应复钉；模块隔离
（slides 零看板/排名模块导入——汇总排名属看板职责）；确定性。零网络；全
合成占位。
"""
import ast
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from slides import render_slides, slides_from_conclusions  # noqa: E402

GOOD = [
    {"work_id": 42, "work_title": "作品42（占位）",
     "evaluations": [{"evaluator": "评委甲（占位）", "verdict": "入围",
                      "score": "92.50（保留两位原样）", "comment": "逻辑清晰（占位评语）"}]},
]
HTML = render_slides(slides_from_conclusions(GOOD)["pages"])


class TestR2Verbatim:
    def test_comment_verbatim_in_page(self):
        """R2 字面断言：评语逐字（转义形态）进页面。"""
        import html as _html
        assert _html.escape("逻辑清晰（占位评语）") in HTML

    def test_zero_rewrite_literal_set(self):
        """R2：字面集合一致——HTML 转义解码后含全部评语/分数原字面。"""
        import html as _html
        import re
        decoded = _html.unescape(HTML)
        for c in GOOD:
            for ev in c["evaluations"]:
                assert ev["comment"] in decoded
                assert ev["score"] in decoded


class TestR4ScoreUntouched:
    def test_score_original_string_in_page(self):
        """R4：分数 = 评审记录原值（含保留位数）逐字在位。"""
        assert "92.50（保留两位原样）" in HTML

    def test_zero_arithmetic_on_scores(self):
        """R4 AST：模块零分数数值运算（零 sum/mean 聚合评分值）——汇总只计
        条数（len），排名归看板职责。"""
        src = (REPO / "scripts" / "slides.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(
                    node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                raise AssertionError(f"slides.py 出现数值运算 {ast.dump(node.op)}")

    def test_summary_counts_only(self):
        """R4：汇总尾页只呈现计数（works_total/evaluations_total）。"""
        doc = slides_from_conclusions(GOOD)
        summary = doc["pages"][-1]
        assert summary["kind"] == "summary"
        assert summary["works_total"] == 1
        assert summary["evaluations_total"] == 1
        assert "平均" not in render_slides(doc["pages"])


class TestR3Offline:
    def test_zero_external_links(self):
        """R3：产物零外链 URL/零 src=/零 @import/零 <link——断网完整可用。"""
        for token in ("http://", "https://", "src=", "@import", "<link",
                      "<script", "url("):
            assert token not in HTML, token

    def test_single_file_inline_style(self):
        assert "<style>" in HTML and "</style>" in HTML


class TestR1AndIsolation:
    def test_page_mapping_recheck(self):
        """R1 复钉：页序=结论记录序（封面+每作品一页+汇总）。"""
        doc = slides_from_conclusions(GOOD)
        kinds = [p["kind"] for p in doc["pages"]]
        assert kinds == ["cover", "work", "summary"]
        assert doc["pages"][1]["work_id"] == 42

    def test_no_board_or_ranking_imports(self):
        """模块隔离：slides 零看板/排名模块导入（汇总排名属看板职责）。"""
        banned = {"urllib", "requests", "socket", "http", "subprocess",
                  "leaderboard", "ranking", "dashboard"}
        tree = ast.parse((REPO / "scripts" / "slides.py").read_text(
            encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module.split(".")[0]]
            for mod in mods:
                assert mod not in banned, f"slides.py 导入了 {mod}"

    def test_deterministic(self):
        assert HTML == render_slides(slides_from_conclusions(GOOD)["pages"])


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-q"])
