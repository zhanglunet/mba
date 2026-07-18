#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_candidate.py — 舆情事件「候选取数」半自动助手(反捏造前提下减负)。

把手工加事件里**机械**的部分自动化,但**判断字段留人工**、**引用只来自真实源站**:

  draft <url> [<url> ...] [--brand SLUG]
      curl 每个 URL(走 $HTTPS_PROXY 出口 + CA + 浏览器 UA),提取**逐字标题**、
      抓 URL 内嵌日期、猜 source_type、(给 --brand 时)算下一个事件 id 并查维度适用性,
      打印一段**候选事件 YAML 草稿**到 stdout。dim/severity/direction/lens_map 标 TODO,
      由人工核验后再粘进 watch/<slug>/events.yaml。**脚本从不编造 quote**——只回填 curl
      到的真实标题(quote_type: title)。

  verify [--brand SLUG]
      反捏造自审 + 死链检测:对所有 quote_type=title 的事件,重新 curl url,核对其
      quote 是否仍在源站标题里(去空白/实体后规范化匹配)。报告 OK / MISMATCH / DEAD。
      **需要网络**(和 draft 一样只在本机/有出口的环境跑,不进 CI —— CI 不出网)。

用法示例:
  python3 scripts/watch-tools/fetch_candidate.py draft https://... --brand spacex
  python3 scripts/watch-tools/fetch_candidate.py verify --brand asiainfo
"""
import argparse
import datetime
import glob
import html as htmlmod
import os
import re
import subprocess
import sys

try:
    import yaml
except ImportError:
    print("fetch_candidate: 需要 PyYAML(pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WATCH = os.path.join(ROOT, "watch")
MATRIX = os.path.join(WATCH, "matrix.yaml")
CA = "/root/.ccr/ca-bundle.crt"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# 站名后缀分隔符:标题里 " - 站名" / " | 站名" / "_站名" 常见,取正文部分。
SUFFIX_SEPS = [" - ", " | ", " – ", "_", " — "]
# 域名 → source_type(与 validate_watch 的枚举一致)
SOURCE_BY_HOST = [
    (("xueqiu.com", "eastmoney.com", "10jqka.com.cn", "guba"), "investor_community"),
    (("finance.sina", "stcn.com", "cnstock", "yicai.com", "21jingji.com", "caixin",
      "wallstreetcn", "sahmcapital.com", "investing.com", "bloomberg", "reuters.com/markets"), "finance"),
    (("weibo.com", "zhihu.com", "xiaohongshu", "douyin", "x.com", "twitter.com"), "social"),
    (("gov.cn", "samr.gov", "miit.gov", "fcc.gov", "sec.gov", "court.gov"), "regulator"),
    (("google.", "baidu.com/s", "bing.com"), "search"),
]


def norm(s):
    """去空白 + HTML 实体解码 + 全半角常见标点归一,用于反捏造匹配。"""
    s = htmlmod.unescape(str(s))
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", "", s)


def curl(url, timeout=25):
    cmd = ["curl", "-sSL", "--max-time", str(timeout), "-A", UA]
    if os.path.exists(CA):
        cmd += ["--cacert", CA]
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def extract_titles(html):
    """返回 (title_tag, h1)。都做 HTML 实体解码。"""
    t = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    h = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    def clean(m):
        if not m:
            return ""
        x = re.sub(r"<[^>]+>", "", m.group(1))  # 去内层标签
        return htmlmod.unescape(x).strip()
    return clean(t), clean(h)


def strip_suffix(title):
    """去掉 " - 站名" / "_站名" 这类尾缀,取文章标题正文。保守:尾缀 ≤14 字才切。"""
    best = title
    for sep in SUFFIX_SEPS:
        idx = title.rfind(sep)
        if idx > 0:
            head, tail = title[:idx], title[idx + len(sep):]
            if 0 < len(tail) <= 14 and head:
                if len(head) < len(best):
                    best = head
    return best.strip()


def url_date(url):
    m = re.search(r"(20\d{2})[/\-_]?(\d{2})[/\-_]?(\d{2})", url)
    if not m:
        return None
    y, mo, d = m.groups()
    try:
        return datetime.date(int(y), int(mo), int(d)).isoformat()
    except ValueError:
        return None


def guess_source(url):
    for hosts, st in SOURCE_BY_HOST:
        if any(h in url for h in hosts):
            return st
    return "media"


def next_id(slug, date):
    path = os.path.join(WATCH, slug, "events.yaml")
    n = 0
    if os.path.exists(path):
        for e in (yaml.safe_load(open(path, encoding="utf-8")) or []):
            m = re.search(rf"-{re.escape(slug)}-(\d+)$", str(e.get("id", "")))
            if m:
                n = max(n, int(m.group(1)))
    return f"{date or 'YYYY-MM-DD'}-{slug}-{n + 1:03d}"


def brand_dims(slug):
    if not os.path.exists(MATRIX):
        return {}
    brands = (yaml.safe_load(open(MATRIX, encoding="utf-8")) or {}).get("brands", {})
    dims = brands.get(slug) or {}
    return {k: ("on" if v is True else "off" if v is False else v) for k, v in dims.items()}


# ── draft ────────────────────────────────────────────────────────────────────
def cmd_draft(args):
    slug = args.brand
    dims = brand_dims(slug) if slug else {}
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    applicable = [d for d, v in dims.items() if v != "off"] if dims else []
    print(f"# fetch_candidate draft —— 候选事件,dim/severity/direction/lens_map 待人工核验")
    if slug:
        print(f"# 品牌 {slug} 可用维度(非 off):{'/'.join(applicable) or '—'}")
    for url in args.urls:
        html = curl(url)
        if html is None:
            print(f"\n# ⚠️ curl 失败(出口未放行 / 反爬 / 超时):{url}")
            continue
        tt, h1 = extract_titles(html)
        # 优先用较干净的:h1 通常无站名尾缀
        raw = h1 if (h1 and len(h1) <= len(tt or h1)) else tt
        quote = strip_suffix(raw or tt or "")
        date = url_date(url)
        st = guess_source(url)
        warn = "  # ⚠️ 超 100 字,需缩短或改摘句" if len(quote) > 100 else ""
        eid = next_id(slug, date) if slug else f"{date or 'YYYY-MM-DD'}-<slug>-NNN"
        print(f"""
