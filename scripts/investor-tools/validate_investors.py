#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_investors.py — 投资人维度(investors/<slug>.yaml)数据静态硬 gate。

**为什么要单开一个维度**(而不是塞进 founders):`founders/` 是**按品牌建索引**的 ——
校验器强制 `brand ∈ site/published-reports.txt` 且文件名 == brand。投资人不隶属某个被审品牌
(徐新投过京东/网易/美团,但她不是任何一家的创始人),硬塞就得伪造一个 brand,那是造假。
故 **investors 按人建索引**(文件名 == slug == 对应 perspective 的 slug)。

守三件事(与 validate_founders 同哲学):
  A. 结构底线:investor(name_cn/role/status)+ 至少 1 条 career;每条 career 必须有非空
     period/milestone/**evidence**(反捏造:履历里程碑必须带 provenance);portfolio(可选)
     每条必须有 brand + **evidence**。
  B. 判断/事实字段合法:status 枚举合法;career[].lens 与 relation 的 key ⊆ 5 镜头;
     relation 每个值必须以「分析:」开头(反捏造:关系是标注分析,不冒充本人原话);
     perspective_slug(非空时)必须存在对应 perspectives/<slug>-perspective/SKILL.md。
  C. 唯一性:文件名 slug == 顶层 slug 字段;slug 全局唯一;**且不得与 founders/ 的品牌 slug 撞名**
     (晚餐用 slug 找参与者,撞名会让它指错人)。

用法:
  python3 scripts/investor-tools/validate_investors.py             # 校验全部投资人数据
  python3 scripts/investor-tools/validate_investors.py --selftest  # 自测:证明每类违规都会被抓
退出码:有违规 → 1;否则 0。investors/ 不存在或无文件时通过(功能未启用不算错)。
"""
import glob
import os
import sys

try:
    import yaml
except ImportError:
    print("validate_investors: 需要 PyYAML(pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INVESTORS_DIR = os.path.join(ROOT, "investors")
FOUNDERS_DIR = os.path.join(ROOT, "founders")
PERSPECTIVES = os.path.join(ROOT, "perspectives")

LENSES = {"origin", "category", "leverage", "identity", "signal"}
STATUSES = {"现任", "已离任", "已退休", "已故"}
# 同 founders:relation 是**标注分析**(非本人原话),必须以「分析:」开头(半/全角冒号均可)。
RELATION_MARKERS = ("分析:", "分析：")


def _nonempty(v):
    return isinstance(v, str) and v.strip() != ""


def validate_one(path, data, seen_slugs, founder_slugs):
    errs = []
    stem = os.path.splitext(os.path.basename(path))[0]
    ctx = f"investors/{stem}.yaml"

    if not isinstance(data, dict):
        return [f"{ctx}: 顶层不是 mapping"]

    # ── C. 唯一性 / 命名 ────────────────────────────────────────────────
    slug = data.get("slug")
    if not _nonempty(slug):
        errs.append(f"{ctx}: 缺 slug")
    elif slug != stem:
        errs.append(f"{ctx}: slug `{slug}` 与文件名 `{stem}` 不一致")
    else:
        if slug in seen_slugs:
            errs.append(f"{ctx}: slug `{slug}` 重复")
        seen_slugs.add(slug)
        if slug in founder_slugs:
            errs.append(f"{ctx}: slug `{slug}` 与 founders/ 的品牌撞名 —— "
                        f"晚餐按 slug 找参与者,撞名会指错人")

    # ── A. 结构底线 ────────────────────────────────────────────────────
    inv = data.get("investor")
    if not isinstance(inv, dict):
        errs.append(f"{ctx}: 缺 investor 段")
    else:
        for k in ("name_cn", "role", "status"):
            if not _nonempty(inv.get(k)):
                errs.append(f"{ctx}: investor.{k} 缺失或为空")
        st = inv.get("status")
        if _nonempty(st) and st not in STATUSES:
            errs.append(f"{ctx}: investor.status `{st}` 非法({'/'.join(sorted(STATUSES))})")

    career = data.get("career")
    if not isinstance(career, list) or not career:
        errs.append(f"{ctx}: career 必须是非空列表(至少 1 条履历)")
    else:
        for i, c in enumerate(career):
            cc = f"{ctx} career[{i}]"
            if not isinstance(c, dict):
                errs.append(f"{cc}: 不是 mapping")
                continue
            for k in ("period", "milestone", "evidence"):
                if not _nonempty(c.get(k)):
                    errs.append(f"{cc}.{k} 缺失或为空"
                                + ("(反捏造:里程碑必须带 provenance)" if k == "evidence" else ""))
            for ln in (c.get("lens") or []):
                if ln not in LENSES:
                    errs.append(f"{cc}.lens `{ln}` 非法({'/'.join(sorted(LENSES))})")

    for i, p in enumerate(data.get("portfolio") or []):
        pc = f"{ctx} portfolio[{i}]"
        if not isinstance(p, dict):
            errs.append(f"{pc}: 不是 mapping")
            continue
        for k in ("brand", "evidence"):
            if not _nonempty(p.get(k)):
                errs.append(f"{pc}.{k} 缺失或为空"
                            + ("(反捏造:投资案例必须带 provenance)" if k == "evidence" else ""))

    # ── B. 判断字段合法 ────────────────────────────────────────────────
    rel = data.get("relation")
    if rel is not None:
        if not isinstance(rel, dict):
            errs.append(f"{ctx}: relation 必须是 mapping")
        else:
            for k, v in rel.items():
                if k not in LENSES:
                    errs.append(f"{ctx}: relation key `{k}` 非法({'/'.join(sorted(LENSES))})")
                if not _nonempty(v) or not str(v).lstrip().startswith(RELATION_MARKERS):
                    errs.append(f"{ctx}: relation.{k} 必须以「分析:」开头 "
                                f"—— 关系是标注分析,不冒充本人原话")

    ps = data.get("perspective_slug")
    if _nonempty(ps):
        if not os.path.isfile(os.path.join(PERSPECTIVES, f"{ps}-perspective", "SKILL.md")):
            errs.append(f"{ctx}: perspective_slug `{ps}` 没有对应的 "
                        f"perspectives/{ps}-perspective/SKILL.md")
    return errs


def founder_brand_slugs():
    return {os.path.splitext(os.path.basename(p))[0]
            for p in glob.glob(os.path.join(FOUNDERS_DIR, "*.yaml"))}


def run():
    paths = sorted(glob.glob(os.path.join(INVESTORS_DIR, "*.yaml")))
    if not paths:
        print("validate_investors: investors/ 无数据(功能未启用)—— 跳过。")
        return 0
    seen, founders = set(), founder_brand_slugs()
    errs = []
    for p in paths:
        try:
            data = yaml.safe_load(open(p, encoding="utf-8"))
        except Exception as e:
            errs.append(f"investors/{os.path.basename(p)}: YAML 解析失败:{e}")
            continue
        errs += validate_one(p, data, seen, founders)
    if errs:
        print("validate_investors: ❌ 发现问题", file=sys.stderr)
        for e in errs:
            print("  - " + e, file=sys.stderr)
        return 1
    print(f"validate_investors: ✅ {len(paths)} 份投资人档案通过"
          f"(履历带 provenance、镜头合法、关系标注「分析:」、slug 不与品牌撞名)。")
    return 0


def _selftest():
    """每类违规造一个假样本,证明门禁真的会抓(与 validate_founders 同哲学)。"""
    def ok_doc(**over):
        d = {
            "slug": "demo",
            "perspective_slug": "",
            "investor": {"name_cn": "某某", "role": "创始合伙人", "status": "现任"},
            "career": [{"period": "2020", "milestone": "创办某基金",
                        "evidence": "example.com/a", "lens": ["origin"]}],
            "portfolio": [{"brand": "somebrand", "evidence": "example.com/b"}],
            "relation": {"origin": "分析:示例"},
        }
        d.update(over)
        return d

    cases = [
        ("干净样本应通过", ok_doc(), 0),
        ("缺 investor 段必抓", ok_doc(investor=None), 1),
        ("status 非法必抓", ok_doc(investor={"name_cn": "某某", "role": "R", "status": "在职"}), 1),
        ("career 为空必抓", ok_doc(career=[]), 1),
        ("career 缺 evidence 必抓(反捏造)",
         ok_doc(career=[{"period": "2020", "milestone": "M", "evidence": "", "lens": []}]), 1),
        ("career lens 非法必抓",
         ok_doc(career=[{"period": "2020", "milestone": "M", "evidence": "E", "lens": ["nope"]}]), 1),
        ("portfolio 缺 evidence 必抓(反捏造)",
         ok_doc(portfolio=[{"brand": "b", "evidence": ""}]), 1),
        ("relation 不以「分析:」开头必抓(反捏造)",
         ok_doc(relation={"origin": "她认为品牌最重要"}), 1),
        ("relation key 非法必抓", ok_doc(relation={"nope": "分析:x"}), 1),
        ("perspective_slug 不存在必抓", ok_doc(perspective_slug="no-such-person"), 1),
        ("slug 与文件名不一致必抓", ok_doc(slug="other"), 1),
    ]
    fails = []
    for name, doc, want in cases:
        got = validate_one(os.path.join(INVESTORS_DIR, "demo.yaml"), doc, set(), set())
        hit = 1 if got else 0
        if hit != want:
            fails.append(f"{name}(期望 {'报错' if want else '通过'},实际 {'报错' if hit else '通过'})")

    # slug 与 founders 品牌撞名必须被抓 —— 晚餐按 slug 找参与者,撞名会指错人
    got = validate_one(os.path.join(INVESTORS_DIR, "demo.yaml"), ok_doc(), set(), {"demo"})
    if not any("撞名" in e for e in got):
        fails.append("slug 与 founders 品牌撞名必抓")

    if fails:
        print("validate_investors --selftest: ❌ " + "; ".join(fails), file=sys.stderr)
        return 1
    print(f"validate_investors --selftest: ✅ {len(cases) + 1} 组断言全部通过(门禁有牙)")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv[1:] else run())
