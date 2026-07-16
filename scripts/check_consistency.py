#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_consistency.py — E2-6 跨文件一致性守卫。

锁住几处"分散在多个文件、会随开发悄悄漂移"的常量,让它们在漂移时 CI 变红,
而不是靠人肉巡检。只校验**机器可判定、且不会误伤历史快照**的不变量:

  1. 版本对齐:SKILL.md 里给每份 FRESH 报告拷贝的 panel.yaml 模板 `mba_version`
     必须等于 SKILL.md front-matter 的 `version`(E2-6 修的正是这条:模板长期停在 0.2.38)。
  2. docs 索引完整:每个 `docs/NN-*.md` 都必须在 `docs/README.md` 索引里被引用。
  3. 评委数自洽:`perspectives/*-perspective/` 目录数 == `site/api/judges.json.count`
     == `docs/09-agent-api.md` 里写的 "N 个评委人物视角"。
  4. 工具数自洽:`packages/mcp-server/src/server.ts` 的 `registerTool(` 次数
     == `docs/13-mcp-quickstart.md` 的 "全部 N 个工具"。
  5. 维度口径:`site/api/methodology.json` 的 core 维度 == 7、总维度 == 9(7 核心 + 2 高级)。
  6. 首页卡片对齐:`build_home_cards.py --check`(site/index.html 监控区 == reports-meta.yaml)。
  7. panorama 名单:`site/panorama.html` 手写评委数组的唯一 slug 数 == perspectives 目录数(G1)。

