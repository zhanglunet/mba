#!/usr/bin/env python3
"""
new_weekly.py — scaffold and publish MBA weekly reports.

The Markdown file under docs/weekly/ is the single source of truth; the styled
site page (site/weekly.html) is generated from it, so the two never drift.

Commands:
  python3 scripts/new_weekly.py new [YYYY-MM-DD] [--milestone "..."]
      Create docs/weekly/<date>.md from TEMPLATE.md and add a row to the index.
      (date defaults to today.)

  python3 scripts/new_weekly.py publish [YYYY-MM-DD]
      Re-render ALL docs/weekly/*.md → site/weekly/<date>.html archive pages,
      and the latest one → site/weekly.html, each with a 历史周报 timeline
      (date + milestone) linking every issue. Date argument is accepted for
      backward compatibility but publish always regenerates everything —
      pages are deterministic functions of the Markdown sources.

Typical flow: `new` → fill in the Markdown → `publish` → commit md + site pages.
"""

import re
import sys
import html
import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WEEKLY_DIR = REPO / "docs" / "weekly"
TEMPLATE = WEEKLY_DIR / "TEMPLATE.md"
INDEX = WEEKLY_DIR / "README.md"
SITE_PAGE = REPO / "site" / "weekly.html"
SITE_ARCHIVE_DIR = REPO / "site" / "weekly"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ── Markdown → styled HTML ───────────────────────────────────────────────────

