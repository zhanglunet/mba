#!/usr/bin/env python3
"""指挥舱 e2e 验收（PRD-062/T5，trend #328）。

以 deepseek 为真实品牌走通全链路：
  1. 采集：sentiment_collector / competitor_tracker
     （--skip-live 离线模式两段置 null；实时采集失败时该段置 null，
      任何情况下不得抛错中断链路）
  2. 聚合：build_deck_json.build_deck → deck.json
     （断言顶层键齐全 + health 数值与真实报告一致）
  3. dashboard 渲染：静态检查 dashboard.html 引用 data/deck.json
     （浏览器实际渲染效果靠人工，见验收报告）
  4. 定时刷新：refresh_deck.py --check-only 对一份构造的"异动版" deck，
     断言 5 条异动口径触发预期条目
  5. 异动告警：dry-run 模式（真实 detect_anomalies + build_message，
     不调 send_feishu），断言告警文本含品牌名与异动条数

每步打印 [PASS]/[FAIL] 并附关键证据；最后汇总，任一步 FAIL 则 exit 1。
纯标准库，不调 LLM。

用法：
  python3 scripts/e2e_command_deck.py [--skip-live] [--report PATH]
                                      [--workdir DIR] [--keep-workdir]
"""

import argparse
import copy
import datetime
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
SHANGHAI = datetime.timezone(datetime.timedelta(hours=8))

BRAND = "deepseek"
REPORT_DEFAULT = REPO_ROOT / "published" / "reports" / "deepseek" / "report.md"

# 健康度断言锚点：与 published/reports/deepseek/report.md 真实值一致
EXPECT = {"score_total": 208, "score_normalized": 8.32,
          "report_version": "v3", "lens_count": 5}

results = []  # (step_name, ok, evidence)


def check(name, ok, evidence=""):
    results.append((name, bool(ok), evidence))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name,
                         (" — " + evidence) if evidence else ""))
    return bool(ok)


