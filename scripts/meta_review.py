#!/usr/bin/env python3
"""mba 元评审审计（PRD-063/T2，trend #332）。

用纯计算复核评委 panel 打分的一致性——"评委的评委"，评审公信力的第二道锁。
输入 `published/reports/<brand>/report.md`，解析 `## Score Matrix` 为纯数字矩阵，
按 `docs/plans/2026-10-18-meta-review-spec.md`（§一）做 4 项审计，
输出 §二 的一页审计摘要 + 附录明细。

只用标准库（statistics/math 手写公式，见 T1 规范 §六），不调 LLM，无网络 I/O。
确定性：同一份输入跑 10 次，结果一字不差（无随机、无时间戳、无未排序字典遍历，
排序显式指定 key，浮点保留 2 位小数）。

设计原则：只出审计报告，不改分；措辞是"分歧点"/"疑似"，不是"错误"/"定罪"。

PRD-177/T3（trend #887）起支持可选只读消费 findings.json（`--findings <path>`，
schema `prd-177-v1`，PRD-177/T1/T2）：审计项 4（分歧定位）输出行附 finding id
回指线索 + 附录 F 线索段。消费纪律与 ci_gate_status（PRD-151/T3）同款：
只读不解释、版本字段纪律（只认 findings_version=prd-177-v1，未知版本拒读）、
findings 有问题时降级说明（退出码不受影响，审计本身照常产出）。三态合法性
判定权在 scripts/validate_findings.py，本脚本不重复校验 R-1…R-7；
四项审计算法与 A–F 阈值一字不动，findings 只作回指线索。

用法：
  python3 scripts/meta_review.py published/reports/<brand>/report.md [-o out.md] \
      [--findings published/reports/<brand>/versions/vN*/findings.json]
"""
import argparse
import json
import math
import pathlib
import re
import sys


# ---------- findings 只读消费（PRD-177/T3，trend #887） ----------

FINDINGS_VERSION = "prd-177-v1"
FINDING_STATUSES = ("confirmed", "needs_validation", "rejected")
EXPERT_LENSES = ("origin", "category", "leverage", "identity", "signal")
CLIP_CHARS = 40  # 附录 F 线索句截断长度（一页可读）


def load_findings(path):
    """只读加载 findings.json。返回 (doc_or_None, notes)。

    版本不识别 / JSON 不可解析 / 顶层形态非法 → (None, notes)（降级，不抛错）。
    """
    notes = []
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return None, ["findings 文件无法读取（%s）" % e]
    try:
        doc = json.loads(text)
    except ValueError as e:
        return None, ["findings JSON 不可解析（%s）" % e]
    if not isinstance(doc, dict):
        return None, ["findings 顶层不是 JSON object，拒读"]
    if doc.get("findings_version") != FINDINGS_VERSION:
        return None, ["findings_version=%r 版本不识别（本消费方只认 %s），"
                      "拒读不猜测语义" % (doc.get("findings_version"),
                                          FINDINGS_VERSION)]
    if not isinstance(doc.get("findings"), list):
        return None, ["findings 字段不是数组，拒读"]
    return doc, notes


def build_findings_view(path, doc, notes):
    """把 findings doc 整流为渲染线索视图（只取线索字段，排序显式，确定性）。"""
    by_lens = {}   # 专家镜头短名 -> [finding id]（排序后）
    nv, rj = [], []  # (id, judge_slug, 说明)
    tally = {s: 0 for s in FINDING_STATUSES}
    skipped = 0
    if doc is not None:
        for f in doc.get("findings", []):
            if not isinstance(f, dict):
                skipped += 1
                continue
            fid, status = f.get("id"), f.get("status")
            if not isinstance(fid, str) or status not in FINDING_STATUSES:
                skipped += 1
                continue
            tally[status] += 1
            if status == "needs_validation":
                nv.append((fid, str(f.get("judge_slug", "?")),
                           str(f.get("unresolved_fact", ""))))
            elif status == "rejected":
                rj.append((fid, str(f.get("judge_slug", "?")),
                           str(f.get("rejected_reason", ""))))
            lens = f.get("lens")
            if lens in EXPERT_LENSES:
                by_lens.setdefault(lens, []).append(fid)
        for ids in by_lens.values():
            ids.sort()
        nv.sort()
        rj.sort()
    return {"path": str(path), "doc": doc, "notes": list(notes),
            "by_lens": by_lens, "nv": nv, "rj": rj, "tally": tally,
            "skipped": skipped}


