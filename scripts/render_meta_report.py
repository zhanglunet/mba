#!/usr/bin/env python3
"""mba 元评审审计报告渲染（PRD-063/T3，trend #334）。

把 `scripts/meta_review.py`（T2）的 Markdown 审计输出，渲染成人类可读的
单页 HTML 审计报告（学 iFixAi 的"120 秒可读"），给管理层/人工复核看。

输入：T2 的 Markdown（stdin 或文件）；输出：单页 HTML（stdout 或 -o 文件）。

一页摘要区（首屏）：A–F 评级大字展示（附"只反映分歧程度，不等于打分质量"注脚）
  → Top3 分歧点（一行一条：维度/σ/评委对/分差）→ 建议复核项（只说"建议人工复核"）。
附录区：一致性矩阵 / 离群记录 / 松紧度画像 / 解析备注 / 热力图对照，分区可折叠。

风格复用 `published/reports/deepseek/report.html` 的已验证要素：
serif 字体栈、CSS 变量、viewport、手机可看。不引入重型框架，纯标准库。

措辞纪律（T1 §四）：全文用"分歧点"/"疑似"，不用"错误"/"定罪"；只出报告不改分。

用法：
  python3 scripts/meta_review.py published/reports/deepseek/report.md \\
      | python3 scripts/render_meta_report.py -o audit.html
  python3 scripts/render_meta_report.py audit.md -o audit.html
"""

import argparse
import html
import pathlib
import re
import sys

# 评级配色：A 绿 / B 蓝 / C 琥珀 / D、F 赭红
GRADE_COLORS = {
    "A": "var(--green)",
    "B": "var(--blue)",
    "C": "var(--warn)",
    "D": "var(--accent)",
    "F": "var(--accent)",
}

CSS = """
:root {
  --ink: #111;
  --paper: #faf8f3;
  --muted: #6b6760;
  --rule: #1a1a1a;
  --accent: #c1440e;
  --green: #1a7a4a;
  --blue: #1a4a7a;
  --warn: #d97706;
  --line: #e2ddd2;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--paper);
  color: var(--ink);
  font-family: ui-serif, "Noto Serif SC", "Songti SC", Georgia, serif;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 820px; margin: 0 auto; padding: 48px 28px 96px; }
@media (max-width: 640px) { .wrap { padding: 28px 16px 64px; } }
header {
  border-bottom: 2px solid var(--rule);
  padding-bottom: 16px;
  margin-bottom: 32px;
}
.mark {
  font-family: ui-sans-serif, "Inter", -apple-system, sans-serif;
  font-weight: 800; letter-spacing: 0.02em; font-size: 20px;
}
.mark .dot { color: var(--accent); }
.meta { color: var(--muted); font-size: 14px; margin-top: 8px; }
h1 { font-size: 30px; margin: 0 0 4px; }
h2 { font-size: 22px; margin: 40px 0 12px; border-bottom: 1px solid var(--line); padding-bottom: 8px; }
.summary {
  border: 2px solid var(--rule);
  border-radius: 10px;
  padding: 24px 24px 8px;
  background: #fffdf8;
}
.grade-row { display: flex; align-items: center; gap: 20px; margin: 8px 0 4px; flex-wrap: wrap; }
.grade-badge {
  width: 96px; height: 96px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 52px; font-weight: 800;
  border: 5px solid; background: var(--paper);
  flex: 0 0 auto;
}
.grade-note { color: var(--muted); font-size: 14px; max-width: 520px; }
.top3 { list-style: none; padding: 0; margin: 12px 0; }
.top3 li {
  padding: 10px 14px; margin: 8px 0;
  border: 1px solid var(--line); border-left: 4px solid var(--accent);
  border-radius: 6px; background: #fff;
}
.top3 .dim { font-weight: 700; font-size: 18px; margin-right: 10px; }
.top3 .sigma { color: var(--muted); font-size: 14px; margin-right: 10px; }
.review-items { padding-left: 20px; }
.review-items li { margin: 6px 0; }
.disclaimer { color: var(--muted); font-size: 14px; margin: 12px 0 4px; }
details {
  border: 1px solid var(--line); border-radius: 8px;
  margin: 12px 0; background: #fff;
}
summary {
  cursor: pointer; padding: 12px 16px; font-weight: 700;
  font-family: ui-sans-serif, "Inter", -apple-system, sans-serif; font-size: 15px;
}
summary:hover { color: var(--accent); }
.details-body { padding: 4px 16px 16px; overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 14px; margin: 8px 0; }
th, td { border: 1px solid var(--line); padding: 6px 10px; text-align: center; }
th { background: #f3efe6; font-weight: 700; }
ul.plain { padding-left: 20px; margin: 8px 0; }
ul.plain li { margin: 4px 0; }
footer { color: var(--muted); font-size: 13px; margin-top: 48px; border-top: 1px solid var(--line); padding-top: 12px; }
"""


