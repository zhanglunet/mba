#!/usr/bin/env python3
"""
new_daily.py — 生成 / 维护 MBA 每日工作日报,并可合成周报草稿。

日报盘点「前一天合并到 main 的提交 / PR」——数据源是 git,可验证、不靠人工回忆
(反捏造)。docs/daily/<date>.md 为单一记录;docs/daily/README.md 索引自动重建。

命令:
  python3 scripts/new_daily.py new [YYYY-MM-DD] [--ref REF] [--allow-empty]
      生成某日(默认「昨天」,按 Asia/Shanghai 计)的日报。默认无提交则跳过、不落文件
      (定时任务据此判断要不要 commit);--allow-empty 强制写一个「无提交」占位。

  python3 scripts/new_daily.py week [YYYY-MM-DD]
      把某日所在自然周(周一–周日)已有的日报合成一份周报草稿,打印到 stdout,
      方便粘进 scripts/new_weekly.py new 的 Markdown。

  python3 scripts/new_daily.py index
      仅按 docs/daily/*.md 现状重建索引(README.md)。

时区:提交时间统一按 Asia/Shanghai(+08:00)归日,CI 在 UTC 跑也不会错位。
"""
import argparse
import datetime
import glob
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DAILY_DIR = REPO / "docs" / "daily"
INDEX = DAILY_DIR / "README.md"
PR_URL = "https://github.com/zhanglunet/mba/pull/{}"
CST = datetime.timezone(datetime.timedelta(hours=8))  # Asia/Shanghai

# commit 类型 → 中文分组名(展示顺序即列表顺序;含本仓库自用类型 design/research/publish)
CATS = [
    ("feat", "功能"), ("fix", "修复"), ("perf", "性能"), ("refactor", "重构"),
    ("design", "设计"), ("docs", "文档"), ("research", "调研"), ("test", "测试"),
    ("build", "构建"), ("ci", "CI"), ("style", "样式"),
    ("release", "发布"), ("chore", "杂项"),
]
CAT_CN = dict(CATS)
CAT_ORDER = [t for t, _ in CATS] + ["other"]
TYPE_ALIAS = {"publish": "release"}  # publish 归并到「发布」
SUBJ_RE = re.compile(r"^(\w+)(?:\(([^)]*)\))?(!)?:\s*(.*)$")
PR_RE = re.compile(r"\(#(\d+)\)\s*$")

START = "<!-- DAILY-INDEX:START — 由 scripts/new_daily.py 生成,勿手改 -->"
END = "<!-- DAILY-INDEX:END -->"


def yesterday():
    return (datetime.datetime.now(CST) - datetime.timedelta(days=1)).date()


def parse_date(s):
    return datetime.date.fromisoformat(s)


