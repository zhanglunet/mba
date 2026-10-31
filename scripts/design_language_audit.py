#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-205/T4（trend #1028）：确定性检查自动化——可机检项先机检。

按 PRD-205/T1 设计 §五（docs/plans/2026-10-26-design-language-spec.md）实现 T4 范围：
  输入设计语言文件 + 待检产物文件列表，按 `checks` 登记分类逐条判定：
  - machine：对产物做确定性抽取与比对（T1 §5.1 css-value-set 类方法的 JSON 子集实现）；
  - manual：输出 skip-manual，不冒充通过（人工项留给评委，T1 §2.4）。
  输出机检报告（findings 数组 + 供评委跳过/人工两清单，衔接 T3 评委接入）。
  退出码：存在任一 fail → 非 0；只有 note/pass/skip-manual → 0（T1 §5.2）。
  fail-closed：checks 登记未知方法 / 登记编号不在 rules / 条目缺 checks 登记 /
  机检器未实现该条目判定器 → 记入 errors，ok=False。
  边界（一期从简，超界不猜）：色彩仅查 16 进制字面量（rgb()/命名色不查）；
  间距/字号仅查 px 值（0 允许；auto/%/em/calc 不查）；动效仅查时长（0 视为禁用不查）；
  CSS 选择器 #id 与色值同形时因只查 color 系属性取值而不受影响。
  另含 T1 §5.3 mirror-set 检查（镜像文件存在时编号集合必须一致；缺失仅登记不判失败）。
  复用 T2 加载器读文件；纯 stdlib，零网络；示例全虚构。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from design_language_loader import load_design_language

_REPO = Path(__file__).resolve().parents[1]
DEFAULT_DL_PATH = _REPO / "design" / "design-language.json"
DEFAULT_MIRROR_PATH = _REPO / "design" / "DESIGN-LANGUAGE.md"

# T1 §5.1：解析产物 HTML/CSS（含 <style> 与内联样式）
_STYLE_BLOCK_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
_STYLE_ATTR_RE = re.compile(r'style\s*=\s*"([^"]*)"')
_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_DECL_RE = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;{}\"']+)")
_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_PX_RE = re.compile(r"(-?\d+(?:\.\d+)?)px\b")
_TIME_RE = re.compile(r"(\d+(?:\.\d+)?)(ms|s)\b")

# 色值承载属性（只查属性取值，避免选择器 #id 同形误报）
_COLOR_PROPS = {"background", "border", "box-shadow", "outline", "fill", "stroke", "text-shadow"}


def _is_color_prop(prop: str) -> bool:
    return "color" in prop or prop in _COLOR_PROPS


def _is_space_prop(prop: str) -> bool:
    return prop in ("padding", "margin") or prop.startswith("padding-") or prop.startswith("margin-")


def _is_motion_prop(prop: str) -> bool:
    return prop in ("transition", "animation") or prop.startswith("transition-") or prop.startswith("animation-")


def style_fragments(text: str) -> str:
    """抽取产物中全部样式片段：<style> 块 + 内联 style 属性（去注释）。"""
    parts = [m.group(1) for m in _STYLE_BLOCK_RE.finditer(text)]
    parts += [m.group(1) for m in _STYLE_ATTR_RE.finditer(text)]
    return _COMMENT_RE.sub(" ", "\n".join(parts))


def declarations(style_text: str) -> list[tuple[str, str]]:
    """样式片段 → [(属性名, 值)]（小写属性名）。"""
    out: list[tuple[str, str]] = []
    for m in _DECL_RE.finditer(style_text):
        prop = m.group(1).strip().lower()
        value = m.group(2).strip()
        if prop and value:
            out.append((prop, value))
    return out


def _token_set(dl: dict[str, Any], group: str) -> list[float]:
    tokens = dl.get("tokens", {}).get(group, {})
    values: list[float] = []
    if isinstance(tokens, dict):
        for v in tokens.values():
            if isinstance(v, str):
                m = _PX_RE.search(v)
                if m:
                    values.append(float(m.group(1)))
                elif group == "motion":
                    t = _TIME_RE.search(v)
                    if t:
                        values.append(float(t.group(1)) * (1 if t.group(2) == "ms" else 1000))
    return values


def _hex_set(dl: dict[str, Any]) -> set[str]:
    tokens = dl.get("tokens", {}).get("color", {})
    if not isinstance(tokens, dict):
        return set()
    return {v.strip().lower() for v in tokens.values() if isinstance(v, str) and v.strip().startswith("#")}


