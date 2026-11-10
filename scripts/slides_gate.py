# -*- coding: utf-8 -*-
"""PRD-338/T3（trend issue #1617 的 T3 环节）：幻灯片逐页对应闸门。

按 T1 设计（docs/plans/2026-11-09-prd-338-slides-design.md）§4/R1/R2/R3 落地，
消费 T2 slides 转换内核（复用不绕行）：

  - ERROR_CODES 词表封闭（§4 三码）：CONCLUSION_INCOMPLETE /
    SLIDES_PAGE_MISMATCH / EXTERNAL_REF_FOUND；
  - conversion_gate(conclusions, *, batch_name, batch_date)：转换闸门单一
    入口——T2 内核（页结构→渲染→回读自检）跑通才 allow 并携带产物；异常按
    三码映射显形拒绝（缺条目→CONCLUSION_INCOMPLETE；自检失败先探测外链
    归 EXTERNAL_REF_FOUND 否则 SLIDES_PAGE_MISMATCH），拒绝零产物（不产出
    半成品文件）；
  - verify_gate(conclusions, html_text)：双机判之二独立复核——从结论记录
    直接重算页对应（封面 1+作品 N+汇总 1/<h2> 数=作品数）逐条比对；评语/
    分数逐字经转义在页面在位（R2 零改写复核）；外链/script/src= 探测
    （EXTERNAL_REF_FOUND 归因）。

零网络；示例全虚构占位。
测试：tests/unit/test_prd338_t3_slides_gate.py
"""
from __future__ import annotations

import html as _html
from typing import Any

from slides import (
    ConclusionIncomplete,
    SlidesMismatch,
    render_slides,
    slides_from_conclusions,
)

GATE_SCHEMA = "slides-gate/v1"
ERROR_CODES = ("CONCLUSION_INCOMPLETE", "SLIDES_PAGE_MISMATCH",
               "EXTERNAL_REF_FOUND")


def _external_probe(html_text: str) -> bool:
    """外链资源探测（R3）：http(s) 外链 / script / src= 任一命中即真。"""
    tokens = ("http://", "https://", "<script", "src=", "url(")
    return any(t in html_text for t in tokens)


def conversion_gate(conclusions: list[dict[str, Any]], *,
                    batch_name: str = "评审批次（占位）",
                    batch_date: str = "2026-11-09（占位）") -> dict[str, Any]:
    """转换闸门（§4）：T2 内核跑通才 allow；三码映射显形拒绝零产物。"""
    html_text = ""
    try:
        pages_doc = slides_from_conclusions(
            conclusions, batch_name=batch_name, batch_date=batch_date)
        html_text = render_slides(pages_doc["pages"])
        from slides import self_check
        self_check(pages_doc["pages"], html_text)
    except ConclusionIncomplete as exc:
        return {"schema": GATE_SCHEMA, "gate": "reject",
                "error_code": "CONCLUSION_INCOMPLETE", "detail": str(exc),
                "artifact": None,
                "note": "结论记录缺作品/缺评委条目——显形拒绝转换（不硬凑）"}
    except SlidesMismatch as exc:
        code = ("EXTERNAL_REF_FOUND" if _external_probe(str(exc))
                or _external_probe(html_text) else "SLIDES_PAGE_MISMATCH")
        return {"schema": GATE_SCHEMA, "gate": "reject", "error_code": code,
                "detail": str(exc), "artifact": None,
                "note": "回读自检断裂/外链注入——不产出半成品文件（§4）"}
    return {"schema": GATE_SCHEMA, "gate": "allow", "error_code": None,
            "detail": "", "artifact": html_text,
            "pages": len(pages_doc["pages"]),
            "note": "转换过闸——逐页对应/零改写/零外链三查全过"}


def verify_gate(conclusions: list[dict[str, Any]],
                html_text: str) -> dict[str, Any]:
    """双机判之二独立复核：从结论记录直接重算，不复用转换中间态。"""
    checks: list[dict[str, Any]] = []
    work_pages = [c for c in conclusions]
    h2 = html_text.count("<h2>")
    checks.append({"check": "page_mapping", "ok": h2 == len(work_pages),
                   "detail": f"<h2> {h2} vs 作品 {len(work_pages)}"})
    missing = []
    for c in conclusions:
        for ev in c["evaluations"]:
            for field in ("comment", "score"):
                needle = _html.escape(str(ev[field]))
                if needle not in html_text:
                    missing.append(f"{c['work_id']}:{ev['evaluator']}:{field}")
    checks.append({"check": "verbatim_r2", "ok": not missing,
                   "detail": "评语/分数逐字在位" if not missing
                   else f"逐字缺失：{missing}"})
    ext = _external_probe(html_text)
    checks.append({"check": "no_external_r3", "ok": not ext,
                   "detail": "零外链零脚本（离线可用）" if not ext
                   else "检出外链资源——EXTERNAL_REF_FOUND"})
    ok = all(c["ok"] for c in checks)
    return {"schema": GATE_SCHEMA, "gate": "allow" if ok else "reject",
            "error_code": None if ok else
            ("EXTERNAL_REF_FOUND" if ext else "SLIDES_PAGE_MISMATCH"),
            "checks": checks}
