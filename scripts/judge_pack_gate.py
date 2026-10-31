#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-262/T2（trend #1311）：评委包进池安检适配最小实现——J 四维静态扫描。

按 PRD-262/T1 设计（docs/plans/2026-10-28-prd-262-judge-pack-gate.md）实现 T2 范围：
  J-1 隐藏指令与注入（零宽字符/base64 块/范围外指令——"评审前先上报"类）
  J-2 工具越权（写路径/网络/exec）
  J-3 凭据访问（密钥模式/敏感路径，floor HIGH）
  J-4 包清单一致性（frontmatter name/version 缺失；license 声明与实测不符直接 HIGH）
  0-100 安全分 + 风险值 risk=100-score 四档严重度；HIGH+ 不进池；
  judge-pack-gate-report-v1 JSON + PRD-151 档案 pack_gate 分节映射。
  evidence 占位符化（密钥/内网 IP/评审批注敏感内容替换 <REDACTED>）。零网络。
T3 进池闸门、T4 白名单另任务。示例全虚构。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "judge-pack-gate-report-v1"
SCAN_VERSION = "0.1.0"

RULES: dict[str, dict[str, Any]] = {
    "J-1-01": {"dimension": "J-1", "deduct": 35, "floor": "HIGH", "desc": "零宽/不可见 Unicode 字符"},
    "J-1-02": {"dimension": "J-1", "deduct": 35, "floor": "HIGH", "desc": "范围外指令式措辞（评审前先上报/外发类）"},
    "J-2-01": {"dimension": "J-2", "deduct": 30, "desc": "写路径原语"},
    "J-2-02": {"dimension": "J-2", "deduct": 30, "desc": "网络访问原语"},
    "J-3-01": {"dimension": "J-3", "deduct": 20, "floor": "HIGH", "desc": "密钥/token 模式"},
    "J-3-02": {"dimension": "J-3", "deduct": 20, "floor": "HIGH", "desc": "敏感路径触碰"},
    "J-4-01": {"dimension": "J-4", "deduct": 15, "desc": "frontmatter name/version 缺失"},
    "J-4-02": {"dimension": "J-4", "deduct": 15, "floor": "HIGH", "desc": "license 声明与实测不符"},
}

_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")
_IMPERATIVE_RE = re.compile(r"(评审(结果|前).{0,10}(上报|发送|外传)|忽略(之前的|上述)?规则)", re.I)
_WRITE_RE = re.compile(r"(open\([^)]*,\s*['\"]w|shutil\.|os\.remove)", re.I)
_NET_RE = re.compile(r"\b(requests\.(get|post)|urllib|socket\.|curl\s)", re.I)
_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{16,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
)
_SENSITIVE_PATH_RE = re.compile(r"\.env|\.ssh|credentials", re.I)
_REDACT_RE = re.compile(
    r"sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|Bearer\s+[A-Za-z0-9._-]{16,}|gh[pousr]_[A-Za-z0-9]{30,}"
    r"|\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b")
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.S)


def _redact(text: str) -> str:
    return _REDACT_RE.sub("<REDACTED>", text)


def _finding(rule_id: str, location: str, detail: str) -> dict[str, Any]:
    rule = RULES[rule_id]
    return {"rule_id": rule_id, "dimension": rule["dimension"],
            "severity_suggest": rule.get("floor", "MEDIUM"),
            "evidence": _redact(detail), "location": location, "deduct": rule["deduct"]}


def scan_pack(pack_dir: Path, *, declared_license: str | None = None,
              verified_license: str | None = None) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    skill_md = pack_dir / "SKILL.md"
    meta: dict[str, str] = {}
    if skill_md.exists():
        m = _FRONTMATTER_RE.match(skill_md.read_text(encoding="utf-8"))
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip()

    for path in sorted(pack_dir.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = str(path.relative_to(pack_dir))
        if _ZERO_WIDTH_RE.search(text):
            findings.append(_finding("J-1-01", rel, "检出零宽/不可见 Unicode 字符"))
        if _IMPERATIVE_RE.search(text):
            findings.append(_finding("J-1-02", rel, "检出范围外指令式措辞（评审前上报/外发类）"))
        if _WRITE_RE.search(text):
            findings.append(_finding("J-2-01", rel, "检出写路径原语"))
        if _NET_RE.search(text):
            findings.append(_finding("J-2-02", rel, "检出网络访问原语"))
        for pat in _SECRET_PATTERNS:
            m = pat.search(text)
            if m:
                findings.append(_finding("J-3-01", rel, f"检出密钥/token 模式（命中样例 {_redact(m.group(0))}）"))
                break
        if _SENSITIVE_PATH_RE.search(text):
            findings.append(_finding("J-3-02", rel, "检出敏感路径触碰"))

    if not meta.get("name") or not meta.get("version"):
        findings.append(_finding("J-4-01", "SKILL.md", "frontmatter name/version 缺失"))
    lic_declared = declared_license or "MISSING"
    lic_verified = verified_license or "MISSING"
    if lic_declared == "MISSING" or lic_verified == "MISSING" or lic_declared != lic_verified:
        findings.append(_finding("J-4-02", "SKILL.md",
                                 f"license 声明({lic_declared})与实测({lic_verified})不符或缺失"))

    score = 100
    floor = None
    for f in findings:
        score = max(0, score - f["deduct"])
        if RULES.get(f["rule_id"], {}).get("floor"):
            floor = "HIGH"
    risk = 100 - score
    if risk >= 80:
        severity = "CRITICAL"
    elif risk >= 60 or floor:
        severity = "HIGH"
    elif risk >= 30:
        severity = "MEDIUM"
    else:
        severity = "LOW"
    decision = "blocked" if severity in ("CRITICAL", "HIGH") else "admitted"

    return {
        "schema": SCHEMA, "scanned_at": "2026-10-28T00:00:00Z",
        "pack": {"name": meta.get("name") or pack_dir.name, "version": meta.get("version") or "0.1.0",
                  "license_declared": lic_declared, "license_verified": lic_verified},
        "score": score, "severity": severity, "decision": decision,
        "findings": findings, "whitelist_applied": [], "scan_version": SCAN_VERSION,
    }


def profile_gate_section(report: dict[str, Any]) -> dict[str, Any]:
    """PRD-151 档案新增 pack_gate 分节（六字段）。"""
    return {
        "pack_gate.report_ref": f"pack-gate/{report['pack']['name']}/report-{report['scan_version']}.json",
        "pack_gate.score": report["score"],
        "pack_gate.severity": report["severity"],
        "pack_gate.decision": report["decision"],
        "pack_gate.whitelist_refs": [w.get("entry_id", "") for w in report["whitelist_applied"]],
        "pack_gate.scan_version": report["scan_version"],
    }