def _evidence(prop: str, value: str, expect: str) -> str:
    return f"声明 {prop}: {value}（登记集合外）｜期望 {expect}"


def _check_colors(dl: dict[str, Any], decls: list[tuple[str, str]], decl_count: list[int]) -> list[str]:
    """DL-C01：品牌色取值必须来自 tokens.color 登记集合（css-value-set）。"""
    allowed = _hex_set(dl)
    expect = "tokens.color 登记集合 " + " ".join(sorted(allowed))
    hits = []
    for prop, value in decls:
        if not _is_color_prop(prop):
            continue
        decl_count[0] += 1
        for hx in _HEX_RE.findall(value):
            if hx.lower() not in allowed:
                hits.append(_evidence(prop, hx, expect))
    return hits


def _check_font_size(dl: dict[str, Any], decls: list[tuple[str, str]], decl_count: list[int]) -> list[str]:
    """DL-T01：font-size 必须来自 tokens.size 字号阶梯（css-value-set）。"""
    allowed = set(_token_set(dl, "size"))
    expect = "tokens.size 字号阶梯 " + "/".join(f"{int(v)}px" for v in sorted(allowed))
    hits = []
    for prop, value in decls:
        if prop != "font-size":
            continue
        decl_count[0] += 1
        for px in _PX_RE.findall(value):
            if float(px) not in allowed:
                hits.append(_evidence(prop, f"{px}px", expect))
    return hits


def _check_spacing(dl: dict[str, Any], decls: list[tuple[str, str]], decl_count: list[int]) -> list[str]:
    """DL-S01：padding/margin 必须来自 tokens.spacing 间距档（0 允许）。"""
    allowed = set(_token_set(dl, "spacing"))
    expect = "tokens.spacing 间距档 " + "/".join(f"{int(v)}px" for v in sorted(allowed)) + "（0 允许）"
    hits = []
    for prop, value in decls:
        if not _is_space_prop(prop):
            continue
        decl_count[0] += 1
        for px in _PX_RE.findall(value):
            if float(px) != 0.0 and float(px) not in allowed:
                hits.append(_evidence(prop, f"{px}px", expect))
    return hits


def _check_motion(dl: dict[str, Any], decls: list[tuple[str, str]], decl_count: list[int]) -> list[str]:
    """DL-M01：动效时长必须来自 tokens.motion 预设档（0 视为禁用，允许）。"""
    allowed = set(_token_set(dl, "motion"))
    expect = "tokens.motion 时长档 " + "/".join(f"{int(v)}ms" for v in sorted(allowed))
    hits = []
    for prop, value in decls:
        if not _is_motion_prop(prop):
            continue
        decl_count[0] += 1
        for num, unit in _TIME_RE.findall(value):
            ms = float(num) * (1 if unit == "ms" else 1000)
            if ms == 0.0:
                continue
            if ms not in allowed:
                hits.append(_evidence(prop, f"{num}{unit}", expect))
    return hits


# 机检判定器登记：条目编号 → 判定函数（未登记的 machine 条目 fail-closed）
CHECKERS = {
    "DL-C01": _check_colors,
    "DL-T01": _check_font_size,
    "DL-S01": _check_spacing,
    "DL-M01": _check_motion,
}


def build_registry(dl: dict[str, Any]) -> dict[str, Any]:
    """按 checks 登记把条目分为 machine / manual 两桶；登记异常 fail-closed 进 errors。"""
    checks = dl.get("checks") or {}
    rules = {r.get("id"): r for r in dl.get("rules", []) if isinstance(r, dict)}
    errors: list[str] = []
    machine: dict[str, dict[str, Any]] = {}
    manual: dict[str, dict[str, Any]] = {}
    for rid, method in checks.items():
        rule = rules.get(rid)
        if rule is None:
            errors.append(f"checks 登记的条目编号不存在: {rid}（fail-closed）")
            continue
        if method == "machine":
            machine[rid] = rule
        elif method == "manual":
            manual[rid] = rule
        else:
            errors.append(f"checks 登记未知判定方法: {rid} -> {method}（fail-closed）")
    for rid in rules:
        if rid not in checks:
            errors.append(f"条目缺少 checks 登记（机检器不猜测机检/人工）: {rid}（fail-closed）")
    return {"machine": machine, "manual": manual, "errors": errors}


