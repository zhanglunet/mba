#!/usr/bin/env python3
"""竞品追踪（PRD-062/T2，trend #319）。

按可配置的对标品牌列表（watch_list），从 RSS 源抓取各品牌近 7 天动态，
输出指挥舱聚合 JSON 的 `competitors` 段：对标品牌清单 + Top5 关键事件。

一期说明：`comparison`（本品牌 vs 对标品牌评分对比）按 T1 设计为 `null`，
二期"多品牌视图"启用时再填——这是预留，不是缺失。

降级：单个品牌/源抓取失败 → 跳过并记 stderr 警告；
全部源失败 → 输出 JSON `null`（看板显示"数据暂缺"，设计好的降级）。

RSS 抓取与文本处理复用 sentiment_collector 的函数（同一目录 importlib 加载），
避免两份实现分叉。纯标准库。

用法：
  python3 scripts/competitor_tracker.py [--config config/deck_sources.json] [-o /tmp/competitors.json]
"""
import argparse
import datetime
import importlib.util
import json
import pathlib
import re
import sys
import urllib.parse

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "deck_sources.json"
SHANGHAI = datetime.timezone(datetime.timedelta(hours=8))


def _load_sentiment_collector():
    here = pathlib.Path(__file__).resolve().parent
    mod_path = here / "sentiment_collector.py"
    spec = importlib.util.spec_from_file_location("sentiment_collector", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def collect_competitors(config: dict,
                        now: datetime.datetime | None = None) -> dict | None:
    """返回 competitors 段 dict；全部源失败时返回 None（调用方写 null）。"""
    sc = _load_sentiment_collector()
    now = now or datetime.datetime.now(SHANGHAI)
    c_cfg = config.get("competitors", {})
    watch_list = c_cfg.get("watch_list", [])
    queries = c_cfg.get("queries", {})
    feed_tpl = c_cfg.get("feed", "")
    days = int(c_cfg.get("days", 7))
    max_events = int(c_cfg.get("max_events", 5))
    max_items = int(c_cfg.get("max_items_per_feed", 50))
    if not watch_list or not feed_tpl:
        print("WARN: 未配置竞品 watch_list 或 RSS 源", file=sys.stderr)
        return None

    cutoff = now - datetime.timedelta(days=days)
    events, seen_urls = [], set()
    fetched_any = False
    for brand in watch_list:
        brand_queries = queries.get(brand, [brand])
        q = brand_queries[0]
        url = feed_tpl.format(query=urllib.parse.quote(q))
        try:
            items = sc.fetch_rss(url, max_items=max_items)
            fetched_any = True
        except Exception as e:
            print(f"WARN: 竞品 {brand} 源抓取失败: {e}", file=sys.stderr)
            continue
        qls = [x.lower() for x in brand_queries]
        for it in items:
            if it["published"] < cutoff:
                continue
            hay = (it["title"] + " " + it["summary"]).lower()
            if not any(ql in hay for ql in qls):
                continue
            # 同一篇文章可能命中多个品牌：按 URL 全局去重，归属首次命中的品牌
            #（watch_list 顺序），避免 Top5 里同一事件占多坑。
            ukey = it["url"].split("?")[0].lower() or re.sub(r"\s+", " ", it["title"].lower())
            if ukey in seen_urls:
                continue
            seen_urls.add(ukey)
            events.append({
                "brand": brand,
                "title": it["title"],
                "at": it["published"].astimezone(SHANGHAI).isoformat(),
                "url": it["url"],
                "_ts": it["published"].timestamp(),
            })

    if not fetched_any:
        print("WARN: 全部竞品源抓取失败，该段输出 null", file=sys.stderr)
        return None

    events.sort(key=lambda e: e["_ts"], reverse=True)
    top = [{k: e[k] for k in ("brand", "title", "at", "url")} for e in events[:max_events]]
    return {
        "updated_at": now.isoformat(),
        "watch_list": watch_list,
        "events": top,
        "comparison": None,  # 一期预留，二期多品牌视图启用时再填
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="竞品追踪（PRD-062/T2）")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="数据源配置文件")
    ap.add_argument("-o", "--output", help="输出文件（缺省打印到 stdout）")
    args = ap.parse_args()

    config = json.loads(pathlib.Path(args.config).read_text(encoding="utf-8"))
    section = collect_competitors(config)
    out = json.dumps(section, ensure_ascii=False, indent=2)
    if args.output:
        pathlib.Path(args.output).write_text(out + "\n", encoding="utf-8")
        print(f"written: {args.output} ({'null' if section is None else 'ok'})")
    else:
        sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
