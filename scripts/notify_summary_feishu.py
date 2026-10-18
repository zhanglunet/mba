#!/usr/bin/env python3
"""飞书推送摘要版（PRD-023/T4，trend #129）。

报告产出后，把 T1 格式的一页摘要推到飞书群，完整报告给链接
（代替"全文推送"；T1 §四.4：飞书推送版 = 同一文本，附完整报告链接）。

- 默认摘要版：`generate_exec_summary.extract()` 纯抽取（T2，不重新打分、
  不引入新结论）→ 纯文本一屏 + 完整报告链接。
- `--full`：推送完整报告正文（超长时截断并注明，仍附链接）——保留
  完整版推送能力，默认摘要版（PRD 口径）。
- webhook 只从环境变量读（默认 `FEISHU_WEBHOOK`，可用 `--webhook-env`
  改名），仓库不硬编码任何 webhook；未配置时跳过（exit 0，非阻断）。
- `--dry-run`：只打印将要发送的文本，不 POST（供 T5 e2e 与本地自测用；
  接口保持稳定：函数名/参数不变）。

纯标准库，不调 LLM。摘要内容全部来自报告原文抽取，无新结论。

用法：
  python3 scripts/notify_summary_feishu.py --report published/reports/deepseek/report.md [--dry-run] [--full]

退出码：0=已推送 / dry-run / 无 webhook 跳过；1=POST 失败；2=参数或报告错误。
"""
import argparse
import base64
import hashlib
import hmac
import importlib.util
import json
import os
import pathlib
import sys
import time
import urllib.request
import urllib.error

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
SITE = "https://mbabrand.com"  # 与 scripts/notify_feishu.py 同口径（公开站点，非密钥）
FULL_TEXT_LIMIT = 30000  # --full 时正文截断上限（飞书单条消息长度限制的保守内值）


def _load_sibling(name):
    spec = importlib.util.spec_from_file_location(
        name, SCRIPTS_DIR / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def extract_summary(report_path):
    """T2 纯抽取：返回一页摘要 dict（键与 generate_exec_summary.render 一致）。"""
    ges = _load_sibling("generate_exec_summary")
    return ges.extract(pathlib.Path(report_path))


def report_url(slug):
    """完整报告链接（与 notify_feishu.py 的 [报告 →] 同口径）。"""
    return f"{SITE}/reports/{slug}/"


def build_summary_text(d, url):
    """T1 一页摘要 → 飞书纯文本（一屏可读）+ 完整报告链接。

    区块顺序与 generate_exec_summary.render() 一致（T1 §四.4"同一文本"）。
    纯函数，无副作用；T5 e2e 可直接调（接口稳定）。
    """
    v, pv = d.get("version", ""), d.get("prev_version", "")
    ver = f"v{v}" if v else ""
    head = "【MBA 一页摘要】%s" % d.get("brand", "?")
    if ver:
        head += " · " + ver
    if d.get("date"):
        head += " · " + d["date"]
    lines = [
        head,
        "",
        "一句话定位：%s" % d.get("positioning", "本轮无"),
        "综合评分：%s" % d.get("score", "本轮无"),
        "最强维度：%s" % d.get("top_dims", "本轮无"),
        "最弱维度：%s" % d.get("bottom_dims", "本轮无"),
        "评委最大分歧点：%s" % d.get("dissent", "本轮无"),
        "90 天行动 Top3：%s" % d.get("actions", "本轮无"),
        "",
        ("EVOLUTION delta（v%s → v%s）" % (pv, v)) if pv and v else "EVOLUTION delta",
        "· 本次评分变化：%s" % d.get("delta_score", "本轮无"),
        "· 移动的维度：%s" % d.get("delta_dims", "本轮无"),
        "· 新增关键事件：%s" % d.get("delta_events", "本轮无"),
        "· 触发器状态：%s" % d.get("delta_triggers", "本轮无"),
        "· 一句话为什么变：%s" % d.get("delta_why", "本轮无"),
        "",
        "完整报告：%s" % url,
    ]
    return "\n".join(lines)


def build_full_text(report_path, url, limit=FULL_TEXT_LIMIT):
    """完整版推送文本：报告正文（超长截断并注明）+ 完整报告链接。"""
    text = pathlib.Path(report_path).read_text(encoding="utf-8").strip()
    note = ""
    if len(text) > limit:
        text = text[:limit].rstrip() + "\n…"
        note = "\n（正文过长已截断，详见完整报告链接）"
    return "%s%s\n\n完整报告：%s" % (text, note, url)


def sign(secret, timestamp):
    """飞书自定义机器人签名（与 notify_feishu.py 同算法）。"""
    string_to_sign = "%s\n%s" % (timestamp, secret)
    digest = hmac.new(string_to_sign.encode("utf-8"), b"",
                      digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def post_text(webhook_url, text, secret=None, timeout=15):
    """飞书 text 消息推送。返回 (ok, detail)。"""
    body = {"msg_type": "text", "content": {"text": text}}
    if secret:
        ts = str(int(time.time()))
        body = {"timestamp": ts, "sign": sign(secret, ts), **body}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(webhook_url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:
        return False, "network error: %s" % e
    try:
        j = json.loads(raw)
    except ValueError:
        return False, "non-JSON response: %s" % raw[:200]
    if j.get("code") == 0 or j.get("StatusCode") == 0:
        return True, "ok"
    return False, "feishu error: %s" % raw[:200]


def main() -> int:
    ap = argparse.ArgumentParser(description="飞书推送摘要版（PRD-023/T4）")
    ap.add_argument("--report", required=True,
                    help="完整报告路径，如 published/reports/deepseek/report.md")
    ap.add_argument("--dry-run", action="store_true",
                    help="只打印将要发送的文本，不 POST（自测/T5 e2e 用）")
    ap.add_argument("--full", action="store_true",
                    help="推送完整报告正文（默认只推一页摘要）")
    ap.add_argument("--webhook-env", default="FEISHU_WEBHOOK",
                    help="读取 webhook URL 的环境变量名（默认 FEISHU_WEBHOOK）")
    args = ap.parse_args()

    report_path = pathlib.Path(args.report)
    if not report_path.is_file():
        print("ERROR: 报告不存在: %s" % args.report, file=sys.stderr)
        return 2
    slug = report_path.parent.name
    url = report_url(slug)

    if args.full:
        text = build_full_text(report_path, url)
        mode = "完整版"
    else:
        try:
            d = extract_summary(report_path)
        except Exception as e:  # noqa: BLE001 —— 抽取失败大声报错，不推空消息
            print("ERROR: 摘要抽取失败: %s" % e, file=sys.stderr)
            return 2
        text = build_summary_text(d, url)
        mode = "摘要版"

    if args.dry_run:
        print("[dry-run] 飞书推送（%s，未 POST）：" % mode)
        print(text)
        return 0

    webhook = os.environ.get(args.webhook_env, "").strip()
    if not webhook:
        print("[feishu] 未设置 %s — 跳过推送（非阻断）" % args.webhook_env)
        return 0
    secret = os.environ.get("FEISHU_SIGN_SECRET", "").strip() or None
    ok, detail = post_text(webhook, text, secret)
    print("[feishu] 摘要推送（%s）:%s（%s）" % (mode, "成功" if ok else "失败", detail))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