历史快照(published/reports/* 的 MBA Version 戳、dated handoff / changelog / 进度日志)
**不在校验范围**——它们记录的是当时状态,不该被"对齐"。

退出码:有任一不变量被破坏 → 1;全部通过 → 0。
"""
import os, re, sys, json, glob, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def rd(rel):
    p = os.path.join(ROOT, rel)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else None

def check_version_alignment():
    s = rd("metric-brand-auditor/SKILL.md")
    if s is None:
        return False, "metric-brand-auditor/SKILL.md 不存在"
    fm = re.search(r"(?m)^version:\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)", s)
    tmpl = re.search(r"mba_version:\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)", s)
    if not fm or not tmpl:
        return False, f"未能同时解析 front-matter version({bool(fm)})与 panel 模板 mba_version({bool(tmpl)})"
    if fm.group(1) != tmpl.group(1):
        return False, (f"SKILL front-matter version={fm.group(1)} 与 panel.yaml 模板 mba_version={tmpl.group(1)} 不一致 "
                       f"—— 每份 FRESH 报告会拷这个模板,必须同步(改 front-matter 时一起改)。")
    return True, f"SKILL version == panel 模板 mba_version == {fm.group(1)}"

def check_docs_index():
    readme = rd("docs/README.md")
    if readme is None:
        return False, "docs/README.md 不存在"
    numbered = sorted(os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "docs", "[0-9][0-9]-*.md")))
    missing = [d for d in numbered if d not in readme]
    if missing:
        return False, f"docs/README.md 索引未收录:{', '.join(missing)}(每个 docs/NN-*.md 都要在索引里)"
    return True, f"docs 索引完整({len(numbered)} 个编号文档全部被引用)"

def check_judge_count():
    persp = glob.glob(os.path.join(ROOT, "perspectives", "*-perspective"))
    n_dir = len([d for d in persp if os.path.isfile(os.path.join(d, "SKILL.md"))])
    problems = []
    try:
        api = json.loads(rd("site/api/judges.json") or "{}").get("count")
        if api != n_dir:
            problems.append(f"site/api/judges.json.count={api} != 目录数 {n_dir}(跑 build_agents_api.py)")
    except Exception as e:
        problems.append(f"读 judges.json 失败:{e}")
    d09 = rd("docs/09-agent-api.md") or ""
    m = re.search(r"(\d+)\s*个评委人物视角", d09)
    if m and int(m.group(1)) != n_dir:
        problems.append(f"docs/09 写 '{m.group(1)} 个评委' != 目录数 {n_dir}")
    if problems:
        return False, " · ".join(problems)
    return True, f"评委数自洽(perspectives 目录 == judges.json == docs/09 == {n_dir})"

def check_tool_count():
    srv = rd("packages/mcp-server/src/server.ts")
    if srv is None:
        return True, "packages/mcp-server/src/server.ts 不存在(跳过)"
    n_tools = len(re.findall(r"server\.registerTool\(", srv))
    d13 = rd("docs/13-mcp-quickstart.md") or ""
    m = re.search(r"全部\s*(\d+)\s*个工具", d13)
    if m and int(m.group(1)) != n_tools:
        return False, f"docs/13 写 '全部 {m.group(1)} 个工具' != server.ts registerTool 次数 {n_tools}"
    return True, f"工具数自洽(server.ts registerTool == docs/13 == {n_tools})"

def check_dimensions():
    try:
        meth = json.loads(rd("site/api/methodology.json") or "{}")
    except Exception as e:
        return True, f"methodology.json 读取失败,跳过({e})"
    dims = meth.get("dimensions")
    if not isinstance(dims, list):
        return True, "methodology.json 无 dimensions 数组(跳过)"
    core = sum(1 for d in dims if d.get("tier") == "core")
    total = len(dims)
    if core != 7 or total != 9:
        return False, f"维度口径漂移:core={core}(应 7)· total={total}(应 9,7 核心 + 2 高级)"
    return True, "维度口径自洽(7 核心 + 2 高级 = 9)"

def check_home_cards():
    """首页(site/index.html)报告卡片必须与 site/reports-meta.yaml 同步(F6)。
    卡片由 build_home_cards.py 从 reports-meta 生成;此处跑其 --check 拦漂移
    (anthropic 卡片曾长期停在 v1/$965B 就是双源漂移的后果)。"""
    script = os.path.join(ROOT, "scripts", "build_home_cards.py")
    if not os.path.exists(script):
        return True, "build_home_cards.py 不存在(跳过)"
    try:
        r = subprocess.run([sys.executable, script, "--check"],
                           capture_output=True, text=True, cwd=ROOT)
    except Exception as e:
        return True, f"无法运行 build_home_cards(跳过):{e}"
    if r.returncode == 0:
        return True, "首页卡片与 reports-meta.yaml 同步(无漂移)"
    if r.returncode == 2:
        # 依赖缺失(如无 PyYAML)——非漂移;build_agents_api --check 会另行兜底
        return True, "build_home_cards 依赖缺失(跳过);build_agents_api --check 兜底"
    lines = [x for x in (r.stdout or r.stderr or "").strip().splitlines() if x.strip()]
    return False, "首页卡片漂移 —— " + (lines[0] if lines else "跑 build_home_cards.py 重生成")

def check_panorama_roster():
    """panorama.html 的评委名单是手写内联数组(F('名','slug',…)/S('名','slug')),
    不像 judge.html 那样走 /api/judges.json —— 曾因此静默漂移。此处锁:页面内
    唯一 slug 数必须等于 perspectives 目录数(G1,docs/11 G 系列)。"""
    html_src = rd("site/panorama.html")
    if html_src is None:
        return True, "site/panorama.html 不存在(跳过)"
    slugs = set(re.findall(r"[FS]\('[^']*','([a-z0-9-]+)'", html_src))
    persp = glob.glob(os.path.join(ROOT, "perspectives", "*-perspective"))
    n_dir = len([d for d in persp if os.path.isfile(os.path.join(d, "SKILL.md"))])
    if len(slugs) != n_dir:
        missing = {os.path.basename(d).removesuffix("-perspective") for d in persp} - slugs
        extra = slugs - {os.path.basename(d).removesuffix("-perspective") for d in persp}
        return False, (f"panorama 评委名单漂移:页面 {len(slugs)} 人 != 目录 {n_dir} 人"
                       + (f" · 页面缺 {sorted(missing)}" if missing else "")
                       + (f" · 页面多 {sorted(extra)}" if extra else ""))
    return True, f"panorama 评委名单自洽(页面唯一 slug == 目录数 == {n_dir})"

def check_founders():
    """创始人维度(founders/*.yaml)跨源自洽:brand ∈ 发布白名单、履历带 provenance、
    perspective_slug 真实。委托 validate_founders.py(单一真源逻辑,避免重复实现)。
    founders/ 不存在 = 功能未启用,通过。"""
    fdir = os.path.join(ROOT, "founders")
    if not os.path.isdir(fdir) or not glob.glob(os.path.join(fdir, "*.yaml")):
        return True, "founders/ 未启用(跳过)"
    script = os.path.join(ROOT, "scripts", "founder-tools", "validate_founders.py")
    if not os.path.exists(script):
        return True, "validate_founders.py 不存在(跳过)"
    try:
        r = subprocess.run([sys.executable, script], capture_output=True, text=True, cwd=ROOT)
    except Exception as e:
        return True, f"无法运行 validate_founders(跳过):{e}"
    if r.returncode == 2:
        return True, "validate_founders 依赖缺失(跳过)"
    n = len(glob.glob(os.path.join(fdir, "*.yaml")))
    if r.returncode == 0:
        return True, f"创始人档案自洽({n} 份 brand 对齐白名单 · perspective_slug 真实)"
    lines = [x for x in (r.stderr or r.stdout or "").strip().splitlines() if x.strip()]
    return False, "创始人档案违规 —— " + (lines[-1] if lines else "跑 validate_founders.py")

def check_collabs():
    """创始人晚餐(collabs/*.yaml)跨源自洽:双方均有创始人档案、镜头合法、诚实盒在位。
    委托 validate_collabs.py(单一真源逻辑)。collabs/ 不存在 = 功能未启用,通过。"""
    cdir = os.path.join(ROOT, "collabs")
    if not os.path.isdir(cdir) or not glob.glob(os.path.join(cdir, "*.yaml")):
        return True, "collabs/ 未启用(跳过)"
    script = os.path.join(ROOT, "scripts", "collab-tools", "validate_collabs.py")
    if not os.path.exists(script):
        return True, "validate_collabs.py 不存在(跳过)"
    try:
        r = subprocess.run([sys.executable, script], capture_output=True, text=True, cwd=ROOT)
    except Exception as e:
        return True, f"无法运行 validate_collabs(跳过):{e}"
    if r.returncode == 2:
        return True, "validate_collabs 依赖缺失(跳过)"
    n = len(glob.glob(os.path.join(cdir, "*.yaml")))
    if r.returncode == 0:
        return True, f"创始人晚餐自洽({n} 场,双方均有创始人档案 · 诚实盒在位)"
    lines = [x for x in (r.stderr or r.stdout or "").strip().splitlines() if x.strip()]
    return False, "创始人晚餐违规 —— " + (lines[-1] if lines else "跑 validate_collabs.py")

def check_dinner_home():
    """首页「创始人晚餐 · 亮点」块(site/index.html 的 DINNER 区)必须与 collabs/*.yaml 同步。
    块由 build_collab_dinners.py 从 collabs 生成;此处跑其 --check-home 拦漂移
    (同 build_home_cards 的双源防线)。collabs/ 未启用或依赖缺失 → 通过。"""
    cdir = os.path.join(ROOT, "collabs")
    if not os.path.isdir(cdir) or not glob.glob(os.path.join(cdir, "*.yaml")):
        return True, "collabs/ 未启用(跳过)"
    script = os.path.join(ROOT, "scripts", "build_collab_dinners.py")
    if not os.path.exists(script):
        return True, "build_collab_dinners.py 不存在(跳过)"
    try:
        r = subprocess.run([sys.executable, script, "--check-home"],
                           capture_output=True, text=True, cwd=ROOT)
    except Exception as e:
        return True, f"无法运行 build_collab_dinners(跳过):{e}"
    if r.returncode == 0:
        return True, "首页晚餐亮点块与 collabs/*.yaml 同步(无漂移)"
    if r.returncode == 2:
        return True, "build_collab_dinners 依赖缺失(跳过)"
    lines = [x for x in (r.stdout or r.stderr or "").strip().splitlines() if x.strip()]
    return False, "首页晚餐亮点块漂移 —— " + (lines[0] if lines else "跑 build_collab_dinners.py 重生成")

def check_industries():
    """产业维度(docs/23):每个发布白名单品牌在 reports-meta 都有 industry 且 ∈ 6 个合法 CN 标签。
    正则解析 reports-meta(不引 yaml 依赖,与本守卫零依赖风格一致)。"""
    meta = rd("site/reports-meta.yaml")
    wl = rd("site/published-reports.txt")
    if meta is None or wl is None:
        return True, "reports-meta / 白名单缺失(跳过)"
    valid = {"人工智能", "消费", "硬科技·航天", "智能制造·硬件", "企业服务·安全", "教育"}
    whitelist = [l.strip() for l in wl.splitlines() if l.strip() and not l.strip().startswith("#")]
    ind_by = {}
    for b in re.split(r"\n\s*- slug:\s*", "\n" + meta)[1:]:
        slug = b.split("\n", 1)[0].strip()
        m = re.search(r"\n\s*industry:\s*(\S+)", b)
        ind_by[slug] = m.group(1).strip() if m else None
    bad = [f"{s}={ind_by.get(s)!r}" for s in whitelist if ind_by.get(s) not in valid]
    if bad:
        return False, "产业标签缺失/非法:" + ", ".join(bad) + f"(须 ∈ {sorted(valid)})"
    return True, f"产业维度自洽({len(whitelist)} 品牌均有合法 industry · 6 类)"

CHECKS = [
    ("版本对齐", check_version_alignment),
    ("docs 索引完整", check_docs_index),
    ("评委数自洽", check_judge_count),
    ("工具数自洽", check_tool_count),
    ("维度口径", check_dimensions),
    ("首页卡片对齐", check_home_cards),
    ("panorama 名单", check_panorama_roster),
    ("创始人维度", check_founders),
    ("创始人晚餐", check_collabs),
    ("产业维度", check_industries),
    ("晚餐亮点对齐", check_dinner_home),
]

def main():
    print("MBA 一致性守卫(check_consistency.py)")
    print("=" * 60)
    hard = 0
    for name, fn in CHECKS:
        ok, msg = fn()
        print(f"  {'✅ OK  ' if ok else '❌ FAIL'} {name:<12} {msg}")
        if not ok:
            hard += 1
    print("=" * 60)
    if hard:
        print(f"❌ 一致性守卫失败({hard} 项漂移)。")
        return 1
    print("✅ 一致性守卫通过。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
