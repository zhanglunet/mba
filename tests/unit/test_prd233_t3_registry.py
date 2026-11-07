# -*- coding: utf-8 -*-
"""PRD-233/T3 自测：评委总登记册——检索/触发条件/验收例（trend #1167）。

运行：uv run --with pytest python -m pytest tests/unit/test_prd233_t3_registry.py -q

覆盖（T1 §四/§五/§六 + PRD-227 适配）：映射解析（43 位对账 26/8/4/5）、消费者
横切组 3 位单列（§四.3）、登记册覆盖全部 46 位（验收）、规范合规校验、triggers
非空回退链（Explicit triggers → 归包理由）、验收例机械生成含 slug 与包名、
检索（触发词命中/大小写不敏感/短词拒绝/确定性）、双载体同源（registry.json
重新生成 == 落盘文件；REGISTRY.md 重新渲染 == 落盘文件）、缺 JSON/缺映射报错
不静默。零网络；只读。
"""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from judge_registry import (  # noqa: E402
    CROSSCUT_INFO,
    DESIGN_DOC,
    EXPECTED_COUNTS,
    JUDGES_API_DIR,
    REGISTRY_MD_PATH,
    REGISTRY_PATH,
    build_registry,
    load_judges,
    parse_mapping,
    render_md,
    search,
    total_judges,
    validate_registry,
)

DESIGN_TEXT = DESIGN_DOC.read_text(encoding="utf-8")


class 映射解析Tests(unittest.TestCase):
    def test_43_experts_mapped_with_exact_counts(self):
        mapping = parse_mapping(DESIGN_TEXT)
        self.assertEqual(len(mapping), 43)
        counts = {}
        for info in mapping.values():
            counts[info["pack"]] = counts.get(info["pack"], 0) + 1
        self.assertEqual(counts, EXPECTED_COUNTS)

    def test_secondary_packs_parsed(self):
        """兼项解析（§四.3：17 位有兼项；如 leijun→copy、awintour→visual）。"""
        mapping = parse_mapping(DESIGN_TEXT)
        self.assertIn("copy", mapping["leijun"]["secondary"])
        self.assertIn("visual", mapping["awintour"]["secondary"])
        self.assertEqual(mapping["arnault"]["secondary"], [])

    def test_positioning_from_doc_verbatim(self):
        mapping = parse_mapping(DESIGN_TEXT)
        self.assertIn("心智", mapping["jiangnanchun"]["positioning"])


class 登记册构建Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.judges = load_judges()
        cls.registry = build_registry(DESIGN_TEXT, cls.judges)

    def test_covers_all_46_judges(self):
        """验收：登记册覆盖全部评委（43 专家 + 3 消费者横切）。"""
        self.assertEqual(total_judges(self.registry), 46)
        registered = {s["name"] for p in self.registry["packs"] for s in p["skills"]}
        crosscut = {s["name"] for s in self.registry["x-crosscut"]["skills"]}
        self.assertEqual(len(registered), 43)
        self.assertEqual(crosscut, set(CROSSCUT_INFO["members"]))

    def test_spec_compliant(self):
        self.assertEqual(validate_registry(self.registry), [])
        self.assertEqual(self.registry["alignment"], "skill-pack-layering-spec@1.0.0")

    def test_pack_names_and_versions(self):
        names = [p["name"] for p in self.registry["packs"]]
        self.assertEqual(names, ["mba-brand", "mba-copy", "mba-visual", "mba-compliance"])
        for pack in self.registry["packs"]:
            self.assertEqual(pack["version"], "0.1.0")
            self.assertEqual(pack["spec_version"], "1.0.0")

    def test_triggers_nonempty_with_fallback_chain(self):
        """triggers 非空：Explicit triggers 段优先，缺省回退 T1 归包理由。"""
        for pack in self.registry["packs"]:
            for skill in pack["skills"]:
                self.assertTrue(skill["triggers"].strip(), f"{skill['name']} 无触发条件")
        skeptic = next(s for s in self.registry["x-crosscut"]["skills"]
                       if s["name"] == "brand-skeptic")
        self.assertIn("消费者", skeptic["triggers"])  # 消费者人设带 Explicit triggers

    def test_acceptance_examples_mechanical_with_slug_and_pack(self):
        """验收例按 §六.1 句式机械生成（含 slug 与包名，不虚构内容）。"""
        for pack in self.registry["packs"]:
            for skill in pack["skills"]:
                example = skill["x-acceptance_example"]
                self.assertIn(skill["name"], example)
                self.assertIn(pack["name"], example)
                self.assertIn("期望", example)

    def test_role_and_perspective_ref(self):
        arnault = next(s for p in self.registry["packs"] for s in p["skills"]
                       if s["name"] == "arnault")
        self.assertEqual(arnault["x-role"], "expert")
        self.assertEqual(arnault["x-perspective_ref"], "perspectives/arnault-perspective/")

    def test_mapping_json_missing_judge_rejected(self):
        """T1 映射有但评委 JSON 缺 → 报错不静默。"""
        judges = {k: v for k, v in self.judges.items() if k != "arnault"}
        with self.assertRaises(Exception):
            build_registry(DESIGN_TEXT, judges)

    def test_judge_not_in_mapping_rejected(self):
        """评委 JSON 有但映射未登记 → 报错（不得静默缺席）。"""
        judges = dict(self.judges)
        judges["ghost-judge"] = {"slug": "ghost-judge", "name_cn": "幽灵",
                                 "panels": [], "description": ""}
        with self.assertRaises(Exception):
            build_registry(DESIGN_TEXT, judges)


class 检索Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = build_registry(DESIGN_TEXT, load_judges())

    def test_search_by_positioning_keyword(self):
        hits = search(self.registry, "心智")
        self.assertIn("jiangnanchun", {h["name"] for h in hits})

    def test_search_case_insensitive_slug(self):
        hits = search(self.registry, "ARNault")
        self.assertIn("arnault", {h["name"] for h in hits})

    def test_search_consumer_group(self):
        hits = search(self.registry, "可信")
        self.assertIn("brand-skeptic", {h["name"] for h in hits})

    def test_short_query_rejected(self):
        with self.assertRaises(Exception):
            search(self.registry, "品")

    def test_deterministic_order(self):
        self.assertEqual(search(self.registry, "定位"), search(self.registry, "定位"))


class 双载体同源Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = build_registry(DESIGN_TEXT, load_judges())

    def test_registry_json_in_sync(self):
        on_disk = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        rebuilt = build_registry(DESIGN_TEXT, load_judges())
        self.assertEqual(on_disk, rebuilt)

    def test_registry_md_is_current_render(self):
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(REGISTRY_MD_PATH.read_text(encoding="utf-8"),
                         render_md(registry))

    def test_render_contains_all_packs_and_crosscut(self):
        rendered = render_md(self.registry)
        self.assertIn("46 位评委", rendered)
        for pack in self.registry["packs"]:
            self.assertIn(pack["name"], rendered)
        self.assertIn("横切组，非 sub-pack", rendered)
        self.assertIn("46 位评委", rendered)


if __name__ == "__main__":
    unittest.main()
