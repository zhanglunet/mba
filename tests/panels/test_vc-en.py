# tests/panels/test_vc-en.py
"""vc-en panel 独立验收测试（PRD-022/T2）。

只做静态检查，不调 LLM、不跑真实打分。
规范见 docs/plans/2026-10-17-panel-test-spec.md §一。
"""
import pathlib

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PANEL = REPO_ROOT / "metric-brand-auditor" / "panels" / "vc-en.yaml"
EXPECTED_JUDGES = 5


def load():
    return yaml.safe_load(PANEL.read_text(encoding="utf-8"))


def test_yaml_parses():
    assert isinstance(load(), dict)


def test_top_level_fields():
    d = load()
    for k in ("name", "display_name", "description", "judges"):
        assert k in d, f"missing field: {k}"


def test_name_matches_filename():
    assert load()["name"] == PANEL.stem


def test_judge_count():
    judges = load()["judges"]
    assert isinstance(judges, list) and len(judges) == EXPECTED_JUDGES


def test_judge_fields():
    for j in load()["judges"]:
        for k in ("slug", "display_name_cn", "display_name_en", "language", "weight"):
            assert k in j, f"judge {j.get('slug')} missing field: {k}"


def test_slug_unique():
    slugs = [j["slug"] for j in load()["judges"]]
    assert len(slugs) == len(set(slugs)), "duplicate slug"


def test_weight_valid():
    for j in load()["judges"]:
        w = j["weight"]
        assert isinstance(w, (int, float)) and 0 < w <= 2.0, f"judge {j['slug']} bad weight: {w}"
