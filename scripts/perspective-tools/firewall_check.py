#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
firewall_check.py — anti-fabrication firewall (MBA 立身之本,机器门禁)

对每套 perspective 校验两类「声称的逐字引用」,**必须**在该套 references/research/*.md 语料
(quotes.md + 01-06)里逐字存在(规范化后子串匹配),否则 = 可能捏造 / 漂移 → CI fail:

  (1) SKILL「## Core Mental Models / 关键引用」区里的 `>` blockquote 逐字引用;
  (2) F4:「## 表达DNA / Expression DNA」等区 ```代码块``` 里**带来源署名**的代表句式
      (如 `… —— 致股东信，2018` / `… — Startup = Growth, 2012`)——署名=声称是真引语,必须有据。

**豁免**:无来源署名的「Representative lines / 代表句式 / answer scaffold」句式模板(常带
`{占位符}`)是合法的风格演示,不是声称的引语,不校验(避免误伤合法的风格样例)。

这把 CLAUDE.md 坑#3 的「反捏造靠人工 grep」升级成机器强制门禁;F4 把覆盖从「只查 `>`」
扩到「也查带署名的代表句式」(此前 22/43 套的行内/代码块引用是盲区)。

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

# ---- F4:带署名的「代表句式」代码块引用 ----
# 表达DNA / Expression DNA 等区里 ```text 代码块中的句子分两类:
#   - **带来源署名**(如 `…… —— 致股东信，2018` / `… — Startup = Growth, 2012`)= 声称的真引语 → 必须逐字在 research;
#   - **无署名**(「Representative lines / 代表句式 / answer scaffold」的句式模板,常带 {占位符})= 合法的风格样例 → 豁免。
# 只校验前者,把「引了一句署名却不在语料」的漏洞补上,同时不误伤合法的句式演示。
_DNA_SECTIONS = ("表达dna", "expression dna", "表达风格", "代表", "representative", "金句", "句式")
# 来源信号:出现年份 / 出处词 / 大写 essay 标题起始,才把结尾的 — / —— 当作署名(避免误吃句内破折号)
_SRC_SIGNAL = re.compile(r"(1[89]\d\d|20\d\d|年会|发布会|讲话|演讲|大会|访谈|致股东|股东信|公开信|自传|Commencement|essay|Source|source|Growth|Wealth|—\s*[A-Z])")
_ATTR_RE = re.compile(r"\s[—–]\s+(?P<a>\S.*)$|\s*——\s*(?P<b>\S.*)$")

def _split_attribution(line: str):
    """若 line 以「来源署名」结尾,返回 (正文, True);否则 (原文, False)。
    只有署名段带来源信号时才切,避免误吃句内的破折号。"""
    m = _ATTR_RE.search(line)
    if m:
        src = m.group("a") or m.group("b") or ""
        if _SRC_SIGNAL.search(src):
            return line[:m.start()].rstrip(), True
    return line, False

def extract_attributed_fence_quotes(skill_text: str):
    """表达DNA / 关键引用区 ```代码块``` 内、带来源署名的引用(块级合并多行,只到署名行为止)。"""
    lines = skill_text.splitlines()
    quotes, in_sec, in_fence, unit = [], False, False, []
    for ln in lines:
        st = ln.strip()
        if st.startswith("## "):
            low = st.lower()
            in_sec = _is_quote_section(st) or any(k in low for k in _DNA_SECTIONS)
            in_fence = False; unit = []
            continue
        if st.startswith("```"):
            in_fence = not in_fence
            if not in_fence:
                unit = []  # 出块:未署名残余=风格样例,丢弃
            continue
        if not (in_sec and in_fence):
            continue
        body, attributed = _split_attribution(st)
        if body:
            unit.append(body)
        if attributed:
            q = " ".join(unit).strip()
            if len(q) >= 8:
                quotes.append(q)
            unit = []
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
    # 去成对首尾引号 + 去句尾标点(「抢钱。」应命中语料里的「抢钱」)
    out = []
    for c in cands:
        out.append(c)
        c3 = c.strip("\"'“”‘’「」")
        if c3 != c:
            out.append(c3)
        c4 = re.sub(r"[。.!?！?：:；;、,，\s\"'“”‘’「」]+$", "", c).strip()
        if c4 and c4 != c:
            out.append(c4)
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
    quotes = extract_skill_quotes(skill) + extract_attributed_fence_quotes(skill)
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
        # 多句体兜底:整段不中再逐句(如 paulg「A startup is…. The only essential thing is growth.」),要求每句命中
        sents = [s for s in re.split(r"(?<=[。.!?！?])\s+", q) if len(s.strip()) >= 8]
        if len(sents) >= 2 and all(match_one(s) for s in sents):
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
