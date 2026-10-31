#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-205/T3（trend #1027）：评委接入——评审引用设计语言条目编号。

按 PRD-205/T1 设计 §6.2（docs/plans/2026-10-26-design-language-spec.md）实现 T3 范围：
  评委与生成器（T2）消费同一份 design/design-language.json；
  每条设计类评审意见必须带条目编号，字段 rule / level / evidence / expect，
  意见可定位到具体条目；引用不存在或已 deprecated 的编号 → 意见无效；
  任一硬规则违反 → 设计维度判 fail；只有建议级 → 不影响 pass/fail，只记录；
  评审记录注明所依据的设计语言文件版本。
纯 stdlib，零网络；示例全虚构。
"""
from __future__ import annotations

from typing import Any

# T1 §2.4 用语（hard/advice）与 T2 落地文件用语（hard/soft）的同义词登记
_LEVEL_ALIASES = {"hard": "hard", "advice": "soft", "soft": "soft"}


def normalize_level(level: Any) -> str | None:
    """归一评审意见的级别表述；不在词表内返回 None。"""
    if not isinstance(level, str):
        return None
    return _LEVEL_ALIASES.get(level.strip().lower())


def rule_index(dl: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """条目编号 → 条目对象 的索引（供定位与存在性校验）。"""
    index: dict[str, dict[str, Any]] = {}
    for rule in dl.get("rules", []):
        if isinstance(rule, dict) and isinstance(rule.get("id"), str):
            index[rule["id"]] = rule
    return index


def validate_finding(dl: dict[str, Any], finding: dict[str, Any]) -> dict[str, Any]:
    """校验一条设计评审意见能否定位到设计语言条目。

    必填字段（T1 §6.2）：rule（条目编号）/ level（与文件登记一致）/
    evidence（文件 + 选择器或行号 + 实际值）/ expect（期望值或登记集合）。
    返回 {"ok": bool, "reasons": [...], "located": {...} | None}；
    located 含条目描述，意见据此定位到具体条目。
    """
    reasons: list[str] = []
    if not isinstance(finding, dict):
        return {"ok": False, "reasons": ["意见必须是对象"], "located": None}

    rid = finding.get("rule")
    if not isinstance(rid, str) or not rid.strip():
        return {"ok": False, "reasons": ["缺少 rule 条目编号"], "located": None}

    index = rule_index(dl)
    rule = index.get(rid)
    if rule is None:
        return {"ok": False, "reasons": [f"条目编号不存在: {rid}"], "located": None}
    if rule.get("status") == "deprecated":
        return {"ok": False, "reasons": [f"条目已 deprecated: {rid}"], "located": None}

    level = normalize_level(finding.get("level"))
    if level is None:
        reasons.append(f"level 不在词表（hard/advice/soft）: {finding.get('level')!r}")
    elif level != rule.get("severity"):
        reasons.append(
            f"level 与文件登记不一致: 意见 {level} vs 条目 {rid} 登记为 {rule.get('severity')}"
        )

    for field in ("evidence", "expect"):
        val = finding.get(field)
        if not isinstance(val, str) or not val.strip():
            reasons.append(f"缺少 {field}（T1 §6.2 必填）")

    located = {
        "rule": rid,
        "rule_description": rule.get("description", ""),
        "level": rule.get("severity"),
    }
    return {"ok": not reasons, "reasons": reasons, "located": located}


def review_findings(dl: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    """评委提交一批设计评审意见 → 定位、校验并给出设计维度结论。

    结论规则（T1 §6.2）：任一硬规则违反 → fail；只有建议级 → pass_with_notes；
    无意见 → pass。无效意见不参与结论，但逐条列出（元评审可直接驳回）。
    """
    entries: list[dict[str, Any]] = []
    hard_violations = 0
    notes = 0
    invalid = 0
    for finding in findings:
        check = validate_finding(dl, finding)
        entry = dict(finding) if isinstance(finding, dict) else {"finding": finding}
        entry["status"] = "valid" if check["ok"] else "invalid"
        if check["ok"]:
            entry["located"] = check["located"]
            if check["located"]["level"] == "hard":
                hard_violations += 1
            else:
                notes += 1
        else:
            entry["invalid_reasons"] = check["reasons"]
            invalid += 1
        entries.append(entry)

    if hard_violations:
        verdict = "fail"
    elif notes:
        verdict = "pass_with_notes"
    else:
        verdict = "pass"
    return {
        "dl_version": dl.get("meta", {}).get("version"),
        "verdict": verdict,
        "counts": {"hard_violations": hard_violations, "notes": notes, "invalid": invalid},
        "findings": entries,
    }


def format_finding(entry: dict[str, Any]) -> str:
    """一条已定位意见的单行可读形式：[编号] (级别) 证据 → 期望。"""
    if entry.get("status") != "valid":
        return f"[无效] {entry.get('invalid_reasons')}"
    loc = entry["located"]
    return (
        f"[{loc['rule']}] ({loc['level']}) {entry.get('evidence', '')}"
        f" → 期望 {entry.get('expect', '')}"
    )