# ── git ──────────────────────────────────────────────────────────────────────
def git_commits(ref):
    """返回 [(date, type, scope, desc, pr)] —— ref 上全部非合并提交(committer date 按 +08:00 归日)。"""
    out = subprocess.run(
        ["git", "log", ref, "--no-merges", "--pretty=%cI%x1f%s"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout
    rows = []
    for line in out.splitlines():
        if "\x1f" not in line:
            continue
        ci, subj = line.split("\x1f", 1)
        try:
            d = datetime.datetime.fromisoformat(ci).astimezone(CST).date()
        except ValueError:
            continue
        pr = None
        m = PR_RE.search(subj)
        if m:
            pr = int(m.group(1))
            subj = subj[: m.start()].rstrip()
        sm = SUBJ_RE.match(subj)
        if sm:
            typ, scope, desc = sm.group(1), sm.group(2) or "", sm.group(4)
            typ = TYPE_ALIAS.get(typ, typ)
            if typ not in CAT_CN:
                typ = "other"
        else:
            typ, scope, desc = "other", "", subj
        rows.append((d, typ, scope, desc, pr))
    return rows


PLACEHOLDER_NOTE = (
    "<!-- 人工补充:今日重点 / 关键决策 / 踩坑 / 明日计划。git 盘点之外的东西写这里。 -->"
)


def extract_supplement(md_text):
    """从已有日报里抽出「## 补充说明」和结尾 `---` 之间的人工正文。
    返回去除首尾空行后的正文;若只剩占位注释 / 空,返回 ""(视为未填)。"""
    lines = md_text.split("\n")
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == "## 补充说明")
    except StopIteration:
        return ""
    body = []
    for l in lines[start + 1:]:
        if l.strip() == "---":
            break
        body.append(l)
    text = "\n".join(body).strip()
    if not text or text == PLACEHOLDER_NOTE:
        return ""
    return text


# ── 渲染日报 ─────────────────────────────────────────────────────────────────
def render_daily(date, items, note=None):
    by_type = {}
    for _, typ, scope, desc, pr in items:
        by_type.setdefault(typ, []).append((scope, desc, pr))
    n_pr = len({pr for *_, pr in items if pr})
    lines = [
        f"# 日报 · {date.isoformat()}",
        "",
        f"> 自动生成:盘点 {date.isoformat()}(Asia/Shanghai)合并到 main 的提交 / PR"
        f"(`scripts/new_daily.py`)。「工作盘点」由 git 派生、可验证;「补充说明」留人工。",
        "",
        f"## 工作盘点({len(items)} 项)",
        "",
    ]
    if not items:
        lines.append("_当日无合并到 main 的提交。_")
    for typ in CAT_ORDER:
        group = by_type.get(typ)
        if not group:
            continue
        label = CAT_CN.get(typ, "其他")
        lines.append(f"### {label}({len(group)})")
        for scope, desc, pr in group:
            tag = f" `{scope}`" if scope else ""
            ref = f" · [#{pr}]({PR_URL.format(pr)})" if pr else ""
            lines.append(f"- {desc}{tag}{ref}")
        lines.append("")
    lines += [
        "## 补充说明",
        "",
        note if note else PLACEHOLDER_NOTE,
        "",
        "---",
        f"提交:{len(items)} · PR:{n_pr}",
        "",
    ]
    return "\n".join(lines)


def commit_count(md_text):
    m = re.search(r"^提交:(\d+)", md_text, re.M)
    return int(m.group(1)) if m else 0


# ── 索引 ─────────────────────────────────────────────────────────────────────
def rebuild_index():
    files = sorted(glob.glob(str(DAILY_DIR / "20[0-9][0-9]-[0-9][0-9]-[0-9][0-9].md")), reverse=True)
    rows = []
    for f in files:
        date = os.path.basename(f)[:-3]
        txt = Path(f).read_text(encoding="utf-8")
        first = next((l for l in txt.splitlines() if l.startswith("### ")), "")
        rows.append(f"| {date} | [{date}.md]({date}.md) | {commit_count(txt)} |")
    block = (
        START + "\n"
        "\n| 日期 | 日报 | 提交数 |\n|---|---|---|\n"
        + ("\n".join(rows) if rows else "| — | — | — |")
        + "\n\n" + END
    )
    if INDEX.exists():
        cur = INDEX.read_text(encoding="utf-8")
        if START in cur and END in cur:
            new = re.sub(re.escape(START) + r".*?" + re.escape(END), block, cur, flags=re.S)
            INDEX.write_text(new, encoding="utf-8")
            return len(rows)
    INDEX.write_text(INDEX_HEADER + block + "\n", encoding="utf-8")
    return len(rows)


INDEX_HEADER = """# MBA 日报

每天盘点**前一天合并到 main 的工作**(提交 / PR),持续记录。数据源是 git,可验证。
由 `scripts/new_daily.py` 生成,每日定时任务(`.github/workflows/daily-report.yml`)自动落库。
用 `python3 scripts/new_daily.py week <日期>` 可把一周日报合成周报草稿,喂给 `new_weekly.py`。

"""


# ── 周报合成 ─────────────────────────────────────────────────────────────────
def synth_week(date):
    monday = date - datetime.timedelta(days=date.weekday())
    days = [monday + datetime.timedelta(days=i) for i in range(7)]
    by_type, total, prs = {}, 0, set()
    have = []
    for d in days:
        f = DAILY_DIR / f"{d.isoformat()}.md"
        if not f.exists():
            continue
        have.append(d.isoformat())
        txt = f.read_text(encoding="utf-8")
        cur = None
        for line in txt.splitlines():
            if line.startswith("### "):
                name = re.sub(r"\(\d+\)\s*$", "", line[4:]).strip()
                cur = name
            elif line.startswith("- ") and cur:
                by_type.setdefault(cur, []).append(line[2:])
                total += 1
                for m in re.finditer(r"#(\d+)\]", line):
                    prs.add(m.group(1))
            elif line.startswith("## "):
                cur = None
    out = [
        f"# 周报合成草稿 · {monday.isoformat()} ~ {(monday + datetime.timedelta(days=6)).isoformat()}",
        "",
        f"> 由 {len(have)} 份日报合成({'、'.join(have) or '无'});共 {total} 项、约 {len(prs)} 个 PR。"
        f"粘进 `scripts/new_weekly.py new` 的 Markdown 后精简成叙事。",
        "",
    ]
    for name, arr in by_type.items():
        out.append(f"## {name}({len(arr)})")
        out += [f"- {x}" for x in arr]
        out.append("")
    return "\n".join(out)


# ── 命令 ─────────────────────────────────────────────────────────────────────
def cmd_new(args):
    date = parse_date(args.date) if args.date else yesterday()
    all_commits = git_commits(args.ref)
    items = [c for c in all_commits if c[0] == date]
    if not items and not args.allow_empty:
        print(f"[daily] {date} 无合并到 main 的提交 —— 跳过(用 --allow-empty 强制写占位)。")
        return 0
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    out = DAILY_DIR / f"{date.isoformat()}.md"
    # 保留已手填的「补充说明」——重生成只刷新 git 派生的工作盘点,不清掉人工内容。
    note = extract_supplement(out.read_text(encoding="utf-8")) if out.exists() else ""
    out.write_text(render_daily(date, items, note=note or None), encoding="utf-8")
    kept = "（保留已手填补充说明）" if note else ""
    n = rebuild_index()
    print(f"[daily] 写入 docs/daily/{date.isoformat()}.md（{len(items)} 项）{kept} · 索引 {n} 天")
    return 0


def cmd_week(args):
    date = parse_date(args.date) if args.date else yesterday()
    print(synth_week(date))
    return 0


def cmd_index(_args):
    n = rebuild_index()
    print(f"[daily] 索引重建 —— {n} 天")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="MBA 每日工作日报")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_new = sub.add_parser("new", help="生成某日日报(默认昨天)")
    p_new.add_argument("date", nargs="?")
    p_new.add_argument("--ref", default="HEAD", help="盘点哪个 ref 的提交(默认 HEAD)")
    p_new.add_argument("--allow-empty", action="store_true", help="无提交也写占位")
    p_new.set_defaults(func=cmd_new)
    p_week = sub.add_parser("week", help="把某日所在周的日报合成周报草稿")
    p_week.add_argument("date", nargs="?")
    p_week.set_defaults(func=cmd_week)
    sub.add_parser("index", help="重建索引").set_defaults(func=cmd_index)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