def _inline(text: str) -> str:
    """Escape, then apply **bold** / *italic* / `code`."""
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def _split_row(line: str) -> list:
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def render_body(md: str) -> str:
    """Render the report body (everything after the metadata block)."""
    # Drop the title + metadata block up to the first horizontal rule.
    parts = md.split("\n---\n", 1)
    body = parts[1] if len(parts) == 2 else md

    lines = body.split("\n")
    out: list[str] = []
    i = 0
    first_para_done = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped == "" or stripped == "---":
            i += 1
            continue

        # HTML comment (guidance) — skip
        if stripped.startswith("<!--"):
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
            i += 1
            continue

        # Headings
        if stripped.startswith("### "):
            txt = stripped[4:].strip()
            m = re.match(r"^(\d+)[.、]\s*(.*)$", txt)
            if m:
                out.append(f'<h3><span class="n">{m.group(1)}</span>{_inline(m.group(2))}</h3>')
            else:
                out.append(f"<h3>{_inline(txt)}</h3>")
            i += 1
            continue
        if stripped.startswith("## "):
            out.append(f"<h2>{_inline(stripped[3:].strip())}</h2>")
            i += 1
            continue

        # Table
        if stripped.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            if len(rows) >= 2:
                header = _split_row(rows[0])
                th = "".join(f"<th>{_inline(c)}</th>" for c in header)
                body_rows = ""
                for r in rows[2:]:  # skip the |---| separator
                    tds = "".join(f"<td>{_inline(c)}</td>" for c in _split_row(r))
                    body_rows += f"<tr>{tds}</tr>"
                out.append(
                    f'<div class="t-wrap"><table><thead><tr>{th}</tr></thead>'
                    f"<tbody>{body_rows}</tbody></table></div>"
                )
            continue

        # Lists
        if re.match(r"^([-*]|\d+[.、])\s+", stripped):
            items = []
            while i < len(lines) and re.match(r"^([-*]|\d+[.、])\s+", lines[i].strip()):
                item = re.sub(r"^([-*]|\d+[.、])\s+", "", lines[i].strip())
                items.append(f"<li>{_inline(item)}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        # Italic-only line → muted footnote
        if re.match(r"^\*[^*].*\*$", stripped):
            out.append(f'<p class="note-line">{_inline(stripped)}</p>')
            i += 1
            continue

        # Paragraph. The first one (the one-liner summary) becomes the lead box.
        if not first_para_done:
            out.append(f'<p class="lead">{_inline(stripped)}</p>')
            first_para_done = True
        else:
            out.append(f"<p>{_inline(stripped)}</p>")
        i += 1

    return "\n  ".join(out)


def parse_meta(md: str) -> dict:
    def grab(label):
        m = re.search(rf"^\*\*{label}\*\*[：:]\s*(.+)$", md, re.MULTILINE)
        return m.group(1).strip() if m else ""
    return {"period": grab("周期"), "milestone": grab("里程碑")}


PAGE_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>项目周报 · MBA — Metric Brand Auditor</title>
<meta name="description" content="MBA 项目周报：本周解决了哪些问题、交付了哪些功能、沉淀了哪些方法论。面向非技术读者，聚焦业务价值。" />
<meta property="og:title" content="项目周报 · MBA" />
<meta property="og:url" content="https://mbabrand.com/weekly.html" />
<style>
  :root {{
    --ink: #111; --paper: #faf8f3; --paper-2: #f0ece3; --muted: #6b6760;
    --rule: #1a1a1a; --accent: #c1440e; --card: #fff;
    --green: #2a7a4b; --green-bg: #edf7f1;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    background: var(--paper); color: var(--ink);
    font-family: ui-serif, "Noto Serif SC", "Songti SC", Georgia, serif;
    line-height: 1.68; -webkit-font-smoothing: antialiased;
  }}
  .wrap {{ max-width: 820px; margin: 0 auto; padding: 56px 28px 100px; }}
  header {{
    border-bottom: 2px solid var(--rule); padding-bottom: 18px; margin-bottom: 36px;
    display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap;
  }}
  .mark {{ font-family: ui-sans-serif, "Inter", -apple-system, sans-serif; font-weight: 800; letter-spacing: 0.02em; font-size: 22px; }}
  .mark a {{ color: inherit; text-decoration: none; }}
  .mark .dot {{ color: var(--accent); }}
  nav a {{ font-family: ui-sans-serif, "Inter", -apple-system, sans-serif; font-size: 13px; color: var(--ink); text-decoration: none; border-bottom: 1px solid var(--ink); margin-left: 18px; }}
  nav a:hover {{ color: var(--accent); border-color: var(--accent); }}
  nav a.current {{ color: var(--accent); border-color: var(--accent); }}
  h1 {{ font-size: clamp(28px, 4.4vw, 44px); line-height: 1.16; margin: 0 0 10px; font-weight: 800; letter-spacing: -0.01em; }}
  .sub {{ font-size: 16px; color: var(--muted); margin: 0 0 8px; font-style: italic; }}
  .chip {{
    display: inline-block; font-family: ui-sans-serif, "Inter", -apple-system, sans-serif;
    font-size: 11px; font-weight: 700; letter-spacing: 0.08em; padding: 3px 10px;
    border: 1px solid var(--muted); color: var(--muted); border-radius: 999px;
    margin: 0 8px 28px 0; text-transform: uppercase;
  }}
  .chip.hl {{ border-color: var(--accent); color: var(--accent); }}
  h2 {{
    font-family: ui-sans-serif, "Inter", -apple-system, sans-serif;
    font-size: 13px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--muted); margin: 52px 0 16px; padding-top: 18px; border-top: 2px solid var(--rule);
  }}
  h3 {{ font-size: 19px; font-weight: 700; margin: 26px 0 6px; letter-spacing: -0.01em; }}
  h3 .n {{ color: var(--accent); font-family: ui-sans-serif, sans-serif; font-size: 14px; margin-right: 8px; }}
  p {{ margin: 0 0 14px; }}
  .lead {{ background: var(--card); border-left: 4px solid var(--accent); padding: 18px 22px; border-radius: 0 6px 6px 0; margin: 0 0 8px; font-size: 17px; }}
  .note-line {{ color: var(--muted); font-style: italic; font-size: 14px; }}
  .t-wrap {{ overflow-x: auto; margin: 16px 0 24px; }}
  table {{ border-collapse: collapse; width: 100%; font-family: ui-sans-serif, -apple-system, sans-serif; font-size: 14px; }}
  th {{ background: #1a1a1a; color: #f3f1ea; text-align: left; padding: 9px 12px; font-weight: 600; white-space: nowrap; }}
  td {{ border: 1px solid #e0ddd6; padding: 9px 12px; vertical-align: top; }}
  tr:nth-child(even) td {{ background: #fbf9f4; }}
  ul {{ padding-left: 20px; margin: 0 0 14px; }}
  li {{ margin: 0 0 8px; }}
  strong {{ font-weight: 700; }}
  code {{ font-family: ui-monospace, monospace; font-size: 0.9em; background: #f0ece3; padding: 1px 5px; border-radius: 3px; }}
  footer {{
    margin-top: 56px; padding-top: 20px; border-top: 2px solid var(--rule);
    font-family: ui-sans-serif, -apple-system, sans-serif; font-size: 13px; color: var(--muted);
    display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap;
  }}
  footer a {{ color: var(--muted); }}
  /* 历史周报时间线 */
  .timeline {{ list-style: none; padding: 0; margin: 8px 0 0; font-family: ui-sans-serif, "Inter", -apple-system, sans-serif; }}
  .timeline li {{ position: relative; padding: 0 0 18px 26px; border-left: 2px solid #e0ddd6; margin-left: 6px; }}
  .timeline li:last-child {{ padding-bottom: 4px; }}
  .timeline li::before {{
    content: ""; position: absolute; left: -6px; top: 6px; width: 10px; height: 10px;
    border-radius: 50%; background: var(--paper); border: 2px solid var(--muted);
  }}
  .timeline li.current::before {{ background: var(--accent); border-color: var(--accent); }}
  .tl-date {{ font-size: 12px; font-weight: 700; color: var(--muted); letter-spacing: 0.06em; }}
  .tl-date a {{ color: inherit; text-decoration: none; border-bottom: 1px solid var(--muted); }}
  .tl-date a:hover {{ color: var(--accent); border-color: var(--accent); }}
  .timeline li.current .tl-date {{ color: var(--accent); }}
  .tl-ms {{ font-size: 14px; margin-top: 2px; line-height: 1.5; }}
  .tl-tag {{ font-size: 10px; font-weight: 800; color: #fff; background: var(--accent); border-radius: 999px; padding: 1px 8px; margin-left: 8px; vertical-align: 1px; }}
</style>
</head>
<body>
<div class="wrap">

  <header>
    <div class="mark"><a href="/">MBA<span class="dot">.</span></a></div>
    <nav>
      <a href="/">品牌监控</a>
      <a href="/watch/">舆情信号</a>
      <a href="/panorama.html">评委全景</a>
      <a href="/starmap.html">知识星图</a>
      <a href="/docs.html">文档</a>
      <a href="https://github.com/zhanglunet/mba">GitHub</a>
    </nav>
  </header>

  <h1>项目周报</h1>
  <p class="sub">Weekly Report · 面向非技术读者，聚焦业务价值</p>
  <div>
    <span class="chip">{period}</span>
    <span class="chip hl">里程碑 · {milestone}</span>
  </div>

  {content}

  <h2>历史周报 · Timeline</h2>
  <ol class="timeline">
{timeline}
  </ol>

  <footer>
    <span>MBA · Metric Brand Auditor · © 2026 MBA · Jason · 清风 · John · 技术支持 <a href="https://marsdata.ai">marsdata.ai</a></span>
    <span>
      <a href="/">主页</a> ·
      <a href="/roadmap.html">Roadmap</a> ·
      <a href="{doc_url}">原始文档</a>
    </span>
  </footer>

</div>
</body>
</html>
"""


# ── commands ─────────────────────────────────────────────────────────────────

def cmd_new(args: list):
    date = args[0] if args and not args[0].startswith("-") else datetime.date.today().isoformat()
    milestone = "（本周里程碑）"
    if "--milestone" in args:
        milestone = args[args.index("--milestone") + 1]

    dest = WEEKLY_DIR / f"{date}.md"
    if dest.exists():
        print(f"refusing to overwrite existing {dest.relative_to(REPO)}")
        return 1

    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("{{DATE}}", date).replace("{{MILESTONE}}", milestone)
    dest.write_text(text, encoding="utf-8")
    print(f"created {dest.relative_to(REPO)}")

    # Add an index row (right under the table header separator).
    if INDEX.exists():
        idx = INDEX.read_text(encoding="utf-8")
        row = f"| 截至 {date} | [{date}.md]({date}.md) | {milestone} |"
        if f"[{date}.md]" not in idx:
            idx = re.sub(r"(\n\|[-\s|]+\|\n)", r"\1" + row + "\n", idx, count=1)
            INDEX.write_text(idx, encoding="utf-8")
            print(f"added index row to {INDEX.relative_to(REPO)}")

    print(f"\nnext: fill in {dest.relative_to(REPO)}, then:\n  python3 scripts/new_weekly.py publish {date}")
    return 0


def _plain(s: str) -> str:
    """Chips / timeline are plain styled labels — strip markdown emphasis markers."""
    return re.sub(r"[*`]", "", s)


def list_issues():
    """All weekly issues, newest first: [(date, md_text, meta)]."""
    issues = []
    for p in sorted(WEEKLY_DIR.glob("*.md"), reverse=True):
        if not DATE_RE.match(p.stem):
            continue  # README / TEMPLATE
        md = p.read_text(encoding="utf-8")
        issues.append((p.stem, md, parse_meta(md)))
    return issues


def render_timeline(issues, current_date):
    """时间线:每期一个节点(日期 + 里程碑),当前期高亮。最新一期链 /weekly.html。"""
    items = []
    for i, (date, _md, meta) in enumerate(issues):
        href = "/weekly.html" if i == 0 else f"/weekly/{date}.html"
        cur = ' class="current"' if date == current_date else ""
        tag = '<span class="tl-tag">本期</span>' if date == current_date else ""
        ms = html.escape(_plain(meta["milestone"]) or "—", quote=False)
        items.append(
            f'    <li{cur}><div class="tl-date"><a href="{href}">截至 {date}</a>{tag}</div>'
            f'<div class="tl-ms">{ms}</div></li>'
        )
    return "\n".join(items)


def render_issue_page(date, md, meta, timeline_html):
    period = html.escape(_plain(meta["period"]) or f"周期 · 截至 {date}", quote=False)
    milestone = html.escape(_plain(meta["milestone"]) or "—", quote=False)
    doc_url = f"https://github.com/zhanglunet/mba/blob/main/docs/weekly/{date}.md"
    return PAGE_TEMPLATE.format(
        period=period, milestone=milestone, content=render_body(md),
        timeline=timeline_html, doc_url=doc_url,
    )


def cmd_publish(args: list):
    # date 参数向后兼容;publish 恒重生成全部页面(页面是 md 的确定性函数)。
    issues = list_issues()
    if not issues:
        print("no weekly issues found under docs/weekly/")
        return 1
    if args and DATE_RE.match(args[0]) and not (WEEKLY_DIR / f"{args[0]}.md").exists():
        print(f"not found: docs/weekly/{args[0]}.md")
        return 1

    SITE_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    # 清掉已删除期数的孤儿页
    known = {f"{d}.html" for d, _, _ in issues}
    for p in SITE_ARCHIVE_DIR.glob("*.html"):
        if p.name not in known:
            p.unlink()
            print(f"removed orphan {p.relative_to(REPO)}")

    for date, md, meta in issues:
        page = render_issue_page(date, md, meta, render_timeline(issues, date))
        (SITE_ARCHIVE_DIR / f"{date}.html").write_text(page, encoding="utf-8")
        print(f"wrote site/weekly/{date}.html")

    latest_date, latest_md, latest_meta = issues[0]
    SITE_PAGE.write_text(
        render_issue_page(latest_date, latest_md, latest_meta, render_timeline(issues, latest_date)),
        encoding="utf-8",
    )
    print(f"wrote {SITE_PAGE.relative_to(REPO)} (latest = {latest_date}, timeline {len(issues)} 期)")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    cmd, rest = args[0], args[1:]
    if cmd == "new":
        return cmd_new(rest)
    if cmd == "publish":
        return cmd_publish(rest)
    print(f"unknown command '{cmd}'. use 'new' or 'publish'.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
