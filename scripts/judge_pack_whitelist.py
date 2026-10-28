#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-262/T4（trend #1313）：误报白名单与复核——单条规则级放行 + 全程审计留痕（可审计）。

按 PRD-262/T1 设计实现 T4 范围：
  WhitelistManager：误报白名单登记/查询/审计——
    add(rule_id, scope, reason, reviewer, now)：登记一条白名单——
      reason 与 reviewer 必填（复核责任到人，空即拒）；
      条目只覆盖**单条规则**（rule_id）× 单一作用域（scope，一般为评委包名），无通配；
      90 天过期（expires_at = added_at + 90 天，过期自动失效）；
    check(rule_id, scope, now)：查询有效条目——命中返回条目 dict，未命中/已过期返回 None；
    audit_log()：机读审计日志——added / checked_hit / checked_miss / checked_expired
      全事件留痕（at/rule_id/scope/entry_id），可回放、可复核。
  进池闸门对接：registration_gate(..., whitelist=manager)（judge_pack_gate_gate.py）——
    blocked 报告的全部 findings 均命中该包有效白名单条目 → 放行，且把命中的条目写入
    报告 whitelist_applied / 档案 pack_gate.whitelist_refs 留痕；任一 finding 未命中仍拒。

安全口径：白名单是「误报复核」通道，不是后门——单条规则级（不按包整体放行）、
限期（90 天）、责任到人（reviewer 必填）、事件全留痕（可审计）。

零网络；示例数据全虚构；不含真实主机名、账号、密钥。

运行自测：python3 -m pytest tests/unit/test_judge_pack_whitelist.py -q
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

WHITELIST_TTL_DAYS = 90


class WhitelistError(ValueError):
    """白名单登记非法（reason/reviewer 缺失等）。"""


def _to_dt(value: datetime | str) -> datetime:
    """datetime 或 ISO 字符串 → aware datetime（naive 视为 UTC）。"""
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class WhitelistManager:
    """误报白名单：条目 = (rule_id, scope) 单条规则级，90 天过期，事件全留痕。"""

    def __init__(self, now_fn: Callable[[], datetime] | None = None):
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self._entries: list[dict[str, Any]] = []
        self._audit: list[dict[str, Any]] = []
        self._seq = 0

    # ── 登记 ──

    def add(self, rule_id: str, scope: str, reason: str = "", reviewer: str = "",
            now: datetime | str | None = None) -> dict[str, Any]:
        """登记一条白名单（单条规则 × 单一作用域）。reason/reviewer 必填，缺失/空即拒。"""
        if not isinstance(reason, str) or not reason.strip():
            raise WhitelistError("reason 必填——误报理由须写明（复核依据）")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise WhitelistError("reviewer 必填——复核责任到人")
        added = _to_dt(now) if now is not None else self._now_fn()
        self._seq += 1
        entry = {
            "entry_id": f"WL-{self._seq:04d}",
            "rule_id": str(rule_id),
            "scope": str(scope),
            "reason": reason.strip(),
            "reviewer": reviewer.strip(),
            "added_at": _iso(added),
            "expires_at": _iso(added + timedelta(days=WHITELIST_TTL_DAYS)),
        }
        self._entries.append(entry)
        self._audit.append({"event": "added", "at": entry["added_at"],
                            "entry_id": entry["entry_id"], "rule_id": entry["rule_id"],
                            "scope": entry["scope"], "reviewer": entry["reviewer"]})
        return dict(entry)

    # ── 查询 ──

    def check(self, rule_id: str, scope: str,
              now: datetime | str | None = None) -> dict[str, Any] | None:
        """查询 (rule_id, scope) 的有效条目：命中返回条目；未命中/已过期返回 None。"""
        nowdt = _to_dt(now) if now is not None else self._now_fn()
        hit = None
        for entry in self._entries:
            if entry["rule_id"] == str(rule_id) and entry["scope"] == str(scope):
                hit = entry  # 取最近登记的一条
        base = {"at": _iso(nowdt), "rule_id": str(rule_id), "scope": str(scope)}
        if hit is None:
            self._audit.append({**base, "event": "checked_miss"})
            return None
        if nowdt > _to_dt(hit["expires_at"]):
            self._audit.append({**base, "event": "checked_expired",
                                "entry_id": hit["entry_id"], "expires_at": hit["expires_at"]})
            return None
        self._audit.append({**base, "event": "checked_hit", "entry_id": hit["entry_id"]})
        return dict(hit)

    # ── 审计 ──

    def audit_log(self) -> list[dict[str, Any]]:
        """机读审计日志（副本）：added/checked_hit/checked_miss/checked_expired 全事件。"""
        return [dict(a) for a in self._audit]