def load_module(name):
    spec = importlib.util.spec_from_file_location(
        "e2e_" + name, SCRIPTS_DIR / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def step1_collect(skip_live, sources_cfg):
    """采集：两段采集器跑通；失败/离线时置 null，不得抛错。"""
    sc = load_module("sentiment_collector")
    ct = load_module("competitor_tracker")
    now = datetime.datetime.now(SHANGHAI)
    sentiment = competitors = None
    mode = "offline(--skip-live)"
    if not skip_live:
        mode = "live"
        try:
            sentiment = sc.collect_sentiment(BRAND, sources_cfg, now=now)
        except Exception as e:  # noqa: BLE001 —— 采集失败只降级，不中断
            print("  WARN: 舆情采集异常，置 null: %s" % e)
            sentiment = None
        try:
            competitors = ct.collect_competitors(sources_cfg, now=now)
        except Exception as e:  # noqa: BLE001
            print("  WARN: 竞品追踪异常，置 null: %s" % e)
            competitors = None
    ok_shape = ((sentiment is None or isinstance(sentiment, dict))
                and (competitors is None or isinstance(competitors, dict)))
    return check("1/5 采集", ok_shape,
                 "模式=%s；sentiment=%s，competitors=%s" % (
                     mode,
                     "null" if sentiment is None else "dict",
                     "null" if competitors is None else "dict"))


def step2_aggregate(report_path, sources_cfg, skip_live, workdir):
    """聚合：build_deck 生成 deck.json；断言顶层键 + health 真实值。"""
    bdj = load_module("build_deck_json")
    try:
        deck = bdj.build_deck(report_path, sources_cfg, skip_live=skip_live)
    except Exception as e:  # noqa: BLE001
        return check("2/5 聚合", False, "build_deck 抛错: %s" % e), None
    need_keys = {"brand", "generated_at", "health", "sentiment", "competitors"}
    ok_keys = need_keys <= set(deck.keys())
    h = deck.get("health") or {}
    ok_health = (h.get("score_total") == EXPECT["score_total"]
                 and abs(float(h.get("score_normalized", -1))
                         - EXPECT["score_normalized"]) < 1e-9
                 and h.get("report_version") == EXPECT["report_version"]
                 and len(h.get("lenses", [])) == EXPECT["lens_count"])
    ok_brand = deck.get("brand") == BRAND
    baseline = workdir / "deck_baseline.json"
    baseline.write_text(json.dumps(deck, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    ev = ("顶层键%s；health=%s/%s/%s/%d lens；基线→%s" % (
        "齐全" if ok_keys else "缺失",
        h.get("score_total"), h.get("score_normalized"),
        h.get("report_version"), len(h.get("lenses", [])),
        baseline.name))
    return check("2/5 聚合", ok_keys and ok_health and ok_brand, ev), deck


def step3_dashboard():
    """dashboard 渲染：静态检查 dashboard.html 引用 deck 数据源。"""
    html_path = REPO_ROOT / "dashboard.html"
    if not html_path.is_file():
        return check("3/5 dashboard 渲染", False, "dashboard.html 不存在")
    html = html_path.read_text(encoding="utf-8")
    ok = "data/deck.json" in html or "deck.json" in html
    return check("3/5 dashboard 渲染", ok,
                 "静态检查通过（引用 deck.json）；浏览器实际渲染靠人工")


def build_mutated(baseline):
    """构造"异动版" deck：5 条口径各触发至少一条。"""
    new = copy.deepcopy(baseline)
    new["health"]["score_total"] = 200          # 208→200，降 8 分（阈值 5）
    for l in new["health"]["lenses"]:
        if l.get("key") == "signal":
            l["mean"] = 8.0                     # 9.0→8.0，变化 1.0（阈值 0.5）
    new["sentiment"] = {
        "updated_at": datetime.datetime.now(SHANGHAI).isoformat(),
        "daily_volume": [
            {"date": "2026-10-17", "positive": 5, "neutral": 3, "negative": 10},
            {"date": "2026-10-18", "positive": 6, "neutral": 3, "negative": 20},
        ],                                      # 负面 10→20，+100%（阈值 50%）
        "top_events": [
            {"title": "e2e 合成热点", "summary": "验收构造",
             "sentiment": "negative",
             "at": datetime.datetime.now(SHANGHAI).isoformat()},
        ],
    }
    new["competitors"] = {
        "updated_at": datetime.datetime.now(SHANGHAI).isoformat(),
        "watch_list": ["e2e"],
        "events": [
            {"brand": "e2e", "title": "e2e 合成竞品事件",
             "at": datetime.datetime.now(SHANGHAI).isoformat()},
        ],
    }
    return new


def step4_refresh(baseline, workdir, refresh_cfg_path):
    """定时刷新：--check-only 对异动版 deck，断言 5 条口径触发预期。"""
    mutated = build_mutated(baseline)
    old_p, new_p = workdir / "deck_old.json", workdir / "deck_new.json"
    old_p.write_text(json.dumps(baseline, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    new_p.write_text(json.dumps(mutated, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "refresh_deck.py"),
         "--check-only", "--old", str(old_p), "--new", str(new_p),
         "--config", str(refresh_cfg_path)],
        capture_output=True, text=True, timeout=120)
    out = r.stdout or ""
    expects = ["下降 8 分",       # 口径 1：综合评分下降超阈值
               "信号",            # 口径 2：lens 变化超阈值
               "负面声量",        # 口径 3：负面声量日环比突增
               "舆情新增热点",    # 口径 4：新增 Top 热点
               "竞品新增事件"]    # 口径 5：新增竞品关键事件
    missing = [e for e in expects if e not in out]
    ok = r.returncode == 0 and not missing
    ev = "exit=%d；5 条口径%s" % (
        r.returncode, "全部触发" if not missing else "缺失: %s" % missing)
    ok_all = check("4/5 定时刷新", ok, ev)
    return ok_all, (old_p, new_p, mutated)


def step5_alert(baseline, mutated, refresh_cfg_path):
    """异动告警：dry-run（真实 detect+build_message，不调飞书），
    断言文本含品牌名与异动条数。"""
    rd = load_module("refresh_deck")
    thr = json.loads(pathlib.Path(refresh_cfg_path).read_text(
        encoding="utf-8")).get("alert", {}).get("thresholds", {})
    alerts = rd.detect_anomalies(baseline, mutated, thr)
    ts = datetime.datetime.now(SHANGHAI).isoformat()
    message = rd.build_message(baseline.get("brand") or BRAND, alerts, ts)
    ok = (BRAND in message
          and ("共 %d 条异动" % len(alerts)) in message
          and len(alerts) >= 5)
    print("  [dry-run] 告警文本（未调飞书）：")
    for ln in message.splitlines():
        print("    " + ln)
    return check("5/5 异动告警", ok,
                 "dry-run；含品牌名与「共 %d 条异动」" % len(alerts))


def main() -> int:
    ap = argparse.ArgumentParser(description="指挥舱 e2e 验收（PRD-062/T5）")
    ap.add_argument("--skip-live", action="store_true",
                    help="离线模式：舆情/竞品两段置 null（默认开启以保证可重复）")
    ap.add_argument("--no-skip-live", dest="skip_live", action="store_false",
                    help="尝试实时采集（失败时该段置 null，不中断）")
    ap.add_argument("--report", default=str(REPORT_DEFAULT),
                    help="健康度报告路径")
    ap.add_argument("--workdir", default=None, help="工作目录（缺省为临时目录）")
    ap.add_argument("--keep-workdir", action="store_true",
                    help="保留工作目录（缺省自动清理）")
    ap.set_defaults(skip_live=True)
    args = ap.parse_args()

    print("== 指挥舱 e2e 验收（PRD-062/T5）品牌=%s 模式=%s ==" % (
        BRAND, "offline" if args.skip_live else "live"))

    report_path = pathlib.Path(args.report)
    if not report_path.is_file():
        check("0/5 前置", False, "报告不存在: %s" % report_path)
        return 1
    sources_cfg = json.loads(
        (REPO_ROOT / "config" / "deck_sources.json").read_text(
            encoding="utf-8"))
    refresh_cfg = REPO_ROOT / "config" / "deck_refresh.json"
    if not refresh_cfg.is_file():
        check("0/5 前置", False, "刷新配置不存在: %s" % refresh_cfg)
        return 1
    check("0/5 前置", True, "报告与配置就绪")

    tmp = None
    if args.workdir:
        workdir = pathlib.Path(args.workdir)
        workdir.mkdir(parents=True, exist_ok=True)
    else:
        tmp = tempfile.TemporaryDirectory(prefix="e2e_deck_")
        workdir = pathlib.Path(tmp.name)

    ok1 = step1_collect(args.skip_live, sources_cfg)
    ok2, baseline = step2_aggregate(report_path, sources_cfg,
                                    args.skip_live, workdir)
    ok3 = step3_dashboard()
    if baseline is None:
        check("4/5 定时刷新", False, "无基线 deck，跳过")
        check("5/5 异动告警", False, "无基线 deck，跳过")
    else:
        ok4, triple = step4_refresh(baseline, workdir, refresh_cfg)
        ok5 = step5_alert(baseline, triple[2], refresh_cfg) if ok4 else \
            check("5/5 异动告警", False, "第 4 步未通过，跳过")

    if tmp is not None and not args.keep_workdir:
        tmp.cleanup()

    print("== 汇总 ==")
    failed = [n for n, ok, _ in results if not ok]
    for n, ok, ev in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", n))
    if failed:
        print("e2e FAIL：%d 步未通过" % len(failed))
        return 1
    print("e2e PASS：%d/%d 步通过" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
