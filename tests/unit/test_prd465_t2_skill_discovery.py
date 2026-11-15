# -*- coding: utf-8 -*-
"""PRD-465/T2 测试（trend #2246 的 T2 环节）：mba skill 发现层。
运行：uv run --with pytest python -m pytest tests/unit/test_prd465_t2_skill_discovery.py -q
覆盖（T1 §1.3 + §6 + R1~R2）：索引三源并集/marketplace 不作源/超长描述
只读合规字段/触发命中高于描述命中/插件关键词命中/无命中空推荐/
确定性排序/落库/不碰评审分数/AST 零网络。零网络；全合成占位。
"""
import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path

MOD_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(MOD_DIR))

from skill_discovery import (  # noqa: E402
    DESCRIPTION_MAX, ERROR_CODES, REVIEW_VERDICTS, DiscoveryError,
    DiscoveryLedger, load_index, recommend, tokenize,
)

REGISTRY = {
    "schema": "judge-pack-registry/v1",
    "packs": [
        {"name": "mba-brand", "skills": [
            {"name": "arnault",
             "triggers": "\"用 Bernard Arnault 视角\", "
                         "\"LVMH / Arnault 会怎么看\"",
             "x-positioning": "品牌组合经营（占位）",
             "x-perspective_ref": "perspectives/arnault-perspective/"},
            {"name": "jobs",
             "triggers": "「用乔布斯视角」「Jobs 会怎么看」",
             "x-positioning": "产品与发布（占位）",
             "x-perspective_ref": "perspectives/jobs-perspective/"},
        ]},
    ],
}

ARNAULT_SKILL = """---
name: arnault-perspective
description: |
  奢侈品品牌组合经营视角：看 Maison 长期价值、desirability。

  Use as: 品牌定位审计评委。

  Explicit triggers: “用 Bernard Arnault 视角”、“奢侈品定位”。
---

# 视角（占位）
"""

JOBS_SKILL = """---
name: jobs-perspective
description: |
  产品发布视角：看产品定义与发布节奏。

  Use as: 产品评审评委。
---

# 视角（占位）
"""

SHOPPER_SKILL = """---
name: first-glance-shopper-perspective
description: |
  模拟消费者人设（合成角色，非真实人物）——货架 3 秒扫描型直觉快判视角。

  Use as: 消费者视角评委。

  Explicit triggers: “用普通消费者视角看”、“第一印象怎么样”、“会不会买”。
---

# 视角（占位）
"""

LONG_SKILL = """---
name: long-desc-perspective
description: |
  %s
---

# 视角（占位）
""" % ("超长描述词（占位）" * 200)

METRIC_SKILL = """---
name: metric-brand-auditor
description: |
  品牌指标审计：用量化指标盘点品牌资产。

  Explicit triggers: “品牌指标怎么样”、“量化盘点”。
---

# 指标（占位）
"""


def build_root(tmp: Path) -> Path:
    (tmp / "registry.json").write_text(
        json.dumps(REGISTRY, ensure_ascii=False), encoding="utf-8")
    (tmp / "perspectives" / "arnault-perspective").mkdir(parents=True)
    (tmp / "perspectives" / "arnault-perspective" / "SKILL.md").write_text(
        ARNAULT_SKILL, encoding="utf-8")
    (tmp / "perspectives" / "jobs-perspective").mkdir(parents=True)
    (tmp / "perspectives" / "jobs-perspective" / "SKILL.md").write_text(
        JOBS_SKILL, encoding="utf-8")
    (tmp / "perspectives" / "first-glance-shopper-perspective").mkdir(
        parents=True)
    (tmp / "perspectives" / "first-glance-shopper-perspective"
     / "SKILL.md").write_text(SHOPPER_SKILL, encoding="utf-8")
    (tmp / "perspectives" / "long-desc-perspective").mkdir(parents=True)
    (tmp / "perspectives" / "long-desc-perspective" / "SKILL.md").write_text(
        LONG_SKILL, encoding="utf-8")
    (tmp / "plugins" / "mba-brand-audit").mkdir(parents=True)
    (tmp / "plugins" / "mba-brand-audit" / "manifest.json").write_text(
        json.dumps({"name": "mba-brand-audit", "version": "0.1.0",
                    "description": "品牌资产盘点与竞争定位审计"},
                   ensure_ascii=False), encoding="utf-8")
    (tmp / "plugins" / "mba-copy-review").mkdir(parents=True)
    (tmp / "plugins" / "mba-copy-review" / "manifest.json").write_text(
        json.dumps({"name": "mba-copy-review", "version": "0.1.0",
                    "description": "文案评审",
                    "keywords": ["文案", "广告语"]},
                   ensure_ascii=False), encoding="utf-8")
    (tmp / "metric-brand-auditor").mkdir(parents=True)
    (tmp / "metric-brand-auditor" / "SKILL.md").write_text(
        METRIC_SKILL, encoding="utf-8")
    # marketplace 只含 1 个插件（T1 §1.3）：发现层不以它作源
    (tmp / ".claude-plugin").mkdir(parents=True)
    (tmp / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"plugins": [{"name": "bogus-marketplace-only-skill"}]},
                   ensure_ascii=False), encoding="utf-8")
    return tmp


