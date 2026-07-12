#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_home_cards.py — 从 site/reports-meta.yaml 生成首页(site/index.html)的**品牌监控台**区块。

**为什么存在**:首页卡片必须与 `reports-meta.yaml` 单一真源同步(F6 教训:双源导致 anthropic
卡片长期停在 v1/$965B)。本生成器产出 `<!-- REPORTS:START/END -->` 之间的整个监控区,
`--check` 漂移门禁接 `check_consistency`(第 6 项硬 gate)。

**生成什么**(重设计后 · 监控台形态):
  - KPI 行(4 个 stat tile):监控品牌数(评委/面板数从源码目录实数)· 最新审计 · 最大变动
    (仅同面板 score_history 可算数值 Δ 的品牌)· 审计最高分;
  - 可排序品牌卡片网格(默认按审计日期倒序):大号评分 + Δ/模式 badge + sparkline(有
    score_history 才画)+ panel chip + 一句话动向(headline)+ 版本导航;
  - 卡片可点(拉伸链接),版本 chip 单独可点(z-index 浮层,防 <a> 嵌套踢出 DOM)。

数据字段(reports-meta.yaml 每条):
  headline        一句话动向(卡片主文案)
  score_history   [{v, score[, note]}] 同面板版本分数序列 → sparkline;≥2 点且无 movement
                  覆盖时自动算 Δ badge
  movement        文本 badge(如 "v3 跨面板"),存在时覆盖数值 Δ(跨面板混算不诚实)
  versions        [{v, date[, file|current]}] 版本导航(与 F6 相同)

用法:
  python3 scripts/build_home_cards.py            # 就地重写监控区块
  python3 scripts/build_home_cards.py --check     # 只校验无漂移(CI 门禁),漂移则 exit 1
