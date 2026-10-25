#!/usr/bin/env python3
"""findings.json 三态校验器（PRD-177/T2，trend #886）。

校验每品牌每轮评审的机读结论文件 `published/reports/<brand>/versions/vN*/findings.json`
（schema = findings_version `prd-177-v1`，设计见 PRD-177/T1，trend #885）。三态词表
confirmed / needs_validation / rejected 沿 trend 家族已实现词表（PRD-169 / PRD-187）。

只用标准库，无网络 I/O，确定性：同一份输入跑 10 次输出逐字节一致
（PRD-063/T5 e2e 同款验收法）。不调 LLM、不改任何评分业务逻辑——本工具只做
机读投影文件的合法性校验，是「评委结论 → 机读」链路的第一道机器门（T2）。

──────────────────────────────────────────────────────────────────────────────
schema 摘要（字段级定义以 PRD-177/T1 §二为准，此处是校验器执行的机器口径）

顶层字段（全部必填）：
  findings_version  固定 "prd-177-v1"；未知版本按「版本不识别」拒读（§3.3 纪律）
  brand_slug        与目录名一致的字符串
  panel             panel yaml 的 name（用于 R-4 judge_slug 归属核对）
  report_ref        仓库相对路径，指向同轮 report.md
  counts            三态计数 {"confirmed","needs_validation","rejected"}，与 findings[] 对账
  findings          数组，可为空（空时 counts 三态必须全 0）

finding 对象：
  id                `^F-(<judge-slug>|lead)-\\d{3}$`，文件内唯一，且评委段 == judge_slug
  status            confirmed / needs_validation / rejected（禁第四态）
  judge_slug        panel judges 之一；Lead 聚合层结论用保留字 "lead"
  lens              origin/category/leverage/identity/signal；c1–c5 预留（PRD-178/T3 起）；
                    null = 跨口径结论
  claim             ≤80 字的一句话结论
  evidence          ≥1 条，每条 {source_ref, quote, kind}
    source_ref      仓库相对路径（可带 #L 行锚），必须真实存在、不得逃出仓库根
    quote           逐字引用，必须在 source_ref 指向文件中逐字存在（反捏造防火墙）
    kind            synthesis / report / review / research
  unresolved_fact   status=needs_validation 时必填非空
  rejected_reason   status=rejected 时必填非空；confirmed 时两字段必须缺省
  severity          不设（品牌审计结论无 likelihood×impact 口径，T1 §2.2）

三态操作语义（T1 §2.3）：confirmed 需完整依据链（evidence ≥2 条且覆盖 ≥2 种 kind，
或含 ≥1 条 synthesis 逐字引用）；needs_validation 需明确未决事实；rejected 留痕不删。
本校验器只拦「形态非法」，不判「该不该 confirmed」——那是评委/复核的判断。

──────────────────────────────────────────────────────────────────────────────
校验规则固定清单（T1 §3.2，R-1…R-7，一字不差落地）：

  R-1  JSON 可解析；顶层字段齐；counts 与 findings[] 实际三态计数逐项一致
  R-2  每 finding：id 格式且文件内唯一；status / lens / evidence[].kind 枚举合法
  R-3  条件必填：needs_validation ⇒ unresolved_fact 非空；rejected ⇒ rejected_reason
       非空；confirmed ⇒ unresolved_fact / rejected_reason 必须缺省
  R-4  judge_slug ∈ panel judges ∪ {lead}；source_ref 路径在仓库内真实存在
  R-5  evidence[].quote 在 source_ref 文件中逐字存在（三态无一例外）
  R-6  claim ≤80 字；evidence ≥1 条
  R-7  占位符纪律：文档全部字符串值无真实内部主机名 / IP / 账号 / 密钥
       （复用 PRD-151 C-3 正则清单与白名单；JSON 值级扫描，避免 JSON 语法字符误伤）

适配层（reviews/<slug>.md → findings 投影，默认 needs_validation）见
scripts/adapt_findings.py；本文件不负责投影。

用法（在仓库根）：
  python3 scripts/validate_findings.py published/reports/<brand>/versions/v1/findings.json
  python3 scripts/validate_findings.py <path> --root <repo-root>   # 测试 fixture 用

退出码：0 = 合法；1 = 校验失败（R-1…R-7 任一违规）；2 = 用法或 IO 错误。
报告纪律（120 秒可读）：结论行 → 违规清单（字段级路径）→ 附录机器可读 JSON 行；
不含时间戳 / 耗时 / 绝对路径，同输入逐字节可复现。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = "prd-177-v1"
STATUSES = ("confirmed", "needs_validation", "rejected")
LENSES = ("origin", "category", "leverage", "identity", "signal",
          "c1", "c2", "c3", "c4", "c5")  # c1–c5 为 PRD-178 消费者题组预留
EVIDENCE_KINDS = ("synthesis", "report", "review", "research")
LEAD = "lead"
CLAIM_MAX_CHARS = 80

ID_RE = re.compile(r"^F-([a-z0-9][a-z0-9-]*)-\d{3}$")

# R-7 复用 PRD-151 C-3 正则清单（T1 §3.2「复用 PRD-151 C-3 正则清单」）：
# 单一真源 import，不在本文件复制正则，清单演进时两边同步。
_TOOLS_DIR = Path(__file__).resolve().parent / "perspective-tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
from quality_gate import KIND_LABEL, scan_c3_text  # noqa: E402

TOP_FIELDS = ("findings_version", "brand_slug", "panel", "report_ref", "counts", "findings")


def load_panel_judges(root: Path, panel: str) -> tuple[list[str] | None, str | None]:
    """读 <root>/metric-brand-auditor/panels/<panel>.yaml 的 judges slug 列表。

    返回 (slugs, error)。panel 文件不存在或解析不出 judges 时返回 (None, 原因)。
    复用 validate_panels.py 的极简 YAML 解析（与该工具同款「不依赖 PyYAML」纪律）。
    """
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", panel or ""):
        return None, "panel 名非法"
    path = root / "metric-brand-auditor" / "panels" / f"{panel}.yaml"
    if not path.is_file():
        return None, f"panel yaml 不存在: metric-brand-auditor/panels/{panel}.yaml"
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import validate_panels  # noqa: E402
        data = validate_panels.parse_panel(path)
    except Exception as e:  # noqa: BLE001 —— 解析失败按可读错误报告，不让工具崩
        return None, f"panel yaml 解析失败: {e}"
    slugs = [str(j.get("slug", "")) for j in (data.get("judges") or []) if j.get("slug")]
    if not slugs:
        return None, f"panel yaml 无 judges: {panel}"
    return slugs, None


def safe_rel_path(source_ref: str) -> tuple[str, str | None]:
    """拆 `path#L锚` 并检查路径形态。返回 (纯路径, 错误)。"""
    rel = source_ref.split("#", 1)[0].strip()
    if not rel:
        return "", "source_ref 为空"
    if rel.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", rel):
        return rel, "source_ref 是绝对路径（必须为仓库相对路径）"
    if ".." in Path(rel).parts:
        return rel, "source_ref 含 `..`（不得逃出仓库根）"
    if "\\" in rel:
        return rel, "source_ref 含反斜杠（必须用 `/` 分隔）"
    return rel, None


def validate(data_text: str, root: Path, rel_display: str) -> list[dict]:
    """跑 R-1…R-7，返回违规清单（每项 {rule, path, message}，顺序确定性）。"""
    v: list[dict] = []

    def add(rule: str, path: str, message: str) -> None:
        v.append({"rule": rule, "path": path, "message": message})

    # ── R-1：JSON 可解析 + 顶层字段 ───────────────────────────────────────────
    try:
        doc = json.loads(data_text)
    except ValueError as e:
        add("R-1", "$", f"JSON 不可解析: {e}")
        return v
    if not isinstance(doc, dict):
        add("R-1", "$", "顶层必须是 JSON object")
        return v

    missing = [k for k in TOP_FIELDS if k not in doc]
    if missing:
        add("R-1", "$", f"顶层字段缺失: {', '.join(missing)}")
    if doc.get("findings_version") != SCHEMA_VERSION:
        add("R-1", "$.findings_version",
            f"版本不识别（期望 {SCHEMA_VERSION}，消费方拒读不猜测语义）")
    for k in ("brand_slug", "panel", "report_ref"):
        val = doc.get(k)
        if k in doc and (not isinstance(val, str) or not val.strip()):
            add("R-1", f"$.{k}", "必须是非空字符串")

    findings = doc.get("findings")
    if not isinstance(findings, list):
        add("R-1", "$.findings", "必须是数组（可为空数组）")
        return v

    # ── 逐 finding：R-2 / R-3 / R-6 / R-4 / R-5 ─────────────────────────────
    tally = {s: 0 for s in STATUSES}
    seen_ids: dict[str, int] = {}
    panel_name = doc.get("panel") if isinstance(doc.get("panel"), str) else ""
    panel_judges: list[str] | None = None
    panel_err: str | None = None
    for i, f in enumerate(findings):
        base = f"findings[{i}]"
        if not isinstance(f, dict):
            add("R-2", base, "必须是 JSON object")
            continue

        # R-2 id：格式 + 唯一 + 评委段与 judge_slug 一致
        fid = f.get("id")
        if not isinstance(fid, str) or not ID_RE.fullmatch(fid):
            add("R-2", f"{base}.id", "格式必须是 F-<judge-slug>-NNN（NNN 三位数字）")
        else:
            if fid in seen_ids:
                add("R-2", f"{base}.id", f"文件内重复（首次出现于 findings[{seen_ids[fid]}]）")
            else:
                seen_ids[fid] = i

        # R-2 status 枚举
        status = f.get("status")
        if status not in STATUSES:
            add("R-2", f"{base}.status",
                f"枚举非法（合法值: {' / '.join(STATUSES)}；禁第四态）")
        elif isinstance(status, str):
            tally[status] += 1

        # R-2 lens 枚举（允许 null）
        lens = f.get("lens")
        if "lens" not in f:
            add("R-2", f"{base}.lens", "必填字段缺失（可为 null = 跨口径结论）")
        elif lens is not None and lens not in LENSES:
            add("R-2", f"{base}.lens",
                f"枚举非法（合法值: {' / '.join(LENSES[:5])}；c1–c5 预留；或 null）")

        # R-3 条件必填
        if status == "needs_validation":
            uf = f.get("unresolved_fact")
            if not isinstance(uf, str) or not uf.strip():
                add("R-3", f"{base}.unresolved_fact",
                    "status=needs_validation 时必填非空（卡在哪个未决事实）")
        if status == "rejected":
            rr = f.get("rejected_reason")
            if not isinstance(rr, str) or not rr.strip():
                add("R-3", f"{base}.rejected_reason",
                    "status=rejected 时必填非空（为何证伪 / 撤回；条目留痕不删）")
        if status == "confirmed":
            for k in ("unresolved_fact", "rejected_reason"):
                if k in f:
                    add("R-3", f"{base}.{k}",
                        "status=confirmed 时必须缺省（不带未决事实 / 撤回理由）")

        # R-6 claim ≤80 字
        claim = f.get("claim")
        if not isinstance(claim, str) or not claim.strip():
            add("R-6", f"{base}.claim", "必须是非空字符串（一句话结论）")
        elif isinstance(claim, str) and len(claim) > CLAIM_MAX_CHARS:
            add("R-6", f"{base}.claim", f"超过 {CLAIM_MAX_CHARS} 字（现 {len(claim)} 字）")

        # R-6 evidence ≥1 + 形态；R-2 kind 枚举；R-4/R-5 source_ref / quote
        evidence = f.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            add("R-6", f"{base}.evidence", "必须是非空数组（≥1 条；空依据即拦）")
        else:
            for j, ev in enumerate(evidence):
                ebase = f"{base}.evidence[{j}]"
                if not isinstance(ev, dict):
                    add("R-2", ebase, "必须是 JSON object {source_ref, quote, kind}")
                    continue
                kind = ev.get("kind")
                if kind not in EVIDENCE_KINDS:
                    add("R-2", f"{ebase}.kind",
                        f"枚举非法（合法值: {' / '.join(EVIDENCE_KINDS)}）")
                sref = ev.get("source_ref")
                if not isinstance(sref, str) or not sref.strip():
                    add("R-4", f"{ebase}.source_ref", "必须是非空字符串（仓库相对路径）")
                    continue
                rel, err = safe_rel_path(sref)
                if err:
                    add("R-4", f"{ebase}.source_ref", err)
                    continue
                target = root / rel
                if not target.is_file():
                    add("R-4", f"{ebase}.source_ref", f"路径在仓库内不存在: {rel}")
                    continue
                # R-5 逐字引用（三态无一例外，反捏造防火墙联动）
                quote = ev.get("quote")
                if not isinstance(quote, str) or not quote:
                    add("R-5", f"{ebase}.quote", "必须是非空字符串（逐字引用）")
                    continue
                try:
                    text = target.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError) as e:
                    add("R-5", f"{ebase}.source_ref", f"文件无法以 UTF-8 读取: {rel} ({e})")
                    continue
                if quote not in text:
                    add("R-5", f"{ebase}.quote",
                        f"逐字引用未命中 {rel}（quote 必须在 source_ref 文件中逐字存在）")

        # R-4 judge_slug ∈ panel judges ∪ {lead}
        js = f.get("judge_slug")
        if not isinstance(js, str) or not js.strip():
            add("R-4", f"{base}.judge_slug", "必须是非空字符串（panel judges 之一或 lead）")
        else:
            if panel_judges is None and panel_err is None:
                panel_judges, panel_err = load_panel_judges(root, panel_name)
            if panel_err:
                # panel 级错误对每个 finding 只报一次（$.panel 路径去重）
                if not any(x["rule"] == "R-4" and x["path"] == "$.panel" for x in v):
                    add("R-4", "$.panel", f"无法核对 judge_slug 归属: {panel_err}")
            elif js != LEAD and js not in panel_judges:
                add("R-4", f"{base}.judge_slug",
                    f"judge_slug {js!r} 不在 panel {panel_name!r} 的 judges 内"
                    f"（合法: {', '.join(sorted(panel_judges))} ∪ lead）")

        # id 评委段与 judge_slug 一致（id 格式 ^F-(<judge-slug>|lead)-NNN$ 的参数化语义）
        if isinstance(fid, str) and isinstance(js, str) and ID_RE.fullmatch(fid or ""):
            id_slug = ID_RE.fullmatch(fid).group(1)
            if id_slug != js:
                add("R-2", f"{base}.id", f"评委段 {id_slug!r} 与 judge_slug {js!r} 不一致")

    # ── R-1 counts 对账 ──────────────────────────────────────────────────────
    counts = doc.get("counts")
    if not isinstance(counts, dict) or set(counts.keys()) != set(STATUSES):
        add("R-1", "$.counts",
            f"必须且只含三态键: {', '.join(STATUSES)}")
    else:
        bad = [k for k, val in counts.items() if type(val) is not int]
        if bad:
            add("R-1", "$.counts", f"计数值必须是整数: {', '.join(bad)}")
        else:
            mismatch = [f"{k}: counts={counts[k]} vs 实际={tally[k]}"
                        for k in STATUSES if counts[k] != tally[k]]
            if mismatch:
                add("R-1", "$.counts", "与 findings[] 实际三态计数不一致（" + "；".join(mismatch) + "）")

    # ── R-7 占位符纪律（复用 PRD-151 C-3 正则清单，白名单先剔除）────────────
    # JSON 值级扫描：只扫文档全部字符串值（claim / quote / unresolved_fact 等），
    # 避免把 JSON 语法字符（行尾引号逗号等）误当凭据赋值右侧；正则清单与白名单
    # 与 quality_gate 同源。字段级路径报告（如 findings[0].claim）。
    for pointer, text in iter_strings(doc):
        multi = len(text.splitlines()) > 1
        for ln, kind, line in scan_c3_text(text):
            add("R-7", pointer + (f"#L{ln}" if multi else ""),
                f"命中 PRD-151 C-3 清单 [{KIND_LABEL.get(kind, kind)}]: {line}")

    return v


def iter_strings(obj, pointer: str = "$"):
    """深度优先遍历 JSON 文档全部字符串值（dict 插入序 / list 下标序，确定性）。"""
    if isinstance(obj, str):
        yield pointer, obj
    elif isinstance(obj, dict):
        for k, val in obj.items():
            yield from iter_strings(val, f"{pointer}.{k}")
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            yield from iter_strings(val, f"{pointer}[{i}]")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="findings.json 三态校验器（PRD-177/T2，schema prd-177-v1，R-1…R-7）")
    parser.add_argument("findings_json", help="findings.json 路径（仓库相对或绝对）")
    parser.add_argument("--root", type=Path, default=None,
                        help="仓库根（source_ref / panel yaml 的解析基准；默认本脚本所在仓库根）")
    args = parser.parse_args(argv)

    root = (args.root or Path(__file__).resolve().parents[1]).resolve()
    path = Path(args.findings_json)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        print(f"ERROR: 文件不存在: {path}", file=sys.stderr)
        return 2
    try:
        data_text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        print(f"ERROR: 无法读取文件: {e}", file=sys.stderr)
        return 2

    rel_display = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name
    violations = validate(data_text, root, rel_display)

    ok = not violations
    print(f"== validate_findings ({SCHEMA_VERSION}) ==")
    if ok:
        try:
            n = len(json.loads(data_text).get("findings", []))
        except ValueError:
            n = 0
        print(f"结论: PASS {rel_display}（findings {n} 条，R-1…R-7 全过）")
    else:
        print(f"结论: FAIL {rel_display}（{len(violations)} 项违规）")
        print("违规清单:")
        for x in violations:
            print(f"  [{x['rule']}] {x['path']}: {x['message']}")
    appendix = {
        "tool": "validate_findings",
        "schema": SCHEMA_VERSION,
        "file": rel_display,
        "ok": ok,
        "error_count": len(violations),
        "violations": violations,
    }
    print("附录: " + json.dumps(appendix, ensure_ascii=False,
                               separators=(",", ":"), sort_keys=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
