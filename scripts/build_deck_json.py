#!/usr/bin/env python3
"""指挥舱聚合脚本（PRD-062/T2，trend #319）。

把三段数据源合并成指挥舱唯一的聚合 JSON（T1 §五 schema），
dashboard（T3）只读这个文件，不直连任何采集源：

  health      ← 本品牌最新报告产物（Score Matrix 表尾 + Mean 列 5 lens）
  sentiment   ← scripts/sentiment_collector.py（失败 → null）
  competitors ← scripts/competitor_tracker.py（失败 → null）

任一段缺失 → 该段为 `null`（不是空对象），看板按 T1 设计显示"数据暂缺"。

health 抽取复用 scripts/generate_exec_summary.py 的 extract()
（品牌/版本/审计日期口径一致），lens 矩阵解析为本脚本自有逻辑
（Mean 列 `**8.6** ↔` 格式，`lenses` 为数组、不硬编码维度数量；
`delta` 取值与报告图例一致：↔ / ↑n / ↓n）。

纯标准库，不调 LLM，无重型依赖。

用法：
  python3 scripts/build_deck_json.py published/reports/deepseek/report.md \\
      [-o data/deck.json] [--config config/deck_sources.json] [--skip-live]

  --skip-live：跳过实时采集（sentiment/competitors 置 null），用于离线自测。
"""
import argparse
import datetime
import importlib.util
import json
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "deck_sources.json"
SHANGHAI = datetime.timezone(datetime.timedelta(hours=8))

# deck.json schema 版本（PRD-098/T3 第一批 V1）：对应 T1 §五 schema
# （顶层 brand/generated_at + health/sentiment/competitors 三段结构）。
# schema 不兼容变更（增删段、改字段口径）递增主版本；消费方
# （dashboard/ask.html）按此版本号判断兼容性。仅标注，不影响产物结构。
DECK_SCHEMA_VERSION = "1.0.0"


def _load_module(name: str):
    here = pathlib.Path(__file__).resolve().parent
    mod_path = here / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def extract_health(report_path: pathlib.Path) -> dict:
    """从报告产物抽取 health 段。取不到核心数据时抛 ValueError（大声失败）。"""
    gen = _load_module("generate_exec_summary")
    text = report_path.read_text(encoding="utf-8")
    d = gen.extract(report_path)

    # ---- Score Matrix 表尾 ----
    m = re.search(r"Score Total:\s*([\d.]+)\s*/\s*(\d+)", text)
    if not m:
        raise ValueError("报告缺少 Score Total，health 段无法生成")
    score_total, score_max = int(float(m.group(1))), int(m.group(2))
    m = re.search(r"Score Normalized:\s*([\d.]+)\s*/\s*10", text)
    if not m:
        raise ValueError("报告缺少 Score Normalized，health 段无法生成")
    score_normalized = float(m.group(1))

    # ---- lens 行：| Origin / 起源叙事 | …5 评委… | **8.6** ↔ | ----
    lenses = []
    sm_start = text.find("## Score Matrix")
    sm_text = text[sm_start:] if sm_start >= 0 else text
    for line in sm_text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|") if c.strip()]
        if len(cells) < 3 or "Judge Total" in cells[0]:
            continue
        if "/" not in cells[0]:
            continue
        key_en, name_cn = [p.strip() for p in cells[0].split("/", 1)]
        mean_cell = cells[-1]
        mm = re.search(r"\*\*([\d.]+)\*\*", mean_cell)
        if not mm:
            continue
        dm = re.search(r"(↔|↑[\d.]+|↓[\d.]+)", mean_cell)
        lenses.append({
            "key": key_en.lower(),
            "name_cn": name_cn,
            "mean": float(mm.group(1)),
            "delta": dm.group(1) if dm else "↔",
        })
    if not lenses:
        raise ValueError("Score Matrix 未解析出 lens 行，health 段无法生成")

    report_date = d.get("date") or ""
    version = d.get("version") or ""
    updated_at = (f"{report_date}T00:00:00+08:00" if report_date
                  else datetime.datetime.now(SHANGHAI).isoformat())
    return {
        "updated_at": updated_at,
        "score_total": score_total,
        "score_max": score_max,
        "score_normalized": score_normalized,
        "report_version": f"v{version}" if version else "",
        "report_date": report_date,
        "lenses": lenses,
    }


def build_deck(report_path: pathlib.Path, config: dict,
               skip_live: bool = False) -> dict:
    now = datetime.datetime.now(SHANGHAI)
    brand = report_path.parent.name  # T1 §五示例：brand 取品牌目录名
    health = extract_health(report_path)

    sentiment = None
    competitors = None
    if not skip_live:
        sc = _load_module("sentiment_collector")
        ct = _load_module("competitor_tracker")
        try:
            sentiment = sc.collect_sentiment(brand, config, now=now)
        except Exception as e:
            print(f"WARN: 舆情采集异常，该段置 null: {e}", file=sys.stderr)
        try:
            competitors = ct.collect_competitors(config, now=now)
        except Exception as e:
            print(f"WARN: 竞品追踪异常，该段置 null: {e}", file=sys.stderr)

    return {
        "brand": brand,
        "generated_at": now.isoformat(),
        "health": health,
        "sentiment": sentiment,
        "competitors": competitors,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="指挥舱聚合 JSON 生成（PRD-062/T2）")
    ap.add_argument("report", help="完整报告路径，如 published/reports/deepseek/report.md")
    ap.add_argument("-o", "--output", default=str(REPO_ROOT / "data" / "deck.json"),
                    help="输出文件（缺省 data/deck.json）")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="数据源配置文件")
    ap.add_argument("--skip-live", action="store_true",
                    help="跳过实时采集（sentiment/competitors 置 null），离线自测用")
    args = ap.parse_args()

    report_path = pathlib.Path(args.report)
    if not report_path.is_file():
        print(f"ERROR: 报告不存在: {report_path}", file=sys.stderr)
        return 2
    config = json.loads(pathlib.Path(args.config).read_text(encoding="utf-8"))

    try:
        deck = build_deck(report_path, config, skip_live=args.skip_live)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    out_path = pathlib.Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(deck, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    h = deck["health"]
    print(f"written: {out_path}")
    print(f"health: {h['score_total']}/{h['score_max']} 归一化 {h['score_normalized']} "
          f"{h['report_version']} {h['report_date']} lenses={len(h['lenses'])}")
    print(f"sentiment: {'null' if deck['sentiment'] is None else 'ok'} | "
          f"competitors: {'null' if deck['competitors'] is None else 'ok'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
