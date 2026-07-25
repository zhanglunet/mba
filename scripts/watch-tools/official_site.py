#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""官网新闻页直采 —— 给 Google News 不收录的品牌兜底。

## 为什么要这个

`fetch_candidate.py discover` 的两路召回都走 Google News RSS:
① 品牌名(媒体转述)② `site:<官方新闻源>`(一手原文)。
但**部分中文品牌的官网 Google News 根本不索引**——2026-07-25 实测
`moonshot.cn` / `about.meituan.com` / `dji.com/newsroom` 的 `site:` 召回**均为 0**。
这些品牌只能靠媒体转述,官方口径进不来。本模块是第三路:**直接抓官网新闻页**。

## 为什么不写"每站一套 CSS 选择器"

那是最容易想到、也最难维护的做法:站点改版即静默失效,而 CI 不出网、无法回归。
实测发现更好的抓手——**现代官网多是 Next.js / Nuxt,数据以 JSON 内嵌在页面里**
(美团新闻中心的 `__NEXT_DATA__` 里就有 `newsCenterlist`,字段齐整还带日期)。
所以这里做的是**通用提取**:抽出内嵌 JSON → 自动找"看起来像新闻列表"的对象数组
(≥3 条、且 ≥60% 的条目同时有标题类字段与日期类字段)→ 取最大的那个。
**不写死任何站点的路径**,换站点、站点改版只要还用同一套框架就仍然能跑。

## 边界(与反捏造一致)

- 只搬运**标题 / 日期 / 链接**,逐字取自页面,**不改写不翻译不生成**。
- dim / severity / direction 一律留给后续分类环节判断,本模块不碰。
- 拿不到就**如实报 0**(调用方会告警),**绝不编造条目**。

## 已知不适用

纯客户端渲染、数据走 XHR 的站点抓不到(实测:好未来 `100tal.com/news` 的 HTML 里
只有页面标题与月份选择器,新闻走 `gw-web-api.100tal.com` 接口)。
微博是登录墙(`Sina Visitor System`)、微信公众号的发现入口(搜狗)是 JS 壳,
**curl 都拿不到**——这两条路要真做得上带登录态的云浏览器,不在本模块范围。

    python3 scripts/watch-tools/official_site.py --selftest        # 离线自检(用 fixture)
    python3 scripts/watch-tools/official_site.py --url <新闻页 URL> # 手动试一个站
