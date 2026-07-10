#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_self_conflict.py — self-conflict 静态拦截(打分可信度护栏)

两个模式:

  validate(默认,CI gate):
    - 每套 perspective 的 SKILL.md「Self-Conflict Rule」区必须写了 `--panel-drop <own-slug>`
      (处理换行:把 SKILL 全文空白折叠后匹配)。
    - metric-brand-auditor/self-conflict.yaml 里每个 slug 必须是真实 perspective。
    - (软警告)self-conflict.yaml 里的评委若不在任何 panel 中,仅提示。
    退出码:有硬失败 → 1;否则 0。

  query(拦截用):
    check_self_conflict.py --brand "<name>" [--panel <name> | --industry <name>]
    → 列出该(panel/industry/全部)里与被审品牌强关联的评委 + 建议的 --panel-drop flags。
    命中冲突 → 退出码 2(便于脚本判断);无冲突 → 0。

  smoke(自测):check_self_conflict.py --smoke
"""
import sys, os, re, glob, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MBA = os.path.join(ROOT, "metric-brand-auditor")
PANELS = os.path.join(MBA, "panels")
SC_YAML = os.path.join(MBA, "self-conflict.yaml")

def _yaml():
    import yaml
    return yaml

def load_map():
    y = _yaml()
    with open(SC_YAML, encoding="utf-8") as f:
        data = y.safe_load(f) or {}
    return data.get("judges", {}) or {}

def all_perspectives():
    return sorted(
        os.path.basename(d).replace("-perspective", "")
        for d in glob.glob(os.path.join(ROOT, "perspectives", "*-perspective"))
    )

def skill_path(slug):
    return os.path.join(ROOT, "perspectives", f"{slug}-perspective", "SKILL.md")

def panel_judges(panel_name):
    y = _yaml()
    p = os.path.join(PANELS, f"{panel_name}.yaml")
    if not os.path.exists(p):
        return None
    data = y.safe_load(open(p, encoding="utf-8")) or {}
    return [j.get("slug") for j in data.get("judges", []) if j.get("slug")]

def industry_to_panel(industry):
    y = _yaml()
    p = os.path.join(PANELS, "industries.yaml")
    if not os.path.exists(p):
        return None
    data = y.safe_load(open(p, encoding="utf-8")) or {}
    m = data.get("industries", data)  # tolerate either top-level or nested
    if isinstance(m, dict):
        v = m.get(industry)
        if isinstance(v, dict):
            return v.get("panel")
        return v
    return None

# ── matching ────────────────────────────────────────────────────────────────
def norm(s):
    return re.sub(r"[\s\-_.·’'\"()（）]+", "", str(s)).lower()

def _has_cjk(s):
    return any("一" <= ch <= "鿿" for ch in s)

def orgs_hit(brand, orgs):
    b = norm(brand)
    hits = []
    for org in orgs:
        a = norm(org)
        if not a:
            continue
        # 子串匹配门槛:纯 ASCII 需 ≥3 字符(避免 X / YC / 360 误拦 Xiaomi 等);
        # 含 CJK 的别名 ≥2 字即可(华为 / 苹果 / 小米 等中文品牌名信息密度高,
        # 2 字已足够唯一,若也要 ≥3 则几乎所有中文品牌都拦不到)。
        allow_substr = len(a) >= 3 or (_has_cjk(a) and len(a) >= 2)
        if allow_substr:
            if a in b or b in a:
                hits.append(org)
        else:  # 1-2 字符纯 ASCII 别名(X / YC / 360…)只做精确整体匹配
            if a == b:
                hits.append(org)
    return hits

def conflicted_judges(brand, judges_map, restrict=None):
    out = []
    for slug, meta in judges_map.items():
        if restrict is not None and slug not in restrict:
            continue
        hits = orgs_hit(brand, (meta or {}).get("orgs", []))
        if hits:
            out.append((slug, hits, (meta or {}).get("type", "")))
    return out

# ── validate ────────────────────────────────────────────────────────────────
def cmd_validate():
    jmap = load_map()
    persps = set(all_perspectives())
    hard = 0

    # 1) every SKILL Self-Conflict Rule names --panel-drop <own-slug>
    missing = []
    for slug in sorted(persps):
        txt = open(skill_path(slug), encoding="utf-8").read()
        flat = re.sub(r"\s+", " ", txt)  # 折叠换行,兼容 `--panel-drop\npthiel`
        if f"--panel-drop {slug}" not in flat:
            missing.append(slug)
    if missing:
        hard += 1
        print(f"FAIL  {len(missing)} SKILL(s) 的 Self-Conflict Rule 未写 `--panel-drop <own-slug>`:")
        for s in missing:
            print(f"        ✗ {s}")
    else:
        print(f"OK    全 {len(persps)} 套 SKILL 的 Self-Conflict Rule 都写了 --panel-drop <own-slug>")

    # 2) every yaml slug is a real perspective
    bad = [s for s in jmap if s not in persps]
    if bad:
        hard += 1
        print(f"FAIL  self-conflict.yaml 有 {len(bad)} 个未知 slug: {bad}")
    else:
        print(f"OK    self-conflict.yaml {len(jmap)} 个 slug 全部是真实 perspective")

    # 3) every yaml entry has non-empty orgs
    empty = [s for s, m in jmap.items() if not (m or {}).get("orgs")]
    if empty:
        hard += 1
        print(f"FAIL  self-conflict.yaml 有空 orgs: {empty}")

    # 4) soft: yaml judge not in any panel
    all_panel_slugs = set()
    for pf in glob.glob(os.path.join(PANELS, "*.yaml")):
        if os.path.basename(pf) == "industries.yaml":
            continue
        js = panel_judges(os.path.basename(pf).replace(".yaml", ""))
        if js:
            all_panel_slugs.update(js)
    orphan = [s for s in jmap if s not in all_panel_slugs]
    if orphan:
        print(f"note  {len(orphan)} 个 self-conflict 评委不在任何 panel(仅提示): {sorted(orphan)}")

    print("=" * 56)
    if hard:
        print(f"❌ self-conflict validate 失败({hard} 类硬错误)。")
        return 1
    print(f"✅ self-conflict validate 通过(43 套 panel-drop 完整 · 关联表 {len(jmap)} 评委)。")
    return 0

# ── query ───────────────────────────────────────────────────────────────────
def cmd_query(brand, panel=None, industry=None):
    jmap = load_map()
    restrict = None
    scope = "全部评委"
    if industry:
        panel = industry_to_panel(industry) or panel
        if not panel:
            print(f"industry '{industry}' 未映射到任何 panel。"); return 1
        scope = f"industry {industry} → panel {panel}"
    if panel:
        js = panel_judges(panel)
        if js is None:
            print(f"panel '{panel}' 不存在。"); return 1
        restrict = set(js)
        if not industry:
            scope = f"panel {panel}"

    hits = conflicted_judges(brand, jmap, restrict)
    print(f"审计品牌: {brand}   范围: {scope}")
    if not hits:
        print("✅ 无 self-conflict —— 该范围内没有评委与此品牌强关联。")
        return 0
    print(f"⚠️  {len(hits)} 位评委与「{brand}」强关联(评自家/强关联品牌,分数不中立):")
    for slug, matched, typ in hits:
        print(f"   • {slug:14s} [{typ}]  命中: {', '.join(matched)}")
    drops = " ".join(f"--panel-drop {s}" for s, _, _ in hits)
    print(f"\n建议: MBA 跑分时加  {drops}")
    print("   (或保留但让 MBA Lead 在 Phase 5 置 quality_flag: judge_self_conflict:<slug>)")
    return 2

def cmd_smoke():
    jmap = load_map()
    cases = [
        ("小米 SU7", "auto", ["leijun"]),
        ("华为 Mate", None, ["renzhengfei"]),
        ("拼多多", "cross-border", ["huangzheng"]),
        ("LVMH 旗下 Dior", "luxury-en", ["arnault", "burton"]),  # burton=Givenchy(LVMH), arnault=LVMH
        ("农夫山泉", "consumer-cn", ["zhongshanshan"]),
        ("一个完全无关的新品牌XYZ", None, []),
    ]
    ok = True
    for brand, panel, expect in cases:
        restrict = set(panel_judges(panel)) if panel else None
        got = sorted(s for s, _, _ in conflicted_judges(brand, jmap, restrict))
        exp = sorted(expect)
        # 允许命中是期望的超集(如 LVMH 命中 arnault+burton;子集判定)
        good = set(exp).issubset(set(got)) and (got == [] if exp == [] else True)
        print(f"[{'PASS' if good else 'FAIL'}] brand={brand!r} panel={panel} → {got} (expect ⊇ {exp})")
        ok = ok and good
    print("=" * 40)
    print("✅ smoke 全过" if ok else "❌ smoke 有失败")
    return 0 if ok else 1

def main(argv):
    ap = argparse.ArgumentParser(description="MBA self-conflict 静态拦截")
    ap.add_argument("--brand", help="被审品牌名(query 模式)")
    ap.add_argument("--panel", help="限定某 panel")
    ap.add_argument("--industry", help="限定某 industry(经 industries.yaml 映射)")
    ap.add_argument("--smoke", action="store_true", help="跑自测用例")
    args = ap.parse_args(argv)

    if args.smoke:
        return cmd_smoke()
    if args.brand:
        return cmd_query(args.brand, args.panel, args.industry)
    return cmd_validate()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
