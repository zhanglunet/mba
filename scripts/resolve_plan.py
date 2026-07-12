#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resolve_plan.py — `/mba <brand> --dry-run` 的确定性实现:**跑前预览、不花一分钱**。

给定品牌 + flags,解析出这次 `/mba` 会怎么跑,而**不执行任何研究 / 评委 / LLM 调用**:
  · panel(解析顺序:--panel > --industry 映射 > reports/<brand>/panel.yaml 绑定 > default)
  · 评委名单 + 每位的 perspective 是否可用(perspectives/<slug>-perspective/SKILL.md)
  · 自动生效的 flag(无 WUYING_API_KEY → --quick;全部评委缺失 → --no-judges;部分缺 → judges_incomplete)
  · self-conflict 冲突评委 + 建议的 --panel-drop(复用 check_self_conflict 的关联表)
  · 会跑哪些阶段(研究 / 合成 / 评审 / 合并 / EVOLUTION|PANEL-MERGE)与大致 sub-agent 规模
  · 若 panel 文件缺失 / industry 映射到不存在的 panel → 会 ABORT(退出码 2),提前告诉你

这把 SKILL.md Phase 0 的路由/自检逻辑落成一个可复用、可测的脚本,`--dry-run` 直接调它。

用法:
  python3 scripts/resolve_plan.py <brand> [--panel P|--industry I] [--quick] [--no-judges]
                                          [--focus 1,2,7] [--refresh] [--panel-merge P2] [--json]
  python3 scripts/resolve_plan.py --selftest      # golden 断言(接 CI)