def _clip(text, n=CLIP_CHARS):
    text = " ".join(text.split())
    return text if len(text) <= n else text[:n] + "…"


# ---------- 解析 ----------

def strip_md_bold(s):
    return s.replace("**", "").strip()


def parse_cell_number(cell):
    """单元格只取数字部分：`**8→9** ↑1` -> 9（取当前版本分数，忽略版本标记）。
    非数字单元格（如 `—`）返回 None。"""
    t = strip_md_bold(cell)
    token = t.split()[0] if t.split() else ""
    nums = re.findall(r"\d+", token)
    return int(nums[-1]) if nums else None


def short_lens(label):
    """`Origin / 起源叙事` -> `Origin`（展示用短名，确定性）。"""
    return label.split("/")[0].strip()


def section_text(md, title):
    m = re.search(r"^## " + re.escape(title) + r"\b.*$", md, re.M)
    if not m:
        return ""
    rest = md[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    return rest[:nxt.start()] if nxt else rest


def parse_score_matrix(md):
    """解析 ## Score Matrix 为纯数字矩阵。panel 人数/维度数从表推导，不硬编码。"""
    notes = []
    sec = section_text(md, "Score Matrix")
    lines = [ln for ln in sec.splitlines() if ln.strip().startswith("|")]
    if len(lines) < 3:
        return None
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines]
    header = [strip_md_bold(c) for c in rows[0]]
    mean_idx = next((i for i, h in enumerate(header) if "mean" in h.lower()), len(header))
    judges = header[1:mean_idx]
    lenses, scores, judge_totals = [], {}, None
    for cells in rows[1:]:
        if all(re.fullmatch(r":?-+:?", strip_md_bold(c)) for c in cells):
            continue  # 分隔行
        label = strip_md_bold(cells[0])
        if label.lower() == "judge total":
            vals = []
            for j, cell in enumerate(cells[1:mean_idx]):
                v = parse_cell_number(cell)
                if v is None:
                    notes.append("Judge Total 行评委 %s 单元格无数字，已跳过" % judges[j])
                else:
                    vals.append(v)
            judge_totals = vals
            continue
        vals = {}
        for j, cell in enumerate(cells[1:mean_idx]):
            v = parse_cell_number(cell)
            if v is None:
                notes.append("维度 %s / 评委 %s 单元格无数字，已跳过" % (label, judges[j]))
            else:
                vals[judges[j]] = v
        if vals:
            lenses.append(label)
            scores[label] = vals
    total = re.search(r"Score Total:\s*(\d+)\s*/\s*(\d+)", sec)
    norm = re.search(r"Score Normalized:\s*([\d.]+)\s*/\s*([\d.]+)", sec)
    meta = {
        "score_total": "%s/%s" % (total.group(1), total.group(2)) if total else None,
        "score_normalized": "%s/%s" % (norm.group(1), norm.group(2)) if norm else None,
    }
    return {"lenses": lenses, "judges": judges, "scores": scores,
            "judge_totals": judge_totals, "notes": notes, "meta": meta}


def parse_heatmap(md):
    """解析 ## Dissent Heatmap 代码块：lens -> (σ, 分歧文字)。无该章节返回 None。"""
    sec = section_text(md, "Dissent Heatmap")
    if not sec:
        return None
    m = re.search(r"```(.*?)```", sec, re.S)
    if not m:
        return None
    out = {}
    for ln in m.group(1).splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("Lens"):
            continue
        toks = ln.split()
        if len(toks) < 3:
            continue
        sig = next((t for t in toks[1:] if re.fullmatch(r"\d+\.\d+", t)), None)
        if sig is None:
            continue
        out[toks[0].lower()] = (float(sig), ln.split(sig, 1)[1].strip())
    return out


# ---------- 统计（手写公式，见 T1 规范 §六） ----------

def mean(xs):
    return sum(xs) / len(xs)


def pstdev(xs):
    mu = mean(xs)
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / len(xs))


def pearson(a, b):
    mua, mub = mean(a), mean(b)
    num = sum((x - mua) * (y - mub) for x, y in zip(a, b))
    da = sum((x - mua) ** 2 for x in a)
    db = sum((y - mub) ** 2 for y in b)
    if da == 0 or db == 0:
        return None
    return num / math.sqrt(da * db)


def f2(x):
    return "%.2f" % x


