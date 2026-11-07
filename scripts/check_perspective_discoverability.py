#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-234/T3：品牌技能跨工具加载验证（trend issue #1172）。

对 perspectives/<slug>-perspective/ 46 个技能包做**结构级可发现性检查**，口径
对齐主流 agent 工具的 skill 发现规则（同 PRD-226/T3 contract 仓口径）：目录下有
SKILL.md、YAML frontmatter 含 name（=目录名、kebab-case）与非空 description
（≤1024 字符——超限会被工具截断/拒载，逐项报实际长度）、路径无空格大写、正文
非空、无真实主机名/密钥。另加本仓消费纪律（PRD-199 口径，与 T2 align_pack 一致）：
metadata.version（行锚定检测）、metadata.standard=agentskills-2026-10、
description 含触发式句式（Use as: / Explicit triggers:）。

诚实范围声明：本检查是**离线结构级**验证；真实异构工具加载实测归 T5（#1174）
抽样加载。检查结果机读输出（perspective-discoverability-report/v1），**失败项
一律带 reason**（本单验收即「验证记录齐全，失败项有原因说明」——当前出厂状态
的失败项如实报告，不做粉饰）。

用法：
    python3 scripts/check_perspective_discoverability.py                 # 全量检查
    python3 scripts/check_perspective_discoverability.py --json PATH     # 机读报告落盘

退出码：0=全部通过，1=存在失败项（本单当前预期为 1——metadata 缺失为已知差距，
由 T4 版本与变更规范落地处置）。

测试：tests/unit/test_prd234_t3_discoverability.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PERSPECTIVES_DIR = REPO_ROOT / "perspectives"
DESCRIPTION_MAX = 1024
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# 密钥字面量：真实密钥形态（sk- 后 ≥16 位； (?<![A-Za-z]) 防 musk-perspective 之类
# 仓内命名词子串误报）；ghp_/AKIA 同理加长下限
SECRET_RE = re.compile(
    r"((?<![A-Za-z])sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})")
# 内网/凭据纪律：PRD 禁的是**内部**主机名、IP 与凭据——perspectives 里的公开研究
# 引文 URL（媒体/官网/出处署名）是仓库事实，不属于违规面
INTERNAL_HOST_RE = re.compile(
    r"https?://(?:[^/\s@]+@)?"                       # URL 内嵌 basic-auth 凭据
    r"(?:10\.\d|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.127\.)"
    r"|https?://[^/\s]+\.(?:internal|local|lan|corp)(?:[/:]|$)"
    r"|https?://(?:[a-z0-9-]+\.)?(?:intranet|internal)\.",
    re.IGNORECASE,
)


def _frontmatter_block(text: str) -> str | None:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return match.group(1) if match else None


