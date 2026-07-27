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


# 行情页 / 纯 ticker 等噪音标题(discover 中文源里高频):不是"事件",别入候选。
# 保守:只挡明显的行情/报价页与极短无信息标题,避免误伤真新闻(如提到"市值/股价"的报道)。
_NOISE_RE = re.compile(
    r"股票股价|实时行情|资金流向|千股千评|股吧|行情中心|历史行情|个股行情|最新股价"
    r"|Stock\s*Price.*Quote|Quote.*Stock\s*Price|\bNASDAQ:\s|\bNYSE:\s|\bstock\s+quote\b",
    re.I,
)


def is_noise(title):
    """True = 行情/报价页或纯 ticker 等噪音,不入候选。"""
    t = (title or "").strip()
    if _NOISE_RE.search(t):
        return True
    core = strip_suffix(t)
    # 极短、基本没信息量(如 "谷歌-A")
    if len(core.replace(" ", "")) <= 4:
        return True
    # 纯 ticker 标题(如 "GOOGL" / "BABA")
    if re.fullmatch(r"[A-Z]{2,6}(\.[A-Z]{1,4})?", core.strip()):
        return True
    # 官网**分页 / 栏目 / 资源页**——2026-07-25 接官方源后冒出来的新噪音:
    # "Transformation - Page 37 of 37" / "Tech in Action - Page 41 of 41" /
    # "Floodlights-G1131097396" / "Device as a Service"(产品目录页)。
    # 它们是站点结构页,不是新闻,进了候选只会白烧分类预算。
    if re.search(r"\bPage\s+\d+\s+of\s+\d+\b", core, re.I):
        return True
    if re.fullmatch(r"[\w \u2019'&-]{0,40}-[A-Z]?\d{6,}", core.strip()):
        return True
    return False


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
# 中文源:标题直接是中文(取自中文媒体),满足「候选标题中文化」且**不做翻译**——
# quote 仍是源站逐字标题(反捏造:中文标题来自中文源,非机器翻译)。
GNEWS = "https://news.google.com/rss/search?q={q}&hl=zh-CN&gl=CN&ceid=CN:zh"
# 官方源(site:)必须走**英文档**:2026-07-25 实测,13 个官方新闻源在中文档召回
# 几乎全为 0(anthropic.com/news → 0),英文档 13/13 全有(anthropic 16 条,
# 首条即 "Introducing Claude Opus 5")。官方条目标题因此是英文一手原文——
# 反捏造不变:quote 仍是源 feed 逐字标题,不翻译、不改写。
GNEWS_EN = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def _published_slugs():
    path = os.path.join(ROOT, "site", "published-reports.txt")
    out = []
    if os.path.exists(path):
        for ln in open(path, encoding="utf-8"):
            s = ln.strip()
            if s and not s.startswith("#"):
                out.append(s)
    return out


ATOM_NS = "{http://www.w3.org/2005/Atom}"


def parse_feed(xml):
    """任意 RSS 2.0 / Atom feed → [{title, link, date}](date 归一为 YYYY-MM-DD,认不出留空)。

    给 `rss_feeds`(§9.9 免费社媒线)用:自托管 RSSHub 输出 RSS 2.0,但"任意 RSS 源"
    的承诺意味着 Atom 也要认(GitHub releases.atom 就是 Atom)。**解析失败返回空列表,
    绝不编造**;标题/链接逐字取自 feed,反捏造同官网直采。
    """
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime
    if not xml:
        return []
    try:
        root = ET.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
    except Exception:
        return []
    out = []
    for it in root.findall(".//item"):                      # RSS 2.0
        t = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        raw = (it.findtext("pubDate") or "").strip()
        try:
            d = parsedate_to_datetime(raw).date().isoformat()
        except Exception:
            m = re.search(r"20\d{2}-\d{2}-\d{2}", raw)
            d = m.group(0) if m else ""
        if t and link:
            out.append({"title": t, "link": link, "date": d})
    for e in root.findall(f".//{ATOM_NS}entry"):            # Atom
        t = (e.findtext(f"{ATOM_NS}title") or "").strip()
        ln = e.find(f"{ATOM_NS}link")
        link = (ln.get("href") if ln is not None else "").strip()
        raw = (e.findtext(f"{ATOM_NS}published") or e.findtext(f"{ATOM_NS}updated") or "").strip()
        m = re.search(r"20\d{2}-\d{2}-\d{2}", raw)
        if t and link:
            out.append({"title": t, "link": link, "date": m.group(0) if m else ""})
    return out


