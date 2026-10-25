#!/usr/bin/env python3
"""mba 元评审 CI 摘要（PRD-063/T4，trend #336）。

在 PR 改动 metric-brand-auditor/panels/** yaml 时由 CI 调用：
自动选 published/reports/ 下 **Audit Date** 最新的品牌报告，
跑 scripts/meta_review.py（T2），把一页审计摘要
（总体一致性评级 / Top3 分歧点 / 建议复核项）输出为
$GITHUB_STEP_SUMMARY 用的 Markdown。

只报告、不设合并门禁：
- 本脚本永远 exit 0；审计失败/无报告时输出降级说明，不抛错。
- workflow 侧另有 `continue-on-error: true` 双保险；
  且该 job 不在分支保护的 required 列表里（仓库设置侧，由维护者确认）。

措辞纪律（T1 §四）：全文只出现"分歧点"/"疑似"/"建议人工复核"，
不出现"错误"/"定罪"（含否定式引用，一并净化）。

PRD-177/T3（trend #887）：可选 `--findings <path>` 透传给 meta_review.py，
在审计项 4（Top3 分歧点）输出行附 finding id 回指线索。消费纪律：只读不解释、
版本字段纪律（只认 prd-177-v1，由 meta_review 侧拒读）；文件不存在时输出
降级说明，不影响审计与退出码（永远 exit 0）。

用法：
  python3 scripts/ci_meta_review.py [--reports-dir DIR] [--report PATH] \
      [--findings published/reports/<brand>/versions/vN*/findings.json]
"""

import argparse
import pathlib
import re
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent


def _sanitize(text: str) -> str:
    """措辞纪律净化：去掉"错误"/"定罪"字样（含否定式引用）。"""
    text = re.sub(r"[，,]非[“\"]错误[”\"]/[“\"]定罪[”\"]结论", "", text)
    text = re.sub(r"不是[“\"]打分错误[”\"]的结论", "不作结论性判断", text)
    return text


def find_latest_report(reports_dir: pathlib.Path):
    """按 **Audit Date** 选最新的品牌报告。

    无日期的报告视为最旧；日期相同时按品牌名排序取末位（全确定）。
    一个都找不到时返回 None。
    """
    candidates = []
    for report in sorted(reports_dir.glob("*/report.md")):
        try:
            head = report.read_text(encoding="utf-8")[:3000]
        except OSError:
            continue
        m = re.search(r"\*\*Audit Date\*\*:\s*(\d{4}-\d{2}-\d{2})", head)
        date = m.group(1) if m else "0000-00-00"
        candidates.append((date, report.parent.name, report))
    if not candidates:
        return None
    candidates.sort(key=lambda c: (c[0], c[1]))
    return candidates[-1][2]


def run_audit(report_path: pathlib.Path, extra_args: list[str] | None = None):
    """跑 T2 审计（可附 PRD-177/T3 --findings 透传），返回 (stdout, err_note)。失败时 stdout 为 None。"""
    try:
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "meta_review.py"), str(report_path),
             *(extra_args or [])],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except Exception as e:  # noqa: BLE001 —— CI 里只报告，不抛错
        return None, f"审计脚本执行异常：{e}"
    if r.returncode != 0:
        return None, f"审计脚本退出码 {r.returncode}：{(r.stderr or '').strip()[-300:]}"
    return r.stdout, ""


def extract_summary(audit_md: str) -> dict:
    """从 T2 输出的"一页审计摘要"提取：评级 / 最大σ / Top3 / 建议复核项。"""
    d = {"grade": "?", "max_sigma": "?", "top3": [], "review": []}
    m = re.search(r"总体一致性评级：([A-F])", audit_md)
    if m:
        d["grade"] = m.group(1)
    m = re.search(r"最大维度 σ=([\d.]+)", audit_md)
    if m:
        d["max_sigma"] = m.group(1)

    in_summary = in_top3 = in_review = False
    for ln in audit_md.splitlines():
        if ln.startswith("## 一页审计摘要"):
            in_summary = True
            continue
        if in_summary and ln.startswith("## "):
            break
        if not in_summary:
            continue
        if re.match(r"^2\.\s*\*\*Top3 分歧点", ln):
            in_top3, in_review = True, False
            continue
        if re.match(r"^3\.\s*\*\*建议复核项", ln):
            in_top3, in_review = False, True
            continue
        if in_top3:
            m = re.match(r"^\s*\d+\.\s*(.+?)\s*$", ln)
            if m:
                d["top3"].append(m.group(1))
        elif in_review:
            s = ln.strip()
            if s.startswith("- "):
                d["review"].append(s[2:].strip())
            elif s.startswith("（") and s.endswith("）"):
                d["review"].append(s)
    return d