def _sanitize(text: str) -> str:
    """措辞纪律净化：把"错误"/"定罪"的字样（含否定式引用）改写掉，
    全文只保留"分歧点"/"疑似"/"建议人工复核"。"""
    text = re.sub(r"[，,]非[“\"]错误[”\"]/[“\"]定罪[”\"]结论", "", text)
    text = re.sub(r"不是[“\"]打分错误[”\"]的结论", "不作结论性判断", text)
    return text


def _strip_md(text: str) -> str:
    """去掉行内 markdown 加粗/代码标记，保留纯文本。"""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text.strip()


def _md_table_to_html(lines: list) -> str:
    """把 markdown 表格行转成 HTML table。"""
    rows = []
    for ln in lines:
        ln = ln.strip()
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue  # 分隔行
        rows.append(cells)
    if not rows:
        return ""
    out = ["<table>"]
    out.append("<tr>" + "".join(f"<th>{html.escape(c)}</th>" for c in rows[0]) + "</tr>")
    for r in rows[1:]:
        out.append("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def _md_list_to_html(lines: list) -> str:
    items = []
    for ln in lines:
        ln = ln.strip()
        if ln.startswith("- "):
            items.append(f"<li>{html.escape(_strip_md(ln[2:]))}</li>")
    if not items:
        return ""
    return '<ul class="plain">\n' + "\n".join(items) + "\n</ul>"


def parse_audit(md: str) -> dict:
    """解析 T2 的 Markdown 审计输出。缺失关键区块时抛 ValueError（大声失败）。"""
    d: dict = {}

    m = re.search(r"总体一致性评级：([A-F])", md)
    if not m:
        raise ValueError("解析不到总体一致性评级（T2 输出格式不符）")
    d["grade"] = m.group(1)

    m = re.search(r"评级只反映“分歧程度”，\*\*不等于“打分质量”\*\*", md)
    d["grade_disclaimer"] = '评级只反映“分歧程度”，不等于“打分质量”' if m else ""

    m = re.search(r"最大维度 σ=([\d.]+)", md)
    d["max_sigma"] = m.group(1) if m else ""

    m = re.search(r"^> 输入：(.+)$", md, re.M)
    d["input_line"] = _sanitize(_strip_md(m.group(1))) if m else ""

    # Top3 分歧点
    top3 = []
    for ln in md.splitlines():
        m = re.match(
            r"^\s*\d+\.\s*([^：]+)：σ=([\d.]+)，分数范围\s*(\S+?)；(.+?)，分差\s*(\d+)\s*$",
            ln,
        )
        if m:
            top3.append({
                "dim": m.group(1).strip(),
                "sigma": m.group(2),
                "range": m.group(3),
                "sides": m.group(4).strip(),
                "diff": m.group(5),
            })
            if len(top3) == 3:
                break
    d["top3"] = top3

    # 建议复核项：取 "3. **建议复核项**" 到 "## 附录" 之间的内容
    m = re.search(r"3\.\s*\*\*建议复核项\*\*：?\s*\n(.*?)\n## 附录", md, re.S)
    review_lines = m.group(1).splitlines() if m else []
    review_items = []
    tail_note = ""
    for ln in review_lines:
        s = ln.strip()
        if s.startswith("- "):
            review_items.append(_strip_md(s[2:]))
        elif s.startswith("（") and s.endswith("）") and not review_items == []:
            tail_note = _strip_md(s)
    d["review_items"] = review_items
    d["review_note"] = _sanitize(tail_note)

    # 附录：### A. ~ ### E.
    appendix = []
    parts = re.split(r"^### ([A-E])\.\s*(.+)$", md, flags=re.M)
    # parts: [前, 字母, 标题, 正文, 字母, 标题, 正文, ...]
    for i in range(1, len(parts) - 1, 3):
        letter, title, body = parts[i], parts[i + 1].strip(), parts[i + 2]
        blines = [l for l in body.splitlines() if l.strip()]
        table_lines = [l for l in blines if l.strip().startswith("|")]
        if table_lines:
            body_html = _md_table_to_html(table_lines)
            rest = [l for l in blines if not l.strip().startswith("|")]
            if rest:
                body_html += _md_list_to_html(rest) or "".join(
                    f"<p>{html.escape(_strip_md(l))}</p>" for l in rest if _strip_md(l)
                )
        elif any(l.strip().startswith("- ") for l in blines):
            body_html = _md_list_to_html(blines)
        else:
            body_html = "".join(
                f"<p>{html.escape(_strip_md(l))}</p>" for l in blines if _strip_md(l)
            )
        appendix.append({"letter": letter, "title": _strip_md(title), "html": body_html})
    d["appendix"] = appendix

    m = re.search(r"^> 生成方式：(.+?)(?:\n> (.+?))?$", md, re.M)
    d["footer"] = " ".join(_strip_md(x) for x in m.groups() if x) if m else ""

    return d


def render_html(d: dict) -> str:
    color = GRADE_COLORS.get(d["grade"], "var(--ink)")
    top3_html = "\n".join(
        "<li><span class=\"dim\">{dim}</span>"
        "<span class=\"sigma\">σ={sigma} · 分数范围 {rng} · 分差 {diff}</span><br>{sides}</li>".format(
            dim=html.escape(t["dim"]), sigma=html.escape(t["sigma"]),
            rng=html.escape(t["range"]), diff=html.escape(t["diff"]),
            sides=html.escape(t["sides"]),
        )
        for t in d["top3"]
    ) or "<li>本轮无</li>"
    review_html = "\n".join(
        f"<li>{html.escape(x)}</li>" for x in d["review_items"]
    ) or "<li>本轮无</li>"
    appendix_html = "\n".join(
        "<details>\n<summary>{letter}. {title}</summary>\n"
        '<div class="details-body">\n{body}\n</div>\n</details>'.format(
            letter=html.escape(a["letter"]), title=html.escape(a["title"]), body=a["html"]
        )
        for a in d["appendix"]
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>元评审审计报告（PRD-063）</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <div>
    <div class="mark">MBA<span class="dot">.</span> 元评审审计报告</div>
    <div class="meta">{html.escape(d["input_line"])}</div>
  </div>
</header>

<section class="summary">
  <h1>一页审计摘要</h1>
  <div class="grade-row">
    <div class="grade-badge" style="border-color: {color}; color: {color};">{html.escape(d["grade"])}</div>
    <div>
      <div><strong>总体一致性评级：{html.escape(d["grade"])}</strong>（最大维度 σ={html.escape(d["max_sigma"])}）</div>
      <div class="grade-note">注：{html.escape(d["grade_disclaimer"])}</div>
    </div>
  </div>
  <h2>Top3 分歧点</h2>
  <ul class="top3">
{top3_html}
  </ul>
  <h2>建议复核项</h2>
  <ul class="review-items">
{review_html}
  </ul>
  <p class="disclaimer">{html.escape(d["review_note"])}</p>
</section>

<h2>附录</h2>
{appendix_html}

<footer>{html.escape(d["footer"])}</footer>
</div>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="mba 元评审审计报告渲染（Markdown → 单页 HTML）")
    ap.add_argument("input", nargs="?", help="T2 的 Markdown 输出文件（缺省从 stdin 读）")
    ap.add_argument("-o", "--output", help="输出 HTML 文件（缺省打印到 stdout）")
    args = ap.parse_args()

    if args.input:
        p = pathlib.Path(args.input)
        if not p.is_file():
            print(f"ERROR: 输入文件不存在: {p}", file=sys.stderr)
            return 2
        md = p.read_text(encoding="utf-8")
    else:
        md = sys.stdin.read()
    if not md.strip():
        print("ERROR: 输入为空", file=sys.stderr)
        return 2

    try:
        d = parse_audit(md)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    out = render_html(d)
    if args.output:
        pathlib.Path(args.output).write_text(out, encoding="utf-8")
        print(f"written: {args.output}")
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