ENV_PLACEHOLDER = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")


def expand_secrets(url):
    """把 `rss_feeds` URL 里的 `${ENV_NAME}` 占位符换成环境变量真值。

    **为什么非有这层不可**:本仓库是**公开仓库**,而 RSSHub 的 `ACCESS_KEY` 必须跟在 URL 上
    (`?key=…`)。把密钥直接写进 `site/reports-meta.yaml` = **把密钥公开发布**。
    故 meta 里只存占位符(`?key=${RSSHUB_KEY}`),真值走 GitHub Actions secrets → 环境变量,
    只在 runner 内存里出现。

    返回 `(真实URL, 缺失的变量名列表)`。**缺失时调用方必须跳过、不要发请求** ——
    带空 key 去请求会被 RSSHub 拒(403/401),表现得像"路由挂了",
    等于**把配置错误伪装成源站故障**,排错时会追错方向。

    ⚠️ 调用方打日志/写候选 md 时**一律打模板串(未展开的那个)**,不能打返回值 ——
    否则密钥会进公开 Actions 日志和提交进仓库的候选文件。
    """
    if not url:
        return url, []
    missing = []

    def sub(m):
        v = os.environ.get(m.group(1), "")
        if not v.strip():
            missing.append(m.group(1))
            return m.group(0)
        return v

    return ENV_PLACEHOLDER.sub(sub, url), missing