退出码:正常 0;会 ABORT(panel 缺失/industry 死映射)2;selftest 失败 1。
"""
import sys, os, re, json, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_self_conflict as sc  # 复用 panel_judges / industry_to_panel / conflicted_judges / skill_path / load_map

ROOT = sc.ROOT
REPORTS = os.path.join(ROOT, "published", "reports")
DIMENSIONS = ["origin", "product", "distribution", "community", "visual", "competition", "reception"]


def slugify(brand: str) -> str:
    """品牌 → 目录 slug 的朴素规则(仅用于探测已有报告做 EVOLUTION 提示)。"""
    s = re.sub(r"[\s_/]+", "-", brand.strip().lower())
    s = re.sub(r"[^a-z0-9-]", "", s)
    return re.sub(r"-+", "-", s).strip("-")


def _norm_name(s: str) -> str:
    return re.sub(r"[\s\-_./·’'\"()（）]+", "", str(s)).lower()


def existing_report_slug(brand: str):
    """若品牌已有报告目录,返回该 slug,否则 None。

    先按目录名/slug 匹配;再查 site/reports-meta.yaml 的 brand_cn/brand_en
    —— 这样中文品牌名(如「美团」)也能映射到英文 slug(meituan)做 EVOLUTION 探测。"""
    if not os.path.isdir(REPORTS):
        return None
    cand = {slugify(brand), brand.strip().lower(), _norm_name(brand)}
    dirs = os.listdir(REPORTS)
    for d in dirs:
        if d.lower() in cand or slugify(d) in cand:
            return d
    # reports-meta.yaml 品牌名映射(中英文)
    meta = os.path.join(ROOT, "site", "reports-meta.yaml")
    if os.path.exists(meta):
        try:
            import yaml
            bn = _norm_name(brand)
            for r in (yaml.safe_load(open(meta, encoding="utf-8")) or {}).get("reports", []):
                names = {_norm_name(r.get("brand_cn", "")), _norm_name(r.get("brand_en", "")),
                         _norm_name(r.get("card_brand", ""))}
                if bn and bn in {n for n in names if n} and r.get("slug") in dirs:
                    return r["slug"]
        except Exception:
            pass
    return None


def resolve(brand, panel=None, industry=None, quick=False, no_judges=False,
            focus=None, refresh=False, panel_merge=None, wuying=None):
    """返回解析后的计划 dict(纯读,不执行)。"""
    notes, abort = [], None

    # WUYING key:优先用显式参数(测试可控),否则读环境
    has_wuying = wuying if wuying is not None else bool(os.environ.get("WUYING_API_KEY"))

    # ── panel 解析(严格按 SKILL Phase 0 优先级)──
    brand_report = existing_report_slug(brand)
    if panel:
        panel_name, how = panel, "--panel flag"
    elif industry:
        mapped = sc.industry_to_panel(industry)
        if not mapped:
            abort = f"--industry '{industry}' 在 industries.yaml 无映射"
            panel_name, how = None, "industry(未映射)"
        else:
            panel_name, how = mapped, f"--industry {industry} → {mapped}"
    elif brand_report and os.path.exists(os.path.join(REPORTS, brand_report, "panel.yaml")):
        bp = sc.panel_judges  # noqa (only to keep import used)
        import yaml
        pdata = yaml.safe_load(open(os.path.join(REPORTS, brand_report, "panel.yaml"), encoding="utf-8")) or {}
        panel_name, how = pdata.get("panel", "default"), f"品牌绑定 reports/{brand_report}/panel.yaml"
    else:
        panel_name, how = "default", "回退 default"

    judges = sc.panel_judges(panel_name) if panel_name else None
    if panel_name and judges is None:
        abort = abort or f"panel '{panel_name}' 文件不存在(panels/{panel_name}.yaml)"

    # ── 评委可用性 ──
    avail, missing = [], []
    for j in (judges or []):
        (avail if os.path.exists(sc.skill_path(j)) else missing).append(j)

    # ── 自动 flag ──
    auto = []
    if not has_wuying and not quick:
        quick = True
        auto.append("--quick(WUYING_API_KEY 未设)")
    if judges and len(missing) == len(judges) and not no_judges:
        no_judges = True
        auto.append("--no-judges(该 panel 评委 perspective 全部缺失)")
    judges_incomplete = bool(missing) and not no_judges and len(missing) < len(judges or [])
    if judges_incomplete:
        notes.append(f"judges_incomplete:{len(avail)}/{len(judges)}(缺 {', '.join(missing)})")

    # ── self-conflict → --panel-drop ──
    drops = []
    if judges:
        for slug, hits, typ in sc.conflicted_judges(brand, sc.load_map(), restrict=set(judges)):
            drops.append({"slug": slug, "hits": hits, "type": typ})

    # ── 模式 & 阶段 ──
    if panel_merge:
        mode = "panel-merge"
    elif refresh:
        mode = "evolution" if brand_report else "fresh"
        if refresh and not brand_report:
            notes.append("--refresh 指定但无历史基线 → 退化为 FRESH")
    else:
        mode = "fresh"

    dims = [d for i, d in enumerate(DIMENSIONS, 1) if not focus or i in focus]
    effective_judges = 0 if no_judges else len(avail)
    phases = ["Phase 0 · 路由 + 自检"]
    phases.append(f"Phase 1 · 维度研究（{len(dims)} 维{' · --focus' if focus else ''}{' · --quick 仅 open-web' if quick else ''}）")
    phases.append("Phase 2 · Lead 合成简报")
    if no_judges:
        phases.append("Phase 3 · 评审 —— 跳过（--no-judges）")
    else:
        phases.append(f"Phase 3 · {effective_judges} 位评委独立打分")
    phases.append("Phase 4 · 合并 + 版本化报告")
    if mode == "evolution":
        phases.append("Phase 5E · EVOLUTION delta（对比历史基线）")
    elif mode == "panel-merge":
        phases.append(f"Phase 5M · PANEL-MERGE（加跑 {panel_merge} 面板对比）")

    sub_agents = len(dims) + effective_judges + 1  # 研究 + 评委 + 合成;合并/EVOLUTION 走主循环
    if mode == "panel-merge":
        sub_agents += len(sc.panel_judges(panel_merge) or [])

    return {
        "brand": brand, "mode": mode, "abort": abort,
        "panel": {"name": panel_name, "resolved_via": how},
        "judges": {"all": judges or [], "available": avail, "missing": missing,
                   "effective": effective_judges, "incomplete": judges_incomplete},
        "flags": {"quick": quick, "no_judges": no_judges, "focus": sorted(focus) if focus else None,
                  "refresh": refresh, "panel_merge": panel_merge, "auto_engaged": auto,
                  "has_wuying": has_wuying},
        "panel_drop": drops,
        "baseline": brand_report,
        "dimensions": dims,
        "phases": phases,
        "est_sub_agents": sub_agents,
        "notes": notes,
    }


def render(plan) -> str:
    L = []
    L.append(f"MBA --dry-run · {plan['brand']}  [{plan['mode'].upper()}]  (预览,不执行、不花 API)")
    L.append("=" * 64)
    if plan["abort"]:
        L.append(f"❌ 会 ABORT:{plan['abort']}")
        L.append("   （panel 文件缺失或 industry 死映射;补齐后再跑,见 panels/README.md）")
        return "\n".join(L)
    p = plan["panel"]
    L.append(f"panel        {p['name']}   ← {p['resolved_via']}")
    j = plan["judges"]
    avail_str = " ".join(f"✓{x}" for x in j["available"]) + " " + " ".join(f"✗{x}" for x in j["missing"])
    L.append(f"评委         {j['effective']}/{len(j['all'])} 生效   {avail_str.strip()}")
    if plan["panel_drop"]:
        for d in plan["panel_drop"]:
            L.append(f"  ⚠ self-conflict: {d['slug']}（命中 {', '.join(d['hits'])}·{d['type']}）→ 建议 --panel-drop {d['slug']}")
    else:
        L.append("  self-conflict: 无（该 panel 无评委审自家品牌）")
    f = plan["flags"]
    L.append(f"flags        quick={f['quick']} · no_judges={f['no_judges']} · focus={f['focus']} · refresh={f['refresh']} · panel_merge={f['panel_merge']}")
    if f["auto_engaged"]:
        L.append(f"  自动生效:{' · '.join(f['auto_engaged'])}")
    if plan["baseline"]:
        L.append(f"基线         reports/{plan['baseline']}/（EVOLUTION 可用）")
    L.append("")
    L.append(f"将跑 {len(plan['phases'])} 个阶段 · 约 {plan['est_sub_agents']} 个 sub-agent:")
    for ph in plan["phases"]:
        L.append(f"  · {ph}")
    for n in plan["notes"]:
        L.append(f"note  {n}")
    return "\n".join(L)


# ── golden 自测(接 CI:证明解析器不回归)──────────────────────────────────────
def selftest() -> int:
    cases = []

    def check(name, cond):
        cases.append((name, bool(cond)))

    # 1) --industry 映射 + self-conflict:猎豹 走 ai-app-cn,fusheng(猎豹创始人)应被建议 --panel-drop
    p = resolve("猎豹", industry="ai-app-cn", wuying=True)
    check("industry→ai-app-cn panel", p["panel"]["name"] == "ai-app-cn")
    check("ai-app-cn 5 评委", len(p["judges"]["all"]) == 5)
    check("猎豹→fusheng self-conflict drop", any(d["slug"] == "fusheng" for d in p["panel_drop"]))
    check("有 WUYING 不自动 --quick", p["flags"]["quick"] is False)

    # 2) --panel 显式覆盖 industry 优先级;default panel 存在
    p = resolve("SomeBrand", panel="default", wuying=True)
    check("--panel 覆盖", p["panel"]["name"] == "default" and "flag" in p["panel"]["resolved_via"])
    check("default 无 self-conflict(通用品牌)", p["panel_drop"] == [])

    # 3) 无 WUYING → 自动 --quick
    p = resolve("SomeBrand", panel="default", wuying=False)
    check("无 WUYING 自动 --quick", p["flags"]["quick"] is True and any("quick" in a for a in p["flags"]["auto_engaged"]))

    # 4) --no-judges → 评审阶段被跳过、生效评委 0
    p = resolve("SomeBrand", panel="default", no_judges=True, wuying=True)
    check("--no-judges 生效评委 0", p["judges"]["effective"] == 0)
    check("--no-judges 跳过评审阶段", any("跳过" in ph for ph in p["phases"]))

    # 5) --focus 收窄维度
    p = resolve("SomeBrand", panel="default", focus={1, 2, 7}, wuying=True)
    check("--focus 3 维", len(p["dimensions"]) == 3)

    # 6) 死映射 industry → ABORT
    p = resolve("SomeBrand", industry="__no_such_industry__", wuying=True)
    check("死 industry → abort", p["abort"] is not None)

    # 7) 不存在的 panel → ABORT
    p = resolve("SomeBrand", panel="__no_such_panel__", wuying=True)
    check("死 panel → abort", p["abort"] is not None)

    # 8) --panel-merge → panel-merge 模式 + Phase 5M
    p = resolve("SomeBrand", panel="vc-en", panel_merge="vc-cn", wuying=True)
    check("panel-merge 模式", p["mode"] == "panel-merge")
    check("Phase 5M 存在", any("5M" in ph for ph in p["phases"]))

    # 9) 中文品牌名 → 英文 slug 基线映射:美团 --refresh 应认出 meituan 历史 → EVOLUTION
    p = resolve("美团", refresh=True, wuying=True)
    check("美团→meituan 基线 → EVOLUTION", p["mode"] == "evolution" and p["baseline"] == "meituan")
    check("美团 品牌绑定 → vc-cn panel", p["panel"]["name"] == "vc-cn")

    print("resolve_plan --selftest（--dry-run golden 断言）")
    print("=" * 56)
    ok = True
    for name, passed in cases:
        print(f"  {'✅' if passed else '❌'} {name}")
        ok = ok and passed
    print("=" * 56)
    print("✅ 全部通过。" if ok else "❌ 有断言失败:解析器发生回归。")
    return 0 if ok else 1


def parse_focus(s):
    if not s:
        return None
    return {int(x) for x in re.split(r"[,\s]+", s.strip()) if x.strip().isdigit()}


def main(argv):
    ap = argparse.ArgumentParser(description="/mba --dry-run 计划解析器")
    ap.add_argument("brand", nargs="?", help="品牌名")
    ap.add_argument("--panel")
    ap.add_argument("--industry")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-judges", dest="no_judges", action="store_true")
    ap.add_argument("--focus")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--panel-merge", dest="panel_merge")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()
    if not a.brand:
        ap.error("需要 <brand>(或 --selftest)")

    plan = resolve(a.brand, panel=a.panel, industry=a.industry, quick=a.quick,
                   no_judges=a.no_judges, focus=parse_focus(a.focus), refresh=a.refresh,
                   panel_merge=a.panel_merge)
    print(json.dumps(plan, ensure_ascii=False, indent=2) if a.json else render(plan))
    return 2 if plan["abort"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
