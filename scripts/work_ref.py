#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-296/T2（trend issue #1482）：评审指令 @评委包/@作品引用解析最小实现。

按 T1 设计（docs/plans/2026-11-04-prd-296-at-judgepack-work-ref-design.md）
§3/§4/§5/§6 实现，候选集为 PRD-233 登记册形态（注入式纯函数——registry.json
未并线前测试用同形态合成登记册，233 合并后生产装配对接）：

  - parse(raw)：@评委包名 / @作品号（十进制）两形态——禁止形态（成员后缀/
    子对象/相对词/双写）抛 RefSyntaxError；
  - resolve(raw, judgepacks, works)：精确匹配，候选数裁决：1 → Resolution
    （评委包=成员清单指纹，canonical JSON SHA-256 前 16——指纹进结论即
    天然审计；撤回作品照常寻址 status 显形，业务拦截不在寻址层）；0 →
    REF_NOT_FOUND；>1（包名唯一不变量破坏）→ REF_REGISTRY_CORRUPT。
    **二值返回** Resolution | Refusal；
  - RefAudit：解析审计（§6）——append-only 只增不删、成败都记、ts 注入。

口径变更走 PRD-282 快照（R1：本模块零口径修改——只记录用了哪一版）。
零网络；示例全虚构占位。
测试：tests/unit/test_prd296_t2_ref.py
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

REF_SCHEMA = "ref-resolution/v1"
PACK_RE = re.compile(r"^@(?P<name>[^@\s/#%@]+)$")
WORK_RE = re.compile(r"^@作品(?P<num>\d+)$")


class RefSyntaxError(ValueError):
    """§3.2 禁止形态——出现即拒绝，不尝试理解。"""


def pack_fingerprint(members: list[str]) -> str:
    """成员清单指纹（canonical JSON SHA-256 前 16）——进结论即审计（T1 §4.1）。"""
    canonical = json.dumps(sorted(members), ensure_ascii=False,
                           separators=(",", ":"))
    return "sha16:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def parse(raw: str) -> dict[str, Any]:
    """引用语法解析：{kind: judgepack|work, name?, work_number?}。"""
    if not isinstance(raw, str) or not raw.strip():
        raise RefSyntaxError(f"引用为空或非字符串：{raw!r}")
    token = raw.strip()
    if token.startswith("@@") or "@" in token[1:] or '"' in token:
        raise RefSyntaxError(f"禁止形态（双写/引号/内嵌@）：{raw!r}（§3.2）")
    m = WORK_RE.match(token)
    if m:
        if "/" in token:
            raise RefSyntaxError(f"作品引用不带子对象（评论寻址不定义）：{raw!r}（§3.2）")
        return {"kind": "work", "name": None, "work_number": int(m.group("num"))}
    m = PACK_RE.match(token)
    if m:
        name = m.group("name")
        if "#" in name:
            raise RefSyntaxError(
                f"引用不带成员后缀（成员清单是指纹整体）：{raw!r}（§3.2）")
        if name.startswith("最新"):
            raise RefSyntaxError(f"相对词不是引用（最新版是业务裁决）：{raw!r}（§3.2）")
        return {"kind": "judgepack", "name": name, "work_number": None}
    raise RefSyntaxError(f"引用须为 @评委包名 / @作品号：{raw!r}（§3.1）")


def resolve(raw: str, judgepacks: list[dict[str, Any]],
            works: list[dict[str, Any]]) -> dict[str, Any]:
    """@名→id 解析（§4.2）：精确匹配 + 候选数裁决。

    judgepacks：[{"name","members":[评委名…]}]；works：[{"work_id","status"}]。
    返回 Resolution | Refusal（二值，T1 §5）。
    """
    token = parse(raw)
    if token["kind"] == "judgepack":
        hits = [p for p in (judgepacks or []) if p.get("name") == token["name"]]
        if len(hits) == 1:
            pack = hits[0]
            members = list(pack.get("members") or [])
            return {
                "schema": REF_SCHEMA, "raw": raw, "kind": "judgepack",
                "judgepack": {"name": pack["name"], "member_count": len(members),
                              "fingerprint": pack_fingerprint(members)},
                "work_id": None,
                "resolution": {"status": "resolved", "candidates": 1,
                               "strategy": "exact"},
            }
        if not hits:
            return _refusal(raw, "REF_NOT_FOUND", [], "评委包")
        return _refusal(raw, "REF_REGISTRY_CORRUPT",
                        [p.get("name") for p in hits],
                        "包名全库唯一不变量破坏（PRD-233 登记册异常显形）")
    hits = [w for w in (works or []) if w.get("work_id") == token["work_number"]]
    if len(hits) == 1:
        work = hits[0]
        return {
            "schema": REF_SCHEMA, "raw": raw, "kind": "work",
            "judgepack": None, "work_id": work["work_id"],
            "meta_summary": {"work_status": work.get("status", "在库（占位）")},
            "resolution": {"status": "resolved", "candidates": 1,
                           "strategy": "exact"},
        }
    return _refusal(raw, "REF_NOT_FOUND" if not hits else "REF_AMBIGUOUS",
                    [w.get("work_id") for w in hits], "作品号")


def _refusal(raw: str, code: str, candidates: list, detail: str) -> dict[str, Any]:
    return {
        "schema": REF_SCHEMA, "raw": raw, "kind": None,
        "judgepack": None, "work_id": None, "meta_summary": None,
        "resolution": {"status": "refused", "error_code": code,
                       "candidates": candidates, "detail": detail},
    }


class RefAudit:
    """解析审计（§6）：append-only 只增不删、成败都记、ts 注入。"""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def log(self, raw: str, outcome: dict[str, Any] | None, *, at: str) -> dict[str, Any]:
        res = (outcome or {}).get("resolution", {})
        entry: dict[str, Any] = {"ts": at, "raw": raw,
                                 "kind": (outcome or {}).get("kind")}
        if res.get("status") == "resolved":
            entry.update({"status": "resolved", "candidates": 1,
                          "resolved": {"judgepack_fingerprint":
                                       (outcome.get("judgepack") or {}).get("fingerprint"),
                                       "work_id": outcome.get("work_id"),
                                       "work_status": (outcome.get("meta_summary")
                                                       or {}).get("work_status")}})
        else:
            entry.update({"status": "refused", "candidates": res.get("candidates", []),
                          "error_code": res.get("error_code"),
                          "detail": res.get("detail")})
        self.records.append(entry)  # 只增不删
        return dict(entry)

    def resolve_logged(self, raw: str, judgepacks: list[dict[str, Any]],
                       works: list[dict[str, Any]], *, at: str) -> dict[str, Any]:
        """一步解析+留痕（语法错也记审计）。"""
        try:
            outcome = resolve(raw, judgepacks, works)
        except RefSyntaxError as exc:
            entry = {"ts": at, "raw": raw, "kind": None, "status": "refused",
                     "candidates": [], "error_code": "REF_SYNTAX_ERROR",
                     "detail": str(exc)}
            self.records.append(entry)
            return {"refused": True, "error_code": "REF_SYNTAX_ERROR",
                    "detail": str(exc), "audit": entry}
        entry = self.log(raw, outcome, at=at)
        if outcome["resolution"]["status"] == "refused":
            return {"refused": True,
                    "error_code": outcome["resolution"]["error_code"],
                    "detail": outcome["resolution"].get("detail"), "audit": entry}
        return {"refused": False, "resolution": outcome, "audit": entry}
