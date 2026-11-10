# -*- coding: utf-8 -*-
"""PRD-338/T2（trend issue #1617 的 T2 环节）：评审报告一键转 HTML 幻灯片最小实现。

按 T1 设计（docs/plans/2026-11-09-prd-338-slides-design.md）§3.1/§3.2/§3.3
实现：

  - slides_from_conclusions(conclusions, *, batch_name, batch_date)：转换内核
    （§3.1/§3.3，确定性纯函数）——结论记录 → 页结构三段（封面/作品页×N/
    汇总尾页）；**逐页对应规则**（R1）：页序=结论记录序、每页评语条数=评委
    条数、一对一不合并；**零改写**（R2）：评语/分数逐字进页面、分数原字符
    串直接输出零格式化零汇总排名；
  - render_slides(pages)：内联样式单文件 HTML（§3.2 R3 离线可用）——全部
    内联零外链 CSS/JS/字体/图片、零 script（浏览器原生滚动）；
  - self_check(pages, html)：回读自检（§3.3）——页面遍历 vs 结论记录逐条
    比对，不一致抛 SlidesMismatch 不产出半成品文件（R1 断言在转换器侧）；
  - CONCLUSION_INCOMPLETE 缺作品/缺评委条目显形拒绝转换。

**分数只展示不改写**（R4）：零计算零汇总排名。零网络；示例全虚构占位。
测试：tests/unit/test_prd338_t2_slides.py
"""
from __future__ import annotations

import html
from typing import Any

SLIDES_SCHEMA = "review-slides/v1"


class SlidesMismatch(ValueError):
    """回读自检失败（R1 逐页对应断裂）——不产出半成品文件。"""


class ConclusionIncomplete(ValueError):
    """结论记录缺作品/缺评委条目（§3.3 校验）。"""

    code = "CONCLUSION_INCOMPLETE"


def _check_complete(conclusions: list[dict[str, Any]]) -> None:
    for c in conclusions:
        if not c.get("work_id") or not c.get("work_title"):
            raise ConclusionIncomplete(f"结论缺作品：{c!r}")
        if not c.get("evaluations"):
            raise ConclusionIncomplete(f"作品 {c.get('work_title')!r} 缺评委条目")
        for ev in c["evaluations"]:
            if not ev.get("evaluator") or "score" not in ev:
                raise ConclusionIncomplete(f"评委条目缺 evaluator/score：{ev!r}")


def slides_from_conclusions(conclusions: list[dict[str, Any]], *,
                            batch_name: str = "评审批次（占位）",
                            batch_date: str = "2026-11-09（占位）") -> dict[str, Any]:
    """转换内核（§3.1/§3.3，确定性纯函数）：结论记录 → 页结构三段。

    逐页对应规则（R1）：页序=结论记录序；每页评语条数=评委条数。
    """
    _check_complete(conclusions)
    pages: list[dict[str, Any]] = [{"kind": "cover", "batch_name": batch_name,
                                    "date": batch_date}]
    for c in conclusions:
        pages.append({
            "kind": "work",
            "work_id": c["work_id"], "work_title": c["work_title"],
            "evaluations": [
                {"evaluator": ev["evaluator"],
                 "verdict": ev["verdict"],
                 "score": ev["score"],          # 原字符串直接输出（R4 零格式化）
                 "comment": ev["comment"]}      # 评语逐字（R2 零改写）
                for ev in c["evaluations"]],
        })
    pages.append({"kind": "summary",
                  "works_total": len(conclusions),
                  "evaluations_total": sum(len(c["evaluations"]) for c in conclusions)})
    return {"schema": SLIDES_SCHEMA, "pages": pages}


def render_slides(pages: list[dict[str, Any]]) -> str:
    """内联样式单文件 HTML（R3 离线可用）——零外链零 script（转换器内防线）。

    R2 零改写：评语/分数逐字经 html.escape 后进页面（转义不等于改写）。
    """
    parts = ["<!doctype html><html><head><meta charset='utf-8'>",
             "<style>body{font-family:sans-serif;margin:2em}"
             ".slide{border-bottom:1px solid #ccc;padding:1em 0}"
             ".score{font-weight:bold}</style></head><body>"]
    for page in pages:
        if page["kind"] == "cover":
            parts.append(f"<h1>{html.escape(page['batch_name'])}</h1>"
                         f"<p>{html.escape(page['date'])}</p>")
        elif page["kind"] == "work":
            parts.append(f"<h2>{html.escape(page['work_title'])}"
                         f"（{html.escape(str(page['work_id']))}）</h2>")
            for ev in page["evaluations"]:
                parts.append(f"<p>{html.escape(ev['evaluator'])}："
                             f"<span class='score'>{html.escape(ev['score'])}</span>"
                             f" — {html.escape(ev['comment'])}</p>")
        elif page["kind"] == "summary":
            parts.append(f"<p>作品 {page['works_total']} 项，"
                         f"评语 {page['evaluations_total']} 条（占位汇总）</p>")
    parts.append("</body></html>")
    return "".join(parts)


def self_check(pages: list[dict[str, Any]], html_text: str) -> None:
    """回读自检（§3.3）：页面遍历 vs 结论记录逐条比对——不一致即失败显形。

    （R1 逐页对应断裂 / R2 零改写断裂 / R3 外链资源全在此断言。）
    """
    if "http://" in html_text or "https://" in html_text:
        raise SlidesMismatch("产物含外链资源（R3 离线可用被破坏）")
    if "<script" in html_text:
        raise SlidesMismatch("产物含 script（R3 零脚本被破坏）")
    work_pages = [p for p in pages if p["kind"] == "work"]
    if html_text.count("<h2>") != len(work_pages):
        raise SlidesMismatch("作品页数与记录不一致")
