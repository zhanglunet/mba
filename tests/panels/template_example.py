# tests/panels/template_example.py
"""新 panel 测试模板（PRD-022/T4，trend #124）。

使用方法（新增 panel 时）：
  1. 复制本文件 → tests/panels/test_<你的panel名>.py
     （例如 panel 叫 fintech，测试文件就叫 test_fintech.py）
  2. 把下面的 PANEL_NAME 改成你的 panel 名（= yaml 文件名去掉 .yaml）。
  3. 把 EXPECTED_JUDGES 改成实际评委人数。
  其余 7 个测试不用动，跑 `python -m pytest tests/panels/test_<你的panel名>.py -q`。

规范依据：docs/plans/2026-10-17-panel-test-spec.md §一（7 项检查）。
只做静态检查，不调 LLM、不跑真实打分。

注意：本文件**故意**不叫 test_*.py（pytest 按 test_*.py / *_test.py 收集），
所以它自己永远不会被 pytest 执行，只是模板。
"""
import pathlib

import yaml

# 【改这里 1/3】你的 panel 名（= metric-brand-auditor/panels/<这里>.yaml）
PANEL_NAME = "your-panel-name"
# 【改这里 2/3】评委人数（= yaml 里 judges 列表的长度）
EXPECTED_JUDGES = 2
# 【改这里 3/3】上面两处改完，把本文件另存为 tests/panels/test_<panel名>.py

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PANEL = REPO_ROOT / "metric-brand-auditor" / "panels" / (PANEL_NAME + ".yaml")


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
    # T1 §一 #4：judges 是非空 list，人数符合预期
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
