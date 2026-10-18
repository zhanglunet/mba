#!/usr/bin/env python3
"""舆情采集器（PRD-062/T2，trend #319）。

从可配置的 RSS 源抓取品牌相关新闻，聚合成指挥舱聚合 JSON 的
`sentiment` 段：近 7 天声量曲线 + 正负面占比 + Top3 热点事件。

情感倾向判定方法（词典启发式——先读这段）：
  文本 = 标题×2 + 摘要（标题权重加倍，标题信息密度最高）；
  分别统计正/负情感词典的出现次数（子串匹配，不做分词）；
  正词多 → positive，负词多 → negative，打平或都没有 → neutral。
  这是粗糙的启发式估计：识别不了否定修饰（"未下跌"）、反讽、
  标题党、"中性报道里出现负面词"等情况；精度要求高的场景请换模型。
  词典见本文件 POS_WORDS / NEG_WORDS（中英双语，可按需扩充）。

降级：单个源抓取/解析失败 → 跳过该源并记 stderr 警告；
全部源失败 → 输出 JSON `null`（看板按 T1 设计显示"数据暂缺"，
这是设计好的降级，不是 bug）。

纯标准库：urllib / xml.etree / email.utils / re / json / datetime。

用法：
  python3 scripts/sentiment_collector.py --brand deepseek \\
      [--config config/deck_sources.json] [-o /tmp/sentiment.json]
"""
import argparse
import datetime
import email.utils
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "deck_sources.json"
SHANGHAI = datetime.timezone(datetime.timedelta(hours=8))
USER_AGENT = "Mozilla/5.0 (compatible; mba-command-deck/1.0)"

# ---------------------------------------------------------------------------
# 情感词典（词典启发式，见模块 docstring）
# ---------------------------------------------------------------------------
POS_WORDS = [
    # 中文
    "增长", "上涨", "突破", "领先", "利好", "创新", "融资", "上市", "获奖",
    "好评", "成功", "发布", "新高", "扩张", "合作", "盈利", "领跑", "首创",
    "加速", "赋能", "看好", "增持", "回购", "分红", "订单", "中标", "量产",
    "出货", "开源", "登顶", "首富", "落地", "暴涨", "大涨", "飙升", "走强",
    # 英文
    "growth", "breakthrough", "funding", "launch", "record", "partnership",
    "profit", "success", "raise", "surge", "innovat", "award", "bullish",
    "upgrade", "beat", "expansion",
]
NEG_WORDS = [
    # 中文
    "下跌", "暴跌", "丑闻", "诉讼", "罚款", "裁员", "亏损", "争议", "批评",
    "封杀", "制裁", "泄露", "事故", "暴雷", "做空", "召回", "监管", "调查",
    "处罚", "减持", "离职", "宕机", "漏洞", "贬值", "腰斩", "爆雷", "重挫", "跳水",
    # 英文
    "lawsuit", "scandal", "fine", "layoff", "loss", "controversy",
    "criticism", "ban", "leak", "crash", "fraud", "bearish", "downgrade",
    "miss", "probe", "recall", "breach", "decline",
]


def classify_sentiment(text: str) -> str:
    """词典启发式判定情感倾向。返回 positive / negative / neutral。"""
    t = text.lower()
    pos = sum(t.count(w.lower()) for w in POS_WORDS)
    neg = sum(t.count(w.lower()) for w in NEG_WORDS)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


# ---------------------------------------------------------------------------
# RSS 抓取（纯标准库）
# ---------------------------------------------------------------------------
def strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_article_url(item: ET.Element, fallback: str) -> str:
    """Google News 的 <link> 是站内跳转，真实文章地址藏在 description 的 <a href> 里。"""
    desc = item.findtext("description", "")
    m = re.search(r'href="([^"]+)"', desc)
    if m and m.group(1).startswith("http"):
        return m.group(1)
    return fallback


def clean_title(title: str) -> str:
    """去掉 Google News 标题末尾的 " - 媒体名" 后缀。"""
    return re.sub(r"\s+-\s+[^-–—]{1,40}$", "", (title or "").strip())


