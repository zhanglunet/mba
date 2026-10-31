# -*- coding: utf-8 -*-
"""PRD-261/T2 自测（trend #1306）：组件库/提示词生成/组件树解析/网关校验。

运行：python3 -m pytest tests/unit/test_prd261_review_widget.py -q

覆盖（T1 §5 T2 验收：「样例可解析为组件树」+网关前置）：
  提示词生成：八组件全覆盖、版本头、模板化（改组件库即变）
  解析：合法树通过；非法 JSON/根错误/超深拒绝
  网关校验：非法属性丢弃（日志）、未知组件替换 warning note、必填缺失拒绝节点
  净树不再含非法内容；校验日志机读可回放

虚构纪律：评审数据全虚构（示例产品/示例评分）；不含真实主机名、账号、密钥。
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from review_widget_board import (  # noqa: E402
    WIDGETS, build_system_prompt, parse_component_tree, validate_tree, TreeSyntaxError,
)

CLEAN_TREE = {
    "component": "panel", "props": {
        "title": "示例产品评审看板", "level": "summary",
        "children": [
            {"component": "verdict-card", "props": {"verdict": "recommend", "confidence": 82,
                                                      "rationale_ref": "findings-001"}},
            {"component": "metric-row", "props": {"label": "示例满意度", "value": "4.2", "unit": "分", "trend": "up"}},
            {"component": "note", "props": {"body": "示例结论说明", "tone": "neutral"}},
        ],
    },
}


class TestSystemPrompt(unittest.TestCase):
    def test_prompt_covers_all_widgets(self):
        prompt = build_system_prompt()
        for name in WIDGETS:
            self.assertIn(name, prompt)
        self.assertIn("review-widget", prompt)
        self.assertIn("不得输出 HTML", prompt)

    def test_prompt_changes_with_library(self):
        """模板化：组件库变提示词变（加一个假组件验证）。"""
        WIDGETS["_probe_"] = {"required": ["x"], "props": {"x": {"type": "str", "max_len": 5}}}
        try:
            self.assertIn("_probe_", build_system_prompt())
        finally:
            WIDGETS.pop("_probe_")
        self.assertNotIn("_probe_", build_system_prompt())


class TestParse(unittest.TestCase):
    def test_clean_tree_parses(self):
        tree = parse_component_tree(json.dumps(CLEAN_TREE, ensure_ascii=False))
        self.assertEqual(tree["component"], "panel")

    def test_bad_json_rejected(self):
        for bad in ("not json", "[]", '{"component": "note"}'):
            with self.assertRaises(TreeSyntaxError):
                parse_component_tree(bad)

    def test_depth_limit(self):
        deep = {"component": "panel", "props": {"title": "x"}}
        node = deep
        for _ in range(10):
            node["props"]["children"] = [{"component": "panel", "props": {}}]
            node = node["props"]["children"][0]
        with self.assertRaises(TreeSyntaxError):
            parse_component_tree(json.dumps(deep))


class TestGateway(unittest.TestCase):
    def test_clean_tree_untouched_no_log_issues(self):
        clean, log = validate_tree(CLEAN_TREE)
        self.assertEqual(clean["component"], "panel")
        self.assertEqual(len(log), 0)
        self.assertEqual(clean["props"]["children"][0]["props"]["verdict"], "recommend")

    def test_illegal_prop_dropped_with_log(self):
        tree = {"component": "panel", "props": {
            "title": "示例", "hack_prop": "<script>",
            "children": [{"component": "note", "props": {"body": "示例", "tone": "neutral"}}]}}
        clean, log = validate_tree(tree)
        self.assertNotIn("hack_prop", clean["props"])
        self.assertTrue(any(e["action"] == "dropped_prop" and e["prop"] == "hack_prop" for e in log))

    def test_unknown_component_replaced_with_warning_note(self):
        tree = {"component": "panel", "props": {
            "title": "示例",
            "children": [{"component": "free_html", "props": {"html": "<script>x</script>"}}]}}
        clean, log = validate_tree(tree)
        child = clean["props"]["children"][0]
        self.assertEqual(child["component"], "note")
        self.assertEqual(child["props"]["tone"], "warning")
        self.assertTrue(any(e["action"] == "replaced_warning" for e in log))
        # 非法内容不渲染：净树里无 script
        self.assertNotIn("<script>", json.dumps(clean, ensure_ascii=False))

    def test_missing_required_node_rejected(self):
        tree = {"component": "panel", "props": {
            "title": "示例",
            "children": [{"component": "verdict-card", "props": {"confidence": 50}}]}}
        clean, log = validate_tree(tree)
        child = clean["props"]["children"][0]
        self.assertEqual(child["component"], "note")  # 被拒后替换为 warning note
        self.assertTrue(any(e["action"] == "node_rejected" for e in log))

    def test_enum_violation_dropped(self):
        tree = {"component": "panel", "props": {
            "title": "示例",
            "children": [{"component": "verdict-card", "props": {"verdict": "maybe", "rationale_ref": "f-1"}}]}}
        clean, log = validate_tree(tree)
        child = clean["props"]["children"][0]
        self.assertEqual(child["component"], "note")  # verdict 非法 → 必填缺失被拒
        self.assertTrue(any(e.get("reason") and "不在" in e["reason"] for e in log))


if __name__ == "__main__":
    unittest.main()
