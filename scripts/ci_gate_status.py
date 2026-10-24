#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mba 评委工程质量门禁 CI 摘要（PRD-151/T3，trend #757）。

在 PR 改动 perspectives/** 时由 meta-review job（panel-validation.yml，PRD-063/T4
先例）调用：对受影响评委跑 scripts/perspective-tools/quality_gate.py（T2），
把"评委工程质量门禁状态"段输出为 $GITHUB_STEP_SUMMARY 用的 Markdown。

与 PRD-063 元评审的挂钩方式（T1 §四，docs/plans/2026-10-23-judge-quality-gate.md）：
1. 触发：git diff --name-only base..head -- perspectives/ 命中的评委套件（§三.2
   "PR 改动 perspectives/** 时跑受影响评委"，复用 meta-review job 的 diff 检测模式）；
   --judges 可显式指定（本地自测用）。
2. 只读接口：门禁结果只经 quality_gate --json-out 的契约 JSON 行（T1 §四.2：
   gate_version/judge_slug/items[id,level,status]/三个计数；status 四值枚举
   pass/warn/fail/exempt，level 固定 P0/P1）传递到本脚本——本脚本对门禁只读
   不解释：不重跑条目、不改判定，只按契约字段渲染。
3. 复核线索联动（§四.3）：--audit-md 提供元评审审计输出（ci_meta_review.py 的
   Markdown，本 PR 同时改 panel yaml 时由 workflow tee 落盘）时，为松紧度画像中
   偏松/偏紧的评委附"最近一次 checklist 结论 + 过门日期"——来源优先级：本次运行
   的契约 JSONL → docs/quality/judges/<slug>-<YYYY-MM-DD>.md 入库归档（§四.5）。
   只加线索，不改元评审四项审计算法与 A–F 阈值；引擎当前单报告（K=1<3）不下
   系统性结论，本段保留该措辞。

只报告、不设合并门禁（PRD-063 §四.3 纪律）：
- 本脚本永远 exit 0；门禁运行失败/找不到评委时输出降级说明，不抛错。
- workflow 侧 meta-review job 另有 continue-on-error: true 双保险。

措辞纪律（PRD-063 §四 / PRD-151）：全文只出现"缺口"/"疑似"/"建议人工复核"，
不出现"错误"/"定罪"措辞；"工程质量缺口"≠"打分错误"。

用法（在仓库根；CI 传 base/head，本地自测可传 --judges）：
  python3 scripts/ci_gate_status.py --base <sha> --head <sha> \
      [--audit-md meta-review-audit.md] [--gate-results FILE]
  python3 scripts/ci_gate_status.py --judges satyanadella,zhouhongyi \
      [--judges-dir DIR] [--panels-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
GATE_SCRIPT = REPO_ROOT / "scripts" / "perspective-tools" / "quality_gate.py"

GATE_VERSION = "prd-151-v1"          # T1 §四.2 契约版本
STATUSES = ("pass", "warn", "fail", "exempt")  # 四值枚举
LEVELS = ("P0", "P1")
CONTRACT_KEYS = ("gate_version", "judge_slug", "items",
                 "pass_count", "warn_count", "exempt_count")
GATE_TIMEOUT = 900  # 秒，与 quality_gate.run_cmd 同量级（CI 冷启动留余量）

# perspectives/<slug>-perspective/** → slug（受影响评委推导）
PERSPECTIVE_PATH = re.compile(r"^perspectives/([A-Za-z0-9_.-]+?)-perspective(?:/|$)")
# 元评审附录 C 松紧度画像行：- 杨植麟：bias=0.32（偏松）[；Judge Total 交叉验证：松]
BIAS_LINE = re.compile(r"^- (.+?)：bias=([+-]?[\d.]+)（(偏松|偏紧|居中)）")
# 入库归档文件名：<slug>-<YYYY-MM-DD>.md（T1 §四.5；过门日期取自文件名，git 锚定）
ARCHIVED_NAME = re.compile(r"^(?P<slug>[A-Za-z0-9_.-]+)-(?P<date>\d{4}-\d{2}-\d{2})\.md$")


# ── 受影响评委推导（T1 §三.2：PR 改动 perspectives/** 时跑受影响评委）──────────
def slugs_from_paths(paths: list[str]) -> list[str]:
    """changed 路径列表 → 去重排序的受影响评委 slug 列表（确定性）。"""
    slugs = set()
    for p in paths:
        m = PERSPECTIVE_PATH.match(p.strip())
        if m:
            slugs.add(m.group(1))
    return sorted(slugs)


def affected_slugs(base: str, head: str) -> list[str] | None:
    """git diff base..head -- perspectives/ → 受影响评委。git 失败返回 None。"""
    try:
        r = subprocess.run(
            ["git", "diff", "--name-only", base, head, "--", "perspectives/"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120)
    except Exception as e:  # noqa: BLE001 —— CI 里只报告，不抛错
        print("ci_gate_status.py: diff 检测执行异常：%s" % e, file=sys.stderr)
        return None
    if r.returncode != 0:
        print("ci_gate_status.py: git diff 退出码 %d：%s"
              % (r.returncode, (r.stderr or "").strip()[-200:]), file=sys.stderr)
        return None
    return slugs_from_paths(r.stdout.splitlines())


# ── 运行门禁并产出契约 JSONL（quality_gate --json-out，T1 §四.2 接口）──────────
def run_gate(slug: str, jsonl_path: pathlib.Path) -> tuple[int, str]:
    """对单个评委跑 quality_gate --judge --json-out。

    返回 (退出码, 说明)。0=PASS、1=FAIL 都是正常产报告（JSONL 已写）；2 及异常
    视为运行失败（降级说明，不阻断）。
    """
    try:
        r = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), "--judge", slug,
             "--json-out", str(jsonl_path)],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=GATE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return 2, "quality_gate 超时（>%ds）" % GATE_TIMEOUT
    except Exception as e:  # noqa: BLE001
        return 2, "quality_gate 执行异常：%s" % e
    note = (r.stderr or "").strip()[-200:]
    return r.returncode, note


# ── 契约 JSONL 读取（元评审侧只读不解释）──────────────────────────────────────
def _contract_ok(payload) -> str | None:
    """校验一行契约 JSON（T1 §四.2）。合法返回 None，否则返回缺口说明。"""
    if not isinstance(payload, dict):
        return "行不是 JSON 对象"
    missing = [k for k in CONTRACT_KEYS if k not in payload]
    if missing:
        return "缺字段 %s" % "、".join(missing)
    if payload["gate_version"] != GATE_VERSION:
        return "gate_version=%r（本消费方只认 %s，契约演进请同步更新）" % (
            payload["gate_version"], GATE_VERSION)
    if not isinstance(payload["judge_slug"], str) or not payload["judge_slug"]:
        return "judge_slug 非法"
    items = payload["items"]
    if not isinstance(items, list) or not items:
        return "items 非法"
    for it in items:
        if not isinstance(it, dict) or set(it) != {"id", "level", "status"}:
            return "items 条目字段非法"
        if not isinstance(it["id"], str):
            return "items 条目 id 非法"
        if it["level"] not in LEVELS:
            return "items 条目 level=%r 非法" % (it["level"],)
        if it["status"] not in STATUSES:
            return "items 条目 status=%r 非法" % (it["status"],)
    for k in ("pass_count", "warn_count", "exempt_count"):
        if not isinstance(payload[k], int) or payload[k] < 0:
            return "%s 非法" % k
    return None


def load_contract_lines(jsonl_path: pathlib.Path) -> tuple[dict, list[str]]:
    """读契约 JSONL → ({slug: payload}, 警告列表)。只读不解释：不重算、不重判。

    同一评委多行时取最后一行（--json-out 追加语义，T3 接口约定）；
    不合法的行跳过并记警告（显式列出，不静默）。
    """
    payloads: dict[str, dict] = {}
    warnings: list[str] = []
    if not jsonl_path.is_file():
        return payloads, ["契约文件不存在：%s（门禁未产出任何结果）" % jsonl_path]
    for ln, line in enumerate(
            jsonl_path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as e:
            warnings.append("第 %d 行不是合法 JSON：%s" % (ln, e))
            continue
        bad = _contract_ok(payload)
        if bad:
            warnings.append("第 %d 行不符合契约：%s" % (ln, bad))
            continue
        payloads[payload["judge_slug"]] = payload
    return payloads, warnings


def verdict_of(payload: dict) -> str:
    """按契约字段机械推导结论（T1 §二 计分口径：P0 任一 fail ⇒ FAIL）。"""
    if any(it["status"] == "fail" and it["level"] == "P0" for it in payload["items"]):
        return "FAIL"
    return "PASS"


# ── §四.3 复核线索联动的数据源 ────────────────────────────────────────────────
def parse_bias_portrait(audit_md: str) -> list[tuple[str, str, str]]:
    """从元评审审计输出解析附录 C 松紧度画像 → [(display_name, bias, 偏松/偏紧/居中)]。

    只读不改：原样保留引擎的排序与措辞；解析不到返回空列表。
    """
    out: list[tuple[str, str, str]] = []
    in_c = False
    for ln in audit_md.splitlines():
        if ln.startswith("### C. 松紧度画像"):
            in_c = True
            continue
        if in_c and ln.startswith("### "):
            break
        if not in_c:
            continue
        m = BIAS_LINE.match(ln)
        if m:
            out.append((m.group(1), m.group(2), m.group(3)))
    return out


def display_to_slugs(panels_dir: pathlib.Path) -> dict[str, list[str]]:
    """panel yaml（行级解析，纯标准库）→ display_name_cn → [slug]（排序去重）。"""
    mapping: dict[str, set[str]] = {}
    for yml in sorted(panels_dir.glob("*.yaml")):
        cur: str | None = None
        try:
            text = yml.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            m_slug = re.match(r"^\s*-\s*slug:\s*(\S+)", line)
            m_cn = re.match(r"^\s*display_name_cn:\s*(.+?)\s*$", line)
            if m_slug:
                cur = m_slug.group(1)
            elif m_cn and cur:
                name = m_cn.group(1).strip("\"'")
                if name:
                    mapping.setdefault(name, set()).add(cur)
    return {k: sorted(v) for k, v in sorted(mapping.items())}


def latest_archived(slug: str, judges_dir: pathlib.Path):
    """入库归档里找该评委最近一次门禁报告（T1 §四.5）→ (date, 结论行, 相对路径)。

    文件名 <slug>-<YYYY-MM-DD>.md，日期取文件名（git 锚定，不依赖运行时钟）；
    结论行取报告内 "结论:" 行原样。找不到返回 None。
    """
    best: tuple[str, pathlib.Path] | None = None
    if judges_dir.is_dir():
        for f in sorted(judges_dir.glob("%s-*.md" % re.escape(slug))):
            m = ARCHIVED_NAME.match(f.name)
            if not m or m.group("slug") != slug:
                continue
            if best is None or m.group("date") > best[0]:
                best = (m.group("date"), f)
    if best is None:
        return None
    date, f = best
    verdict_line = "结论行未解析"
    for line in f.read_text(encoding="utf-8").splitlines():
        if line.startswith("结论"):
            verdict_line = line.strip()
            break
    try:
        rel = str(f.relative_to(REPO_ROOT))
    except ValueError:
        rel = str(f)
    return date, verdict_line, rel


# ── 渲染 ─────────────────────────────────────────────────────────────────────
def _render_linkage(audit_md: str, panels_dir: pathlib.Path, judges_dir: pathlib.Path,
                    payloads: dict) -> list[str]:
    """§四.3 联动段：松紧度画像偏松/偏紧评委 × 最近一次门禁结论（只加线索）。"""
    portrait = parse_bias_portrait(audit_md)
    lines = ["### 复核线索联动（PRD-151/T1 §四.3 · 只加线索，不改评级）", ""]
    if not portrait:
        lines.append("（审计输出未解析到松紧度画像，联动略。）")
        return lines
    lines.append("> 引擎本次输入 1 份报告（K=1<3），不下系统性结论；以下只按画像"
                 "为偏松/偏紧评委附最近一次工程质量门禁结论，供人工复核排优先级——"
                 "偏松/偏紧若伴随 B/C 维度缺口（语料陈旧、quotes 缺锚定等），"
                 "复核优先级提高。")
    lines.append("")
    mapping = display_to_slugs(panels_dir)
    shown = 0
    for name, bias, tag in portrait:
        if tag == "居中":
            continue
        shown += 1
        slugs = mapping.get(name, [])
        if not slugs:
            lines.append("- %s（bias=%s，%s）：panel 档案未找到对应 slug，仅展示画像"
                         % (name, bias, tag))
            continue
        found = []
        for slug in slugs:
            if slug in payloads:  # 本次 PR 运行结果最新
                p = payloads[slug]
                found.append("slug `%s`：本次运行门禁 %s · PASS %d/13 · warn %d · "
                             "exempt %d（gate_version=%s）"
                             % (slug, verdict_of(p), p["pass_count"],
                                p["warn_count"], p["exempt_count"],
                                p["gate_version"]))
                continue
            arch = latest_archived(slug, judges_dir)
            if arch:
                date, verdict_line, rel = arch
                found.append("slug `%s`：最近一次 %s · %s（`%s`）"
                             % (slug, date, verdict_line, rel))
            else:
                found.append("slug `%s`：未见入库门禁报告（`%s` 无 %s-*.md）"
                             % (slug, judges_dir.as_posix(), slug))
        lines.append("- %s（bias=%s，%s）→ %s" % (name, bias, tag, "；".join(found)))
    if shown == 0:
        lines.append("（本轮画像无偏松/偏紧评委，联动略。）")
    lines.append("")
    lines.append("（联动只提供复核线索；元评审四项审计算法与 A–F 阈值未动。）")
    return lines


def render_section(slugs: list[str], payloads: dict, gate_errors: list[tuple[str, str]],
                   warnings: list[str], source_note: str,
                   audit_md: str | None, audit_note: str,
                   panels_dir: pathlib.Path, judges_dir: pathlib.Path) -> str:
    """渲染 job summary Markdown（措辞纪律：缺口/疑似/建议人工复核）。"""
    lines = [
        "## 🚦 评委工程质量门禁状态（PRD-151/T3）",
        "",
        "> 信息展示，不设合并门禁：本段只报告受影响评委的工程质量门禁结论"
        "（P1 过渡期 warn-only）；数据来自 quality_gate 契约 JSON 行"
        "（gate_version=%s，元评审只读不解释）。" % GATE_VERSION,
        "",
        "**受影响评委**（%s）：%s"
        % (source_note, "、".join("`%s`" % s for s in slugs) or "（无）"),
        "",
    ]
    if payloads:
        lines += ["| 评委 | 结论 | PASS | warn | exempt | fail 条目 | warn 条目 |",
                  "|---|---|---|---|---|---|---|"]
        for slug in sorted(payloads):
            p = payloads[slug]
            fails = "、".join(it["id"] for it in p["items"] if it["status"] == "fail") or "—"
            warns = "、".join(it["id"] for it in p["items"] if it["status"] == "warn") or "—"
            lines.append("| `%s` | %s | %d/13 | %d | %d | %s | %s |"
                         % (slug, verdict_of(p), p["pass_count"], p["warn_count"],
                            p["exempt_count"], fails, warns))
        lines += [
            "",
            "（结论按 T1 §二 计分口径机械推导：P0 任一 fail ⇒ FAIL，否则 PASS；"
            "P1 只计 warn。" 
            "逐条明细与建议动作见 job 日志里 quality_gate 完整报告——"
            "工程质量缺口 ≠ 打分错误，评委视角本该有分歧。）",
            "",
        ]
    else:
        lines += ["（未取得任何门禁契约结果，见下方降级说明。）", ""]
    if gate_errors:
        lines.append("**降级说明**（门禁运行失败，只报告，不影响合并）：")
        for slug, note in gate_errors:
            lines.append("- `%s`：quality_gate 退出码 2%s"
                         % (slug, "（%s）" % note if note else ""))
        lines.append("")
    if warnings:
        lines.append("**契约读取警告**（显式列出，不静默）：")
        for w in warnings:
            lines.append("- %s" % w)
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("门禁引擎：`scripts/perspective-tools/quality_gate.py`（PRD-151/T2，"
                 "13 条 checklist：P0 六条收拢既有 CI 硬门 + P1 七条过渡期 warn-only）；"
                 "本段为 PRD-151/T3 元评审挂钩，只读契约 JSON 行，不重跑、不改判定。")
    if audit_md is not None:
        lines += ["", ""]
        lines += _render_linkage(audit_md, panels_dir, judges_dir, payloads)
    elif audit_note:
        lines += ["", "（复核线索联动（§四.3）略：%s）" % audit_note]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="评委工程质量门禁 CI 摘要（PRD-151/T3，只报告，不设门禁）")
    ap.add_argument("--base", help="PR base sha（与 --head 一起做 diff 检测）")
    ap.add_argument("--head", help="PR head sha")
    ap.add_argument("--judges", help="显式指定评委 slug（逗号分隔，本地自测用）")
    ap.add_argument("--gate-results", default="quality-gate-results.jsonl",
                    help="契约 JSONL 路径（quality_gate --json-out 追加写入）")
    ap.add_argument("--audit-md", default=None,
                    help="元评审审计输出 Markdown（ci_meta_review.py 落盘），用于 §四.3 联动")
    ap.add_argument("--judges-dir", default=str(REPO_ROOT / "docs" / "quality" / "judges"),
                    help="入库归档目录（T1 §四.5，最近一次结论的兜底来源）")
    ap.add_argument("--panels-dir", default=str(REPO_ROOT / "metric-brand-auditor" / "panels"),
                    help="panel yaml 目录（display_name_cn → slug 映射）")
    args = ap.parse_args()

    if args.judges:
        slugs = [s.strip() for s in args.judges.split(",") if s.strip()]
        source_note = "--judges 显式指定"
    elif args.base and args.head:
        slugs = affected_slugs(args.base, args.head)
        if slugs is None:
            print(render_section([], {}, [],
                                 ["diff 检测失败（git 异常，详见 job 日志 stderr）"],
                                 "git diff %s..%s -- perspectives/ 命中" % (
                                     args.base[:12], args.head[:12]),
                                 None, "", pathlib.Path(args.panels_dir),
                                 pathlib.Path(args.judges_dir)), end="")
            return 0
        source_note = "git diff %s..%s -- perspectives/ 命中" % (
            args.base[:12], args.head[:12])
    else:
        print("ci_gate_status.py: 需要 --base/--head 或 --judges 之一", file=sys.stderr)
        return 2
    if not slugs:
        print(render_section([], {}, [], ["改动未命中任何 perspectives/<slug>-perspective/ 评委套件"],
                             source_note, None, "", pathlib.Path(args.panels_dir),
                             pathlib.Path(args.judges_dir)), end="")
        return 0

    jsonl = pathlib.Path(args.gate_results)
    try:
        jsonl.unlink()  # 每次运行从空白累积（--json-out 为追加语义）
    except FileNotFoundError:
        pass
    except OSError as e:
        print(render_section(slugs, {}, [], ["契约文件 %s 无法重置：%s" % (jsonl, e)],
                             source_note, None, "", pathlib.Path(args.panels_dir),
                             pathlib.Path(args.judges_dir)), end="")
        return 0

    gate_errors: list[tuple[str, str]] = []
    for slug in slugs:
        rc, note = run_gate(slug, jsonl)
        if rc not in (0, 1):  # 0=PASS 1=FAIL 都是正常产报告；其余降级说明
            gate_errors.append((slug, note))

    payloads, warnings = load_contract_lines(jsonl)

    audit_md: str | None = None
    audit_note = ""
    if args.audit_md:
        p = pathlib.Path(args.audit_md)
        if p.is_file():
            audit_md = p.read_text(encoding="utf-8")
        else:
            audit_note = "%s 不存在（本 PR 未改动 panel yaml 时元评审审计不运行）" % args.audit_md

    print(render_section(slugs, payloads, gate_errors, warnings, source_note,
                         audit_md, audit_note, pathlib.Path(args.panels_dir),
                         pathlib.Path(args.judges_dir)), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