"""
import sys, os, re, glob, datetime

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
WATCH_DIR = os.path.join(ROOT, "watch")

START = "<!-- REPORTS:START — 生成自 site/reports-meta.yaml(scripts/build_home_cards.py)· 勿手改 -->"
END = "<!-- REPORTS:END -->"

# 视觉 token(与报告页一致的纸面系统;up/down 为 polarity 状态色,badge 永远带 ↑/↓ glyph,
# 不做 color-alone)
C_DOWN, C_UP, C_ACCENT, C_DIM = "#b5341a", "#1a7a4a", "#c1440e", "#c9c3b8"


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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


def count_sources():
    """评委/面板实数,从源码目录数(与 check_consistency 同口径)。"""
    judges = len([d for d in glob.glob(os.path.join(ROOT, "perspectives", "*-perspective"))
                  if os.path.isfile(os.path.join(d, "SKILL.md"))])
    panels = len([p for p in glob.glob(os.path.join(ROOT, "metric-brand-auditor", "panels", "*.yaml"))
                  if os.path.basename(p) != "industries.yaml"])
    return judges, panels


# ── sparkline(dataviz 规格:2px 线;仅 polarity 变动才给末段着 up/down 色,
#     非 polarity(如跨面板)整线保持去强调灰、端点用 accent —— 避免误读成下跌;
#     端点 r4 + 2px 纸面环)──
def sparkline_svg(points, color, polar):
    w, h, pad = 96, 30, 5
    lo, hi = min(points), max(points)
    rng = (hi - lo) or 1.0
    n = len(points)
    xs = [pad + i * (w - 2 * pad) / (n - 1) for i in range(n)]
    ys = [h - pad - (p - lo) * (h - 2 * pad) / rng for p in points]
    base = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    last = ""
    if polar and n >= 2:
        last = f'<line x1="{xs[-2]:.1f}" y1="{ys[-2]:.1f}" x2="{xs[-1]:.1f}" y2="{ys[-1]:.1f}" stroke="{color}" stroke-width="2" stroke-linecap="round"/>'
    return (
        f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true">'
        f'<polyline points="{base}" fill="none" stroke="{C_DIM}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
        f"{last}"
        f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="4" fill="{color}" stroke="var(--paper)" stroke-width="2"/>'
        f"</svg>"
    )


def load_watch_pending():
    """未消费(无 consumed_by)的 P0/P1 计数 per slug(W5,docs/16)。
    watch/ 缺失时为空 —— 徽章是加分项不是硬依赖;计数只依赖文件内容,漂移 gate 可确定。"""
    pending = {}
    for path in sorted(glob.glob(os.path.join(WATCH_DIR, "*", "events.yaml"))):
        slug = os.path.basename(os.path.dirname(path))
        try:
            events = yaml.safe_load(open(path, encoding="utf-8")) or []
        except Exception:
            continue
        p0 = sum(1 for e in events if isinstance(e, dict) and e.get("severity") == "P0" and not e.get("consumed_by"))
        p1 = sum(1 for e in events if isinstance(e, dict) and e.get("severity") == "P1" and not e.get("consumed_by"))
        p2 = sum(1 for e in events if isinstance(e, dict) and e.get("severity") == "P2" and not e.get("consumed_by"))
        if p0 or p1:
            pending[slug] = (p0, p1, p2)
    return pending


def render_watch_line(slug, pending):
    """卡片上的「舆情待审」行:P0/P1 计数 + 触发规则命中时的「建议重审」chip + 时间线链接。
    P2/P3 永不上卡(docs/15 §5.2);链接浮于拉伸链接之上(.watch-line z-index)。"""
    if slug not in pending:
        return ""
    p0, p1, p2 = pending[slug]
    chips = ""
    if p0:
        chips += f'<span class="wchip wchip-p0">P0×{p0}</span>'
    if p1:
        chips += f'<span class="wchip wchip-p1">P1×{p1}</span>'
    # 触发规则(2026-07-12 校准,docs/16 §8.3):P0≥1 / P1≥3 / 加权 4·2·0.5 ≥6。
    # P2 只参与加权、不上卡(docs/15 §5.2)。
    hit = p0 >= 1 or p1 >= 3 or (4 * p0 + 2 * p1 + 0.5 * p2) >= 6
    rec = '<span class="wchip wchip-rec">建议重审</span>' if hit else ""
    return (f'\n        <div class="watch-line"><span class="wlabel">舆情待审</span>{chips}{rec}'
            f'<a href="/watch/{slug}/">信号 →</a></div>')


def movement_of(m):
    """返回 (badge_html, delta_abs, spark_color, polar)。movement 文本覆盖数值 Δ(跨面板不混算)。"""
    hist = m.get("score_history") or []
    if m.get("movement"):
        return f'<span class="badge badge-mode">{esc(m["movement"])}</span>', -1.0, C_ACCENT, False
    if len(hist) >= 2:
        delta = round(float(hist[-1]["score"]) - float(hist[-2]["score"]), 2)
        if abs(delta) < 0.005:
            return '<span class="badge badge-flat">↔</span>', 0.0, C_DIM, False
        cls, arrow, color = ("down", "↓", C_DOWN) if delta < 0 else ("up", "↑", C_UP)
        return f'<span class="badge badge-{cls}">{arrow}{abs(delta):.2f}</span>', abs(delta), color, True
    return "", -1.0, C_ACCENT, False


def render_versions(slug, versions):
    links = []
    for v in versions:
        label = esc(v.get("v", ""))
        if v.get("current"):
            links.append(f'<a href="/reports/{slug}/">{label} · 当前</a>')
        else:
            links.append(f'<a href="/reports/{slug}/{v.get("file", "")}">{label}</a>')
    return ('<div class="versions"><span class="vlabel">版本</span>' + "".join(links) + "</div>")


def render_card(m, pending):
    slug = m["slug"]
    score = m.get("score_normalized")
    score_str = f"{score:.2f}" if isinstance(score, (int, float)) else "—"
    badge, delta_abs, spark_color, polar = movement_of(m)
    hist = m.get("score_history") or []
    spark = sparkline_svg([float(h["score"]) for h in hist], spark_color, polar) if len(hist) >= 2 else ""
    versions = render_versions(slug, m["versions"]) if m.get("versions") else ""
    date = fmt_date(m.get("audit_date"))
    return (
        f'      <div class="brand-card" data-score="{score if score is not None else 0}" '
        f'data-date="{date}" data-delta="{delta_abs}">\n'
        f'        <div class="bc-top">\n'
        f'          <a class="card-link" href="/reports/{slug}/"><span class="bc-brand">{esc(m["card_brand"])}</span></a>\n'
        f'          <span class="chip" title="{esc(m.get("card_meta", ""))}">{esc(m.get("panel", ""))}</span>\n'
        f"        </div>\n"
        f'        <div class="bc-score-row">\n'
        f'          <span class="bc-score">{score_str}</span>{badge}{spark}\n'
        f"        </div>\n"
        f'        <div class="bc-meta">{esc(str(m.get("version", "")))} · {esc(date)}</div>\n'
        f'{render_watch_line(slug, pending)}\n'
        f'        <p class="bc-headline">{esc(collapse_ws(m.get("headline", "")))}</p>{versions}\n'
        f"      </div>"
    )


def render_kpis(reports):
    judges, panels = count_sources()
    latest = max(fmt_date(r.get("audit_date")) for r in reports)
    latest_brands = " / ".join(
        f'{r["brand_cn"]} {r.get("version", "")}'.strip()
        for r in reports if fmt_date(r.get("audit_date")) == latest
    )
    # 最大数值变动(仅同面板 history 且无 movement 覆盖)
    mover, mover_delta = None, 0.0
    for r in reports:
        hist = r.get("score_history") or []
        if r.get("movement") or len(hist) < 2:
            continue
        d = round(float(hist[-1]["score"]) - float(hist[-2]["score"]), 2)
        if abs(d) > abs(mover_delta):
            mover, mover_delta = r, d
    top = max(reports, key=lambda r: r.get("score_normalized") or 0)

    tiles = [
        f'<div class="kpi"><div class="kpi-label">监控品牌</div><div class="kpi-value">{len(reports)}</div>'
        f'<div class="kpi-sub">{judges} 评委 · {panels} 面板</div></div>',
        f'<div class="kpi"><div class="kpi-label">最新审计</div><div class="kpi-value">{esc(latest[5:])}</div>'
        f'<div class="kpi-sub">{esc(latest_brands)}</div></div>',
    ]
    if mover:
        arrow, cls = ("↓", "down") if mover_delta < 0 else ("↑", "up")
        hist = mover["score_history"]
        tiles.append(
            f'<div class="kpi"><div class="kpi-label">最大变动</div>'
            f'<div class="kpi-value {cls}">{arrow}{abs(mover_delta):.2f}</div>'
            f'<div class="kpi-sub">{esc(mover["brand_cn"])} {hist[-2]["score"]}→{hist[-1]["score"]}</div></div>'
        )
    tiles.append(
        f'<div class="kpi"><div class="kpi-label">审计最高分</div><div class="kpi-value">{top.get("score_normalized")}</div>'
        f'<div class="kpi-sub">{esc(top["brand_cn"])} · {esc(top.get("panel", ""))}</div></div>'
    )
    return '      <div class="kpi-row">' + "".join(tiles) + "</div>"


def build_block():
    meta = yaml.safe_load(open(META, encoding="utf-8")) or {}
    by_slug = {r["slug"]: r for r in (meta.get("reports") or [])}
    slugs = read_whitelist()
    reports, missing = [], []
    for slug in slugs:
        m = by_slug.get(slug)
        if not m:
            missing.append(slug)
            continue
        for req in ("card_brand", "headline"):
            if not m.get(req):
                raise SystemExit(f"build_home_cards: {slug} 缺 reports-meta 字段 `{req}`")
        reports.append(m)
    if missing:
        raise SystemExit(f"build_home_cards: 白名单 slug 在 reports-meta.yaml 缺 meta:{', '.join(missing)}")

    # 监控台默认序:审计日期倒序,平局按分数倒序(确定性)
    ordered = sorted(reports, key=lambda r: (fmt_date(r.get("audit_date")), r.get("score_normalized") or 0), reverse=True)
    pending = load_watch_pending()
    cards = "\n".join(render_card(m, pending) for m in ordered)
    sort_bar = (
        '      <div class="sort-bar"><span class="sort-label">品牌动向</span>'
        '<span class="sort-controls">排序:'
        '<button class="sort-btn active" data-key="date">最近</button>'
        '<button class="sort-btn" data-key="score">评分</button>'
        '<button class="sort-btn" data-key="delta">变动</button></span></div>'
    )
    return render_kpis(reports) + "\n" + sort_bar + '\n      <div class="brand-grid" id="brandGrid">\n' + cards + "\n      </div>", len(reports)


def splice(index_text: str, block: str) -> str:
    if START not in index_text or END not in index_text:
        raise SystemExit(f"build_home_cards: index.html 缺少标记 {START!r} / {END!r}(请先手动加一次)")
    pre, rest = index_text.split(START, 1)
    _, post = rest.split(END, 1)
    return f"{pre}{START}\n{block}\n      {END}{post}"


def main(argv):
    check = "--check" in argv
    block, n = build_block()
    cur = open(INDEX, encoding="utf-8").read()
    new = splice(cur, block)
    if check:
        if new != cur:
            print("❌ 首页监控区与 reports-meta.yaml 漂移 —— 跑 `python3 scripts/build_home_cards.py` 重生成。")
            cl, nl = cur.splitlines(), new.splitlines()
            for i in range(min(len(cl), len(nl))):
                if cl[i] != nl[i]:
                    print(f"   首个差异 @ 行 {i+1}:\n     - 现有: {cl[i].strip()[:100]}\n     + 应为: {nl[i].strip()[:100]}")
                    break
            return 1
        print(f"✅ 首页监控区与 reports-meta.yaml 同步({n} 个品牌,无漂移)。")
        return 0
    open(INDEX, "w", encoding="utf-8").write(new)
    print(f"[home-cards] 已重写 site/index.html 监控区块 —— {n} 个品牌。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
