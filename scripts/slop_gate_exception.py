#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-206/T4（trend #1033）：破例留痕——无理由破例不可放行。

按 PRD-206/T1 设计 §六（docs/plans/2026-10-26-anti-slop-gate.md）实现 T4 范围：
  - 只有 Reflex 级命中可破例；Floor 不可破例（只能改稿消除，或误报复核推翻命中本身）；
  - 破例记录七字段必填齐全（§6.2）：entry_id / locus / reason / proposer / approver /
    date / scope——即"谁（proposer）/ 何时（date）/ 哪条（entry_id+locus）/ 为什么（reason）"；
  - reason 必须含依据引用（可核查出处）；只有"我觉得没问题"不算理由 → 无效破例；
  - 无效破例四情形（§6.2）：字段缺失 / reason 无依据引用 / approver == proposer（自批）/
    破例对象是 Floor 条目——任一发生，破例视为不存在，verdict 按未破例计算（验收线）；
  - 生效破例回填对应 hit 的 exception_ref；hit 原文保留不改写（不回写、不洗白）；
    hit 上预置的 exception_ref 未经有效破例背书一律剥除（无理由破例不可放行）；
  - scope 固定 single-round（破例效力只限本轮，不构成先例）；
  - 与 PRD-205 设计语言 waivers 语义对齐：DL §6.1 硬规则偏离须声明豁免理由、
    无声明的偏离按违反处理——本模块同理，无有效理由的破例按未破例处理；
    DL 条目编号（如 DL-C05）可作 reason 的依据引用（waiver 式理由机判可查）。
  纯 stdlib，零网络；示例身份一律占位符。
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from slop_gate_crossref import GATE_FLOOR_ENTRIES
from slop_gate_floor import GATE_VERSION

EXCEPTIONS_VERSION = "prd-206-exceptions-v1"

REQUIRED_FIELDS = ("entry_id", "locus", "reason", "proposer", "approver", "date", "scope")

# 依据引用的可判定形态：DL 条目编号 / 门条目编号 / 仓库内可核查路径 / 显式"依据:"标注
_BASIS_PATTERNS = (
    re.compile(r"\bDL-[A-Z]\d{2}\b"),
    re.compile(r"\bSLOP-[TGSC]-\d{2}\b"),
    re.compile(r"\b(?:published|docs|design|scripts|reports)/[\w./-]+"),
    re.compile(r"(?:依据|出处|来源|引用)\s*[:：]\s*\S"),
)
_DATE_FORMAT = "%Y-%m-%d"


def basis_cited(reason: Any) -> bool:
    """reason 是否含可核查的依据引用（无依据 = "我觉得没问题"式理由，不算理由）。"""
    if not isinstance(reason, str):
        return False
    return any(p.search(reason) for p in _BASIS_PATTERNS)