def render_ci_summary(brand: str, report_rel: str, d: dict,
                      findings_rel: str | None = None,
                      findings_note: str = "") -> str:
    """渲染 job summary Markdown（已做措辞净化）。"""
    lines = [
        "## 🔍 元评审 CI 摘要（PRD-063/T4）",
        "",
        "> 信息展示，不设合并门禁：本检查只报告当前打分一致性基线，不 block 合并。",
        "",
        f"**输入报告**：`{report_rel}`（24 个品牌中 Audit Date 最新：{brand}）",
        "",
    ]
    if findings_rel:
        lines.append(
            f"**findings 线索**：`{findings_rel}`（PRD-177/T3 只读回指，"
            "Top3 分歧点行内附 finding id；三态合法性判定权在 "
            "`scripts/validate_findings.py`，四项审计与 A–F 阈值未动）")
        lines.append("")
    if findings_note:
        lines.append(f"**findings 降级说明**：{findings_note}")
        lines.append("")
    lines += [
        f"**总体一致性评级：{d['grade']}**（最大维度 σ={d['max_sigma']}；"
        "评级只反映分歧程度，不等于打分质量）",
        "",
        "**Top3 分歧点**：",
    ]
    if d["top3"]:
        lines.extend(f"{i}. {item}" for i, item in enumerate(d["top3"], 1))
    else:
        lines.append("本轮无")
    lines += ["", "**建议复核项**（建议人工复核）："]
    if d["review"]:
        lines.extend(f"- {item}" for item in d["review"])
    else:
        lines.append("本轮无")
    lines += [
        "",
        "---",
        "审计引擎：`scripts/meta_review.py`（纯计算，未重新打分）；"
        "阈值与基线待多品牌样本攒够后回调（T1 §二）。",
    ]
    return _sanitize("\n".join(lines))


def degraded(note: str) -> str:
    return "\n".join(
        [
            "## 🔍 元评审 CI 摘要（PRD-063/T4）",
            "",
            "> 信息展示，不设合并门禁。",
            "",
            f"本轮未产出审计摘要（{note}），不影响合并。",
        ]
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="元评审 CI 摘要（只报告，不设门禁）")
    ap.add_argument("--reports-dir", default=str(REPO_ROOT / "published" / "reports"))
    ap.add_argument("--report", default=None, help="直接指定报告路径（本地自测用）")
    ap.add_argument("--findings", default=None,
                    help="findings.json 路径（PRD-177/T3 只读线索透传；"
                         "文件不存在时降级说明）")
    args = ap.parse_args()

    findings_args: list[str] = []
    findings_rel: str | None = None
    findings_note = ""
    if args.findings:
        fp = pathlib.Path(args.findings)
        if fp.is_file():
            findings_args = ["--findings", str(fp)]
            try:
                findings_rel = str(fp.resolve().relative_to(REPO_ROOT))
            except ValueError:
                findings_rel = str(fp)
        else:
            findings_note = ("指定的 findings 文件不存在，线索消费降级"
                             "（审计不受影响）：%s" % args.findings)

    if args.report:
        report_path = pathlib.Path(args.report)
        if not report_path.is_file():
            print(degraded(f"指定报告不存在：{args.report}"))
            return 0
    else:
        report_path = find_latest_report(pathlib.Path(args.reports_dir))
        if report_path is None:
            print(degraded("published/reports/ 下未找到品牌报告"))
            return 0

    audit_md, err = run_audit(report_path, findings_args)
    if audit_md is None:
        print(degraded(err))
        return 0

    try:
        rel = str(report_path.relative_to(REPO_ROOT))
    except ValueError:
        rel = str(report_path)
    brand = report_path.parent.name
    print(render_ci_summary(brand, rel, extract_summary(audit_md),
                            findings_rel=findings_rel, findings_note=findings_note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