def fetch_rss(url: str, timeout: int = 20, max_items: int = 50) -> list:
    """抓取单个 RSS，返回 [{title, url, published(datetime), summary}]。"""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    items = []
    for it in root.findall(".//item")[:max_items]:
        try:
            pub = it.findtext("pubDate", "")
            dt = email.utils.parsedate_to_datetime(pub) if pub else None
            if dt is None:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            link = it.findtext("link", "")
            items.append({
                "title": clean_title(it.findtext("title", "")),
                "url": extract_article_url(it, link),
                "published": dt,
                "summary": strip_html(it.findtext("description", ""))[:160],
            })
        except Exception:
            continue
    return items


# ---------------------------------------------------------------------------
# 聚合
# ---------------------------------------------------------------------------
def load_config(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_sentiment(brand: str, config: dict,
                      now: datetime.datetime | None = None) -> dict | None:
    """返回 sentiment 段 dict；全部源失败时返回 None（调用方写 null）。"""
    now = now or datetime.datetime.now(SHANGHAI)
    s_cfg = config.get("sentiment", {})
    brand_queries = config.get("brands", {}).get(brand, {}).get("queries", [brand])
    days = int(s_cfg.get("days", 7))
    max_items = int(s_cfg.get("max_items_per_feed", 50))
    top_n = int(s_cfg.get("top_events", 3))
    feeds = s_cfg.get("feeds") or ([{"name": "default", "url": s_cfg["feed"]}]
                                   if s_cfg.get("feed") else [])
    if not feeds:
        print("WARN: 未配置舆情 RSS 源", file=sys.stderr)
        return None

    cutoff = now - datetime.timedelta(days=days)
    seen, matched = set(), []
    fetched_any = False
    for q in brand_queries:
        ql = q.lower()
        for feed in feeds:
            url = feed["url"].format(query=urllib.parse.quote(q))
            try:
                items = fetch_rss(url, max_items=max_items)
                fetched_any = True
            except Exception as e:
                print(f"WARN: 源 {feed.get('name', url)} 抓取失败: {e}", file=sys.stderr)
                continue
            for it in items:
                if it["published"] < cutoff:
                    continue
                hay = (it["title"] + " " + it["summary"]).lower()
                if ql not in hay:
                    continue
                key = re.sub(r"\s+", " ", it["title"].lower())
                if key in seen:
                    continue
                seen.add(key)
                matched.append(it)

    if not fetched_any:
        print("WARN: 全部舆情源抓取失败，该段输出 null", file=sys.stderr)
        return None

    # 近 7 天声量（含 0 的日期也保留，给柱状图用）
    daily = []
    for i in range(days - 1, -1, -1):
        day = (now - datetime.timedelta(days=i)).date()
        day_items = [it for it in matched if it["published"].astimezone(SHANGHAI).date() == day]
        sents = [classify_sentiment(it["title"] + " " + it["title"] + " " + it["summary"])
                 for it in day_items]
        daily.append({
            "date": day.isoformat(),
            "count": len(day_items),
            "positive": sents.count("positive"),
            "negative": sents.count("negative"),
            "neutral": sents.count("neutral"),
        })

    matched.sort(key=lambda it: it["published"], reverse=True)
    top_events = []
    for it in matched[:top_n]:
        top_events.append({
            "title": it["title"],
            "summary": it["summary"][:80],
            "sentiment": classify_sentiment(it["title"] + " " + it["title"] + " " + it["summary"]),
            "at": it["published"].astimezone(SHANGHAI).isoformat(),
            "url": it["url"],
        })

    return {
        "updated_at": now.isoformat(),
        "daily_volume": daily,
        "top_events": top_events,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="舆情采集器（PRD-062/T2）")
    ap.add_argument("--brand", required=True, help="品牌目录名，如 deepseek")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="数据源配置文件")
    ap.add_argument("-o", "--output", help="输出文件（缺省打印到 stdout）")
    args = ap.parse_args()

    config = load_config(pathlib.Path(args.config))
    section = collect_sentiment(args.brand, config)
    out = json.dumps(section, ensure_ascii=False, indent=2)
    if args.output:
        pathlib.Path(args.output).write_text(out + "\n", encoding="utf-8")
        print(f"written: {args.output} ({'null' if section is None else 'ok'})")
    else:
        sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
