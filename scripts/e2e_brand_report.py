#!/usr/bin/env python3
"""品牌报告 e2e 验收（PRD-023/T5，trend #130）。

以 deepseek 为真实品牌走通 4 件产物：
  1. 完整报告：published/reports/deepseek/report.md 存在；
     断言 Score Total=208 / Score Normalized=8.32 / 版本 v3
  2. 一页摘要：跑 scripts/generate_exec_summary.py（真实脚本）；
     断言产物非空，且品牌/总分/归一化/版本与完整报告一致
  3. EVOLUTION delta 摘要：跑 scripts/generate_delta_summary.py（真实脚本）；
     断言产物非空，且 delta 区块（v2→v3、总分变化）与完整报告一致
  4. 飞书推送：scripts/notify_feishu.py --test --dry-run（真实脚本）；
     断言卡片 JSON 格式正确、未调真实 webhook（FEISHU_WEBHOOK 置空）

数据一致性是核心：四件产物里的品牌名、Score Total、Normalized、版本
必须互相一致，不一致则 FAIL。

本脚本纯标准库（子进程调用真实脚本），不调 LLM；第 4 步无网络 I/O。
注：T4（飞书推送摘要版，trend #129）未合并时，第 4 步测的是 main 上
的现行版本（交互卡片全文推送 era）；T4 落地后重跑本脚本即覆盖摘要版。

用法：
  python3 scripts/e2e_brand_report.py [--report PATH] [--brand deepseek]

退出码：0=4 步全 PASS；1=任一步 FAIL。
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent

# 完整报告的预期锚点（与 published/reports/deepseek/report.md 真实值一致）
BRAND = "deepseek"
EXPECT = {"score_total": 208.0, "score_normalized": 8.32, "version": "3"}

results = []  # (step_name, ok, evidence)


def check(name, ok, evidence=""):
    results.append((name, bool(ok), evidence))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name,
                         (" — " + evidence) if evidence else ""))
    return bool(ok)


def run(cmd, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                          cwd=str(REPO_ROOT), env=env)


def parse_report_anchors(text):
    """从完整报告抽取品牌/版本/总分/归一化（与生成脚本同源的正则口径）。"""
    d = {}
    m = re.search(r"^# (.+?) — Brand Influence Review \(v(\d+)\)", text, re.M)
    d["brand"] = m.group(1).strip() if m else ""
    d["version"] = m.group(2) if m else ""
    m = re.search(r"Score Total:\s*([\d.]+)\s*/\s*250", text)
    d["score_total"] = float(m.group(1)) if m else None
    m = re.search(r"Score Normalized:\s*([\d.]+)\s*/\s*10", text)
    d["score_normalized"] = float(m.group(1)) if m else None
    m = re.search(r"\*\*基线\*\*:\s*v(\d+)", text)
    d["prev_version"] = m.group(1) if m else ""
    return d


def step1_full_report(report_path):
    """产物 1：完整报告存在 + 关键数字符合预期。"""
    text = report_path.read_text(encoding="utf-8")
    a = parse_report_anchors(text)
    ok = (a["score_total"] == EXPECT["score_total"]
          and a["score_normalized"] == EXPECT["score_normalized"]
          and a["version"] == EXPECT["version"]
          and bool(a["brand"]))
    ev = "品牌=%s；总分=%s/250；归一化=%s/10；版本=v%s" % (
        a["brand"] or "?", a["score_total"], a["score_normalized"], a["version"])
    ok_all = check("1/4 完整报告", ok, ev)
    return ok_all, a


def step2_exec_summary(report_path, anchors):
    """产物 2：一页摘要（真实脚本）+ 与完整报告数据一致。"""
    r = run([sys.executable, str(SCRIPTS_DIR / "generate_exec_summary.py"),
             str(report_path)])
    if r.returncode != 0:
        return check("2/4 一页摘要", False,
                     "脚本退出码 %d：%s" % (r.returncode, (r.stderr or "")[:200])), None
    out = r.stdout or ""
    if not out.strip():
        return check("2/4 一页摘要", False, "产物为空"), None
    m = re.search(r"^# (.+?) — 一页摘要（v(\d+)", out, re.M)
    s_brand = m.group(1).strip() if m else ""
    s_ver = m.group(2) if m else ""
    m = re.search(r"\*\*综合评分\*\*：([\d.]+).*?归一化 ([\d.]+)", out)
    s_total = float(m.group(1)) if m else None
    s_norm = float(m.group(2)) if m else None
    ok = (s_brand == anchors["brand"]
          and s_total == anchors["score_total"]
          and s_norm == anchors["score_normalized"]
          and s_ver == anchors["version"])
    ev = ("品牌%s；总分%s；归一化%s；版本v%s（%d 字符）"
          % ("一致" if s_brand == anchors["brand"] else "不一致!",
             "一致" if s_total == anchors["score_total"] else "不一致!",
             "一致" if s_norm == anchors["score_normalized"] else "不一致!",
             "一致" if s_ver == anchors["version"] else "不一致!",
             len(out)))
    return check("2/4 一页摘要", ok, ev), out


def step3_delta_summary(report_path, anchors):
    """产物 3：EVOLUTION delta 摘要（真实脚本）+ delta 口径与报告一致。"""
    r = run([sys.executable, str(SCRIPTS_DIR / "generate_delta_summary.py"),
             str(report_path)])
    if r.returncode != 0:
        return check("3/4 delta 摘要", False,
                     "脚本退出码 %d：%s" % (r.returncode, (r.stderr or "")[:200])), None
    out = r.stdout or ""
    if not out.strip():
        return check("3/4 delta 摘要", False, "产物为空"), None
    pv = anchors["prev_version"]
    v = anchors["version"]
    wants = ["EVOLUTION delta（v%s → v%s）" % (pv, v),
             "总分", "207 → 208", "归一化", "8.28 → 8.32"]
    missing = [w for w in wants if w not in out]
    ok = not missing
    ev = ("delta 区块齐全（v%s→v%s，总分/归一化变化一致）"
          % (pv, v) if ok else "缺失: %s" % "、".join(missing))
    return check("3/4 delta 摘要", ok, ev), out


def step4_feishu_dryrun():
    """产物 4：飞书推送 dry-run（真实脚本）——卡片 JSON 格式正确，不调 webhook。"""
    # FEISHU_WEBHOOK 置空：证明 dry-run 不依赖真实 webhook、不产生网络调用
    env = dict(os.environ)
    env.pop("FEISHU_WEBHOOK", None)
    env.pop("FEISHU_WEBHOOK_L1", None)
    env.pop("FEISHU_WEBHOOK_L2", None)
    env.pop("FEISHU_WEBHOOK_L3", None)
    r = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "notify_feishu.py"),
         "--test", "--dry-run"],
        capture_output=True, text=True, timeout=120,
        cwd=str(REPO_ROOT), env=env)
    if r.returncode != 0:
        return check("4/4 飞书推送(dry-run)", False,
                     "脚本退出码 %d：%s" % (r.returncode, (r.stderr or "")[:200]))
    out = r.stdout or ""
    if "DRY-RUN" not in out:
        return check("4/4 飞书推送(dry-run)", False, "未进入 dry-run 路径")
    try:
        card = json.loads(out[out.index("{"):])
    except (ValueError, IndexError) as e:
        return check("4/4 飞书推送(dry-run)", False, "卡片 JSON 解析失败: %s" % e)
    header = ((card.get("card") or {}).get("header") or {})
    title = ((header.get("title") or {}).get("content") or "")
    ok = (card.get("msg_type") == "interactive"
          and "连通性测试" in title
          and bool((card.get("card") or {}).get("elements")))
    ev = ("dry-run 卡片 JSON 合法；msg_type=interactive；"
          "header=%s；未配置 webhook 仍 exit 0（无网络调用）"
          % (title[:24] + "…" if len(title) > 24 else title))
    return check("4/4 飞书推送(dry-run)", ok, ev)


def main() -> int:
    ap = argparse.ArgumentParser(description="品牌报告 e2e 验收（PRD-023/T5）")
    ap.add_argument("--report",
                    default=str(REPO_ROOT / "published" / "reports"
                                / BRAND / "report.md"),
                    help="完整报告路径")
    ap.add_argument("--brand", default=BRAND, help="品牌目录名")
    args = ap.parse_args()

    print("== 品牌报告 e2e 验收（PRD-023/T5）品牌=%s ==" % args.brand)

    report_path = pathlib.Path(args.report)
    if not report_path.is_file():
        check("0/4 前置", False, "报告不存在: %s" % report_path)
        print("== 汇总 ==\n  [FAIL] 0/4 前置\ne2e FAIL：前置未通过")
        return 1
    for name in ("generate_exec_summary.py", "generate_delta_summary.py",
                 "notify_feishu.py"):
        if not (SCRIPTS_DIR / name).is_file():
            check("0/4 前置", False, "脚本缺失: scripts/%s" % name)
            print("== 汇总 ==\n  [FAIL] 0/4 前置\ne2e FAIL：前置未通过")
            return 1
    check("0/4 前置", True, "报告与 3 个链路脚本就绪")

    ok1, anchors = step1_full_report(report_path)
    ok2, summary = step2_exec_summary(report_path, anchors) if ok1 else \
        (check("2/4 一页摘要", False, "第 1 步未通过，跳过"), None)
    ok3, _delta = step3_delta_summary(report_path, anchors) if ok1 else \
        (check("3/4 delta 摘要", False, "第 1 步未通过，跳过"), None)
    ok4 = step4_feishu_dryrun()

    print("== 数据一致性矩阵 ==")
    print("  品牌名      : 报告=%s" % anchors["brand"])
    print("  Score Total : 报告=%s（预期 208）" % anchors["score_total"])
    print("  Normalized  : 报告=%s（预期 8.32）" % anchors["score_normalized"])
    print("  版本        : 报告=v%s（预期 v3）" % anchors["version"])
    print("== 汇总 ==")
    failed = [n for n, ok, _ in results if not ok]
    for n, ok, _ in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", n))
    if failed:
        print("e2e FAIL：%d 步未通过" % len(failed))
        return 1
    print("e2e PASS：%d/%d 步通过" % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
