# tests/_contract/test_panels.py
"""panel 注册清单与 portrait 契约测试（PRD-022/T2）。

规范见 docs/plans/2026-10-17-panel-test-spec.md §二（已修正版）。
注意：跨 panel 评委 slug 允许复用（有意设计），此处不做全局唯一断言；
panel 内 slug 唯一由各 tests/panels/test_<name>.py 的 test_slug_unique 覆盖。
"""
import pathlib

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PANELS_DIR = REPO_ROOT / "metric-brand-auditor" / "panels"
JUDGES_DIR = REPO_ROOT / "assets" / "judges"

# 注册清单：industries.yaml 是行业→panel 映射表，非 panel，排除在外
EXPECTED_PANELS = {
    "ai-app-cn",
    "auto",
    "consumer-cn",
    "cross-border",
    "default",
    "edu-cn",
    "luxury-en",
    "security-cn-global",
    "vc-cn",
    "vc-en",
}


def panel_names():
    names = {p.stem for p in PANELS_DIR.glob("*.yaml")}
    names |= {p.stem for p in PANELS_DIR.glob("*.yml")}
    return names - {"industries"}


def test_registry_matches():
    actual = panel_names()
    assert actual == EXPECTED_PANELS, (
        f"panel 注册清单漂移: 新增 {sorted(actual - EXPECTED_PANELS)} / "
        f"缺失 {sorted(EXPECTED_PANELS - actual)}"
    )


def test_portraits_exist():
    missing = []
    for stem in sorted(EXPECTED_PANELS):
        d = yaml.safe_load((PANELS_DIR / f"{stem}.yaml").read_text(encoding="utf-8"))
        for j in d.get("judges", []):
            portrait = j.get("portrait")
            if portrait and not (JUDGES_DIR / portrait).is_file():
                missing.append(f"{stem}/{j.get('slug')}: {portrait}")
    assert not missing, "portrait 文件缺失: " + "; ".join(missing)
