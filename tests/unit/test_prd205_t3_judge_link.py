# -*- coding: utf-8 -*-
"""PRD-205/T3 自测（trend #1027）：评委接入——意见定位/无效意见驳回/结论规则/版本留痕。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from design_language_review import (  # noqa: E402
    normalize_level,
    review_findings,
    rule_index,
    validate_finding,
)

DL_PATH = Path(__file__).resolve().parents[2] / "design" / "design-language.json"


def load_dl():
    import json

    return json.loads(DL_PATH.read_text(encoding="utf-8"))


class TestLevelNormalize(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual(normalize_level("hard"), "hard")
        self.assertEqual(normalize_level("advice"), "soft")
        self.assertEqual(normalize_level("soft"), "soft")
        self.assertIsNone(normalize_level("critical"))
        self.assertIsNone(normalize_level(42))


class TestValidateFinding(unittest.TestCase):
    def test_valid_hard_finding_locates(self):
        dl = load_dl()
        finding = {
            "rule": "DL-C01",
            "level": "hard",
            "evidence": "示例页 card.html .btn: 背景 #ff00ff",
            "expect": "tokens.color.primary (#1a73e8)",
        }
        check = validate_finding(dl, finding)
        self.assertTrue(check["ok"], check["reasons"])
        self.assertEqual(check["located"]["rule"], "DL-C01")
        self.assertTrue(check["located"]["rule_description"])
        self.assertEqual(check["located"]["level"], "hard")

    def test_advice_alias_matches_soft_rule(self):
        dl = load_dl()
        finding = {
            "rule": "DL-S01",
            "level": "advice",
            "evidence": "示例页 a.html .row: margin 15px",
            "expect": "间距档位 4/8/16/24/32",
        }
        self.assertTrue(validate_finding(dl, finding)["ok"])

    def test_unknown_rule_invalid(self):
        dl = load_dl()
        check = validate_finding(dl, {"rule": "DL-X99", "level": "hard",
                                      "evidence": "x.html: y", "expect": "z"})
        self.assertFalse(check["ok"])
        self.assertIn("不存在", check["reasons"][0])

    def test_deprecated_rule_invalid(self):
        dl = {"meta": {"version": "9.9.9"},
              "rules": [{"id": "DL-C01", "description": "旧条目",
                         "severity": "hard", "status": "deprecated"}]}
        check = validate_finding(dl, {"rule": "DL-C01", "level": "hard",
                                      "evidence": "x.html: y", "expect": "z"})
        self.assertFalse(check["ok"])
        self.assertIn("deprecated", check["reasons"][0])

    def test_level_mismatch_invalid(self):
        dl = load_dl()
        # 把建议级条目报成硬规则违反 → 无效（不得越级）
        check = validate_finding(dl, {"rule": "DL-S01", "level": "hard",
                                      "evidence": "a.html: 15px", "expect": "档位"})
        self.assertFalse(check["ok"])
        self.assertTrue(any("不一致" in r for r in check["reasons"]))

    def test_missing_evidence_invalid(self):
        dl = load_dl()
        check = validate_finding(dl, {"rule": "DL-C01", "level": "hard", "expect": "x"})
        self.assertFalse(check["ok"])

    def test_missing_expect_invalid(self):
        dl = load_dl()
        check = validate_finding(dl, {"rule": "DL-C01", "level": "hard",
                                      "evidence": "a.html: #ff00ff"})
        self.assertFalse(check["ok"])

    def test_rule_index(self):
        dl = load_dl()
        index = rule_index(dl)
        self.assertIn("DL-C01", index)
        self.assertIn("DL-M01", index)
        self.assertEqual(len(index), len(dl["rules"]))


class TestReviewFindings(unittest.TestCase):
    def test_hard_violation_fail(self):
        dl = load_dl()
        result = review_findings(dl, [{
            "rule": "DL-C01", "level": "hard",
            "evidence": "示例页 card.html .btn: #ff00ff",
            "expect": "tokens.color.primary",
        }])
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(result["counts"]["hard_violations"], 1)
        self.assertEqual(result["findings"][0]["status"], "valid")

    def test_soft_only_pass_with_notes(self):
        dl = load_dl()
        result = review_findings(dl, [{
            "rule": "DL-M01", "level": "advice",
            "evidence": "示例页 a.html .modal: 400ms",
            "expect": "150ms/300ms 档位",
        }])
        self.assertEqual(result["verdict"], "pass_with_notes")
        self.assertEqual(result["counts"]["notes"], 1)

    def test_clean_pass(self):
        dl = load_dl()
        result = review_findings(dl, [])
        self.assertEqual(result["verdict"], "pass")

    def test_invalid_excluded_from_verdict_but_listed(self):
        dl = load_dl()
        result = review_findings(dl, [
            {"rule": "DL-N00", "level": "hard", "evidence": "x", "expect": "y"},
            {"rule": "DL-C01", "level": "hard", "evidence": "card.html: #ff00ff",
             "expect": "#1a73e8"},
        ])
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(result["counts"]["invalid"], 1)
        self.assertEqual(result["findings"][0]["status"], "invalid")
        self.assertTrue(result["findings"][0]["invalid_reasons"])

    def test_version_stamped(self):
        dl = load_dl()
        result = review_findings(dl, [])
        self.assertEqual(result["dl_version"], dl["meta"]["version"])

    def test_mixed_counts(self):
        dl = load_dl()
        result = review_findings(dl, [
            {"rule": "DL-C01", "level": "hard", "evidence": "e1", "expect": "x1"},
            {"rule": "DL-S01", "level": "soft", "evidence": "e2", "expect": "x2"},
            {"rule": "DL-BAD", "level": "hard", "evidence": "e3", "expect": "x3"},
        ])
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(result["counts"],
                         {"hard_violations": 1, "notes": 1, "invalid": 1})

    def test_format_finding_line(self):
        dl = load_dl()
        result = review_findings(dl, [{
            "rule": "DL-C01", "level": "hard",
            "evidence": "card.html .btn: #ff00ff", "expect": "#1a73e8",
        }])
        line = __import__("design_language_review").format_finding(result["findings"][0])
        self.assertIn("[DL-C01]", line)
        self.assertIn("(hard)", line)
        self.assertIn("#ff00ff", line)


if __name__ == "__main__":
    unittest.main()
