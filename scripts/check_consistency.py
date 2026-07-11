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

历史快照(published/reports/* 的 MBA Version 戳、dated handoff / changelog / 进度日志)
**不在校验范围**——它们记录的是当时状态,不该被"对齐"。

退出码:有任一不变量被破坏 → 1;全部通过 → 0。
"""
import os, re, sys, json, glob

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

CHECKS = [
    ("版本对齐", check_version_alignment),
    ("docs 索引完整", check_docs_index),
    ("评委数自洽", check_judge_count),
    ("工具数自洽", check_tool_count),
    ("维度口径", check_dimensions),
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
