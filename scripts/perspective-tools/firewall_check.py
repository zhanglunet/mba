#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
firewall_check.py — anti-fabrication firewall (MBA 立身之本,机器门禁)

对每套 perspective 校验:SKILL.md「## Core Mental Models」区里所有引号内 `>` blockquote
逐字引用,**必须**在该套 references/research/*.md 语料(quotes.md + 01-06)里逐字存在
(规范化后子串匹配)。SKILL 引了一句 research 里没有的话 = 可能捏造 / 漂移 → CI fail。

这把 CLAUDE.md 坑#3 的「反捏造靠人工 grep」升级成机器强制门禁。

用法:
  python3 scripts/perspective-tools/firewall_check.py            # 全 43 套
  python3 scripts/perspective-tools/firewall_check.py <path/to/SKILL.md ...>
  python3 scripts/perspective-tools/firewall_check.py --quiet    # 只打失败 + 汇总

退出码:有任何 SKILL 引用无法在本套语料逐字命中 → 1;否则 0。
"""
import sys, os, re, glob

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- 规范化(镜像本项目手动 firewall 的做法)----
# 全角→半角标点 + 弯引号/破折号/省略号统一
_SRC = "，。：；？！（）【】、《》—–·　％～“”‘’「」"
_DST = ",.:;?!()[],<>--  %~\"\"''\"\""
_TABLE = {ord(a): b for a, b in zip(_SRC, _DST)}
_TABLE.update({ord("…"): "..."})

def _base(s: str) -> str:
    return s.translate(_TABLE)

def norm_cjk(s: str) -> str:
    # 中文:去掉所有空白(CJK 无词间空格)
    return re.sub(r"\s+", "", _base(s))

def norm_en(s: str) -> str:
    # 英文:折叠空白 + 合并 PDF 换行连字符(long- term → long-term)
    s = re.sub(r"\s+", " ", _base(s)).strip()
    return re.sub(r"\s*-\s*", "-", s)

def is_cjk_majority(s: str) -> bool:
    cjk = len(re.findall(r"[一-鿿]", s))
    latin = len(re.findall(r"[A-Za-z]", s))
    return cjk >= latin

# ---- 抽取:SKILL 心智模型 / 关键引用区里的 `>` 引用(中英双语)----
# 逐字引用集中在这些 H2 里;不覆盖 Self-Conflict / Persona / Anti-Fab 等模板区,避免假阳性。
_QUOTE_SECTIONS = ("core mental models", "核心心智模型", "关键引用", "key quote",
                   "金句", "代表性金句", "representative quotes")

def _is_quote_section(h2: str) -> bool:
    low = h2.lower()
    return any(k in low for k in _QUOTE_SECTIONS)

def extract_skill_quotes(skill_text: str):
    """返回心智模型 / 关键引用 H2 区间内的所有 `>` blockquote 行(排除代码块)。"""
    lines = skill_text.splitlines()
    quotes, in_sec, in_fence = [], False, False
    for ln in lines:
        st = ln.strip()
        if st.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if st.startswith("## "):
            in_sec = _is_quote_section(st)
            continue
        if in_sec and st.startswith(">"):
            q = st.lstrip(">").strip()
            # 跳过明显的注记 / 说明行(非逐字引用)
            if q.startswith(("**", "注", "⚠", "利益", "例如", "Note", "note")):
                continue
            if len(q) >= 8:
                quotes.append(q)
    return quotes

def strip_annotation(q: str):
    """生成候选:原样 + 去掉行内 `code` 标签 + 去掉结尾括注 后的版本(全试,任一命中即算过)。"""
    cands = []
    q0 = q.strip()
    cands.append(q0)
    q1 = re.sub(r"`[^`]*`", "", q0).strip()          # 去 `[tag]` code-span
    cands.append(q1)
    for c in (q0, q1):
        # 去结尾双破折号出处标注(jobs 风格:『"..." —— Stanford Commencement』)
        c_dash = re.sub(r"\s*——.*$", "", c).strip()
        cands.append(c_dash)
        # 去结尾括注:（...) / (...) —— 只去结尾一处
        c2 = re.sub(r"[（(][^（）()]*[)）]\s*$", "", c).strip()
        cands.append(c2)
        # 双破折号 + 括注都去
        cands.append(re.sub(r"[（(][^（）()]*[)）]\s*$", "", c_dash).strip())
    # 去成对首尾引号
    out = []
    for c in cands:
        out.append(c)
        c3 = c.strip("\"'“”‘’「」")
        if c3 != c:
            out.append(c3)
    # 去重保序
    seen, uniq = set(), []
    for c in out:
        if c and c not in seen:
            seen.add(c); uniq.append(c)
    return uniq

def load_corpus(persp_dir: str):
    files = sorted(glob.glob(os.path.join(persp_dir, "references", "research", "*.md")))
    raw = ""
    for f in files:
        raw += open(f, encoding="utf-8").read() + "\n"
    return raw, files

def check_perspective(skill_path: str, quiet=False):
    persp_dir = os.path.dirname(skill_path)
    slug = os.path.basename(persp_dir).replace("-perspective", "")
    skill = open(skill_path, encoding="utf-8").read()
    quotes = extract_skill_quotes(skill)
    corpus_raw, files = load_corpus(persp_dir)

    if not corpus_raw.strip():
        # seed:无 research 语料 —— 无法 firewall,报 skip(非失败)
        return {"slug": slug, "status": "skip", "reason": "no research corpus (seed)",
                "checked": len(quotes), "failed": []}

    C_cjk = norm_cjk(corpus_raw)
    C_en = norm_en(corpus_raw)

    def match_one(text):
        """单个引用串:任一 strip_annotation 候选规范化后是语料子串即算命中。"""
        for cand in strip_annotation(text):
            if is_cjk_majority(cand):
                if norm_cjk(cand) in C_cjk:
                    return True
            else:
                if norm_en(cand) in C_en:
                    return True
                if norm_cjk(cand) in C_cjk:   # 兜底:混合语言引用
                    return True
        return False

    failed = []
    for q in quotes:
        # 先整行试;整行不中再按 " / " 拆多引用(如「A（源) / B（源)」),要求每段都命中
        if match_one(q):
            continue
        segs = [s for s in re.split(r"\s+/\s+", q) if len(s.strip()) >= 6]
        if len(segs) >= 2 and all(match_one(s) for s in segs):
            continue
        failed.append(q)

    status = "fail" if failed else "ok"
    return {"slug": slug, "status": status, "checked": len(quotes), "failed": failed}

def main(argv):
    quiet = "--quiet" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if paths:
        skills = []
        for p in paths:
            skills.append(p if p.endswith("SKILL.md") else os.path.join(p, "SKILL.md"))
    else:
        skills = sorted(glob.glob(os.path.join(ROOT, "perspectives", "*-perspective", "SKILL.md")))

    n_ok = n_fail = n_skip = total_q = total_fail = 0
    fails = []
    for sp in skills:
        r = check_perspective(sp, quiet)
        total_q += r["checked"]
        if r["status"] == "ok":
            n_ok += 1
            if not quiet:
                print(f"OK   {r['slug']:24s} {r['checked']} quotes verbatim ✓")
        elif r["status"] == "skip":
            n_skip += 1
            if not quiet:
                print(f"SKIP {r['slug']:24s} {r['reason']}")
        else:
            n_fail += 1
            total_fail += len(r["failed"])
            fails.append(r)
            print(f"FAIL {r['slug']:24s} {len(r['failed'])}/{r['checked']} quote(s) NOT found in research corpus:")
            for q in r["failed"]:
                print(f"       ✗ {q[:110]}")

    print("=" * 60)
    print(f"firewall: {n_ok} ok · {n_fail} FAIL · {n_skip} skip(seed) · {total_q} quotes checked")
    if n_fail:
        print(f"❌ {total_fail} quote(s) across {n_fail} perspective(s) not verbatim in their research corpus.")
        print("   反捏造门禁:SKILL 引用必须逐字存在于本套 references/research;修正引用或补回语料。")
        return 1
    print("✅ 全部 SKILL 引用均在本套 research 语料逐字命中(anti-fabrication firewall 通过)。")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
