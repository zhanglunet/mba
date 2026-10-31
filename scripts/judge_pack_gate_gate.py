#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-262/T3（trend #1312）：评委包进池闸门——注册入口前置校验 + 哈希绑定 + 档案 gate 状态。

按 PRD-262/T1 设计（docs/plans/2026-10-28-prd-262-judge-pack-gate.md）§3.3 实现 T3 范围：
  pack_hash：包文件字典（文件名 → 内容）的规范化 JSON sha256 前 16 位（确定性，键序无关）；
  registration_gate：评委池注册入口前置校验——
    1) 无报告 → 拒（首次进池与版本变更都必须附有效安检报告）；
    2) report.scan_version 与当前扫描器 SCAN_VERSION 不匹配 → 拒（旧规则报告作废，须重扫）；
    3) 哈希不一致 → 拒（改包后旧报告作废；池内登记哈希与包不符同拒，自动重扫）；
    4) report.decision == blocked（或 severity HIGH/CRITICAL）→ 拒（HIGH+ 不进池，硬闸门）；
       T4 误报白名单复核：传入 whitelist（WhitelistManager）时，blocked 报告的**全部 findings**
       均命中该包（scope=pack_name）有效白名单条目 → 放行，命中条目写入报告 whitelist_applied
       与档案 pack_gate.whitelist_refs 留痕；任一 finding 未命中/过期仍拒；
    通过 → admit=True + gate 状态（复用 T2 profile_gate_section 六字段 + pack_hash，供 PRD-151 档案）；
  stamp_pack_hash：把 pack_hash 写入报告（注册登记形态，闸门比对依据）。
  被拦包只返回机读拒因，不产生放行凭据。零网络。白名单条目单条规则级/90 天过期/责任到人
  （见 judge_pack_whitelist.py）。示例全虚构。

运行自测：python3 -m pytest tests/unit/test_prd262_t3_gate.py tests/unit/test_judge_pack_whitelist.py -q
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from judge_pack_gate import SCAN_VERSION, profile_gate_section


def pack_hash(files: dict[str, str]) -> str:
    """包内容哈希：files 字典规范化 JSON（sort_keys + 紧凑分隔符）后 sha256 前 16 位。

    确定性：同一内容与键序无关同哈希；任一文件内容变更即哈希变更。
    """
    canonical = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def stamp_pack_hash(report: dict[str, Any], files: dict[str, str]) -> dict[str, Any]:
    """注册登记形态：把包哈希写入安检报告副本（闸门比对的绑定依据）。"""
    stamped = dict(report)
    stamped["pack_hash"] = pack_hash(files)
    return stamped


def _reject(pack_name: str, reason: str, detail: str, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"admit": False, "pack": pack_name, "reason": reason, "detail": detail,
                           "rescan_required": reason in ("missing_report", "scan_version_mismatch",
                                                         "hash_mismatch", "report_missing_hash")}
    out.update(extra)
    return out