def _apply_quota(off, own, soc, med, limit):
    """把四类召回按名额合成最终候选列表。抽成纯函数是为了能真跑断言,而不是只读源码。

    四类:`off`=官方源 · `own`=**自备 RSS**(用户逐条配进 meta 的 RSSHub 微博等) ·
    `soc`=社区泛查询(`site:zhihu.com`)· `med`=媒体。

    名额规则(两条都是踩坑踩出来的):
      - `off ≤ limit/2`:2026-07-25 首次接线时按原序取 `new[:limit]`,官方条目被整段截掉;
        反过来让官方优先排序,又把媒体面整段挤掉(184 条里 98 条官方)。故给一半保留名额。
      - **社区总名额 ≤ limit/4,且桶内 `own` 排在 `soc` 前面**:2026-07-27 实测发现,
        自备 RSS 与知乎共用一个桶且**排在知乎后面** —— meituan 上 `soc` 有 53 条(知乎泛查询),
        `soc[:3]` 全被知乎占满,**自备 RSS 的 10 条 100% 被挤掉**。更糟的是它**静默**:
        源确实抓到了条目,哨兵不会响,看起来一切正常。用户显式配进 meta 的源,
        优先级必须高于泛查询 —— 这是"有意配置 > 顺带召回"。

    媒体拿剩余名额;都不满时按 官方 → 社区 顺序回填,总数不超过 limit。
    """
    q_off = max(1, limit // 2)
    q_soc = max(1, limit // 4)
    social = (own + soc)[:q_soc]                      # 桶内 own 优先,余额才给泛查询
    shown = (off[:q_off] + social + med)[:limit]
    if len(shown) < limit:
        for pool in (off[q_off:], (own + soc)[q_soc:]):
            shown += [x for x in pool if x not in shown][: limit - len(shown)]
    return shown


def _brand_rss_feeds(slug):
    """该品牌的自备 RSS 源列表(§9.9:自托管 RSSHub 的微博/小红书路由填这里)。

    reports-meta 的 `rss_feeds` 接受**字符串或列表**;没配返回 []——保持原行为,无回归。
    这是免费社媒线的对接口:用户本地 RSSHub 跑通后把 URL 填进 meta,当天流水线即开吃,
    仓库侧零改动。
    """
    for r in _meta_reports():
        if r.get("slug") == slug:
            v = r.get("rss_feeds")
            if isinstance(v, str):
                return [v] if v.strip() else []
            if isinstance(v, list):
                return [str(x) for x in v if str(x).strip()]
            return []
    return []


def _brand_news_page(slug):
    """该品牌的**官网新闻页 URL**(直采兜底),没配则 None。

    给 Google News **不索引官网**的品牌用(实测 `site:about.meituan.com` 召回 0)。
    抓取与解析在 `official_site.py`(通用内嵌 JSON 提取,不写死站点选择器)。
    """
    for r in _meta_reports():
        if r.get("slug") == slug:
            return r.get("news_page") or None
    return None


def _brand_news_site(slug):
    """该品牌的**官方新闻源**(域名或域名+路径),没配则 None。

    2026-07-25 起:此前 discover 的唯一信息源是 Google News 的**品牌名**查询,
    所以官方发布只能靠中文媒体转述被动捡回 —— Anthropic 发 Opus 5 那天,库里进的是
    「中国模型加速AI明星内卷,Anthropic上新Opus 5……」(Opus 5 只是从句),
    官方公告本身没进库。加一条 `site:<官方新闻源>` 查询即可召回一手原文。

    **只给实测召回有效的品牌配**(见 docs/16 §9.6 的召回表):
    根域名不行(`site:apple.com` 会召回 Apple Music 歌曲页、`site:tesla.com` 召回招聘页),
    必须锚到**新闻室子域或路径**(`apple.com/newsroom` / `news.microsoft.com`)。
    中文品牌的官网 Google News 基本不收录(moonshot.cn / about.meituan.com 召回 0),
    故**留空** —— 留空即保持原行为,无回归。
    """
    for r in _meta_reports():
        if r.get("slug") == slug:
            return r.get("news_site") or None
    return None


def _meta_reports():
    meta_path = os.path.join(ROOT, "site", "reports-meta.yaml")
    try:
        return (yaml.safe_load(open(meta_path, encoding="utf-8")) or {}).get("reports", [])
    except Exception:
        return []


def _brand_query(slug):
    """品牌搜索词:中文源下用「brand_cn brand_en」组合(中文召回优先、英文名兜底),回退 slug。"""
    meta_path = os.path.join(ROOT, "site", "reports-meta.yaml")
    try:
        reports = (yaml.safe_load(open(meta_path, encoding="utf-8")) or {}).get("reports", [])
        for r in reports:
            if r.get("slug") == slug:
                cn, en = r.get("brand_cn"), r.get("brand_en")
                if cn and en and en.lower() not in cn.lower():
                    return f"{cn} {en}"
                return cn or en or slug
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
    import hashlib
    cands = []  # 结构化候选(供前台 triage 页 / build_watch_triage.py 消费)
    total_new = 0
    for slug in slugs:
        # 两路召回:① 品牌名(媒体转述)② site:<官方新闻源>(一手原文,没配则跳过)。
        # ② 是 2026-07-25 加的:此前官方发布只能靠媒体转述被动捡回(见 _brand_news_site)。
        queries = [(f"{_brand_query(slug)} when:{args.days}d", "media")]
        news_site = _brand_news_site(slug)
        if news_site:
            queries.append((f"site:{news_site} when:{args.days}d", "official"))
        # 第四路 social:知乎经 Google News 中文档的收录量大且贴题(2026-07-26 实测
        # `site:zhihu.com 美团` 100 条,「如何看待…」问题与专栏正是 W2 社交社区维度的信号)。
        # 微博是登录墙、小红书收录仅 3~5 条、公众号发现入口是 JS 壳——都走不通(见 docs/16 §9.7),
        # 知乎是唯一一个**零新增抓取器**就能拿到的社区源。只取标题入库,不碰知乎反爬墙。
        queries.append((f"site:zhihu.com {_brand_query(slug)} when:{args.days}d", "social"))
        # own_links = **自备 RSS**(用户配进 meta 的 RSSHub 源)。它同时也进 social_links
        # ——分类口径上它确实是 social;单独留一份是为了**名额优先级**(见 _apply_quota)。
        items, official_links, social_links, own_links, failed = [], set(), set(), set(), []
        for qtext, kind in queries:
            # 官方源**两档都查**:绝大多数官方源只有英文档收录(anthropic/openai/lenovo…
            # 中文档全为 0),但 `qianxin.com/news` **只在中文档有**(CN 12 条 / EN 0)。
            # 写死一档就会漏掉另一类,故合并两档结果(重复项由下面的 key 去重兜住)。
            tpls = [GNEWS_EN, GNEWS] if kind == "official" else [GNEWS]   # social/media 走中文档
            for tpl in tpls:
                xml = curl(tpl.format(q=urllib.parse.quote(qtext)))
                if xml is None:
                    failed.append(kind)
                    continue
                try:
                    got = ET.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml).findall(".//item")
                except Exception as e:
                    failed.append(f"{kind}({e})")
                    continue
                if kind == "official":
                    official_links.update((it.findtext("link") or "").strip() for it in got)
                elif kind == "social":
                    social_links.update((it.findtext("link") or "").strip() for it in got)
                items += got
        # ③ 第三路:官网新闻页直采(只给 Google News 不索引官网的品牌配)。
        news_page = _brand_news_page(slug)
        if news_page:
            import official_site
            page = curl(news_page)
            got_site = official_site.parse_news(page, news_page) if page else []
            if not got_site:
                # **哨兵**:配了却抓到 0 条 —— 多半是站点改版把解析打掉了。
                # 这类失效是静默的(没有报错、只是不再有条目),必须显式喊出来。
                msg = f"⚠️ 官网直采 0 条:{slug} <- {news_page}(站点可能改版,解析已失效)"
                print(f"discover: {msg}", file=sys.stderr)
                lines.append(f"\n## {slug} —— {msg}")
            for it in got_site:
                e = ET.Element("item")
                ET.SubElement(e, "title").text = it["title"]
                ET.SubElement(e, "link").text = it["url"]
                if it["date"]:
                    ET.SubElement(e, "pubDate").text = it["date"]
                official_links.add(it["url"])
                items.append(e)
        # ⑤ 第五路:自备 RSS 源(自托管 RSSHub 的微博/小红书路由等,§9.9)。
        for feed_url in _brand_rss_feeds(slug):
            # 密钥走 ${ENV} 占位符(公开仓库不能存明文 key)。**日志与候选 md 一律打 feed_url
            # 这个模板串,不打展开后的真值** —— 展开值带密钥,会进公开 Actions 日志。
            real_url, missing = expand_secrets(feed_url)
            if missing:
                # 与"抓到 0 条"分开报:这是**配置没到位**,不是源站失效,排错方向完全不同。
                msg = (f"⚠️ 自备 RSS 跳过:{slug} <- {feed_url}"
                       f"(环境变量未设置:{', '.join(missing)} —— 在 GitHub Actions secrets 里配)")
                print(f"discover: {msg}", file=sys.stderr)
                lines.append(f"\n## {slug} —— {msg}")
                continue
            feed_xml = curl(real_url)
            got_feed = parse_feed(feed_xml)
            if not got_feed:
                # 哨兵同官网直采:RSSHub 路由挂了 / cookie 过期 都是**静默失效**,必须喊出来。
                msg = f"⚠️ 自备 RSS 0 条:{slug} <- {feed_url}(路由可能失效或 cookie 过期)"
                print(f"discover: {msg}", file=sys.stderr)
                lines.append(f"\n## {slug} —— {msg}")
            for it in got_feed:
                e = ET.Element("item")
                ET.SubElement(e, "title").text = it["title"]
                ET.SubElement(e, "link").text = it["link"]
                if it["date"]:
                    ET.SubElement(e, "pubDate").text = it["date"]
                social_links.add(it["link"])   # 分类口径:自备 RSS 抓的是社媒 → social
                own_links.add(it["link"])      # 名额口径:显式配置的源,优先于泛查询
                items.append(e)
        if failed:
            lines.append(f"\n## {slug} —— ⚠️ 部分源拉取/解析失败:{', '.join(failed)}")
        if not items:
            continue
        urls, titles = _existing(slug)
        dims = brand_dims(slug)
        applicable = "/".join(d for d, v in dims.items() if v != "off") or "—"
        new = []
        seen = set()
        for it in items:
            t = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            raw_date = (it.findtext("pubDate") or "").strip()
            try:
                d = parsedate_to_datetime(raw_date).date().isoformat()
            except Exception:
                # 官网直采(official_site)塞的是 ISO 日期,不是 RFC-2822——
                # 不接住的话日期会整段丢失(候选变成 YYYY-MM-DD 占位,要人工回填)。
                d = raw_date if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", raw_date) else None
            key = norm(strip_suffix(t))
            if not t or not link or not key or key in seen:
                continue
            if link in urls or key in titles:
                continue
            if is_noise(t):  # 行情页 / 纯 ticker 等噪音,不入候选(节省 limit 名额)
                continue
            seen.add(key)
            new.append((t, d, link))
        if not new:
            lines.append(f"\n## {slug} —— 无新候选(窗口内 {args.days} 天)")
            continue
        # **官方源条目排前面**:media 查询在前,若按原序取 `new[:limit]`,官方条目会被
        # limit 整段截掉(2026-07-25 首次接线就踩了这个——官方源拉到了,却 0 条进候选)。
        # 官方一手公告正是本次改动要召回的东西,必须优先占名额。
        # 官方源**保留名额**而非全占:首次接线时官方优先排序把媒体条目整段挤掉
        # (184 条里 98 条官方)。官方一手公告要保证进得来,但媒体的舆情面也不能丢,
        # 故官方最多占一半名额,其余按原序留给媒体。
        off = [x for x in new if x[2] in official_links]
        own = [x for x in new if x[2] in own_links and x[2] not in official_links]
        soc = [x for x in new if x[2] in social_links
               and x[2] not in official_links and x[2] not in own_links]
        med = [x for x in new if x[2] not in official_links and x[2] not in social_links]
        shown = _apply_quota(off, own, soc, med, args.limit)
        omitted = max(0, len(new) - len(shown))
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
            # 召回路径已经确定了 source_type,人工候选 md 里就不该再写死 `media`
            # (2026-07-27:官方公告与自备 RSS 的微博条目在 md 里全被标成 media,
            #  人工照抄就是错标。JSON 侧一直是对的,错的只有给人看的那一份)。
            st = ("official" if link in official_links
                  else "social" if link in social_links else "media")
            cands.append({
                "key": hashlib.sha1(link.encode("utf-8")).hexdigest()[:12],
                "slug": slug,
                "brand": _brand_query(slug),
                "date": d or "",
                "quote": quote,
                "title": quote,
                "url": link,
                "source": (src or "").strip(),
                # 官方源召回的条目显式标注,便于分类时给更高 severity(旗舰发布 = P0)
                "source_type": st,
                "applicable_dims": [dm for dm, v in dims.items() if v != "off"],
                "lens_suggest": ["signal"],
                "fetched_at": now,
            })
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
  source_type: {st} # ↑按召回路径判定,人工核对:official/media/finance/regulator... {src_hint}
  note: "每日自动发现候选;标题/日期/URL 取自 Google News RSS。待人工定维度/等级/方向后入库。\"""".rstrip())
    out = "\n".join(lines) + "\n"
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        open(args.out, "w", encoding="utf-8").write(out)
        # 结构化 JSON 伴生文件(前台 triage 页数据源;.md 供人读,.json 供 build_watch_triage.py)
        jout = os.path.splitext(args.out)[0] + ".json"
        json.dump({"generated_at": now, "window_days": args.days, "candidates": cands},
                  open(jout, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"discover: {total_new} 条新候选 → {args.out} + {jout}")
    else:
        print(out)
    return 0


def cmd_selftest(_args):
    """离线自检:parse_feed(RSS 2.0 / Atom / 垃圾输入)与 rss_feeds 读取。fixture 跑,不出网。"""
    checks, fails = 0, []

    def ok(cond, name):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(name)

    rss2 = """<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>美团发布二季度财报</title><link>https://x/1</link>
            <pubDate>Mon, 20 Jul 2026 08:00:00 GMT</pubDate></item>
      <item><title>无日期条目</title><link>https://x/2</link></item>
      <item><title></title><link>https://x/3</link></item>
    </channel></rss>"""
    got = parse_feed(rss2)
    ok(len(got) == 2, "rss2:空标题条目被丢弃")
    ok(got[0]["date"] == "2026-07-20", "rss2:RFC-2822 日期归一为 ISO")
    ok(got[1]["date"] == "", "rss2:无日期留空,不猜")

    atom = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>v0.6.1 发布</title><link href="https://x/r1"/>
             <updated>2026-07-21T09:30:00Z</updated></entry>
      <entry><title>微博:美团骑士节</title><link href="https://x/r2"/>
             <published>2026-07-17T00:00:00+08:00</published></entry>
    </feed>"""
    got = parse_feed(atom)
    ok(len(got) == 2, "atom:entry 被解析(RSSHub 之外的 Atom 源也认)")
    ok(got[0]["date"] == "2026-07-21" and got[1]["date"] == "2026-07-17",
       "atom:updated/published 都取日期部分")
    ok(got[1]["link"] == "https://x/r2", "atom:link 取 href 属性")

    ok(parse_feed("<html>不是 feed</html>") == [], "垃圾输入:返回空,不编造")
    ok(parse_feed("") == [] and parse_feed(None) == [], "空输入:返回空")

    # ── ${ENV} 密钥占位符(公开仓库不能存明文 ACCESS_KEY)────────────────────
    os.environ["MBA_SELFTEST_KEY"] = "s3cr3t"
    os.environ.pop("MBA_SELFTEST_ABSENT", None)
    u, miss = expand_secrets("https://rsshub.example.com/weibo/user/1?key=${MBA_SELFTEST_KEY}")
    ok(u == "https://rsshub.example.com/weibo/user/1?key=s3cr3t" and miss == [],
       "占位符:环境变量已设 → 展开为真值")
    u, miss = expand_secrets("https://x/a?key=${MBA_SELFTEST_ABSENT}")
    ok(miss == ["MBA_SELFTEST_ABSENT"] and "${MBA_SELFTEST_ABSENT}" in u,
       "占位符:变量缺失 → 报出变量名且不静默替空(调用方须跳过)")
    os.environ["MBA_SELFTEST_BLANK"] = "   "
    _, miss = expand_secrets("https://x/a?key=${MBA_SELFTEST_BLANK}")
    ok(miss == ["MBA_SELFTEST_BLANK"], "占位符:空白值等同缺失(空 key 会被 403,伪装成路由挂了)")
    u, miss = expand_secrets("https://x/plain")
    ok(u == "https://x/plain" and miss == [], "占位符:无占位符的 URL 原样返回(无回归)")

    # ── 名额分配(_apply_quota)—— 2026-07-27 抓到的静默挤压 ────────────────
    def mk(tag, n):
        return [(f"{tag}{i}", "2026-07-27", f"https://{tag}/{i}") for i in range(n)]

    off_, own_, soc_, med_ = mk("off", 1), mk("own", 10), mk("soc", 53), mk("med", 33)
    shown = _apply_quota(off_, own_, soc_, med_, 8)
    ok(len(shown) == 8, "名额:总数不超过 limit")
    ok(any(x[2].startswith("https://own/") for x in shown),
       "名额:自备 RSS 必须进得来(知乎 53 条时曾被 100% 静默挤掉)")
    n_social = sum(1 for x in shown if x[2].startswith(("https://own/", "https://soc/")))
    ok(n_social == max(1, 8 // 4), "名额:社区桶总量仍锁在 limit/4(自备 RSS 不额外扩张)")
    ok(all(x[2].startswith("https://own/")
           for x in shown if x[2].startswith(("https://own/", "https://soc/"))),
       "名额:桶内自备 RSS 排在泛查询之前(显式配置 > 顺带召回)")
    ok(sum(1 for x in shown if x[2].startswith("https://med/")) >= 1,
       "名额:媒体面不被挤空")
    shown2 = _apply_quota(mk("off", 20), [], [], [], 6)
    ok(len(shown2) == 6 and all(x[2].startswith("https://off/") for x in shown2),
       "名额:只有官方源时用回填占满,不留空位")

    import inspect
    src = inspect.getsource(cmd_discover)
    ok("_brand_rss_feeds(" in src and "自备 RSS 0 条" in src,
       "discover:自备 RSS 已接线且带静默失效哨兵")
    ok("social_links.add(it[\"link\"])" in src, "discover:自备 RSS 条目标 social")
    ok("expand_secrets(feed_url)" in src and "curl(real_url)" in src,
       "discover:请求用展开后的真 URL")
    ok("source_type: media #" not in src and "source_type: {st}" in src,
       "discover:候选 md 的 source_type 按召回路径填,不写死 media(人工照抄会错标)")
    # 反密钥泄露:哨兵消息里出现的必须是**模板串** feed_url,不能是展开值 real_url。
    sentinel_lines = [ln for ln in src.splitlines() if "自备 RSS" in ln and "<-" in ln]
    ok(len(sentinel_lines) == 2 and all("{feed_url}" in ln for ln in sentinel_lines),
       "discover:自备 RSS 两个哨兵都打模板串(密钥不进公开日志/候选 md)")
    ok("{real_url}" not in src, "discover:任何日志都不打展开后的 URL")

    print(f"fetch_candidate --selftest: "
          f"{'✅ ' + str(checks) + ' 组断言全部通过' if not fails else '❌ 失败: ' + ', '.join(fails)}")
    return 1 if fails else 0


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
    ps = sub.add_parser("selftest", help="离线自检(feed 解析 fixture,不出网)")
    ps.set_defaults(func=cmd_selftest)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
