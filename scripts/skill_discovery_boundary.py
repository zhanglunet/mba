# -*- coding: utf-8 -*-
"""PRD-465/T4（trend issue #2248 的 T4 环节）：mba skill 发现层 划界断言。

在 T2 最小实现（scripts/skill_discovery.py）与 T3 闸门层
（scripts/skill_discovery_gate.py）之上加划界断言，不改 T2/T3 代码、
不改 T1 设计。发现层只做“发现”，不管以下两件事（T1 设计 §3–§4、
T4 issue 正文）：
  - R1 不碰 mba 现有评审流程与分数：推荐记录不写评审 findings、不写
    评审分数、不碰评委包与品牌审计报告；
  - R2 不绕过 skill 自己的标准安装链路：发现层不替 skill 安装、不写
    registry / marketplace，只读索引源。
落地：
  - scope_check：递归扫描发现记录，评审域 / 安装域的越界字段一律显形
    为 violation；顶层键与各段键集合也在断言范围内；
  - assert_no_review_writes / assert_no_install：两条红线各一条断言入口，
    分别对应 R1 / R2；
  - BoundaryDiscoveryLedger：入账划界，继承 T3 GatedDiscoveryLedger；
    越界记录拒绝入账（DISCOVERY_OUT_OF_SCOPE），洗不进账本；
  - recommendation_shape_check：推荐输出形态断言——顶层键恰为五段，
    候选与推荐只含发现字段，不带安装动作、不带评审写字段；
  - snapshot_sources / sources_unchanged：索引源只读断言——发现全流程
    前后，registry.json / SKILL.md / manifest.json / marketplace.json
    的字节内容须一字不差（发现层只读，不改源数据）。
注意：候选的 score 是发现置信分（[0, 1]，T2 口径），不是评审分数；
review.verdict 是发现复核结论（pending/accepted/rejected，T3 口径），
不是 mba 评审结论——断言用精确键名匹配，不误伤这两处。
零网络零子进程；示例全虚构占位。ASPIRE（Apache-2.0）只作形态借鉴，
本模块为原创实现，未复用其代码。
测试：tests/unit/test_prd465_t4_discovery_boundary.py
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from skill_discovery import (  # noqa: E402
    SCHEMA, DiscoveryError,
)
from skill_discovery_gate import (  # noqa: E402
    GatedDiscoveryLedger,
)

ERROR_CODES = ("DISCOVERY_INCOMPLETE", "DISCOVERY_SCORE_MISMATCH",
               "DISCOVERY_TRACE_MISMATCH", "DISCOVERY_INVALID_REVIEW",
               "DISCOVERY_OUT_OF_SCOPE")
# 发现记录顶层键（T1 §6.2 schema）；多出来的顶层键即越界。
ALLOWED_TOP_KEYS = ("schema", "request", "candidates", "recommendation",
                    "review")
# 各段键集合：多出来的键即越界（推荐段只含 skill/trace/effective，
# 不带安装动作；复核段只含 verdict/reviewer/note）。
REQUEST_KEYS = ("request_id", "text", "supersedes")
CANDIDATE_KEYS = ("skill", "score", "matched", "reason")
RECOMMENDATION_KEYS = ("skill", "trace", "effective")
REVIEW_KEYS = ("verdict", "reviewer", "note")
# 越界字段：精确键名匹配（不用子串，避免误伤候选 score、review.verdict
# 等发现层自有字段）。每域标注归属红线。
OUT_OF_SCOPE_FIELDS = {
    # R1 评审流程与分数：评审写字段不属于发现层。
    "findings": "R1",
    "review_score": "R1",
    "audit_score": "R1",
    "judge_score": "R1",
    "judge_verdict": "R1",
    "verdict_score": "R1",
    "rating": "R1",
    "scorecard": "R1",
    "brand_audit_report": "R1",
    "review_report": "R1",
    # R2 标准安装链路：安装动作与注册表写字段不属于发现层。
    "install": "R2",
    "installed": "R2",
    "install_path": "R2",
    "install_command": "R2",
    "install_action": "R2",
    "install_status": "R2",
    "installed_version": "R2",
    "registry_write": "R2",
    "marketplace_write": "R2",
}
DOMAIN_NAMES = {"R1": "评审流程与分数（R1）",
                "R2": "标准安装链路（R2）"}
# 索引源文件：发现层只读这些文件（T1 §6.1），一律不改。
SOURCE_GLOBS = ("registry.json", "**/SKILL.md", "**/manifest.json",
                "**/marketplace.json")


def _scan(obj: Any, path: str, violations: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            where = f"{path}.{key}" if path else str(key)
            owner = OUT_OF_SCOPE_FIELDS.get(key)
            if owner is not None:
                violations.append(
                    f"{where} 是{DOMAIN_NAMES[owner]}的字段，"
                    "不属于发现层")
            _scan(value, where, violations)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _scan(item, f"{path}[{i}]", violations)


def _check_section_keys(record: dict[str, Any],
                        violations: list[str]) -> None:
    sections = (("request", REQUEST_KEYS), ("review", REVIEW_KEYS))
    for name, allowed in sections:
        section = record.get(name)
        if isinstance(section, dict):
            for key in section:
                if key not in allowed:
                    violations.append(
                        f"{name} 段字段 {key!r} 不属于发现层")
    for cand in record.get("candidates") or []:
        if isinstance(cand, dict):
            for key in cand:
                if key not in CANDIDATE_KEYS:
                    violations.append(
                        f"候选 {cand.get('skill')} 字段 {key!r} "
                        "不属于发现层")
    recommendation = record.get("recommendation")
    if isinstance(recommendation, dict):
        for key in recommendation:
            if key not in RECOMMENDATION_KEYS:
                violations.append(
                    f"推荐段字段 {key!r} 不属于发现层")


def scope_check(record: dict[str, Any]) -> dict[str, Any]:
    """划界断言：发现记录是否只含发现层自己的东西。

    违反任一条即 in_scope=False 并列出全部 violation：越界字段、顶层多余
    键、各段多余键。
    """
    violations: list[str] = []
    if not isinstance(record, dict):
        return {"schema": SCHEMA, "in_scope": False,
                "violations": ["入账对象不是发现记录"]}
    for key in record:
        if key not in ALLOWED_TOP_KEYS:
            violations.append(f"顶层字段 {key!r} 不属于发现层 schema")
    _scan(record, "", violations)
    _check_section_keys(record, violations)
    return {"schema": SCHEMA, "in_scope": not violations,
            "violations": violations}


def assert_no_review_writes(record: dict[str, Any]) -> list[str]:
    """R1 边界：记录里没有评审流程与分数的写字段。"""
    return [v for v in scope_check(record)["violations"] if "R1" in v]


def assert_no_install(record: dict[str, Any]) -> list[str]:
    """R2 边界：记录里没有安装链路的字段。"""
    return [v for v in scope_check(record)["violations"] if "R2" in v]


class BoundaryDiscoveryLedger(GatedDiscoveryLedger):
    """入账划界：越界记录拒绝入账，洗不进账本。"""

    def record(self, rec: dict[str, Any]) -> dict[str, Any]:
        scope = scope_check(rec)
        if not scope["in_scope"]:
            raise DiscoveryError(
                "DISCOVERY_OUT_OF_SCOPE：记录越界，不属于发现层："
                + "；".join(scope["violations"]))
        return super().record(rec)


def recommendation_shape_check(out: dict[str, Any]) -> dict[str, Any]:
    """推荐输出形态断言：推荐只含发现字段，不带安装动作、不带评审写字段。

    顶层键恰为 schema/request/candidates/recommendation/review 五段；
    候选只含 skill/score/matched/reason；推荐只含 skill/trace/effective。
    """
    violations: list[str] = []
    if not isinstance(out, dict):
        return {"schema": SCHEMA, "ok": False,
                "violations": ["推荐输出不是记录"]}
    extra = sorted(set(out) - set(ALLOWED_TOP_KEYS))
    if extra:
        violations.append(f"推荐输出顶层多余字段 {extra}")
    violations.extend(scope_check(out)["violations"])
    return {"schema": SCHEMA, "ok": not violations,
            "violations": violations}


def snapshot_sources(root: str | Path) -> dict[str, str]:
    """索引源快照：{相对路径: sha256}，只读断言的比对基线。"""
    root = Path(root)
    snapshot: dict[str, str] = {}
    for pattern in SOURCE_GLOBS:
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                snapshot[str(path.relative_to(root))] = \
                    hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def sources_unchanged(root: str | Path,
                      snapshot: dict[str, str]) -> dict[str, Any]:
    """索引源只读断言：发现流程前后源文件字节内容须一字不差。

    返回 changed 列表（新增/删除/改动的文件相对路径）；为空即只读成立。
    """
    now = snapshot_sources(root)
    changed = sorted({*now} ^ {*snapshot} |
                     {k for k in now if now.get(k) != snapshot.get(k)})
    return {"schema": SCHEMA, "unchanged": not changed,
            "changed": changed}