"""

import os, re, sys, json, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

# 标题 / 日期字段的常见命名(按优先级)。新站点若用了新叫法,加在这里即可,不必写选择器。
TITLE_KEYS = ("newsTitle", "title", "headline", "articleTitle", "subject", "name")
DATE_KEYS = ("newsDate", "date", "publishTime", "publishedAt", "createTime",
             "createdAt", "releaseTime", "pubDate", "time")
LINK_KEYS = ("url", "link", "href", "detailUrl", "newsUrl", "path")
ID_KEYS = ("newsNo", "id", "articleId", "newsId")

MIN_ITEMS = 3          # 少于这么多条,不像是新闻列表
MATCH_RATIO = 0.6      # 至少这么大比例的条目要同时有标题与日期


def _pick(d, keys):
    for k in keys:
        v = d.get(k)
        if isinstance(v, (str, int)) and str(v).strip():
            return str(v).strip()
    return ""


def extract_embedded_json(html):
    """抽出页面里内嵌的状态 JSON(Next.js / Nuxt / 通用 __INITIAL_STATE__)。拿不到返回 None。"""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except ValueError:
            pass
    for pat in (r"window\.__NUXT__\s*=\s*(\{.*?\});?\s*</script>",
                r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});?\s*</script>"):
        m = re.search(pat, html, re.S)
        if m:
            try:
                return json.loads(m.group(1))
            except ValueError:
                pass   # Nuxt 常把状态序列化成函数,不是合法 JSON —— 属正常,交给调用方报 0
    return None


def find_feeds(obj, path="", out=None, depth=0):
    """递归找"像新闻列表"的对象数组 → [(json路径, 条数, 条目列表)]。"""
    out = [] if out is None else out
    if depth > 8:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            find_feeds(v, f"{path}.{k}", out, depth + 1)
    elif isinstance(obj, list):
        dicts = [x for x in obj if isinstance(x, dict)]
        if len(dicts) >= MIN_ITEMS:
            hit = sum(1 for x in dicts if _pick(x, TITLE_KEYS) and _pick(x, DATE_KEYS))
            if hit >= max(MIN_ITEMS, int(len(dicts) * MATCH_RATIO)):
                out.append((path, len(dicts), dicts))
        for i, v in enumerate(obj[:8]):
            find_feeds(v, f"{path}[{i}]", out, depth + 1)
    return out


def _norm_date(s):
    """把常见写法归一到 YYYY-MM-DD;认不出就返回空(**不猜**)。"""
    s = str(s or "").strip()
    m = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    if re.fullmatch(r"\d{13}", s):      # 毫秒时间戳
        import datetime
        return datetime.datetime.utcfromtimestamp(int(s) / 1000).date().isoformat()
    if re.fullmatch(r"\d{10}", s):      # 秒时间戳
        import datetime
        return datetime.datetime.utcfromtimestamp(int(s)).date().isoformat()
    return ""


def parse_news(html, base_url=""):
    """页面 HTML → [{title, date, url}](按日期倒序)。抓不到就返回**空列表**,绝不编造。"""
    data = extract_embedded_json(html)
    if data is None:
        return []
    feeds = sorted(find_feeds(data), key=lambda x: -x[1])
    if not feeds:
        return []
    _, _, items = feeds[0]
    out, seen = [], set()
    for it in items:
        title = _pick(it, TITLE_KEYS)
        date = _norm_date(_pick(it, DATE_KEYS))
        if not title or title in seen:
            continue
        seen.add(title)
        link = _pick(it, LINK_KEYS)
        if link and not link.startswith("http") and base_url:
            link = base_url.rstrip("/") + "/" + link.lstrip("/")
        if not link:                     # 没有独立链接时退回列表页 + 条目 id(仍是真实可核 URL)
            nid = _pick(it, ID_KEYS)
            link = f"{base_url}#{nid}" if (base_url and nid) else base_url
        out.append({"title": title, "date": date, "url": link})
    out.sort(key=lambda x: x["date"] or "", reverse=True)
    return out


def _selftest():
    checks, fails = 0, []

    def ok(cond, name):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(name)

    # ① Next.js 形状(美团新闻中心的真实结构,字段名照抄实测结果)
    nextjs = json.dumps({"props": {"pageProps": {"newsCenterlist": [
        {"newsTitle": "美团试点骑手“等灯停表”", "newsDate": "2026-07-17", "newsNo": "A1", "newsOrigin": "央广网"},
        {"newsTitle": "让AI走进物理世界,清华大学和美团开启新一期合作", "newsDate": "2026-07-15", "newsNo": "A2"},
        {"newsTitle": "美团发布首届“司南口腔榜”", "newsDate": "2026-07-10", "newsNo": "A3"},
    ], "newsTypeList": [{"typeName": "全部", "typeVal": "all"}]}}}, ensure_ascii=False)
    html = f'<html><script id="__NEXT_DATA__" type="application/json">{nextjs}</script></html>'
    got = parse_news(html, "https://about.meituan.com/news")
    ok(len(got) == 3, "next.js:抽出全部 3 条")
    ok(got[0]["date"] == "2026-07-17", "next.js:按日期倒序")
    ok("等灯停表" in got[0]["title"], "next.js:标题逐字搬运")
    ok(got[0]["url"].startswith("https://about.meituan.com/news"), "next.js:无独立链接时回落列表页+id")
    # newsTypeList 只有 3 条但没有日期字段 —— 不能被误当成新闻列表
    ok(all("typeName" not in str(x["title"]) for x in got), "只挑同时有标题与日期的数组")

    # ② 拿不到就如实报 0(**绝不编造**)——这是本模块最重要的性质
    ok(parse_news("<html><body>纯客户端渲染,没有内嵌 JSON</body></html>") == [],
       "无内嵌 JSON → 返回空,不编造")
    ok(parse_news('<html><script>window.__NUXT__={};window.__NUXT__.config={a:1}</script></html>') == [],
       "Nuxt 只有 config(好未来那种)→ 返回空,不编造")
    ok(parse_news("") == [], "空页面 → 返回空")

    # ③ 日期归一:认不出就留空,不猜
    ok(_norm_date("2026-07-17") == "2026-07-17", "日期:ISO")
    ok(_norm_date("2026年7月5日") == "2026-07-05", "日期:中文写法")
    ok(_norm_date("2026/07/17 10:00") == "2026-07-17", "日期:斜杠+时间")
    ok(_norm_date("上周") == "", "日期:认不出留空(不猜)")

    # ④ 通用性:换一套字段名(title/publishTime)也要能认
    alt = json.dumps({"data": {"list": [
        {"title": f"公告 {i}", "publishTime": f"2026-07-{10+i:02d}", "url": f"/n/{i}"} for i in range(4)]}})
    got2 = parse_news(f'<html><script id="__NEXT_DATA__">{alt}</script></html>', "https://x.com")
    ok(len(got2) == 4 and got2[0]["url"] == "https://x.com/n/3",
       "通用:换字段名仍能认 + 相对链接补全")

    print(f"official_site --selftest: "
          f"{'✅ ' + str(checks) + ' 组断言全部通过' if not fails else '❌ 失败: ' + ', '.join(fails)}")
    return 1 if fails else 0


def main(argv):
    ap = argparse.ArgumentParser(description="官网新闻页直采(通用内嵌 JSON 提取)")
    ap.add_argument("--url", help="试抓一个新闻页")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not args.url:
        ap.error("给 --url 或 --selftest")
    sys.path.insert(0, HERE)
    import fetch_candidate as fc
    html = fc.curl(args.url)
    if html is None:
        print(f"official_site: 拉取失败 {args.url}", file=sys.stderr)
        return 1
    items = parse_news(html, args.url)
    print(f"official_site: {args.url} → {len(items)} 条")
    for it in items[:10]:
        print(f"  {it['date'] or '????-??-??'}  {it['title'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
