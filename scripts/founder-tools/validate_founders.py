#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_founders.py — 创始人维度(founders/<slug>.yaml)数据静态硬 gate。

守三件事(与 validate_watch 同哲学):

  A. 结构底线:每个文件 brand + founder(name_cn/role/status)+ 至少 1 条 career;
     每条 career 必须有非空 period/milestone/**evidence**(反捏造:履历里程碑必须带 provenance)。
  B. 判断/事实字段合法:status 枚举合法;career[].lens 与 relation 的 key ⊆ 5 镜头;
     perspective_slug(非空时)必须存在对应 perspectives/<slug>-perspective/SKILL.md。
  C. 品牌对齐:brand 必须 ∈ site/published-reports.txt 白名单;文件名 slug == brand;brand 唯一。

用法:
  python3 scripts/founder-tools/validate_founders.py             # 校验全部 founders 数据
  python3 scripts/founder-tools/validate_founders.py --selftest  # 自测:证明每类违规都会被抓
退出码:有违规 → 1;否则 0。founders/ 不存在或无文件时通过(功能未启用不算错)。
"""
import glob
import os
import sys

try:
    import yaml
except ImportError:
    print("validate_founders: 需要 PyYAML(pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FOUNDERS_DIR = os.path.join(ROOT, "founders")
WHITELIST = os.path.join(ROOT, "site", "published-reports.txt")
PERSPECTIVES = os.path.join(ROOT, "perspectives")

LENSES = {"origin", "category", "leverage", "identity", "signal"}
STATUSES = {"现任", "已离任", "已退休", "已故"}


def read_whitelist(path=WHITELIST):
    slugs = []
    for line in open(path, encoding="utf-8"):
        t = line.strip()
        if t and not t.startswith("#"):
            slugs.append(t)
    return slugs


def perspective_exists(slug):
    return os.path.isfile(os.path.join(PERSPECTIVES, f"{slug}-perspective", "SKILL.md"))


def validate_founder(slug, data, whitelist, seen_brands, check_perspective=True):
    """校验单个 founders/<slug>.yaml。返回 errors 列表。"""
    errs = []
    ctx0 = f"founders/{slug}.yaml"
    if not isinstance(data, dict):
        return [f"{ctx0}: 顶层必须是映射"]

    brand = data.get("brand")
    if not brand:
        errs.append(f"{ctx0}: 缺 brand")
    else:
        if brand != slug:
            errs.append(f"{ctx0}: brand `{brand}` 与文件名 slug `{slug}` 不一致")
        if brand not in whitelist:
            errs.append(f"{ctx0}: brand `{brand}` 不在发布白名单(site/published-reports.txt)")
        if brand in seen_brands:
            errs.append(f"{ctx0}: brand `{brand}` 重复")
        seen_brands.add(brand)

    f = data.get("founder")
    if not isinstance(f, dict):
        errs.append(f"{ctx0}: 缺 founder 映射")
    else:
        if not f.get("name_cn"):
            errs.append(f"{ctx0}: founder.name_cn 缺失")
        if not f.get("role"):
            errs.append(f"{ctx0}: founder.role 缺失")
        st = f.get("status")
        if st not in STATUSES:
            errs.append(f"{ctx0}: founder.status `{st}` 非法({'/'.join(sorted(STATUSES))})")
        ps = f.get("perspective_slug")
        if ps and check_perspective and not perspective_exists(ps):
            errs.append(f"{ctx0}: perspective_slug `{ps}` 无对应 perspectives/{ps}-perspective/SKILL.md")

    career = data.get("career")
    if not isinstance(career, list) or not career:
        errs.append(f"{ctx0}: career 必须是非空列表(履历至少 1 条里程碑)")
    else:
        for i, c in enumerate(career):
            cctx = f"{ctx0}.career[{i}]"
            if not isinstance(c, dict):
                errs.append(f"{cctx}: 必须是映射")
                continue
            for field in ("period", "milestone", "evidence"):
                if not c.get(field):
                    errs.append(f"{cctx}: 缺 {field}(反捏造:里程碑必须带 provenance)")
            lens = c.get("lens")
            if lens is not None:
                if not isinstance(lens, list) or not set(lens) <= LENSES:
                    errs.append(f"{cctx}: lens 必须是列表且 ⊆ {sorted(LENSES)}")

    rel = data.get("relation")
    if rel is not None:
        if not isinstance(rel, dict):
            errs.append(f"{ctx0}: relation 必须是映射(镜头→分析文字)")
        elif not set(rel) <= LENSES:
            errs.append(f"{ctx0}: relation 的 key 必须 ⊆ {sorted(LENSES)},实际 {sorted(rel)}")
    return errs


def main():
    if not os.path.isdir(FOUNDERS_DIR):
        print("validate_founders: founders/ 不存在 —— 功能未启用,通过。")
        return 0
    whitelist = read_whitelist()
    files = sorted(glob.glob(os.path.join(FOUNDERS_DIR, "*.yaml")))
    errs = []
    seen_brands = set()
    for path in files:
        slug = os.path.splitext(os.path.basename(path))[0]
        try:
            data = yaml.safe_load(open(path, encoding="utf-8"))
        except yaml.YAMLError as ex:
            errs.append(f"founders/{slug}.yaml: YAML 解析失败 —— {ex}")
            continue
        errs.extend(validate_founder(slug, data, whitelist, seen_brands))

    if errs:
        print("validate_founders: ❌ 发现违规:", file=sys.stderr)
        for e in errs:
            print("  - " + e, file=sys.stderr)
        return 1
    print(f"validate_founders: ✅ 通过 —— {len(files)} 个创始人档案全部合规"
          f"(brand 对齐白名单、履历带 provenance、镜头合法)。")
    return 0


# ------------------------------------------------------------- selftest ----

def selftest():
    """证明每类违规都会被抓(门禁要自证有牙)。"""
    whitelist = ["demo"]

    def ok(**over):
        d = {
            "brand": "demo",
            "founder": {"name_cn": "张三", "role": "创始人", "status": "现任"},
            "career": [{"period": "2020", "milestone": "创立 demo", "evidence": "公开记录", "lens": ["origin"]}],
            "relation": {"origin": "分析文字"},
        }
        d.update(over)
        return d

    def run(data, **kw):
        return validate_founder("demo", data, whitelist, set(), check_perspective=False, **kw)

    cases = [
        ("合法档案应通过", ok(), 0),
        ("缺 brand 必抓", ok(brand=None), 1),
        ("brand 不在白名单必抓", ok(brand="ghost"), 1),  # 同时 slug 不一致也算,≥1
        ("status 非法必抓", ok(founder={"name_cn": "张三", "role": "创始人", "status": "在职"}), 1),
        ("缺 founder.name_cn 必抓", ok(founder={"role": "创始人", "status": "现任"}), 1),
        ("career 为空必抓", ok(career=[]), 1),
        ("career 缺 evidence 必抓", ok(career=[{"period": "2020", "milestone": "x"}]), 1),
        ("career.lens 越界必抓", ok(career=[{"period": "2020", "milestone": "x", "evidence": "y", "lens": ["vibe"]}]), 1),
        ("relation key 越界必抓", ok(relation={"vibe": "x"}), 1),
    ]
    failed = []
    for name, data, expect_min in cases:
        got = len(run(data))
        if (expect_min == 0 and got != 0) or (expect_min > 0 and got < expect_min):
            failed.append(f"{name}: 期望 {'0' if expect_min == 0 else '≥1'} 条违规,实得 {got} —— {run(data)}")

    # brand 重复应抓
    shared = set()
    dup = validate_founder("demo", ok(), whitelist, shared, check_perspective=False)
    dup += validate_founder("demo", ok(), whitelist, shared, check_perspective=False)
    if not dup:
        failed.append("brand 重复应抓,实得 0")

    if failed:
        print("validate_founders --selftest: ❌", file=sys.stderr)
        for f in failed:
            print("  - " + f, file=sys.stderr)
        return 1
    print(f"validate_founders --selftest: ✅ {len(cases) + 1} 组断言全部通过(门禁有牙)。")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv[1:] else main())