class TestIndex(unittest.TestCase):
    def test_union_counts(self):
        with tempfile.TemporaryDirectory() as td:
            index = load_index(build_root(Path(td)))
            self.assertTrue(index["registry_loaded"])
            self.assertEqual(index["counts"],
                             {"perspective": 4, "plugin": 2, "metric": 1})
            self.assertEqual(index["total"], 7)

    def test_registry_missing_perspective_gets_triggers_from_frontmatter(self):
        with tempfile.TemporaryDirectory() as td:
            index = load_index(build_root(Path(td)))
            by_skill = {e["skill"]: e for e in index["entries"]}
            shopper = by_skill["first-glance-shopper-perspective"]
            self.assertIn("第一印象怎么样", shopper["triggers"])
            self.assertIn("会不会买", shopper["triggers"])

    def test_marketplace_not_a_source(self):
        with tempfile.TemporaryDirectory() as td:
            index = load_index(build_root(Path(td)))
            skills = {e["skill"] for e in index["entries"]}
            self.assertNotIn("bogus-marketplace-only-skill", skills)

    def test_long_description_not_compliant(self):
        with tempfile.TemporaryDirectory() as td:
            index = load_index(build_root(Path(td)))
            by_skill = {e["skill"]: e for e in index["entries"]}
            long_entry = by_skill["long-desc-perspective"]
            self.assertGreater(len(long_entry["description"]),
                               DESCRIPTION_MAX)
            self.assertFalse(long_entry["description_compliant"])

    def test_manifest_without_keywords_tolerated(self):
        with tempfile.TemporaryDirectory() as td:
            index = load_index(build_root(Path(td)))
            by_skill = {e["skill"]: e for e in index["entries"]}
            self.assertEqual(by_skill["mba-brand-audit"]["keywords"], [])
            self.assertEqual(by_skill["mba-copy-review"]["keywords"],
                             ["文案", "广告语"])