- id: {eid}
  date: {date or 'YYYY-MM-DD   # ⚠️ URL 无内嵌日期,curl 正文核对'}
  dim: W?            # TODO 人工:该品牌非 off 的维度
  severity: P?       # TODO 人工:P0..P3
  direction: neutral # TODO 人工:pos/neg/neutral/mixed(model-judged)
  direction_by: model-judged
  title: "{quote}"   # TODO 人工:改写成描述性标题(可保留要点)
  quote: "{quote}"{warn}
  quote_type: title
  url: {url}
  fetched_at: "{now}"
  lens_map: [signal] # TODO 人工:⊆ origin/category/leverage/identity/signal
  source_type: {st}
  note: "候选自动取数,已 curl 核对逐字标题;日期以 URL 内嵌自证。待人工定维度/等级/方向。\"""".rstrip())
    print("\n# 核验后粘进 watch/<slug>/events.yaml,再跑 validate_watch.py。")
    return 0


# ── verify ───────────────────────────────────────────────────────────────────
def cmd_verify(args):
    files = sorted(glob.glob(os.path.join(WATCH, "*", "events.yaml")))
    if args.brand:
        files = [f for f in files if os.path.basename(os.path.dirname(f)) == args.brand]
    ok = mismatch = dead = skip = 0
    for path in files:
        slug = os.path.basename(os.path.dirname(path))
        for e in (yaml.safe_load(open(path, encoding="utf-8")) or []):
            if not isinstance(e, dict) or e.get("quote_type") != "title":
                skip += 1
                continue
            html = curl(e.get("url", ""))
            if html is None:
                print(f"DEAD     {slug}/{e.get('id')} — curl 失败 {e.get('url')}")
                dead += 1
                continue
            tt, h1 = extract_titles(html)
            page = norm((tt or "") + "\x1f" + (h1 or ""))
            if norm(e.get("quote", "")) in page:
                ok += 1
            else:
                print(f"MISMATCH {slug}/{e.get('id')} — quote 不在源站标题里")
                print(f"           quote: {e.get('quote')}")
                print(f"           title: {tt}")
                mismatch += 1
    print(f"\nverify: ✅ {ok} 命中 · ⚠️ {mismatch} 不符 · 💀 {dead} 死链 · ⏭ {skip} 跳过(非 title 引用)")
    return 1 if (mismatch or dead) else 0


# ── discover ─────────────────────────────────────────────────────────────────
# 每品牌拉 Google News RSS,dedup 现有事件,emit 候选草稿(判断字段留 TODO)。
# 与 draft 同哲学:脚本只回填**源 feed 的逐字标题/日期/URL**,从不编造 quote,也不擅自定
# dim/severity/direction/lens_map —— 那是人工/评委判断(docs/15 §边界:direction 是显式标注)。
GNEWS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def _published_slugs():
    path = os.path.join(ROOT, "site", "published-reports.txt")
    out = []
    if os.path.exists(path):
        for ln in open(path, encoding="utf-8"):
            s = ln.strip()
            if s and not s.startswith("#"):
                out.append(s)
    return out


def _brand_query(slug):
    """品牌搜索词:优先 reports-meta 的 brand_en(Google News 英文召回好),回退 slug。"""
    meta_path = os.path.join(ROOT, "site", "reports-meta.yaml")
    try:
        reports = (yaml.safe_load(open(meta_path, encoding="utf-8")) or {}).get("reports", [])
        for r in reports:
            if r.get("slug") == slug:
                return r.get("brand_en") or r.get("brand_cn") or slug
    except Exception:
        pass
    return slug