def _scalar_name(frontmatter: str) -> str | None:
    match = re.search(r"^name:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
    return match.group(1) if match else None


def _block_description(frontmatter: str) -> str:
    """description 块标量（| 形态）：取 description: 之后到下一个顶层 key 的缩进块。"""
    match = re.search(r"^description:\s*\|?\s*\n((?:[ \t]+.*\n?|\n)*)", frontmatter, re.MULTILINE)
    if match:
        return match.group(1).strip()
    match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    return match.group(1).strip() if match else ""


def check_skill(skill_dir: Path) -> dict:
    """单技能包结构级可发现性检查；返回 {skill, ok, checks:[{item, ok, reason}]}。"""
    checks: list[dict] = []

    def record(item: str, ok: bool, reason: str | None = None) -> None:
        checks.append({"item": item, "ok": ok, **({"reason": reason} if reason else {})})

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        record("SKILL.md 存在", False, f"{skill_dir.name}/ 缺 SKILL.md（主流工具发现入口）")
        return {"skill": skill_dir.name, "ok": False, "checks": checks}
    text = skill_md.read_text(encoding="utf-8")
    frontmatter = _frontmatter_block(text)
    if frontmatter is None:
        record("frontmatter 可解析", False, "SKILL.md 缺 frontmatter（首行必须为 ---）")
        return {"skill": skill_dir.name, "ok": False, "checks": checks}
    record("frontmatter 可解析", True)

    name = _scalar_name(frontmatter)
    if not name:
        record("name 在位", False, "frontmatter 缺 name（工具按 name 注册技能）")
    elif not NAME_RE.match(name):
        record("name kebab-case", False, f"name={name!r} 不符合 kebab-case")
    elif name != skill_dir.name:
        record("name 与目录同名", False, f"name={name!r} 与目录名 {skill_dir.name!r} 不一致")
    else:
        record("name 合规且与目录同名", True)

    description = _block_description(frontmatter)
    if not description:
        record("description 非空", False, "缺 description（触发/检索依据）")
    elif len(description) > DESCRIPTION_MAX:
        record("description 长度", False,
               f"description {len(description)} 字 > {DESCRIPTION_MAX} 上限"
               "（工具侧会被截断/拒载；建议保留前 1024 字内的角色与 Use as 摘要，"
               "全文移入 references/）")
    else:
        record("description 非空且长度合规", True)

    if re.search(r"[\sA-Z]", str(skill_dir.relative_to(REPO_ROOT))) if skill_dir.is_relative_to(REPO_ROOT) else False:
        record("路径规范", False, f"路径含空格或大写：{skill_dir.relative_to(REPO_ROOT)}")
    else:
        record("路径规范（无空格大写）", True)

    has_version = re.search(r"^\s+version:\s*\S", frontmatter, re.MULTILINE) is not None
    if has_version:
        record("metadata.version 在位", True)
    else:
        record("metadata.version 在位", False,
               "缺 metadata.version（PRD-199 口径；随 T4 版本与变更规范落地补齐）")
    if "standard: agentskills-2026-10" in frontmatter:
        record("metadata.standard 对齐声明", True)
    else:
        record("metadata.standard 对齐声明", False,
               "缺 standard: agentskills-2026-10（PRD-199 口径；随 T4 补齐）")
    if ("Use as:" in description) or ("Explicit triggers:" in description):
        record("触发式句式（Use as / Explicit triggers）", True)
    else:
        record("触发式句式（Use as / Explicit triggers）", False,
               "description 缺 Use as:/Explicit triggers: 触发句式（T2 口径）")

    body = text.split("---", 2)[-1].strip()
    if body:
        record("正文非空", True)
    else:
        record("正文非空", False, "frontmatter 之后无正文（工具加载后无可执行指令）")

    secrets = SECRET_RE.findall(text)
    if secrets:
        record("无密钥字面量", False, "发现疑似密钥字面量（占位符纪律）")
    else:
        record("无密钥字面量", True)
    internal = INTERNAL_HOST_RE.findall(text)
    if internal:
        record("无内网主机/凭据", False,
               f"发现内网地址或 URL 内嵌凭据：{sorted(set(internal))[:3]}")
    else:
        record("无内网主机/凭据（公开引文 URL 不在违规面）", True)

    return {"skill": skill_dir.name, "name": name or None,
            "ok": all(c["ok"] for c in checks), "checks": checks}


def check_all(perspectives_dir: Path | None = None) -> dict:
    """全部技能包检查；返回机读报告（发现条件口径 + 逐包结果 + 失败原因汇总）。"""
    root = perspectives_dir if perspectives_dir is not None else PERSPECTIVES_DIR
    skill_dirs = sorted(d for d in root.iterdir() if d.is_dir()) if root.is_dir() else []
    results = [check_skill(d) for d in skill_dirs]
    fm_names = [r.get("name") for r in results if r.get("name")]
    duplicates = {n for n in fm_names if fm_names.count(n) > 1}
    if duplicates:
        for result in results:
            if result.get("name") in duplicates:
                result["ok"] = False
                result["checks"].append({
                    "item": "name 全库唯一", "ok": False,
                    "reason": f"技能名重复：{sorted(duplicates)}（注册冲突）",
                })
    if not results:
        results.append({"skill": "(none)", "ok": False,
                        "checks": [{"item": "发现技能包", "ok": False,
                                    "reason": f"{root} 下无技能目录"}]})
    failures: dict[str, int] = {}
    for result in results:
        for check in result["checks"]:
            if not check["ok"]:
                item = check["item"]
                failures[item] = failures.get(item, 0) + 1
    return {
        "schema": "perspective-discoverability-report/v1",
        "scope": "跨工具可发现性·结构级验证（真实异构工具加载实测归 T5 #1174）",
        "criteria": "SKILL.md + frontmatter name(=目录名, kebab-case)/description(非空≤1024)"
                    "/路径规范/正文非空/无内网主机与凭据（公开引文 URL 不在违规面）"
                    "+ metadata.version/standard + 触发式句式 + name 全库唯一"
                    "（PRD-199 消费纪律与 226/T3 同口径）",
        "perspectives_dir": str(root),
        "results": results,
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r["ok"]),
            "failed": sum(1 for r in results if not r["ok"]),
            "failure_kinds": dict(sorted(failures.items(), key=lambda kv: -kv[1])),
            "failure_reasons": [
                {"skill": r["skill"], "item": c["item"], "reason": c["reason"]}
                for r in results if not r["ok"]
                for c in r["checks"] if not c["ok"]
            ],
        },
    }


def main(argv: list[str]) -> int:
    report = check_all()
    if "--json" in argv:
        out = Path(argv[argv.index("--json") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        print(f"report -> {out}")
    for result in report["results"]:
        mark = "PASS" if result["ok"] else "FAIL"
        print(f"[{mark}] {result['skill']}")
        for check in result["checks"]:
            if not check["ok"]:
                print(f"    - {check['item']}: {check['reason']}")
    s = report["summary"]
    kinds = "；".join(f"{k}×{v}" for k, v in s["failure_kinds"].items())
    print(f"{s['passed']}/{s['total']} passed"
          + (f"（失败类型：{kinds}）" if kinds else ""))
    return 0 if s["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