class TestRecommend(unittest.TestCase):
    def _index(self, td):
        return load_index(build_root(Path(td)))

    def test_trigger_phrase_match_ranks_first(self):
        with tempfile.TemporaryDirectory() as td:
            out = recommend(self._index(td),
                            "用普通消费者视角看，这个品牌第一印象怎么样",
                            request_id="r-001")
            self.assertEqual(out["candidates"][0]["skill"],
                             "first-glance-shopper-perspective")
            self.assertIn("触发句式命中",
                          out["candidates"][0]["reason"])
            self.assertEqual(out["recommendation"]["skill"],
                             "first-glance-shopper-perspective")
            self.assertEqual(out["review"]["verdict"], "pending")

    def test_trigger_beats_description_only(self):
        with tempfile.TemporaryDirectory() as td:
            index = self._index(td)
            trig = recommend(index, "用 Bernard Arnault 视角看 LVMH",
                             request_id="r-t")
            desc = recommend(index, "奢侈品定位",
                             request_id="r-d")
            trig_score = [c["score"] for c in trig["candidates"]
                          if c["skill"] == "arnault-perspective"][0]
            desc_score = [c["score"] for c in desc["candidates"]
                          if c["skill"] == "arnault-perspective"][0]
            self.assertGreater(trig_score, desc_score)
            self.assertLessEqual(desc_score, 0.5)

    def test_plugin_keyword_match(self):
        with tempfile.TemporaryDirectory() as td:
            out = recommend(self._index(td), "帮我看看这句广告语文案",
                            request_id="r-002")
            skills = [c["skill"] for c in out["candidates"]]
            self.assertIn("mba-copy-review", skills)

    def test_no_match_empty(self):
        with tempfile.TemporaryDirectory() as td:
            out = recommend(self._index(td), "zzzqqq 未知词（占位）",
                            request_id="r-003")
            self.assertEqual(out["candidates"], [])
            self.assertIsNone(out["recommendation"])

    def test_deterministic_order(self):
        with tempfile.TemporaryDirectory() as td:
            index = self._index(td)
            first = recommend(index, "品牌定位审计", request_id="r-004")
            second = recommend(index, "品牌定位审计", request_id="r-004")
            self.assertEqual(first, second)
            scores = [c["score"] for c in first["candidates"]]
            self.assertEqual(scores, sorted(scores, reverse=True))
            for c in first["candidates"]:
                self.assertTrue(0 <= c["score"] <= 1)

    def test_tokenize_chinese_ngrams(self):
        terms = tokenize("年轻人视角")
        self.assertIn("年轻人", terms)
        self.assertIn("人视角", terms)

    def test_recommendation_carries_no_review_scores(self):
        with tempfile.TemporaryDirectory() as td:
            out = recommend(self._index(td), "第一印象怎么样",
                            request_id="r-005")
            self.assertEqual(set(out.keys()),
                             {"schema", "request", "candidates",
                              "recommendation", "review"})
            self.assertNotIn("findings", json.dumps(out, ensure_ascii=False))


class TestLedger(unittest.TestCase):
    def test_jsonl_persistence_append_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = build_root(Path(td))
            index = load_index(root)
            path = Path(td) / "discovery" / "log.jsonl"
            led = DiscoveryLedger(path)
            led.record(recommend(index, "第一印象怎么样",
                                 request_id="r-001"))
            led.record(recommend(index, "品牌指标怎么样",
                                 request_id="r-002"))
            self.assertEqual(len(led.entries()), 2)
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)

    def test_incomplete_record_refused(self):
        led = DiscoveryLedger(None)
        with self.assertRaisesRegex(DiscoveryError, "DISCOVERY_INCOMPLETE"):
            led.record({"schema": "mba-skill-discovery/v1", "request": {}})

    def test_score_out_of_range_refused(self):
        led = DiscoveryLedger(None)
        with tempfile.TemporaryDirectory() as td:
            index = load_index(build_root(Path(td)))
            rec = recommend(index, "第一印象怎么样", request_id="r-001")
            rec["candidates"][0]["score"] = 1.5
            with self.assertRaisesRegex(DiscoveryError,
                                        "DISCOVERY_SCORE_MISMATCH"):
                led.record(rec)

    def test_candidates_without_recommendation_refused(self):
        led = DiscoveryLedger(None)
        with tempfile.TemporaryDirectory() as td:
            index = load_index(build_root(Path(td)))
            rec = recommend(index, "第一印象怎么样", request_id="r-001")
            rec["recommendation"] = None
            with self.assertRaisesRegex(DiscoveryError,
                                        "DISCOVERY_INCOMPLETE"):
                led.record(rec)


class TestRedline(unittest.TestCase):
    def test_ast_zero_network_zero_subprocess(self):
        banned = {"urllib", "requests", "socket", "http", "subprocess"}
        src = MOD_DIR / "skill_discovery.py"
        tree = ast.parse(Path(src).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse(imported & banned, imported & banned)

    def test_vocabs_closed(self):
        self.assertEqual(set(REVIEW_VERDICTS),
                         {"pending", "accepted", "rejected"})
        self.assertEqual(set(ERROR_CODES),
                         {"DISCOVERY_INCOMPLETE",
                          "DISCOVERY_SCORE_MISMATCH"})


if __name__ == "__main__":
    unittest.main()
