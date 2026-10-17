#!/usr/bin/env python3
"""一键安装链路模拟验证（PRD-021/T3，trend #118）。

真机 e2e 需要 Claude Code 客户端，VM 上做不了；此处模拟 `plugin install`
链路做静态验证：
  marketplace 清单可解析 → source 目录真实存在 →
  plugin.json 字段齐全且版本三处一致 → skill 落盘且无符号链接。

纯标准库；pytest 或 `python3 tests/test_marketplace_install.py` 均可跑。
"""
import json
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
OFFICIAL_SCHEMA = "https://anthropic.com/claude-code/marketplace.schema.json"
REQUIRED_PLUGIN_FIELDS = ("name", "version", "description", "license")


def load_marketplace():
    return json.loads(MARKETPLACE.read_text(encoding="utf-8"))


def frontmatter_version(skill_md: pathlib.Path) -> str:
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    assert m, f"{skill_md} 缺少 frontmatter"
    mv = re.search(r"^version:\s*(\S+)", m.group(1), re.M)
    assert mv, f"{skill_md} frontmatter 缺 version"
    return mv.group(1).strip().strip("'\"")


def test_marketplace_parses_and_lists_plugins():
    m = load_marketplace()
    assert isinstance(m, dict), "marketplace.json 解析后不是对象"
    assert isinstance(m.get("plugins"), list) and m["plugins"], "plugins 为空"


def test_schema_is_official():
    m = load_marketplace()
    assert m.get("$schema") == OFFICIAL_SCHEMA, f"$schema 不符: {m.get('$schema')}"


def test_plugin_sources_exist():
    for p in load_marketplace()["plugins"]:
        src = (REPO_ROOT / p["source"]).resolve()
        assert src.is_dir(), f"source 目录不存在: {p['source']}"
        assert str(src).startswith(str(REPO_ROOT)), f"source 逃出仓库: {p['source']}"


def test_plugin_manifest_fields_and_version():
    for p in load_marketplace()["plugins"]:
        manifest = REPO_ROOT / p["source"] / ".claude-plugin" / "plugin.json"
        assert manifest.is_file(), f"缺 plugin.json（官方路径）: {manifest}"
        d = json.loads(manifest.read_text(encoding="utf-8"))
        for k in REQUIRED_PLUGIN_FIELDS:
            assert k in d and d[k], f"plugin.json 缺字段: {k}"
        assert d["name"] == p["name"], "plugin.json name 与 marketplace 条目不一致"
        assert str(d["version"]) == str(p["version"]), (
            f"版本不一致: marketplace={p['version']} plugin.json={d['version']}"
        )


def test_skill_present_and_version_matches():
    for p in load_marketplace()["plugins"]:
        skills_dir = REPO_ROOT / p["source"] / "skills"
        assert skills_dir.is_dir(), f"缺 skills 目录: {skills_dir}"
        skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
        assert skill_dirs, "skills 下无 skill 目录"
        for sd in skill_dirs:
            assert (sd / "SKILL.md").is_file(), f"skill 目录缺 SKILL.md: {sd}"
        main = skills_dir / p["name"] / "SKILL.md"
        if main.is_file():
            assert frontmatter_version(main) == str(p["version"]), (
                "SKILL.md frontmatter version 与 marketplace 条目不一致"
            )


def test_no_symlinks_in_plugin_tree():
    for p in load_marketplace()["plugins"]:
        root = REPO_ROOT / p["source"]
        links = [str(x) for x in root.rglob("*") if x.is_symlink()]
        assert not links, f"发现符号链接（须实份拷贝）: {links[:5]}"


if __name__ == "__main__":
    tests = [
        v for k, v in sorted(globals().items())
        if k.startswith("test_") and callable(v)
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print("PASS", t.__name__)
        except AssertionError as e:
            failed += 1
            print("FAIL", t.__name__, "-", e)
    sys.exit(1 if failed else 0)
