#!/usr/bin/env python3
"""指挥舱自动刷新与异动告警（PRD-062/T4，trend #326）。

定时刷新 data/deck.json（节拍见 config/deck_refresh.json），刷新前后对比，
只在"异动"时推送飞书告警，不推常规更新（T1 §七：只推异动不推常规）。

异动口径（阈值来源见 config/deck_refresh.json 的 _threshold_sources）：
  1. 健康度：综合评分 score_total 下降超阈值（缺省 5 分/250）
  2. 健康度：任一 lens 均值变化超阈值（缺省 ±0.5）
  3. 舆情：负面声量日环比增幅超阈值（缺省 +50%；昨日为 0 时按 ≥5 条计）
  4. 舆情：新增 Top 热点事件（天然异动，直接告警）
  5. 竞品：新增关键事件（天然异动，直接告警）

飞书推送：webhook URL 从环境变量（默认 DECK_ALERT_WEBHOOK，可配置）读取，
仓库里不硬编码任何 webhook。未配置时降级为 dry-run：打印到 stdout。

幂等：data/deck_state.json（gitignore，不入库）记录各段 fingerprint 与已告警
事件 key，避免重复告警。webhook 推送失败时不推进状态，下次重跑会重试。

纯标准库，不调 LLM。

用法：
  python3 scripts/refresh_deck.py [--section health|sentiment|competitors|all]
                                  [--report <报告路径>] [--skip-live] [--dry-run]
  python3 scripts/refresh_deck.py --check-only --old old.json --new new.json
                                  # 只检测异动不刷新（自测/排障用），不写状态
  python3 scripts/refresh_deck.py --print-cron
                                  # 打印建议的 crontab 行

退出码：0=正常（含无异动静默）；1=参数/配置错误；2=刷新或推送失败。
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import pathlib
import sys
import urllib.request
import urllib.error

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_REFRESH_CONFIG = REPO_ROOT / "config" / "deck_refresh.json"
SHANGHAI = datetime.timezone(datetime.timedelta(hours=8))
SECTIONS = ("health", "sentiment", "competitors")


def _load_sibling(name):
    here = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(name, here / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _now_iso():
    return datetime.datetime.now(SHANGHAI).isoformat()


def fingerprint(section):
    """段内容的稳定指纹（canonical JSON → sha1）。"""
    canon = json.dumps(section, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"))
    return hashlib.sha1(canon.encode("utf-8")).hexdigest()


def detect_anomalies(old, new, thr):
    """对比新旧 deck，返回 [(去重 key, 告警文本)]。纯函数，无副作用。"""
    alerts = []
    old = old or {}
    new = new or {}

    # ---- 1/2. 健康度 ----
    oh, nh = old.get("health"), new.get("health")
    if isinstance(oh, dict) and isinstance(nh, dict):
        try:
            drop = oh["score_total"] - nh["score_total"]
        except (KeyError, TypeError):
            drop = 0
        if drop > thr["health_score_total_drop"]:
            alerts.append((
                "health:score_drop:%s" % nh["score_total"],
                "健康度：综合评分 %s → %s（下降 %s 分，阈值 %s 分）"
                % (oh["score_total"], nh["score_total"], drop,
                   thr["health_score_total_drop"]),
            ))
        old_lens = {l.get("key"): l for l in oh.get("lenses", [])
                    if isinstance(l, dict)}
        for l in nh.get("lenses", []):
            if not isinstance(l, dict):
                continue
            ol = old_lens.get(l.get("key"))
            if not ol:
                continue
            try:
                delta = float(l["mean"]) - float(ol["mean"])
            except (KeyError, TypeError, ValueError):
                continue
            if abs(delta) > thr["health_lens_change"]:
                name = l.get("name_cn") or l.get("key")
                alerts.append((
                    "health:lens:%s:%s" % (l.get("key"), l["mean"]),
                    "健康度：%s %s → %s（变化 %+.1f，阈值 ±%s）"
                    % (name, ol["mean"], l["mean"], delta,
                       thr["health_lens_change"]),
                ))

    # ---- 3/4. 舆情 ----
    os_, ns_ = old.get("sentiment"), new.get("sentiment")
    if isinstance(ns_, dict):
        dv = ns_.get("daily_volume") or []
        if len(dv) >= 2:
            try:
                prev = int(dv[-2].get("negative", 0))
                cur = int(dv[-1].get("negative", 0))
            except (TypeError, ValueError):
                prev, cur = 0, 0
            pct_thr = thr["sentiment_negative_surge_pct"]
            min_thr = thr["sentiment_negative_surge_min"]
            if prev > 0:
                pct = (cur - prev) / prev * 100
                if pct > pct_thr:
                    alerts.append((
                        "sentiment:surge:%s:%s" % (dv[-1].get("date"), cur),
                        "舆情：昨日负面声量 %s → %s（+%.0f%%，阈值 +%s%%）"
                        % (prev, cur, pct, pct_thr),
                    ))
            elif cur >= min_thr:
                alerts.append((
                    "sentiment:surge:%s:%s" % (dv[-1].get("date"), cur),
                    "舆情：昨日负面声量 0 → %s（此前为 0，阈值 ≥%s 条）"
                    % (cur, min_thr),
                ))
        old_titles = {e.get("title") for e in (os_ or {}).get("top_events", [])
                      if isinstance(e, dict)}
        for e in ns_.get("top_events", []):
            if not isinstance(e, dict):
                continue
            if e.get("title") not in old_titles:
                alerts.append((
                    "sentiment:event:%s" % e.get("title"),
                    "舆情新增热点：%s" % e.get("title"),
                ))

    # ---- 5. 竞品 ----
    oc, nc = old.get("competitors"), new.get("competitors")
    if isinstance(nc, dict):
        old_keys = {(e.get("brand"), e.get("title"))
                    for e in (oc or {}).get("events", [])
                    if isinstance(e, dict)}
        for e in nc.get("events", []):
            if not isinstance(e, dict):
                continue
            if (e.get("brand"), e.get("title")) not in old_keys:
                alerts.append((
                    "competitors:event:%s:%s" % (e.get("brand"), e.get("title")),
                    "竞品新增事件：%s %s" % (e.get("brand"), e.get("title")),
                ))

    return alerts


def build_message(brand, alerts, when_iso):
    lines = ["【指挥舱异动告警】%s · %s" % (brand, when_iso[:16].replace("T", " ")),
             "共 %d 条异动：" % len(alerts)]
    lines += ["• %s" % text for _, text in alerts]
    return "\n".join(lines)


def send_feishu(webhook_url, text):
    """飞书自定义机器人 webhook 推送。成功返回 True。"""
    payload = {"msg_type": "text", "content": {"text": text}}
    req = urllib.request.Request(
        webhook_url, data=json.dumps(payload).encode("utf-8"),
        method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:
        print("ERROR: 飞书推送失败（网络）: %s" % e, file=sys.stderr)
        return False
    try:
        code = json.loads(body).get("code", 0)
    except ValueError:
        code = 0  # 非 JSON 回包按 HTTP 200 视为成功
    if code != 0:
        print("ERROR: 飞书推送失败（code=%s）: %s" % (code, body[:200]),
              file=sys.stderr)
        return False
    return True


def load_state(path):
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            print("WARN: 状态文件损坏，从空状态开始: %s" % path, file=sys.stderr)
    return {"sections": {}, "seen_alert_keys": [], "updated_at": None}


def save_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    tmp.replace(path)


def refresh_section(section, deck, report_path, sources_cfg, skip_live):
    """刷新单个段（复用 T2 模块能力）。返回更新后的 deck。"""
    now = datetime.datetime.now(SHANGHAI)
    bdj = _load_sibling("build_deck_json")
    if section == "health":
        deck["health"] = bdj.extract_health(report_path)
    elif section == "sentiment":
        sc = _load_sibling("sentiment_collector")
        try:
            deck["sentiment"] = sc.collect_sentiment(
                deck.get("brand") or "deepseek", sources_cfg, now=now)
        except Exception as e:
            print("WARN: 舆情采集异常，该段置 null: %s" % e, file=sys.stderr)
            deck["sentiment"] = None
    elif section == "competitors":
        ct = _load_sibling("competitor_tracker")
        try:
            deck["competitors"] = ct.collect_competitors(sources_cfg, now=now)
        except Exception as e:
            print("WARN: 竞品追踪异常，该段置 null: %s" % e, file=sys.stderr)
            deck["competitors"] = None
    deck["generated_at"] = _now_iso()
    return deck


def refresh_all(report_path, sources_cfg, skip_live):
    bdj = _load_sibling("build_deck_json")
    return bdj.build_deck(report_path, sources_cfg, skip_live=skip_live)


def print_cron(cfg):
    root = REPO_ROOT
    for item in cfg.get("schedule", []):
        sec, cron, desc = item["section"], item.get("cron"), item.get("desc", "")
        if cron:
            print("%s cd %s && python3 scripts/refresh_deck.py --section %s  # %s"
                  % (cron, root, sec, desc))
        else:
            print("# %s：%s" % (sec, desc))


def main():
    ap = argparse.ArgumentParser(description="指挥舱自动刷新与异动告警（PRD-062/T4）")
    ap.add_argument("--section", default="all",
                    choices=("all", "health", "sentiment", "competitors"),
                    help="只刷指定段（缺省 all）")
    ap.add_argument("--report", help="健康度报告路径（缺省取刷新配置）")
    ap.add_argument("--config", default=str(DEFAULT_REFRESH_CONFIG),
                    help="刷新配置文件")
    ap.add_argument("--skip-live", action="store_true",
                    help="跳过实时采集（sentiment/competitors 置 null），离线自测用")
    ap.add_argument("--dry-run", action="store_true",
                    help="强制 dry-run：不推送飞书，只打印告警文本")
    ap.add_argument("--check-only", action="store_true",
                    help="只检测异动不刷新：需配合 --old/--new，不写状态文件")
    ap.add_argument("--old", help="--check-only 的旧 deck.json")
    ap.add_argument("--new", help="--check-only 的新 deck.json")
    ap.add_argument("--print-cron", action="store_true",
                    help="打印建议的 crontab 行")
    args = ap.parse_args()

    cfg_path = pathlib.Path(args.config)
    if not cfg_path.is_file():
        print("ERROR: 刷新配置不存在: %s" % cfg_path, file=sys.stderr)
        return 1
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    thr = cfg.get("alert", {}).get("thresholds", {})
    for k, v in {"health_score_total_drop": 5, "health_lens_change": 0.5,
                 "sentiment_negative_surge_pct": 50,
                 "sentiment_negative_surge_min": 5}.items():
        thr.setdefault(k, v)
    deck_path = REPO_ROOT / cfg.get("deck_path", "data/deck.json")
    state_path = REPO_ROOT / cfg.get("state_path", "data/deck_state.json")

    if args.print_cron:
        print_cron(cfg)
        return 0

    # ---------- --check-only：纯检测 ----------
    if args.check_only:
        if not args.old or not args.new:
            print("ERROR: --check-only 需要 --old 与 --new", file=sys.stderr)
            return 1
        old = json.loads(pathlib.Path(args.old).read_text(encoding="utf-8"))
        new = json.loads(pathlib.Path(args.new).read_text(encoding="utf-8"))
        alerts = detect_anomalies(old, new, thr)
        if not alerts:
            return 0  # 无异动：零输出
        print(build_message(new.get("brand") or "?", alerts, _now_iso()))
        return 0

    # ---------- 正常流程：刷新 → 检测 → 告警 ----------
    report_arg = args.report or cfg.get("health", {}).get("report_path")
    report_path = (REPO_ROOT / report_arg) if report_arg else None

    old_deck = None
    if deck_path.is_file():
        try:
            old_deck = json.loads(deck_path.read_text(encoding="utf-8"))
        except ValueError as e:
            print("WARN: 现有 deck.json 解析失败，按无基线处理: %s" % e,
                  file=sys.stderr)

    sources_cfg = json.loads(
        (REPO_ROOT / cfg.get("sources_config",
                             "config/deck_sources.json")).read_text(encoding="utf-8"))

    if args.section == "all":
        if not report_path or not report_path.is_file():
            print("ERROR: 报告不存在: %s（可用 --report 指定）" % report_path,
                  file=sys.stderr)
            return 1
        try:
            new_deck = refresh_all(report_path, sources_cfg, args.skip_live)
        except ValueError as e:
            print("ERROR: %s" % e, file=sys.stderr)
            return 2
    else:
        if old_deck is None:
            print("ERROR: 无现有 deck.json，先跑 --section all 建立基线",
                  file=sys.stderr)
            return 1
        if args.section == "health" and (not report_path
                                         or not report_path.is_file()):
            print("ERROR: 报告不存在: %s（可用 --report 指定）" % report_path,
                  file=sys.stderr)
            return 1
        new_deck = json.loads(json.dumps(old_deck))  # 深拷贝
        new_deck = refresh_section(args.section, new_deck, report_path,
                                   sources_cfg, args.skip_live)

    # 落盘（原子写）
    tmp = deck_path.with_suffix(".tmp")
    deck_path.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(new_deck, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    tmp.replace(deck_path)

    # ---------- 异动检测 ----------
    state = load_state(state_path)
    seen = set(state.get("seen_alert_keys", []))
    raw_alerts = detect_anomalies(old_deck, new_deck, thr)
    alerts = [(k, t) for k, t in raw_alerts if k not in seen]

    # 状态推进：fingerprint 总是跟进；seen keys 只在告警送达后追加
    for s in SECTIONS:
        if isinstance(new_deck.get(s), dict):
            state["sections"][s] = fingerprint(new_deck[s])
    state["updated_at"] = _now_iso()

    if not alerts:
        save_state(state_path, state)
        return 0  # 无异动：stdout 零输出

    message = build_message(new_deck.get("brand") or "?", alerts, _now_iso())
    webhook_env = cfg.get("alert", {}).get("webhook_env",
                                           "DECK_ALERT_WEBHOOK")
    webhook = os.environ.get(webhook_env)
    if args.dry_run or not webhook:
        print("[dry-run] 飞书告警（未配置 %s）：" % webhook_env)
        print(message)
        delivered = True
    else:
        delivered = send_feishu(webhook, message)
        if delivered:
            print("飞书告警已推送（%d 条）" % len(alerts))
    if not delivered:
        # 推送失败：不推进 seen keys，下次重跑重试；状态文件不写。
        print("ERROR: 告警未送达，状态未推进，下次重跑会重试",
              file=sys.stderr)
        return 2
    state["seen_alert_keys"] = sorted(seen | {k for k, _ in alerts})
    save_state(state_path, state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