def _existing(slug):
    path = os.path.join(WATCH, slug, "events.yaml")
    urls, titles = set(), set()
    if os.path.exists(path):
        for e in (yaml.safe_load(open(path, encoding="utf-8")) or []):
            if isinstance(e, dict):
                if e.get("url"):
                    urls.add(str(e["url"]).strip())
                for k in ("quote", "title"):
                    if e.get(k):
                        titles.add(norm(strip_suffix(str(e[k]))))
    return urls, titles


def cmd_discover(args):
    import json
    import urllib.parse
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime

    slugs = [args.brand] if args.brand else _published_slugs()
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# fetch_candidate discover —— 每日自动**发现**的候选事件(判断字段待人工核验)",
        f"# 采源 Google News RSS · 窗口 {args.days} 天 · 生成 {now}",
        "# 反捏造:url/quote/date 取自源 feed;dim/severity/direction/lens_map 为 TODO,由人工/评委判断。",
        "# 核验后把合规项粘进 watch/<slug>/events.yaml、删本候选,再跑 validate_watch.py。",
    ]
    total_new = 0
    for slug in slugs:
        q = urllib.parse.quote(f"{_brand_query(slug)} when:{args.days}d")
        xml = curl(GNEWS.format(q=q))
        if xml is None:
            lines.append(f"\n## {slug} —— ⚠️ RSS 拉取失败(出口/超时)")
            continue
        try:
            items = ET.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml).findall(".//item")
        except Exception as e:
            lines.append(f"\n## {slug} —— ⚠️ RSS 解析失败:{e}")
            continue
        urls, titles = _existing(slug)
        dims = brand_dims(slug)
        applicable = "/".join(d for d, v in dims.items() if v != "off") or "—"
        new = []
        seen = set()
        for it in items:
            t = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            try:
                d = parsedate_to_datetime(it.findtext("pubDate") or "").date().isoformat()
            except Exception:
                d = None
            key = norm(strip_suffix(t))
            if not t or not link or not key or key in seen:
                continue
            if link in urls or key in titles:
                continue
            seen.add(key)
            new.append((t, d, link))
        if not new:
            lines.append(f"\n## {slug} —— 无新候选(窗口内 {args.days} 天)")
            continue
        omitted = max(0, len(new) - args.limit)
        shown = new[: args.limit]
        total_new += len(shown)
        more = f"(另 {omitted} 条同题材省略,防噪音灌水)" if omitted else ""
        lines.append(f"\n## {slug} —— {len(shown)} 条新候选{more} · 可用维度(非 off):{applicable}")
        nid = 0
        for t, d, link in shown:
            nid += 1
            quote, src = (t.rsplit(" - ", 1) + [None])[:2]
            quote = quote.strip()[:100]
            eid = next_id(slug, d)  # next_id 只看已入库事件,批内多条人工顺延 NNN
            qj = json.dumps(quote, ensure_ascii=False)
            src_hint = f"(来源:{src})" if src else ""
            lines.append(f"""
- id: {eid}          # ⚠️ 批内多条时人工顺延 NNN
  date: {d or 'YYYY-MM-DD'}
  dim: W?            # TODO 人工:{applicable} 里选
  severity: P?       # TODO 人工:P0..P3
  direction: neutral # TODO 人工:pos/neg/neutral/mixed(model-judged)
  direction_by: model-judged
  title: {qj}   # TODO 人工:改写成描述性标题
  quote: {qj}
  quote_type: title
  url: {link}
  fetched_at: "{now}"
  lens_map: [signal] # TODO 人工:⊆ origin/category/leverage/identity/signal
  source_type: media # TODO 人工:official/media/finance/regulator... {src_hint}
  note: "每日自动发现候选;标题/日期/URL 取自 Google News RSS。待人工定维度/等级/方向后入库。\"""".rstrip())
    out = "\n".join(lines) + "\n"
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        open(args.out, "w", encoding="utf-8").write(out)
        print(f"discover: {total_new} 条新候选 → {args.out}")
    else:
        print(out)
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="舆情事件候选取数 / 自动发现 / 反捏造自审")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pd = sub.add_parser("draft", help="URL → 候选事件草稿")
    pd.add_argument("urls", nargs="+")
    pd.add_argument("--brand", help="品牌 slug(算下一个 id + 查维度适用性)")
    pd.set_defaults(func=cmd_draft)
    pv = sub.add_parser("verify", help="重新 curl 核对 title 引用仍逐字命中源站")
    pv.add_argument("--brand", help="只核某个品牌")
    pv.set_defaults(func=cmd_verify)
    pg = sub.add_parser("discover", help="每日自动发现:Google News RSS → dedup → 候选草稿")
    pg.add_argument("--brand", help="只发现某个品牌(默认全部已发布品牌)")
    pg.add_argument("--days", type=int, default=7, help="回看窗口天数(默认 7)")
    pg.add_argument("--limit", type=int, default=12, help="每品牌候选上限(防噪音灌水,默认 12)")
    pg.add_argument("--out", help="写入文件(如 watch/_candidates/<date>.md);缺省打印 stdout")
    pg.set_defaults(func=cmd_discover)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
