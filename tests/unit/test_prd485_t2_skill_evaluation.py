# -*- coding: utf-8 -*-
"""PRD-485/T2：mba 评委技能评估最小实现测试。只测本地逻辑，零网络。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import skill_evaluation as ev  # noqa: E402


def _skill(tmp: Path, rel: str, text: str) -> Path:
    p = tmp / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


FULL = """---
name: test-judge
description: 测试评委技能
---
# 测试评委
触发：当需要评审品牌时使用。
约束：必须按六维评分，不得臆造分数。
证据：见 references/research/quotes.md。
"""

BARE = "# 光秃评委\n\n只有正文，没有任何结构。"


def test_jaccard_bounds():
    assert ev.jaccard(set("ab"), set("ab")) == 1.0
    assert ev.jaccard(set("ab"), set("cd")) == 0.0
    assert 0.0 < ev.jaccard({"a", "b"}, {"b", "c"}) < 1.0
    assert ev.jaccard(set(), set()) == 0.0


def test_static_checks_full_and_bare():
    full = ev.static_checks({"text": FULL})
    assert all(full.values()), full
    bare = ev.static_checks({"text": BARE})
    assert not any(bare.values()), bare


def test_overlap_threshold_boundary():
    a = {"name": "a", "path": "perspectives/a/SKILL.md", "text": FULL}
    b = {"name": "b", "path": "perspectives/b/SKILL.md", "text": FULL}
    c = {"name": "c", "path": "perspectives/c/SKILL.md", "text": BARE}
    cands = ev.overlap_candidates([a, b, c])
    assert len(cands) == 1
    assert cands[0]["similarity"] == 1.0
    assert cands[0]["a"] < cands[0]["b"]


def test_evaluate_minimal_pack(tmp_path):
    _skill(tmp_path, "perspectives/a/SKILL.md", FULL)
    _skill(tmp_path, "perspectives/b/SKILL.md", BARE)
    # fixture 与草稿不计入评委包
    _skill(tmp_path, "tests/quality/fixtures/fake-judge/SKILL.md", FULL)
    _skill(tmp_path, "docs/prd/panels/x/SKILL-draft.md", FULL)
    result = ev.evaluate(tmp_path)
    assert result["skill_count"] == 2
    assert result["static_complete"] == 1
    assert result["static_gap"] == 1
    # 无对照数据：行为结论一律待补测
    assert all(s["behavior_verdict"] == "待补测" for s in result["skills"])


def test_evaluate_empty_pack_fails_closed(tmp_path):
    try:
        ev.evaluate(tmp_path)
    except ValueError as e:
        assert "EVALUATION_EMPTY" in str(e)
    else:
        raise AssertionError("空技能包应显形拒绝，不出空报告")


def test_report_and_remediation_append_only(tmp_path):
    _skill(tmp_path, "perspectives/a/SKILL.md", FULL)
    assert ev.main(["--root", str(tmp_path),
                    "--report", "docs/evaluations/r.md",
                    "--remediation", "docs/evaluations/l.md"]) == 0
    report = (tmp_path / "docs/evaluations/r.md").read_text(encoding="utf-8")
    assert "首份" in report and "待补测" in report
    ledger = tmp_path / "docs/evaluations/l.md"
    first = ledger.read_text(encoding="utf-8")
    assert "append-only" in first
    # 第二轮不改写历史章节、不重复追加同一轮
    assert ev.main(["--root", str(tmp_path),
                    "--report", "docs/evaluations/r.md",
                    "--remediation", "docs/evaluations/l.md"]) == 0
    assert ledger.read_text(encoding="utf-8") == first