# ---------- 4 审计项 ----------

def audit(data):
    lenses, judges, scores = data["lenses"], data["judges"], data["scores"]
    # 审计项 1：评委间一致性
    sigma = {}
    for l in lenses:
        sigma[l] = pstdev([scores[l][j] for j in judges])
    corr, corr_notes = {}, []
    for a in judges:
        for b in judges:
            r = pearson([scores[l][a] for l in lenses], [scores[l][b] for l in lenses])
            if r is None:
                corr[(a, b)] = None
                if a != b:
                    corr_notes.append(
                        "相关系数(%s,%s)无定义：评委 %s 或 %s 所有维度打分完全相同（σ=0），记为—"
                        % (a, b, a, b))
            else:
                corr[(a, b)] = r
    top3 = sorted(lenses, key=lambda l: (-sigma[l], l))[:3]
    # 审计项 2：离群值
    outliers = []
    for l in lenses:
        vals = [scores[l][j] for j in judges]
        mu, s = mean(vals), sigma[l]
        if s == 0:
            continue
        for j in judges:
            x = scores[l][j]
            if abs(x - mu) > 2 * s:
                outliers.append({"judge": j, "lens": l, "score": x, "mean": mu,
                                 "z": (x - mu) / s})
    outliers.sort(key=lambda o: (-abs(o["z"]), o["lens"], o["judge"]))
    small_sample = len(judges) < 4
    # 审计项 3：系统性偏见（报告内画像；跨报告 K<3 不下结论）
    all_vals = [scores[l][j] for l in lenses for j in judges]
    mean_all = mean(all_vals)
    bias = {}
    for j in judges:
        bias[j] = mean([scores[l][j] for l in lenses]) - mean_all
    jt_check = None
    jt = data["judge_totals"]
    if jt and len(jt) == len(judges):
        jt_mean = mean(jt)
        jt_check = {}
        for j, v in zip(judges, jt):
            d = v - jt_mean
            jt_check[j] = "松" if d > 0 else ("紧" if d < 0 else "中")
    # 审计项 4：分歧定位
    dissent = []
    for l in top3:
        vals = [(scores[l][j], j) for j in judges]
        lo = min(v for v, _ in vals)
        hi = max(v for v, _ in vals)
        lo_j = sorted(j for v, j in vals if v == lo)
        hi_j = sorted(j for v, j in vals if v == hi)
        dissent.append({"lens": l, "sigma": sigma[l], "lo": lo, "hi": hi,
                        "lo_judges": lo_j, "hi_judges": hi_j, "gap": hi - lo})
    return {"sigma": sigma, "corr": corr, "corr_notes": sorted(set(corr_notes)),
            "top3": top3, "outliers": outliers, "small_sample": small_sample,
            "bias": bias, "judge_total_check": jt_check,
            "mean_all": mean_all, "dissent": dissent}


def rating(max_sigma):
    if max_sigma > 1.8:
        return "F"
    if max_sigma > 1.2:
        return "D"
    if max_sigma > 0.8:
        return "C"
    if max_sigma > 0.5:
        return "B"
    return "A"


# ---------- 渲染（T1 规范 §二） ----------

