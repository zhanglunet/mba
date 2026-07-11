#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_home_cards.py — 从 site/reports-meta.yaml 生成首页(site/index.html)的报告卡片块。

**为什么存在**:首页「已发布审计报告」卡片此前是**手写在 index.html 里**,与
`reports-meta.yaml` 双源——结果 anthropic 卡片长期停在 `v1 · $965B IPO · 191/250 · 7.64`,
而 reports-meta 早已是 `v3 PANEL-MERGE · 179/250 · 7.16`。本生成器把卡片的唯一真源收敛到
reports-meta.yaml,`--check` 漂移门禁(接 check_consistency)杜绝再漂移。

**生成什么**:
  - 卡片顺序 = `published-reports.txt`(与 build.sh 发布顺序一致);
  - 版本行 `{version} · {audit_date}`、takeaway(用 `tl_dr` 干净散文,不再有字面 `**`)、
    描述行(`card_meta`)、品牌行(`card_brand`)、`has_pdf` → PDF 链接;
  - **多版本品牌**(有 `versions:` 列表)渲染「版本演化 EVOLUTION」导航,让 EVOLUTION 的历史
    版本真正可点开(此前 build.sh 排除 versions/,快照无法访问)。
  - 同时把 `<h3>已发布审计报告（N 份）` 的 N 同步为报告数。

只改 `<!-- REPORTS:START -->` … `<!-- REPORTS:END -->` 之间的内容 + h3 计数,其余 index.html 不动。

用法:
  python3 scripts/build_home_cards.py            # 就地重写卡片块 + 计数
  python3 scripts/build_home_cards.py --check     # 只校验无漂移(CI 门禁),漂移则 exit 1
"""
import sys, os, re, datetime

try:
    import yaml
except ImportError:
    print("build_home_cards: 需要 PyYAML(pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
META = os.path.join(SITE, "reports-meta.yaml")
INDEX = os.path.join(SITE, "index.html")
WHITELIST = os.path.join(SITE, "published-reports.txt")

START = "<!-- REPORTS:START — 生成自 site/reports-meta.yaml(scripts/build_home_cards.py)· 勿手改 -->"
END = "<!-- REPORTS:END -->"
H3_RE = re.compile(r"已发布审计报告（\d+\s*份）")


def esc(s: str) -> str:
    """转义卡片文本内容里的 & < >(引号不在文本上下文,无需转义)。"""
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# CJK 字 + 中文标点 + 全角形 + 弯引号 —— 这些字符之间的空格必是 YAML `>-` 折叠引入的
# 假空格(中文无词间空格),要去掉;而拉丁词 / 数字周围的空格(如「PC 龙头」)是有意的,保留。
_CJK = "‘’“”　-〿㐀-䶿一-鿿＀-￯"
_CJK_SPACE = re.compile(f"(?<=[{_CJK}]) (?=[{_CJK}])")


def collapse_ws(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    return _CJK_SPACE.sub("", s)


def fmt_date(d) -> str:
    return d.isoformat() if isinstance(d, datetime.date) else str(d or "")


def read_whitelist():
    slugs = []
    for line in open(WHITELIST, encoding="utf-8"):
        t = line.strip()
        if t and not t.startswith("#"):
            slugs.append(t)
    return slugs


def render_versions(slug: str, versions) -> str:
    """多版本品牌的「版本演化」导航:历史版本 → versions/ 快照,当前版本 → 报告主页。"""
    links = []
    for v in versions:
        label = esc(v.get("v", ""))
        if v.get("current"):
            links.append(f'<a href="/reports/{slug}/">{label} · 当前</a>')
        else:
            f = v.get("file", "")
            links.append(f'<a href="/reports/{slug}/{f}">{label}</a>')
    joined = "\n          ".join(links)
    return (
        '\n        <div class="versions">'
        '\n          <span class="vlabel">版本演化 EVOLUTION</span>'
        f"\n          {joined}"
        "\n        </div>"
    )


def render_card(m: dict) -> str:
    slug = m["slug"]
    brand = esc(m["card_brand"])
    ver = f'{esc(str(m.get("version", "")))} · {esc(fmt_date(m.get("audit_date")))}'
    takeaway = esc(collapse_ws(m.get("tl_dr", "")))
    meta = esc(m["card_meta"])
    pdf = f'\n          <a href="/reports/{slug}/report.pdf">↓ PDF</a>' if m.get("has_pdf") else ""
    versions = render_versions(slug, m["versions"]) if m.get("versions") else ""
    # 卡片是 <div>(非 <a>):品牌名是「拉伸链接」覆盖整卡可点开报告,meta/versions 里的
    # 链接靠 z-index 浮在其上单独可点——避免 <a> 嵌 <a> 触发 HTML5 adoption-agency 把
    # .versions 踢出 .report-card(嵌套锚点会让版本导航脱离卡片、样式失效)。
    return (
        f'      <div class="report-card">\n'
        f'        <div class="top">\n'
        f'          <span class="brand"><a class="card-link" href="/reports/{slug}/">{brand}</a></span>\n'
        f'          <span class="v">{ver}</span>\n'
        f"        </div>\n"
        f'        <div class="takeaway">\n'
        f"          {takeaway}\n"
        f"        </div>\n"
        f'        <div class="meta">\n'
        f"          {meta}{pdf}\n"
        f"        </div>{versions}\n"
        f"      </div>"
    )


def build_block():
    meta = yaml.safe_load(open(META, encoding="utf-8")) or {}
    by_slug = {r["slug"]: r for r in (meta.get("reports") or [])}
    slugs = read_whitelist()
    cards, missing = [], []
    for slug in slugs:
        m = by_slug.get(slug)
        if not m:
            missing.append(slug)
            continue
        for req in ("card_brand", "card_meta"):
            if not m.get(req):
                raise SystemExit(f"build_home_cards: {slug} 缺 reports-meta 字段 `{req}`")
        cards.append(render_card(m))
    if missing:
        raise SystemExit(
            f"build_home_cards: 白名单 slug 在 reports-meta.yaml 缺 meta:{', '.join(missing)}"
        )
    return "\n".join(cards), len(cards)


def splice(index_text: str, block: str, n: int) -> str:
    if START not in index_text or END not in index_text:
        raise SystemExit(
            f"build_home_cards: index.html 缺少标记 {START!r} / {END!r}(请先手动加一次)"
        )
    pre, rest = index_text.split(START, 1)
    _, post = rest.split(END, 1)
    new = f"{pre}{START}\n{block}\n      {END}{post}"
    new = H3_RE.sub(f"已发布审计报告（{n} 份）", new)
    return new


def main(argv):
    check = "--check" in argv
    block, n = build_block()
    cur = open(INDEX, encoding="utf-8").read()
    new = splice(cur, block, n)
    if check:
        if new != cur:
            print("❌ 首页卡片与 reports-meta.yaml 漂移 —— 跑 `python3 scripts/build_home_cards.py` 重生成。")
            # 打印首个差异区,便于定位
            cl, nl = cur.splitlines(), new.splitlines()
            for i in range(min(len(cl), len(nl))):
                if cl[i] != nl[i]:
                    print(f"   首个差异 @ 行 {i+1}:\n     - 现有: {cl[i].strip()[:100]}\n     + 应为: {nl[i].strip()[:100]}")
                    break
            return 1
        print(f"✅ 首页卡片与 reports-meta.yaml 同步({n} 份报告,无漂移)。")
        return 0
    open(INDEX, "w", encoding="utf-8").write(new)
    print(f"[home-cards] 已重写 site/index.html 卡片块 —— {n} 份报告。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