def mirror_set_check(dl: dict[str, Any], mirror_path: str | Path | None) -> dict[str, Any]:
    """T1 §5.3 mirror-set：人读镜像与 YAML/JSON 的条目编号集合必须完全一致。

    镜像缺失 → status=absent（镜像未落地，登记不判失败）；存在但不一致 → mismatch（判失败）。
    """
    if mirror_path is None or not Path(mirror_path).exists():
        return {"path": str(mirror_path) if mirror_path else None, "status": "absent", "ok": True,
                "missing": [], "extra": [], "note": "人读镜像未落地，落地后本检查强制一致"}
    text = Path(mirror_path).read_text(encoding="utf-8")
    ids = set(re.findall(r"\bDL-[A-Z]\d{2}\b", text))
    rule_ids = {r["id"] for r in dl.get("rules", []) if isinstance(r, dict)}
    missing = sorted(rule_ids - ids)
    extra = sorted(ids - rule_ids)
    ok = not missing and not extra
    return {"path": str(mirror_path), "status": "ok" if ok else "mismatch", "ok": ok,
            "missing": missing, "extra": extra, "note": ""}


def audit(dl: dict[str, Any], files: list[str | Path],
          mirror_path: str | Path | None = None) -> dict[str, Any]:
    """机检主流程：逐条目按 checks 分类判定，返回机检报告（T1 §5.2 接口）。"""
    reg = build_registry(dl)
    texts: list[tuple[str, list[tuple[str, str]]]] = []
    for f in files:
        path = Path(f)
        if not path.exists():
            reg["errors"].append(f"待检产物文件不存在: {path}")
            continue
        texts.append((str(path), declarations(style_fragments(path.read_text(encoding="utf-8")))))

    findings: list[dict[str, Any]] = []
    for rid, rule in reg["machine"].items():
        checker = CHECKERS.get(rid)
        if checker is None:
            reg["errors"].append(f"机检器未实现该条目判定器（fail-closed，不冒充通过）: {rid}")
            continue
        level = rule.get("severity", "hard")
        verdict_on_hit = "fail" if level == "hard" else "note"
        any_hit = False
        for fname, decls in texts:
            counter = [0]
            hits = checker(dl, decls, counter)
            if hits:
                any_hit = True
                findings.append({
                    "rule": rid, "level": level, "verdict": verdict_on_hit, "file": fname,
                    "evidence": "；".join(hits),
                })
        if not any_hit:
            checked = sum(len(decls) for _, decls in texts)
            findings.append({
                "rule": rid, "level": level, "verdict": "pass", "file": None,
                "evidence": f"已检 {checked} 处样式声明，全部落在登记集合",
            })

    for rid, rule in reg["manual"].items():
        findings.append({
            "rule": rid, "level": rule.get("severity", "hard"), "verdict": "skip-manual",
            "file": None, "evidence": "人工项（T1 §5.1 manual），机检不冒充通过，留给评委",
        })

    mirror = mirror_set_check(dl, mirror_path)
    errors = list(reg["errors"])
    if not mirror["ok"]:
        errors.append(
            f"mirror-set 不一致：镜像缺编号 {mirror['missing']}，镜像多出编号 {mirror['extra']}"
        )

    counts = {
        "fail": sum(1 for x in findings if x["verdict"] == "fail"),
        "note": sum(1 for x in findings if x["verdict"] == "note"),
        "pass": sum(1 for x in findings if x["verdict"] == "pass"),
        "skip_manual": sum(1 for x in findings if x["verdict"] == "skip-manual"),
    }
    # 衔接 T3 评委：已过项评委可跳过；人工项必须评委判断
    judge = {
        "skip": sorted(x["rule"] for x in findings if x["verdict"] == "pass"),
        "manual": sorted(x["rule"] for x in findings if x["verdict"] == "skip-manual"),
    }
    return {
        "dl_version": dl.get("meta", {}).get("version"),
        "files": [str(f) for f in files],
        "findings": findings,
        "counts": counts,
        "judge": judge,
        "mirror": mirror,
        "errors": errors,
        "ok": counts["fail"] == 0 and not errors,
    }


def exit_code(report: dict[str, Any]) -> int:
    """T1 §5.2 退出码约定：存在任一 fail（或 fail-closed 错误）→ 1；只有 note/pass → 0。"""
    return 0 if report["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PRD-205/T4 设计语言确定性机检（可机检项先机检）")
    parser.add_argument("files", nargs="+", help="待检产物文件（HTML/CSS）")
    parser.add_argument("--dl", default=str(DEFAULT_DL_PATH), help="设计语言文件路径")
    parser.add_argument("--mirror", default=str(DEFAULT_MIRROR_PATH), help="人读镜像路径（缺失则登记 absent）")
    args = parser.parse_args(argv)
    dl = load_design_language(Path(args.dl))
    report = audit(dl, args.files, mirror_path=args.mirror)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
