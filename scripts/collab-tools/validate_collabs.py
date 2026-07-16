#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_collabs.py — 创始人晚餐(品牌×品牌合作推演,collabs/<a>--<b>.yaml)静态硬 gate。

守三件事(与 validate_founders 同哲学):

  A. 结构底线:brands 恰 2 个且都有 founders/<slug>.yaml(都有创始人档案);文件名 == 字母序
     `a--b`;title/scene 非空;courses 非空,每道有 lens/exchange/idea;takeaways 与 tensions
     非空(tensions = 诚实盒,反炒作平衡,强制存在)。
  B. 判断/引用合法:course.lens ⊆ 5 镜头;exchange 每个 who ∈ brands 且 say 非空。
  C. 反捏造(靠数据契约 + 生成器 disclaimer):say 为 AI 演绎,禁止冒充逐字原话——本校验器不做
     语义判定,但强制 brands 都是真实创始人、镜头合法、诚实盒(tensions)在位;disclaimer 由
     build_collab_dinners.py 硬编码渲染。

用法:
  python3 scripts/collab-tools/validate_collabs.py             # 校验全部晚餐
  python3 scripts/collab-tools/validate_collabs.py --selftest  # 自测:证明每类违规都会被抓
退出码:有违规 → 1;否则 0。collabs/ 不存在或无文件时通过(功能未启用不算错)。
"""
import glob
import os
import sys

try:
    import yaml
except ImportError:
    print("validate_collabs: 需要 PyYAML(pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COLLABS_DIR = os.path.join(ROOT, "collabs")
FOUNDERS_DIR = os.path.join(ROOT, "founders")

LENSES = {"origin", "category", "leverage", "identity", "signal"}


def founder_exists(slug):
    return os.path.isfile(os.path.join(FOUNDERS_DIR, f"{slug}.yaml"))


def canonical_stem(brands):
    return "--".join(sorted(brands))


def validate_collab(stem, data, seen_stems, check_founder=True):
    """校验单个 collabs/<stem>.yaml。返回 errors 列表。"""
    errs = []
    ctx0 = f"collabs/{stem}.yaml"
    if not isinstance(data, dict):
        return [f"{ctx0}: 顶层必须是映射"]

    brands = data.get("brands")
    if not isinstance(brands, list) or len(brands) != 2 or not all(isinstance(b, str) for b in brands):
        errs.append(f"{ctx0}: brands 必须是恰好 2 个 slug 的列表")
        brands = [b for b in (brands or []) if isinstance(b, str)]
    if len(set(brands)) != len(brands):
        errs.append(f"{ctx0}: brands 两个 slug 不能相同")
    if brands and stem != canonical_stem(brands):
        errs.append(f"{ctx0}: 文件名应为字母序 `{canonical_stem(brands)}`(brands 的规范化连接)")
    if check_founder:
        for b in brands:
            if not founder_exists(b):
                errs.append(f"{ctx0}: brand `{b}` 无对应 founders/{b}.yaml(晚餐双方都须有创始人档案)")
    if stem in seen_stems:
        errs.append(f"{ctx0}: 晚餐 `{stem}` 重复")
    seen_stems.add(stem)
    brandset = set(brands)

    for field in ("title", "scene"):
        v = data.get(field)
        if not isinstance(v, str) or not v.strip():
            errs.append(f"{ctx0}: {field} 缺失或为空")

    courses = data.get("courses")
    if not isinstance(courses, list) or not courses:
        errs.append(f"{ctx0}: courses 必须是非空列表(至少一道菜)")
    else:
        for i, c in enumerate(courses):
            cctx = f"{ctx0}.courses[{i}]"
            if not isinstance(c, dict):
                errs.append(f"{cctx}: 必须是映射")
                continue
            if c.get("lens") not in LENSES:
                errs.append(f"{cctx}: lens `{c.get('lens')}` 非法(⊆ {sorted(LENSES)})")
            if not c.get("idea") or not isinstance(c.get("idea"), str):
                errs.append(f"{cctx}: 缺 idea(该镜头下的合作点)")
            ex = c.get("exchange")
            if not isinstance(ex, list) or not ex:
                errs.append(f"{cctx}: exchange 必须是非空列表(双方发言)")
            else:
                for j, t in enumerate(ex):
                    tctx = f"{cctx}.exchange[{j}]"
                    if not isinstance(t, dict):
                        errs.append(f"{tctx}: 必须是映射")
                        continue
                    if brandset and t.get("who") not in brandset:
                        errs.append(f"{tctx}: who `{t.get('who')}` 必须 ∈ brands {sorted(brandset)}")
                    if not t.get("say") or not isinstance(t.get("say"), str):
                        errs.append(f"{tctx}: say 缺失或为空")

    for field in ("takeaways", "tensions"):
        v = data.get(field)
        if not isinstance(v, list) or not v:
            errs.append(f"{ctx0}: {field} 必须是非空列表"
                        + ("(诚实盒:合作张力/不搭之处,反炒作平衡)" if field == "tensions" else ""))

    # 可选:首页「创始人晚餐 · 亮点」精选字段(build_collab_dinners 生成首页 DINNER 块用)。
    # featured 必须是 bool;home_highlight(若给)必须指向本场真实存在的 course.lens —— 否则
    # 首页亮点会静默落到别的镜头/首道菜,展示与作者意图不符。
    feat = data.get("featured")
    if feat is not None and not isinstance(feat, bool):
        errs.append(f"{ctx0}: featured 必须是布尔值(true/false)")
    hl = data.get("home_highlight")
    if hl is not None:
        course_lenses = {c.get("lens") for c in (courses if isinstance(courses, list) else [])
                         if isinstance(c, dict)}
        if hl not in course_lenses:
            errs.append(f"{ctx0}: home_highlight `{hl}` 不在本场任一 course 的 lens 中"
                        f"(须 ∈ {sorted(x for x in course_lenses if x)})")
    return errs


def main():
    if not os.path.isdir(COLLABS_DIR):
        print("validate_collabs: collabs/ 不存在 —— 功能未启用,通过。")
        return 0
    files = sorted(glob.glob(os.path.join(COLLABS_DIR, "*.yaml")))
    errs = []
    seen = set()
    for path in files:
        stem = os.path.splitext(os.path.basename(path))[0]
        try:
            data = yaml.safe_load(open(path, encoding="utf-8"))
        except yaml.YAMLError as ex:
            errs.append(f"collabs/{stem}.yaml: YAML 解析失败 —— {ex}")
            continue
        errs.extend(validate_collab(stem, data, seen))

    if errs:
        print("validate_collabs: ❌ 发现违规:", file=sys.stderr)
        for e in errs:
            print("  - " + e, file=sys.stderr)
        return 1
    print(f"validate_collabs: ✅ 通过 —— {len(files)} 场晚餐全部合规"
          f"(双方均有创始人档案、镜头合法、诚实盒在位)。")
    return 0


# ------------------------------------------------------------- selftest ----

def selftest():
    """证明每类违规都会被抓(门禁要自证有牙)。"""
    def ok(**over):
        d = {
            "brands": ["aa", "bb"],
            "title": "示例晚餐", "scene": "假想场景",
            "courses": [{"lens": "origin",
                         "exchange": [{"who": "aa", "say": "立场A"}, {"who": "bb", "say": "立场B"}],
                         "idea": "合作点"}],
            "takeaways": ["合作机会1"],
            "tensions": ["张力1"],
        }
        d.update(over)
        return d

    def run(data):
        return validate_collab("aa--bb", data, set(), check_founder=False)

    cases = [
        ("合法晚餐应通过", ok(), 0),
        ("brands 非 2 必抓", ok(brands=["aa"]), 1),
        ("brands 相同必抓", ok(brands=["aa", "aa"]), 1),
        ("who 越界必抓", ok(courses=[{"lens": "origin", "exchange": [{"who": "cc", "say": "x"}], "idea": "i"}]), 1),
        ("lens 越界必抓", ok(courses=[{"lens": "vibe", "exchange": [{"who": "aa", "say": "x"}], "idea": "i"}]), 1),
        ("course 缺 idea 必抓", ok(courses=[{"lens": "origin", "exchange": [{"who": "aa", "say": "x"}]}]), 1),
        ("say 为空必抓", ok(courses=[{"lens": "origin", "exchange": [{"who": "aa", "say": ""}], "idea": "i"}]), 1),
        ("courses 为空必抓", ok(courses=[]), 1),
        ("takeaways 为空必抓", ok(takeaways=[]), 1),
        ("tensions 为空必抓(诚实盒)", ok(tensions=[]), 1),
        ("scene 为空必抓", ok(scene=""), 1),
        ("home_highlight 指向不存在的镜头必抓", ok(home_highlight="signal"), 1),
        ("featured 非布尔必抓", ok(featured="yes"), 1),
        ("home_highlight 合法应通过", ok(home_highlight="origin"), 0),
        ("featured 合法应通过", ok(featured=True), 0),
    ]
    failed = []
    for name, data, expect_min in cases:
        got = len(run(data))
        if (expect_min == 0 and got != 0) or (expect_min > 0 and got < expect_min):
            failed.append(f"{name}: 期望 {'0' if expect_min == 0 else '≥1'} 条违规,实得 {got} —— {run(data)}")

    # 文件名非规范序应抓:brands 排序后 = aa--bb,但文件名给成 zz--yy
    fn = validate_collab("zz--yy", ok(), set(), check_founder=False)
    if not fn:
        failed.append("文件名非规范序应抓,实得 0")

    # founder 不存在应抓(打开 check_founder)
    miss = validate_collab("aa--bb", ok(), set(), check_founder=True)
    if not miss:
        failed.append("founder 不存在应抓,实得 0")

    if failed:
        print("validate_collabs --selftest: ❌", file=sys.stderr)
        for f in failed:
            print("  - " + f, file=sys.stderr)
        return 1
    print(f"validate_collabs --selftest: ✅ {len(cases) + 1} 组断言全部通过(门禁有牙)。")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv[1:] else main())