def normalize_hits(raw_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把 T2 门输出（{rule_id, evidence}）对齐到 T1 §5.1 schema（{entry_id, tier, locus}）。

    T2 五条 Floor 条目的 tier 依 T3 互引登记表（GATE_FLOOR_ENTRIES）判定；
    登记表外的 rule_id 不猜档位，记 tier=unknown（verdict 按 Floor 保守处理）。
    已是 T1 schema 的命中原样通过。locus 一期从简：T2 形态按 rule_id 生成稳定占位。
    """
    out: list[dict[str, Any]] = []
    for h in raw_hits:
        if not isinstance(h, dict):
            continue
        if "entry_id" in h:
            hit = dict(h)
            hit.setdefault("exception_ref", None)
            out.append(hit)
            continue
        rid = h.get("rule_id")
        tier = "floor" if rid in GATE_FLOOR_ENTRIES else "unknown"
        out.append({
            "entry_id": rid,
            "tier": tier,
            "locus": f"gate-hit:{rid}",
            "evidence_quote": h.get("evidence", ""),
            "note": h.get("note", ""),
            "exception_ref": None,
        })
    return out


def validate_exception(record: Any, hits: list[dict[str, Any]]) -> dict[str, Any]:
    """校验一条破例记录（§6.2 必填齐全 + 无效四情形）。

    返回 {"valid": bool, "reasons": [...], "hit_index": int | None}；
    无效破例的 reasons 逐条列出（留痕可查，元评审可直接驳回）。
    """
    reasons: list[str] = []
    if not isinstance(record, dict):
        return {"valid": False, "reasons": ["破例记录必须是对象"], "hit_index": None}

    for field in REQUIRED_FIELDS:
        val = record.get(field)
        if not isinstance(val, str) or not val.strip():
            reasons.append(f"缺少字段或为空: {field}")

    if reasons:
        return {"valid": False, "reasons": reasons, "hit_index": None}

    # 先按 entry_id + locus 联合定位（同条目多处命中时以 locus 区分），再退回仅按 entry_id
    hit_index: int | None = None
    for i, hit in enumerate(hits):
        if hit.get("entry_id") == record["entry_id"] and hit.get("locus") == record["locus"]:
            hit_index = i
            break
    exact_locus = hit_index is not None
    if hit_index is None:
        for i, hit in enumerate(hits):
            if hit.get("entry_id") == record["entry_id"]:
                hit_index = i
                break
    if hit_index is None:
        reasons.append(f"entry_id 不在本轮 hits 中: {record['entry_id']}")
        return {"valid": False, "reasons": reasons, "hit_index": None}

    hit = hits[hit_index]
    tier = hit.get("tier")
    if tier == "floor":
        reasons.append("破例对象是 Floor 条目——Floor 不可破例（只能改稿或误报复核推翻命中）")
    elif tier != "reflex":
        reasons.append(f"破例对象 tier 不在可破例词表（reflex）: {tier!r}")
    if not exact_locus:
        reasons.append("locus 与对应命中记录不一致")

    if not basis_cited(record["reason"]):
        reasons.append("reason 无依据引用（'我觉得没问题'不算理由，须给可核查出处）")
    if record["approver"].strip() == record["proposer"].strip():
        reasons.append("approver 与 proposer 相同（自批无效）")
    try:
        datetime.strptime(record["date"].strip(), _DATE_FORMAT)
    except ValueError:
        reasons.append("date 非 YYYY-MM-DD 合法日期")
    if record["scope"].strip() != "single-round":
        reasons.append("scope 固定为 single-round（破例效力只限本轮，不构成先例）")

    return {"valid": not reasons, "reasons": reasons, "hit_index": hit_index}


def compute_verdict(hits: list[dict[str, Any]]) -> str:
    """门 verdict（§5.1 三值）：任一 Floor 命中且未被误报复核推翻 → blocked；
    无 Floor 有 Reflex（含已破例与未破例）→ passed_with_warnings；否则 passed。
    review.result == overturned 的命中撤销，不计入 verdict；unknown tier 按 Floor 保守处理。
    """
    active = [h for h in hits if not (h.get("review") or {}).get("result") == "overturned"]
    if any(h.get("tier") in ("floor", "unknown") for h in active):
        return "blocked"
    if any(h.get("tier") == "reflex" for h in active):
        return "passed_with_warnings"
    return "passed"


def apply_exceptions(hits: list[dict[str, Any]],
                     exceptions: list[dict[str, Any]],
                     advisory: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """把破例记录套到本轮命中上：生效破例回填 exception_ref，无效破例视为不存在。

    - hit 原文保留不改写，只允许追加 exception_ref；预置 exception_ref 一律先剥除
      （未经有效破例背书的"已放行"标记不可信——无理由破例不可放行）；
    - 同一命中只认第一条生效破例，重复申请记无效；
    - counts.exceptions 只计生效破例；verdict 按未破例口径重算。
    """
    hits_out = [dict(h) for h in hits]
    for h in hits_out:
        h["exception_ref"] = None

    entries: list[dict[str, Any]] = []
    used: set[int] = set()
    pending_ref: list[tuple[int, int]] = []  # (hit_index, 输出 exceptions 下标)
    for exc in exceptions:
        check = validate_exception(exc, hits_out)
        entry = dict(exc) if isinstance(exc, dict) else {"record": exc}
        entry["valid"] = check["valid"]
        entry["invalid_reasons"] = check["reasons"]
        if check["valid"]:
            idx = check["hit_index"]
            if idx in used:
                entry["valid"] = False
                entry["invalid_reasons"] = ["该命中已有生效破例（一次破例只对应一个命中）"]
            else:
                used.add(idx)
                pending_ref.append((idx, len(entries)))
        entries.append(entry)
    for hit_idx, exc_idx in pending_ref:
        hits_out[hit_idx]["exception_ref"] = f"exceptions[{exc_idx}]"

    active = [h for h in hits_out if not (h.get("review") or {}).get("result") == "overturned"]
    counts = {
        "floor": sum(1 for h in active if h.get("tier") in ("floor", "unknown")),
        "reflex": sum(1 for h in active if h.get("tier") == "reflex"),
        "finish": len(advisory or []),
        "exceptions": sum(1 for e in entries if e["valid"]),
    }
    return {
        "hits": hits_out,
        "exceptions": entries,
        "counts": counts,
        "verdict": compute_verdict(hits_out),
        "invalid_count": sum(1 for e in entries if not e["valid"]),
        "ok": all(e["valid"] for e in entries),
    }


def exception_report(hits: list[dict[str, Any]],
                     exceptions: list[dict[str, Any]],
                     advisory: list[dict[str, Any]] | None = None,
                     brand_slug: str = "example-brand") -> dict[str, Any]:
    """破例留痕报告（与 T1 §5.1 slop_gate.json schema 同构：门版本 + counts 对账 + 全量渲染）。"""
    result = apply_exceptions(hits, exceptions, advisory)
    return {
        "gate_version": GATE_VERSION,
        "exceptions_version": EXCEPTIONS_VERSION,
        "brand_slug": brand_slug,
        "verdict": result["verdict"],
        "counts": result["counts"],
        "hits": result["hits"],
        "advisory": list(advisory or []),
        "exceptions": result["exceptions"],
        "invalid_count": result["invalid_count"],
        "ok": result["ok"],
    }