def registration_gate(pack_name: str, files: dict[str, str],
                      report: dict[str, Any] | None, current_hash: str | None,
                      whitelist: Any | None = None) -> dict[str, Any]:
    """评委池注册入口前置校验。

    参数：
      pack_name：待注册包名（须与报告 pack.name 一致）；
      files：包文件字典（文件名 → 文本内容）；
      report：T2 安检报告 judge-pack-gate-report-v1（应经 stamp_pack_hash 绑定包哈希）；None=未附报告；
      current_hash：评委池当前登记版本的包哈希（首次进池传 None）；
      whitelist：可选 WhitelistManager（T4 误报白名单）——blocked 报告全部 findings 均命中
        scope=pack_name 的有效条目时放行并留痕（whitelist_applied / pack_gate.whitelist_refs）。

    判定顺序（任一不过 → {admit: False, reason, ...}，机读拒因）：
      missing_report → 首次进池/版本变更必须附有效报告；
      pack_name_mismatch → 报告不属于该包；
      scan_version_mismatch → 报告由旧版扫描规则出，作废须重扫；
      report_missing_hash → 报告未绑定包哈希（无效登记形态）；
      hash_mismatch → 改包后旧报告作废（须重扫），或池内登记哈希与实际包不符；
      blocked → HIGH/CRITICAL 不进池（硬闸门；T4：全部 findings 均命中有效白名单方可复核放行）。
    通过 → {admit: True, pack_hash, gate: 档案 gate 状态（pack_gate 六字段 + pack_hash）}；
      白名单放行时附 reason=whitelisted + whitelist_applied（命中条目，机读留痕）。
    """
    # 1) 无报告：首次进池与版本变更必须附有效报告
    if not report or not isinstance(report, dict):
        return _reject(pack_name, "missing_report", "未附有效安检报告——首次进池与版本变更都必须附报告")
    # 2) 报告须属于该包
    if report.get("pack", {}).get("name") != pack_name:
        return _reject(pack_name, "pack_name_mismatch",
                       f"报告包名 {report.get('pack', {}).get('name')!r} 与注册包名不符")
    # 3) 扫描规则版本须与当前一致（旧规则报告作废）
    if report.get("scan_version") != SCAN_VERSION:
        return _reject(pack_name, "scan_version_mismatch",
                       f"报告 scan_version={report.get('scan_version')!r} 与当前 {SCAN_VERSION!r} 不符——须重扫")
    # 4) 哈希绑定：报告须记录包哈希且与实际包一致；池内登记哈希同验
    computed = pack_hash(files)
    report_hash = report.get("pack_hash")
    if not report_hash:
        return _reject(pack_name, "report_missing_hash", "报告未绑定包哈希——非有效登记形态，须重扫")
    if report_hash != computed:
        return _reject(pack_name, "hash_mismatch",
                       "包内容与报告哈希不一致——改包后旧报告作废，自动重扫", pack_hash=computed)
    if current_hash is not None and current_hash != computed:
        return _reject(pack_name, "hash_mismatch",
                       "池内登记哈希与实际包不一致——版本变更须重扫", pack_hash=computed)
    # 5) 硬闸门：HIGH/CRITICAL 不进池；T4 白名单复核：全部 findings 命中有效条目方可放行留痕
    if report.get("decision") == "blocked" or report.get("severity") in ("HIGH", "CRITICAL"):
        applied: list[dict[str, Any]] = []
        if whitelist is not None:
            rule_ids: list[str] = []
            for f in report.get("findings") or []:
                rid = f.get("rule_id")
                if rid and rid not in rule_ids:
                    rule_ids.append(rid)
            per_rule: dict[str, dict[str, Any]] = {}
            for rid in rule_ids:
                entry = whitelist.check(rid, pack_name)
                if entry is None:
                    per_rule = {}
                    break
                per_rule[rid] = entry
            if rule_ids and per_rule:
                seen: set[str] = set()
                for rid in rule_ids:
                    entry = dict(per_rule[rid])
                    if entry["entry_id"] not in seen:
                        seen.add(entry["entry_id"])
                        applied.append(entry)
        if applied:
            # 复核放行：报告留痕（whitelist_applied → 档案 pack_gate.whitelist_refs 同步可读）
            report_wl = dict(report)
            report_wl["whitelist_applied"] = applied
            gate = profile_gate_section(report_wl)
            gate["pack_gate.pack_hash"] = computed
            return {"admit": True, "pack": pack_name, "reason": "whitelisted",
                    "pack_hash": computed, "gate": gate, "whitelist_applied": applied}
        return _reject(pack_name, "blocked",
                       f"安检不通过（severity={report.get('severity')}, score={report.get('score')}）——HIGH+ 不进池",
                       severity=report.get("severity"), score=report.get("score"),
                       report_ref=profile_gate_section(report)["pack_gate.report_ref"])
    # 通过：admit + gate 状态（供 PRD-151 档案）
    gate = profile_gate_section(report)
    gate["pack_gate.pack_hash"] = computed
    return {"admit": True, "pack": pack_name, "reason": "ok", "pack_hash": computed, "gate": gate}
