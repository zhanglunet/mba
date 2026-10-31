# -*- coding: utf-8 -*-
"""PRD-205/T2 自测（trend #1026）：生成器接入——设计语言加载/提示词生成/token 查询。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from design_language_loader import load_design_language, get_token, build_prompt_section  # noqa: E402

DL_PATH = Path(__file__).resolve().parents[2] / "design" / "design-language.json"


class TestLoad(unittest.TestCase):
    def test_load_meta(self):
        dl = load_design_language(DL_PATH)
        self.assertEqual(dl["meta"]["version"], "1.0.0")

    def test_load_tokens_nested(self):
        dl = load_design_language(DL_PATH)
        tokens = dl.get("tokens", {})
        self.assertIsInstance(tokens, dict)
        self.assertTrue(len(tokens) > 0)

    def test_load_rules_list(self):
        dl = load_design_language(DL_PATH)
        rules = dl.get("rules", {})
        self.assertTrue(rules)


class TestTokenQuery(unittest.TestCase):
    def test_get_token_path(self):
        dl = load_design_language(DL_PATH)
        color = get_token(dl, "tokens.color.primary")
        self.assertEqual(color, "#1a73e8")

    def test_get_token_missing_returns_none(self):
        dl = load_design_language(DL_PATH)
        self.assertIsNone(get_token(dl, "tokens.color.nonexistent"))


class TestPromptSection(unittest.TestCase):
    def test_prompt_contains_tokens_and_rules(self):
        dl = load_design_language(DL_PATH)
        prompt = build_prompt_section(dl)
        self.assertIn("设计语言约束", prompt)
        self.assertIn("DL-C01", prompt)
        self.assertIn("primary", prompt)


if __name__ == "__main__":
    unittest.main()
