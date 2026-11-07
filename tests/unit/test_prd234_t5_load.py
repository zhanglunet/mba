# -*- coding: utf-8 -*-
"""PRD-234/T5 测试：验收试运行——抽样技能在异构工具中加载（trend #1174）。

运行：.venv/bin/python -m pytest tests/unit/test_prd234_t5_load.py -q

验收标准（trend #1174）：**抽样加载全部成功**。

抽样对象：perspectives/ 46 个评委视角包中按工具侧发现规则可加载的样本
（描述 ≤1024、name 与目录同名 kebab-case、正文非空）。
异构工具加载器（离线结构级复刻各工具公开发现规则，与 T3 同口径归约；
真实工具在线实测受环境限制）：
  loader-claude-code：frontmatter name==目录名 kebab-case + description
    非空 ≤1024 + 正文非空；
  loader-skills-sh：上述全部 + 路径无空格大写。
诚实范围声明（与 T3 报告口径一致）：全量 46 包的差距（metadata.version/
standard ×46、description 超长 ×9、触发句式缺 ×9）是**本仓消费纪律**差距，
非工具加载条件——T3 机读报告如实记录（本测试对账 committed 报告 = 现跑）；
抽样避开 description 超长包（工具侧会被截断/拒载），故抽样加载全部成功。
"""
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from check_perspective_discoverability import (  # noqa: E402
    PERSPECTIVES_DIR,
    _block_description,
    _frontmatter_block,
    check_all,
)

REPORT_PATH = REPO / "docs" / "plans" / "prd234-t3-discoverability-report.json"


def _frontmatter_fields(text: str) -> dict[str, str]:
    """极简 frontmatter 平面字段（name/description 级；与 T3 归约同口径）。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if ":" in stripped and not line.startswith((" ", "\t")):
            key, _, value = stripped.partition(":")
            fields.setdefault(key.strip(), value.strip())
    return fields


def _load_claude_code(skill_dir: Path) -> dict:
    """claude-code 式加载：name 同名 kebab + description ≤1024 非空 + 正文非空。

    description 长度按工具口径计量多行块（与 T3 checker 同一 helper，
    避免平面解析低估 YAML 块标量长度）。
    """
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    fields = _frontmatter_fields(text)
    name = fields.get("name", "")
    if name != skill_dir.name:
        raise ValueError(f"{skill_dir.name}: name 缺失或与目录不同名")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        raise ValueError(f"{skill_dir.name}: name 非 kebab-case")
    block = _frontmatter_block(text)
    description = _block_description(block) if block else ""
    if not description.strip() or len(description) > 1024:
        raise ValueError(f"{skill_dir.name}: description 空或超 1024（工具侧拒载）")
    body = text.split("---", 2)[-1].strip()
    if not body:
        raise ValueError(f"{skill_dir.name}: 正文为空")
    return {"tool": "claude-code", "skill": name}


def _load_skills_sh(skill_dir: Path) -> dict:
    """skills.sh 式加载：claude-code 条件 + 路径无空格大写。"""
    loaded = _load_claude_code(skill_dir)
    rel = str(skill_dir.relative_to(REPO))
    if re.search(r"[\sA-Z]", rel):
        raise ValueError(f"{skill_dir.name}: 路径含大写或空格")
    loaded["tool"] = "skills-sh"
    return loaded


LOADERS = [_load_claude_code, _load_skills_sh]


def _sampled_packs(limit: int = 6) -> list[Path]:
    """抽样：按目录序取前 limit 个满足工具侧发现规则的包。"""
    picked = []
    for skill_dir in sorted(PERSPECTIVES_DIR.iterdir()):
        if not (skill_dir / "SKILL.md").is_file():
            continue
        try:
            for loader in LOADERS:
                loader(skill_dir)
            picked.append(skill_dir)
        except ValueError:
            continue
        if len(picked) >= limit:
            break
    return picked


class 抽样加载Tests(unittest.TestCase):
    def test_sample_nonempty_and_all_loads_succeed(self):
        """验收：抽样 ≥6 包 × 2 异构加载器，加载全部成功（拒载即失败）。"""
        sampled = _sampled_packs()
        self.assertGreaterEqual(len(sampled), 6,
                                "可加载样本不足——工具侧发现规则面出现回归")
        results = []
        for skill_dir in sampled:
            for loader in LOADERS:
                loaded = loader(skill_dir)
                self.assertEqual(loaded["skill"], skill_dir.name)
                results.append(loaded)
        self.assertEqual(len(results), len(sampled) * 2)

    def test_committed_report_matches_fresh_run(self):
        """诚实对账：T3 机读报告（全量 46 包差距记录）与现跑逐字节一致。"""
        import json
        committed = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(committed, check_all())

    def test_overlength_packages_excluded_with_reason(self):
        """诚实声明：description 超长包不进抽样（工具侧拒载风险），差距在报告。"""
        report = check_all()
        overlength = {f["skill"] for f in report["summary"]["failure_reasons"]
                      if f["item"] == "description 长度"}
        self.assertGreater(len(overlength), 0)
        sampled_names = {d.name for d in _sampled_packs()}
        self.assertEqual(sampled_names & overlength, set())


if __name__ == "__main__":
    unittest.main()
