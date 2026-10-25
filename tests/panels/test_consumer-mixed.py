# tests/panels/test_consumer-mixed.py
"""consumer-mixed panel 独立验收测试（PRD-178/T2，trend #891）。

沿 PRD-022 七项静态检查（tests/panels/template_example.py），另加消费者评委
特有断言：role: consumer、模拟人设诚实标注。只做静态检查，不调 LLM、不跑真实打分。
"""
import pathlib

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PANEL = REPO_ROOT / "metric-brand-auditor" / "panels" / "consumer-mixed.yaml"
EXPECTED_JUDGES = 3
CONSUMER_SLUGS = {"first-glance-shopper", "homework-buyer", "brand-skeptic"}


def load():
    return yaml.safe_load(PANEL.read_text(encoding="utf-8"))


def test_yaml_parses():
    # T1 §一 #1：YAML 可解析、无语法错误（缩进错一位这里就挂，最常见）
    assert isinstance(load(), dict)


def test_top_level_fields():
    # T1 §一 #2：顶层四个字段齐全
    d = load()
    for k in ("name", "display_name", "description", "judges"):
        assert k in d, f"missing field: {k}"


def test_name_matches_filename():
    # T1 §一 #3：name 必须与文件名一致（validate_panels.py 同样硬校验）
    assert load()["name"] == PANEL.stem


def test_judge_count():
    # T1 §一 #4：judges 是非空 list，人数符合预期（T2 落地 3 套消费者人设）
    judges = load()["judges"]
    assert isinstance(judges, list) and len(judges) == EXPECTED_JUDGES


def test_judge_fields():
    # T1 §一 #5：每位评委五个字段齐全
    for j in load()["judges"]:
        for k in ("slug", "display_name_cn", "display_name_en", "language", "weight"):
            assert k in j, f"judge {j.get('slug')} missing field: {k}"


def test_slug_unique():
    # T1 §一 #6：同一 panel 内 slug 不重复（跨 panel 复用允许，不管）
    slugs = [j["slug"] for j in load()["judges"]]
    assert len(slugs) == len(set(slugs)), "duplicate slug"


def test_weight_valid():
    # T1 §一 #7：每位评委 0 < weight <= 2.0
    for j in load()["judges"]:
        w = j["weight"]
        assert isinstance(w, (int, float)) and 0 < w <= 2.0, f"judge {j['slug']} bad weight: {w}"


def test_all_judges_role_consumer():
    # PRD-178/T1 §五.1：本 panel 全部为消费者评委，role 必须显式为 consumer
    for j in load()["judges"]:
        assert j.get("role") == "consumer", f"judge {j['slug']} role must be 'consumer'"
    slugs = {j["slug"] for j in load()["judges"]}
    assert slugs == CONSUMER_SLUGS


def test_description_honest_simulated():
    # PRD-178 风险项：panel 描述必须写明「模拟 / 非真实市场调研」，防止被当真实调研
    d = load()
    assert "模拟" in d["description"]
    assert "非真实市场调研" in d["description"]


def test_consumer_perspective_skills_resolve():
    # PRD-178/T1 §五.1：consumer 评委必须解析到对应人设目录（SKILL.md 真实存在）
    for j in load()["judges"]:
        skill = REPO_ROOT / "perspectives" / f"{j['slug']}-perspective" / "SKILL.md"
        assert skill.is_file(), f"missing perspective skill: {skill}"
        scenario = (
            REPO_ROOT / "perspectives" / f"{j['slug']}-perspective" / "references" / "scenario.md"
        )
        assert scenario.is_file(), f"missing scenario corpus: {scenario}"


def test_display_names_marked_simulated():
    # 诚实盒纪律：消费者评委的显示名必须带「模拟人设」标注
    for j in load()["judges"]:
        assert "模拟" in j["display_name_cn"], f"{j['slug']} display_name_cn 缺模拟标注"
