# -*- coding: utf-8 -*-
"""PRD-485/T2（trend issue #2346 的 T2 环节）：mba 评委技能评估 最小实现。

按 T1 设计（docs/plans/2026-11-17-prd-485-mba-skill-evaluation-design.md）
§八落地，只做 T2 最小版：质量门 + 重叠检测在真实技能包上跑通，产出首份
评估报告落账。合成评测集与实测是 T5 的事，本轮不做。

质量门（T1 §一）本意是量行为（打错分率 / 行为改变率 / 采纳率），需要有技能
vs 无技能的 ablation 对照数据；T2 尚无这类实测数据，按 T1 判定规则“数据
不足（样本 < 30）判待补测”，本轮所有技能的行为结论均为“待补测”，不判过关
也不判失效。本轮质量门跑的是可静态验证的代理指标——技能文本完整性 5 项：
frontmatter name、description、触发条件、约束/规则、证据或引用出处；缺项
进整改清单（修文本，不删技能）。

重叠检测（T1 §二）：技能两两比对。T2 最小版用确定性代理——正文字符
bigram Jaccard 相似度（零依赖、零网络；向量模型选型待后续评估，T1 未锁死），
阈值按 T1 草稿 ≥ 0.8 记候选重叠；相似度只是筛子，不是判决，候选须人工复核
后才确认，确认重叠的才进整改清单（合并或拆分由整改定，不直接删）。

评估范围：perspectives/*/SKILL.md、plugins/*/SKILL.md、
metric-brand-auditor/SKILL.md、research/SKILL.md（评委 panel skill 包）；
排除 tests/ 下的 fixture 与 docs/prd/ 下的草稿。

报告落账：docs/evaluations/2026-11-17-skill-evaluation-report.md（首份报告）；
整改清单 append-only：docs/evaluations/remediation-list.md（只追加新章节，
不改写历史条目）。
零网络零子进程；只读技能文本，只写报告与清单。
测试：tests/unit/test_prd485_t2_skill_evaluation.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA = "mba-skill-evaluation/v1"
OVERLAP_THRESHOLD = 0.8  # T1 §二草稿阈值
MIN_BEHAVIOR_SAMPLE = 30  # T1 §一：样本 < 30 判待补测

# 评委 skill 包在仓内的位置（T1 §六边界：只评包，不评单个评委的测试）
SKILL_ROOTS = ("perspectives", "plugins", "metric-brand-auditor", "research")
EXCLUDE_PREFIXES = ("tests/", "docs/")

# 静态完整性检查：(key, 说明)
CHECKS = (
    ("frontmatter_name", "frontmatter 有 name"),
    ("frontmatter_description", "frontmatter 有 description"),
    ("triggers", "写明触发条件（何时用这个评委）"),
    ("constraints", "写明约束/规则（评分维度、禁令）"),
    ("evidence", "有证据或引用出处（references/链接/案例）"),
)


def _frontmatter(text: str) -> str:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return match.group(1) if match else ""


def _scalar(frontmatter: str, key: str) -> str:
    match = re.search(rf"^{key}:\s*(.+)$", frontmatter, re.MULTILINE)
    return match.group(1).strip() if match else ""


def discover_skills(root: Path) -> list[dict]:
    """发现评委 skill 包：返回 [{name, path, text}]，按 path 确定性排序。"""
    found: list[dict] = []
    for skill_root in SKILL_ROOTS:
        base = root / skill_root
        if not base.exists():
            continue
        for path in sorted(base.rglob("SKILL.md")):
            rel = path.relative_to(root).as_posix()
            if rel.startswith(EXCLUDE_PREFIXES):
                continue
            text = path.read_text(encoding="utf-8")
            fm = _frontmatter(text)
            name = _scalar(fm, "name") or path.parent.name
            found.append({"name": name, "path": rel, "text": text})
    found.sort(key=lambda s: s["path"])
    return found


def static_checks(skill: dict) -> dict[str, bool]:
    """5 项静态完整性检查（T2 质量门代理指标，非行为结论）。"""
    text = skill["text"]
    fm = _frontmatter(text)
    return {
        "frontmatter_name": bool(_scalar(fm, "name")),
        "frontmatter_description": bool(_scalar(fm, "description")),
        "triggers": bool(re.search(r"触发|何时使用|Use when|when to use|"
                                   r"Explicit triggers|trigger", text,
                                   re.IGNORECASE)),
        "constraints": bool(re.search(r"约束|规则|禁止|不得|必须|注意|"
                                      r"评分维度|维度|标准|原则|禁令|rules|"
                                      r"do not", text, re.IGNORECASE)),
        "evidence": bool(re.search(r"references/|https?://|\.md\b", text)),
    }


def _bigrams(text: str) -> set[str]:
    cleaned = re.sub(r"[#*`>\-\[\]()!| \t\r\n]+", "", text.lower())
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    return {cleaned[i:i + 2] for i in range(len(cleaned) - 1)} if len(cleaned) > 1 else set()


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def overlap_candidates(skills: list[dict]) -> list[dict]:
    """两两重叠候选：相似度 ≥ 阈值，按相似度降序、技能路径升序排列。"""
    grams = [(s, _bigrams(s["text"])) for s in skills]
    out: list[dict] = []
    for i in range(len(grams)):
        for j in range(i + 1, len(grams)):
            sim = jaccard(grams[i][1], grams[j][1])
            if sim >= OVERLAP_THRESHOLD:
                out.append({"a": grams[i][0]["path"], "b": grams[j][0]["path"],
                            "similarity": round(sim, 3)})
    out.sort(key=lambda c: (-c["similarity"], c["a"], c["b"]))
    return out


def evaluate(root: Path) -> dict:
    """在真实技能包上跑质量门 + 重叠检测，返回结构化评估结果。"""
    skills = discover_skills(root)
    if not skills:
        raise ValueError("EVALUATION_EMPTY: 评委 skill 包为空，拒绝出空报告")
    per_skill = []
    for skill in skills:
        checks = static_checks(skill)
        missing = [k for k, ok in checks.items() if not ok]
        # 行为结论：无 ablation 对照数据 → 按 T1 §一判待补测
        per_skill.append({
            "name": skill["name"], "path": skill["path"],
            "checks": checks, "missing": missing,
            "static_verdict": "静态完整" if not missing else "待整改-静态缺项",
            "behavior_verdict": "待补测",
            "behavior_reason": "无有技能 vs 无技能对照数据（样本 0 < 30）",
        })
    candidates = overlap_candidates(skills)
    return {
        "schema": SCHEMA,
        "skill_count": len(skills),
        "static_complete": sum(1 for s in per_skill if not s["missing"]),
        "static_gap": sum(1 for s in per_skill if s["missing"]),
        "overlap_candidates": candidates,
        "skills": per_skill,
    }


def render_report(result: dict) -> str:
    lines = [
        "# mba 评委技能评估报告（首份，PRD-485/T2）",
        "",
        "- 日期：2026-11-17；对应 trend issue：zhanglunet/trend#2346；"
        "设计：docs/plans/2026-11-17-prd-485-mba-skill-evaluation-design.md",
        f"- 参评技能：{result['skill_count']} 个（perspectives/plugins/"
        "metric-brand-auditor/research 下的 SKILL.md；不含 tests/ fixture 与"
        " docs/prd/ 草稿）",
        f"- 静态完整：{result['static_complete']} 个；静态缺项："
        f"{result['static_gap']} 个",
        f"- 重叠候选（相似度 ≥ {OVERLAP_THRESHOLD}，待人工复核）："
        f"{len(result['overlap_candidates'])} 对",
        "- 行为结论：全部“待补测”——尚无有技能 vs 无技能对照数据，"
        "按 T1 §一不判过关也不判失效；行为数据待 T5 实测补齐。",
        "",
        "## 逐技能结论",
        "",
        "| 技能 | 静态结论 | 缺项 | 行为结论 |",
        "|---|---|---|---|",
    ]
    for s in result["skills"]:
        lines.append(f"| {s['path']} | {s['static_verdict']} | "
                     f"{'、'.join(s['missing']) or '—'} | {s['behavior_verdict']} |")
    lines += ["", "## 重叠候选", ""]
    if result["overlap_candidates"]:
        lines += ["| 技能 A | 技能 B | 相似度 | 状态 |",
                  "|---|---|---|---|"]
        for c in result["overlap_candidates"]:
            lines.append(f"| {c['a']} | {c['b']} | {c['similarity']} | "
                         "候选（待人工复核） |")
    else:
        lines.append("无候选对。")
    lines += [
        "",
        "## 说明与红线",
        "",
        "- 相似度是筛子不是判决：候选须人工复核确认才进整改清单；评估结论绝不"
        "直接作为删除依据，技能下线另走审批。",
        "- 本报告只评技能包健康度，不审产物（评审流水线）、不审过程（监督回路）"
        "、不给单个评委写测试（独立验收测试）。",
        "- 下一步（T3/T5）：补行为对照数据（样本 ≥ 30）、合成评测集、实测；"
        "评估未过关的技能不得进入下游（T3 闸门）。",
        "",
    ]
    return "\n".join(lines)


def render_remediation_section(result: dict) -> str:
    lines = [
        "## 2026-11-17 首轮评估（PRD-485/T2）",
        "",
        f"参评 {result['skill_count']} 个技能；静态缺项 "
        f"{result['static_gap']} 个；重叠候选 "
        f"{len(result['overlap_candidates'])} 对（待人工复核）。"
        "以下条目只追加、不改写历史。",
        "",
    ]
    for s in result["skills"]:
        if s["missing"]:
            lines.append(f"- [静态缺项] {s['path']}：缺 "
                         f"{'、'.join(s['missing'])}；建议动作：修（补文本）。"
                         "证据：首份评估报告。")
    for c in result["overlap_candidates"]:
        lines.append(f"- [重叠候选] {c['a']} ↔ {c['b']}（相似度 "
                     f"{c['similarity']}）：待人工复核确认；确认重叠后建议"
                     "动作：合并或拆分（由整改定，不直接删）。")
    if result["static_gap"] == 0 and not result["overlap_candidates"]:
        lines.append("- 本轮无新增整改项。")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="mba 评委技能评估最小实现")
    parser.add_argument("--root", default=".",
                        help="仓库根目录（默认当前目录）")
    parser.add_argument("--report",
                        default="docs/evaluations/2026-11-17-skill-evaluation-report.md")
    parser.add_argument("--remediation",
                        default="docs/evaluations/remediation-list.md")
    args = parser.parse_args(argv)
    root = Path(args.root)
    result = evaluate(root)
    report_path = root / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(result), encoding="utf-8")
    remediation_path = root / args.remediation
    remediation_path.parent.mkdir(parents=True, exist_ok=True)
    header = ("# 评委技能整改清单（append-only）\n\n"
              "过期/重叠/失效的技能进清单，记原因、证据、建议动作；"
              "评估结论绝不直接作为删除依据，技能下线另走审批。\n\n")
    section = render_remediation_section(result)
    if remediation_path.exists():
        existing = remediation_path.read_text(encoding="utf-8")
        if "## 2026-11-17 首轮评估" in existing:
            print("remediation list already has this round; not duplicating")
        else:
            remediation_path.write_text(existing + section, encoding="utf-8")
    else:
        remediation_path.write_text(header + section, encoding="utf-8")
    print(json.dumps({"skills": result["skill_count"],
                      "static_complete": result["static_complete"],
                      "static_gap": result["static_gap"],
                      "overlap_candidates": len(result["overlap_candidates"]),
                      "report": args.report,
                      "remediation": args.remediation},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