def render(report_path, data, res, heatmap, findings_view=None):
    lenses, judges, scores = data["lenses"], data["judges"], data["scores"]
    meta = data["meta"]
    max_sigma = max(res["sigma"].values())
    grade = rating(max_sigma)
    src = str(report_path)
    meta_bits = []
    if meta["score_total"]:
        meta_bits.append("Score Total " + meta["score_total"])
    if meta["score_normalized"]:
        meta_bits.append("归一化 " + meta["score_normalized"])
    L = []
    L.append("# 元评审审计报告（PRD-063/T2）")
    L.append("")
    head = "> 输入：`%s`" % src
    if meta_bits:
        head += "（" + "、".join(meta_bits) + "）"
    head += "；审计方式：纯计算（`scripts/meta_review.py`），未重新打分；"
    head += "措辞为“分歧点”/“疑似”，非“错误”/“定罪”结论。"
    if findings_view is not None:
        head += "；findings 线索：`%s`（PRD-177/T3 只读回指）。" % findings_view["path"]
    L.append(head)
    L.append("")
    L.append("## 一页审计摘要")
    L.append("")
    L.append("1. **总体一致性评级：%s**（最大维度 σ=%s；评级只反映“分歧程度”，**不等于“打分质量”**）"
             % (grade, f2(max_sigma)))
    L.append("2. **Top3 分歧点**（σ 降序）：")
    for i, d in enumerate(res["dissent"], 1):
        lo_s = "、".join("%s（%d）" % (j, d["lo"]) for j in d["lo_judges"])
        hi_s = "、".join("%s（%d）" % (j, d["hi"]) for j in d["hi_judges"])
        line = ("   %d. %s：σ=%s，分数范围 %d–%d；%s ↔ %s，分差 %d"
                % (i, short_lens(d["lens"]), f2(d["sigma"]), d["lo"], d["hi"],
                   lo_s, hi_s, d["gap"]))
        if findings_view is not None:
            ids = findings_view["by_lens"].get(short_lens(d["lens"]).lower())
            if ids:
                line += "；findings 线索：%s" % "、".join(ids)
        L.append(line)
    L.append("3. **建议复核项**：")
    if res["outliers"]:
        L.append("   - 离群打分（|score−μ|>2σ）：")
        for o in res["outliers"]:
            L.append("     - %s / %s：%d（维度均值 %s，z=%s）"
                     % (o["judge"], short_lens(o["lens"]), o["score"],
                        f2(o["mean"]), f2(o["z"])))
    else:
        L.append("   - 离群打分：本轮无（|score−μ|>2σ 未触发）")
    L.append("   - 疑似系统性偏见：本次输入 1 份报告（K=1<3），"
             "只出松紧度画像（见附录 C），不下系统性结论。")
    L.append("   （以上仅为“建议人工复核”的线索，不是“打分错误”的结论。）")
    L.append("")
    L.append("## 附录")
    L.append("")
    L.append("### A. 一致性矩阵（Pearson 相关系数，2 位小数）")
    L.append("")
    L.append("|  | " + " | ".join(judges) + " |")
    L.append("|" + "---|" * (len(judges) + 1))
    for a in judges:
        cells = []
        for b in judges:
            r = res["corr"][(a, b)]
            cells.append(f2(r) if r is not None else "—")
        L.append("| %s | %s |" % (a, " | ".join(cells)))
    if res["corr_notes"]:
        L.append("")
        for n in res["corr_notes"]:
            L.append("- " + n)
    L.append("")
    L.append("### B. 全部离群记录")
    L.append("")
    if res["outliers"]:
        for o in res["outliers"]:
            L.append("- %s / %s：%d（维度均值 %s，偏离度 z=%s）"
                     % (o["judge"], short_lens(o["lens"]), o["score"],
                        f2(o["mean"]), f2(o["z"])))
    else:
        L.append("本轮无。")
    if res["small_sample"]:
        L.append("（评委数 <4，2σ 统计意义弱，样本少，仅供参考。）")
    L.append("")
    L.append("### C. 松紧度画像（bias = 评委均值 − 全体均值）")
    L.append("")
    for j in sorted(judges, key=lambda j: (-res["bias"][j], j)):
        b = res["bias"][j]
        tag = "偏松" if b > 0 else ("偏紧" if b < 0 else "居中")
        line = "- %s：bias=%s（%s）" % (j, f2(b), tag)
        if res["judge_total_check"]:
            line += "；Judge Total 交叉验证：%s" % res["judge_total_check"][j]
        L.append(line)
    L.append("")
    L.append("### D. 解析备注")
    L.append("")
    if data["notes"]:
        for n in data["notes"]:
            L.append("- " + n)
    else:
        L.append("无（全部单元格解析成功）。")
    L.append("")
    L.append("### E. 与报告 Dissent Heatmap 对照")
    L.append("")
    if heatmap is None:
        L.append("报告无 Dissent Heatmap 章节，对照略。")
    else:
        L.append("| 维度 | 我方 σ | 报告 σ | 结论 |")
        L.append("|---|---|---|---|")
        for l in sorted(lenses, key=lambda l: (-res["sigma"][l], l)):
            key = short_lens(l).lower()
            if key in heatmap:
                hs, htxt = heatmap[key]
                ok = abs(res["sigma"][l] - hs) <= 0.015
                L.append("| %s | %s | %s | %s |"
                         % (short_lens(l), f2(res["sigma"][l]), f2(hs),
                            "互证" if ok else "差异点"))
            else:
                L.append("| %s | %s | — | 报告热力图无此维度 |"
                         % (short_lens(l), f2(res["sigma"][l])))
        L.append("")
        L.append("报告分歧文字（Top3 维度）：")
        for d in res["dissent"]:
            key = short_lens(d["lens"]).lower()
            txt = heatmap[key][1] if key in heatmap else "（热力图无此维度）"
            L.append("- %s：%s" % (short_lens(d["lens"]), txt))
    if findings_view is not None:
        L.append("")
        L.append("### F. findings 线索（PRD-177/T3，只读）")
        L.append("")
        fv = findings_view
        if fv["doc"] is None:
            L.append("findings 文件：`%s`" % fv["path"])
            for n in fv["notes"]:
                L.append("- 降级：%s" % n)
            L.append("- 以上为 findings 消费降级说明；四项审计未受影响。")
        else:
            doc = fv["doc"]
            counts = doc.get("counts") if isinstance(doc.get("counts"), dict) else {}
            L.append("findings 文件：`%s`（findings_version=%s，panel=%s）"
                     % (fv["path"], doc.get("findings_version"), doc.get("panel")))
            L.append("三态计数（透明化全量）：confirmed %d · needs_validation %d · rejected %d，共 %d 条"
                     % (fv["tally"]["confirmed"], fv["tally"]["needs_validation"],
                        fv["tally"]["rejected"], sum(fv["tally"].values())))
            mismatch = [s for s in FINDING_STATUSES
                        if isinstance(counts.get(s), int) and counts[s] != fv["tally"][s]]
            if mismatch:
                L.append("- 计数对账差异（线索级，判定权在校验器）：%s"
                         % "；".join("%s counts=%s vs 实际=%s" % (s, counts[s], fv["tally"][s])
                                     for s in mismatch))
            if fv["skipped"]:
                L.append("- 形态非法跳过 %d 条（只取线索字段，合法性判定权在"
                         " `scripts/validate_findings.py`）" % fv["skipped"])
            bits = []
            for d in res["dissent"]:
                ids = fv["by_lens"].get(short_lens(d["lens"]).lower())
                if ids:
                    bits.append("%s → %s" % (short_lens(d["lens"]).lower(), "、".join(ids)))
            L.append("Top3 分歧镜头回指：%s" % ("；".join(bits) if bits else "无命中"))
            if fv["nv"]:
                L.append("needs_validation（建议复核）：" +
                         "；".join("%s（%s：%s）" % (fid, js, _clip(txt))
                                   for fid, js, txt in fv["nv"]))
            else:
                L.append("needs_validation（建议复核）：本轮无")
            if fv["rj"]:
                L.append("rejected（留痕）：" +
                         "；".join("%s（%s：%s）" % (fid, js, _clip(txt))
                                   for fid, js, txt in fv["rj"]))
            else:
                L.append("rejected（留痕）：本轮无")
            L.append("")
            L.append("（findings 只作回指线索；四项审计算法与 A–F 阈值未动；"
                     "三态合法性判定权在 `scripts/validate_findings.py`。）")
    L.append("")
    L.append("---")
    L.append("")
    L.append("> 生成方式：纯计算（`scripts/meta_review.py`），未重新打分、不调 LLM；")
    L.append("> 取不到数据的区块标注“本轮无”，不编造。措辞为“分歧点”/“疑似”。")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description="mba 元评审审计（纯计算）")
    ap.add_argument("report", help="完整报告路径，如 published/reports/deepseek/report.md")
    ap.add_argument("-o", "--output", help="输出文件（缺省打印到 stdout）")
    ap.add_argument("--findings", default=None,
                    help="findings.json 路径（PRD-177/T3 只读线索消费；缺省不读，"
                         "版本只认 prd-177-v1）")
    args = ap.parse_args()

    p = pathlib.Path(args.report)
    if not p.is_file():
        print("ERROR: 报告不存在: %s" % p, file=sys.stderr)
        return 2

    md = p.read_text(encoding="utf-8")
    data = parse_score_matrix(md)
    if not data or not data["lenses"]:
        print("ERROR: 未解析到 Score Matrix", file=sys.stderr)
        return 2
    res = audit(data)
    heatmap = parse_heatmap(md)
    findings_view = None
    if args.findings:
        doc, notes = load_findings(args.findings)
        findings_view = build_findings_view(args.findings, doc, notes)
    out = render(p, data, res, heatmap, findings_view)
    if args.output:
        pathlib.Path(args.output).write_text(out, encoding="utf-8")
        print("written: %s" % args.output)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
