#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quality_gate.py — 评委工程质量门抽检脚本（PRD-151/T2，trend #756）

把散在 6 个既有脚本里的评委质量信号收拢成「单评委一页视图」（13 条 checklist：
P0 六条机检 + P1 七条）。设计依据：docs/plans/2026-10-23-judge-quality-gate.md（T1 草案）。

只调用 A 组既有命令、不改它们的业务逻辑；纯标准库（PyYAML/pytest 等依赖只由被调
用的既有脚本自身需要）。

  P0（A 组，任一 fail ⇒ 结论 FAIL；今天 CI 已全量硬门，本脚本只收拢防退步）：
    A-1 check_structure.py --perspective <slug>
    A-2 quality_check.py <SKILL.md>
    A-3 firewall_check.py <单套路径>
    A-4 check_self_conflict.py + --smoke（repo 全局，结果记到被检评委名下）
    A-5 validate_panels.py + pytest tests/panels tests/_contract（repo 全局，同上）
    A-6 build_agents_api.py --check + generate-personas.py 漂移（快照/比对/回写，无 git 操作）

  P1（B/C 组，过渡期 warn-only；T2 只机检 C-3，其余输出「人工/待查」标记）：
    C-3 占位符纪律：正则清单初版（T1 §三.4）扫 SKILL.md + references/research/*.md，
       白名单占位形态（<API_KEY> / akm-xxx / sk-ant-... / example.com 等）不报。

三种运行模式：
  --judge <slug或路径>   单评委跑 13 条并产出报告（PRD-151 T2 验收线）。路径参数指向
                         含 SKILL.md 的目录（金负样本 fixture 用），slug 参数查
                         perspectives/<slug>-perspective/。
  --sample <轮次>        确定性抽 5 套：slug 字典序排序后取 slugs[(5*轮次+i) mod N]，
                         i=0..4。不用时间、不用随机，同轮次可复现。
  --selftest             金样例回归（F8 负样本自测先例）+ 10 次 sha256 确定性验收
                         （PRD-063/T5 e2e 同款验收法）。

报告纪律（120 秒可读）：结论行 → 条目表 → 缺口表 → 豁免（显式列出，不静默）→
附录机器可读 JSON 行（T1 §四.2 接口契约，T3 元评审只读不解释）。报告不含时间戳 /
耗时 / 绝对路径，保证同仓库状态下逐字节可复现。

T2 只报告不阻断（--judge/--sample 以退出码给结论，不接 CI 门）；P1 转 hard gate
另立议题。产物不入库（T1 §四.5：报告走 stdout / PR summary）。

用法（在仓库根）：
  python3 scripts/perspective-tools/quality_gate.py --judge satyanadella
  python3 scripts/perspective-tools/quality_gate.py --judge tests/quality/fixtures/fake-judge
  python3 scripts/perspective-tools/quality_gate.py --sample 0
  python3 scripts/perspective-tools/quality_gate.py --selftest

退出码：0 = 报告产出且结论 PASS；1 = 结论 FAIL（任一 P0 fail）；2 = 用法/IO 错误。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
PERSPECTIVES_DIR = REPO_ROOT / "perspectives"
FIXTURE_JUDGE = "tests/quality/fixtures/fake-judge"  # 金负样本（相对仓库根）
EXEMPTIONS_FILE = REPO_ROOT / "docs/quality/exemptions.yaml"

GATE_VERSION = "prd-151-v1"
SAMPLE_SIZE = 5
SELFTEST_RUNS = 10  # T1 §三.3：金样例连跑 10 次，报告 sha256 逐字节一致
P0_IDS = ("A-1", "A-2", "A-3", "A-4", "A-5", "A-6")

# 13 条 checklist（T1 §二）：id / level / 标题
ITEMS: list[tuple[str, str, str]] = [
    ("A-1", "P0", "结构 spec"),
    ("A-2", "P0", "内容质量 6/6"),
    ("A-3", "P0", "反捏造防火墙"),
    ("A-4", "P0", "self-conflict"),
    ("A-5", "P0", "panel 引用完整"),
    ("A-6", "P0", "派生产物同步"),
    ("B-1", "P1", "research 六路齐全"),
    ("B-2", "P1", "quotes URL 锚定"),
    ("B-3", "P1", "可复制调用示例"),
    ("B-4", "P1", "Boundary 研究截止"),
    ("C-1", "P1", "description 触发短语"),
    ("C-2", "P1", "tier 追踪表如实"),
    ("C-3", "P1", "占位符纪律（机检）"),
]

P1_IDS = {iid for iid, level, _ in ITEMS if level == "P1"}

# T2 起机检的 P1 条目；其余 P1 输出「人工/待查」（T1 §二 B/C 表 + T2 范围）。
MACHINE_P1 = {"C-3"}

# 人工/待查条目的现状描述与建议动作（进缺口表）
MANUAL_ITEMS: dict[str, tuple[str, str]] = {
    "B-1": ("六路文件 01-06.md 是否齐全且每份非空，未机检",
            "人工核对 perspectives/<slug>-perspective/references/research/ 目录"),
    "B-2": ("quotes.md ≥90% 条目带 URL 锚定，未机测（先出人工基线再定阈值）",
            "人工抽核 quotes.md 中 `…](http…)` 形态条目占比"),
    "B-3": ("≥1 个可原样粘贴的调用示例（“用 <slug> 视角看…”），未机检",
            "人工在 SKILL.md / references 中查找调用句式"),
    "B-4": ("Honest Boundary 区含研究截止日期（cutoff），未机检",
            "人工核对该 section 是否写明 cutoff / 截止 / 截稿"),
    "C-1": ("frontmatter description 非空且含显式触发短语，未机检",
            "人工核对 SKILL.md frontmatter 的 Explicit triggers"),
    "C-2": ("docs/10 tier 追踪表 slug 集合与标注如实，未机检",
            "人工对照 docs/10-deepening-perspectives.md 与 perspectives/ 实际"),
}

# ── C-3 占位符纪律：正则清单初版（T1 §三.4）────────────────────────────────────
# 先剔除白名单占位形态，再跑命中正则；命中即 warn（P1 过渡期）。
C3_WHITELIST = [
    r"<API[_-]?KEY>", r"<TOKEN>", r"<SECRET>", r"<PASSWORD>",
    r"\$\{[^}\n]*\}",            # ${ENV_VAR} 引用形态
    r"akm-xxx", r"akm-x{3,}",
    r"sk-ant-\.\.\.", r"sk-ant-x{3,}",
    r"example\.com", r"example\.internal",
    r"\b127\.0\.0\.1\b", r"\blocalhost\b",  # 本机回环示例
]
C3_CRED = re.compile(
    r"(api[_-]?key|token|secret|password)\s*[:=]\s*[\"']?(?P<v>\S+)", re.IGNORECASE)
C3_PRIVATE_IP = re.compile(
    r"\b(?:10|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b")
C3_KEY_PREFIX = re.compile(r"\b(?:akm|sk-ant)-[A-Za-z0-9]{8,}")
C3_PRIVATE_KEY_BLOCK = re.compile(r"-----BEGIN[^\n]*PRIVATE KEY")
# 赋值右侧是显式占位值（<…> / ${…} / xxx / *** / your… / replace_me）→ 不报
C3_PLACEHOLDER_VALUE = re.compile(
    r"^(?:<[^>]+>|\$\{[^}]+\}|x+|\*+|\.+|your[-_a-z0-9]*|replace[_-]?me)$", re.IGNORECASE)

KIND_LABEL = {"cred": "凭据赋值", "ip": "内网网段", "keyprefix": "密钥前缀", "privkey": "私钥块"}


def scan_c3_text(text: str) -> list[tuple[int, str, str]]:
    """返回 [(行号, 命中类别, 行摘录)]。白名单形态先剔除再匹配。"""
    for w in C3_WHITELIST:
        text = re.sub(w, "", text)
    hits: list[tuple[int, str, str]] = []
    for ln, line in enumerate(text.splitlines(), 1):
        m = C3_CRED.search(line)
        if m and not C3_PLACEHOLDER_VALUE.match(m.group("v").strip("\"'")):
            hits.append((ln, "cred", line.strip()[:80]))
        if C3_PRIVATE_IP.search(line):
            hits.append((ln, "ip", line.strip()[:80]))
        if C3_KEY_PREFIX.search(line):
            hits.append((ln, "keyprefix", line.strip()[:80]))
        if C3_PRIVATE_KEY_BLOCK.search(line):
            hits.append((ln, "privkey", line.strip()[:80]))
    return hits


# ── 基础设施 ──────────────────────────────────────────────────────────────────
def run_cmd(args: list[str], timeout: int = 900) -> tuple[int, str]:
    """以仓库根为 cwd 跑命令（相对路径、无随机量），返回 (exit_code, 合并输出)。"""
    proc = subprocess.run(
        [sys.executable, *args], cwd=str(REPO_ROOT), capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=timeout)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def to_repo_rel(p: Path) -> str:
    """仓库根相对路径（报告里不出现绝对路径，保证可复现）。"""
    try:
        return str(p.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return p.as_posix()


def list_slugs() -> list[str]:
    return sorted(p.name[: -len("-perspective")]
                  for p in PERSPECTIVES_DIR.glob("*-perspective")
                  if (p / "SKILL.md").is_file())


def sample_slugs(round_no: int, slugs: list[str] | None = None) -> list[str]:
    """确定性抽样：字典序 + 轮次偏移取模。slugs[(5*round+i) mod N]，i=0..4。"""
    slugs = slugs if slugs is not None else list_slugs()
    if not slugs:
        return []
    n = len(slugs)
    return [slugs[(SAMPLE_SIZE * round_no + i) % n] for i in range(SAMPLE_SIZE)]


def resolve_judge(arg: str) -> tuple[str, Path, bool] | None:
    """--judge 参数 → (slug, 评委目录, 是否 fixture)。找不到返回 None。

    先按 slug 查 perspectives/<slug>-perspective/；再把参数当目录路径（当前目录或
    仓库根下），用于金负样本 fixture 等不入 perspectives/ 的合成评委。
    """
    skill = PERSPECTIVES_DIR / f"{arg}-perspective" / "SKILL.md"
    if skill.is_file():
        return arg, skill.parent, False
    for base in (Path.cwd(), REPO_ROOT):
        d = Path(arg) if base == Path.cwd() else base / arg
        if arg.endswith("/SKILL.md"):
            d = d.parent
        if d.is_dir() and (d / "SKILL.md").is_file():
            slug = d.name
            if slug.endswith("-perspective"):
                slug = slug[: -len("-perspective")]
            return slug, d, True
    return None


def load_exemptions() -> dict[str, list[str]]:
    """读 docs/quality/exemptions.yaml（T1 §五；文件尚不存在 → 空）。

    只做极简行级解析（纯标准库约束）：- slug: X / item_id: Y 成对出现。
    expires 过期判断依赖时钟锚策略，留 T3 接入（T2 阶段文件不存在，恒为空）。
    """
    out: dict[str, list[str]] = {}
    if not EXEMPTIONS_FILE.is_file():
        return out
    cur: str | None = None
    for line in EXEMPTIONS_FILE.read_text(encoding="utf-8").splitlines():
        m_slug = re.match(r"^\s*-\s*slug:\s*(\S+)", line)
        m_item = re.match(r"^\s*item_id:\s*(\S+)", line)
        if m_slug:
            cur = m_slug.group(1)
        elif m_item and cur:
            out.setdefault(cur, []).append(m_item.group(1))
    return out


# ── P0 机检（A 组：直接调用仓库既有命令）──────────────────────────────────────
def check_a1(slug: str, skill_dir: Path, is_fixture: bool) -> tuple[str, str]:
    """A-1 结构 spec。真实评委走 check_structure.py --perspective（T1 验收口径）；
    fixture 不在 perspectives/ 下（CLI 不支持任意目录），退而调用同目录模块的
    check_one()——同一套判定逻辑，未改它一行。"""
    if is_fixture:
        sys.path.insert(0, str(SCRIPT_DIR))
        try:
            from check_structure import check_one  # noqa: PLC0415
        finally:
            sys.path.remove(str(SCRIPT_DIR))
        missing = check_one(skill_dir / "SKILL.md")
        return ("fail" if missing else "pass"), "check_structure check_one %d 处缺失" % len(missing)
    rc, out = run_cmd(["scripts/perspective-tools/check_structure.py",
                       "--perspective", slug])
    m = re.search(r"(\d+)/(\d+) perspectives pass", out)
    detail = ("check_structure %s (exit %d)" % (m.group(0), rc)) if m else \
             ("check_structure exit %d" % rc)
    return ("pass" if rc == 0 else "fail"), detail


def check_a2(skill_dir: Path) -> tuple[str, str]:
    rc, out = run_cmd(["scripts/perspective-tools/quality_check.py",
                       to_repo_rel(skill_dir / "SKILL.md")])
    m = re.search(r"结果[:：]\s*(\d+)/(\d+)", out)
    detail = ("quality_check %s/6 (exit %d)" % (m.group(1), rc)) if m else \
             ("quality_check exit %d" % rc)
    return ("pass" if rc == 0 else "fail"), detail


def check_a3(skill_dir: Path) -> tuple[str, str]:
    rc, out = run_cmd(["scripts/perspective-tools/firewall_check.py",
                       to_repo_rel(skill_dir / "SKILL.md")])
    m = re.search(r"firewall:\s*(\d+) ok · (\d+) FAIL · (\d+) skip\(seed\) · (\d+) quotes checked", out)
    detail = ("firewall %s quotes checked · %s FAIL (exit %d)"
              % (m.group(4), m.group(2), rc)) if m else ("firewall exit %d" % rc)
    return ("pass" if rc == 0 else "fail"), detail


def check_a4(slug: str, cache: dict | None = None) -> tuple[str, str]:
    """A-4 self-conflict（repo 全局 validate + smoke；结果记到被检评委名下）。"""
    if cache is not None and "a4" in cache:
        rc_v, rc_s, out_v = cache["a4"]
    else:
        rc_v, out_v = run_cmd(["scripts/check_self_conflict.py"])
        rc_s, _ = run_cmd(["scripts/check_self_conflict.py", "--smoke"])
        if cache is not None:
            cache["a4"] = (rc_v, rc_s, out_v)
    detail = "self-conflict validate exit %d · smoke exit %d（全局门）" % (rc_v, rc_s)
    if rc_v == 0 and rc_s == 0:
        return "pass", detail
    named = f"✗ {slug}" in out_v  # 该评委是否在 validate 未声明名单里
    return "fail", detail + ("；本评委在未声明 --panel-drop 名单" if named else
                             "；全局失败（未必是本评委，见运行日志）")


def _pytest_summary(out: str) -> str:
    """取 pytest 汇总行并去掉耗时（耗时随机器变，会破坏逐字节复现）。"""
    for line in reversed(out.strip().splitlines()):
        if re.search(r"\d+ (?:passed|failed|error)", line):
            return re.sub(r"\s+in\s+[\d.]+s\s*$", "", line.strip())
    return "pytest 汇总未解析"


def check_a5(slug: str, cache: dict | None = None) -> tuple[str, str]:
    """A-5 panel 引用完整（validate_panels + tests/panels tests/_contract，全局门）。"""
    if cache is not None and "a5" in cache:
        rc_v, rc_p, summ = cache["a5"]
    else:
        rc_v, _ = run_cmd(["scripts/validate_panels.py"])
        rc_p, out_p = run_cmd(["-m", "pytest", "tests/panels", "tests/_contract", "-q"])
        summ = _pytest_summary(out_p)
        if cache is not None:
            cache["a5"] = (rc_v, rc_p, summ)
    detail = "validate_panels exit %d · pytest %s（全局门）" % (rc_v, summ)
    return ("pass" if rc_v == 0 and rc_p == 0 else "fail"), detail


PERSONAS_GENERATED = [
    REPO_ROOT / "packages/mcp-server/src/llm/personas.generated.ts",
    REPO_ROOT / "packages/mcp-server/src/llm/panels.generated.ts",
]


def check_a6(slug: str, cache: dict | None = None) -> tuple[str, str]:
    """A-6 派生产物同步（坑#2）：site/api --check + mcp personas 漂移。

    personas 子检镜像 mcp-ci.yml 的做法（生成后 git diff --quiet），但不做任何 git
    操作：先快照生成物字节 → 跑生成器 → 比对 → finally 回写快照，工作树零残留。
    """
    if cache is not None and "a6" in cache:
        return cache["a6"]
    rc_api, _ = run_cmd(["scripts/build_agents_api.py", "--check"])
    api_part = "site/api --check exit %d" % rc_api
    snapshot = {p: (p.read_bytes() if p.exists() else None) for p in PERSONAS_GENERATED}
    try:
        rc_gen, _ = run_cmd(["packages/mcp-server/scripts/generate-personas.py"])
        drift = any((p.read_bytes() if p.exists() else None) != snapshot[p]
                    for p in PERSONAS_GENERATED)
    finally:
        for p, raw in snapshot.items():  # 无论成败都恢复现场
            if raw is None:
                if p.exists():
                    p.unlink()
            elif not p.exists() or p.read_bytes() != raw:
                p.write_bytes(raw)
    if rc_gen != 0:
        status, gen_part = "fail", "mcp personas 生成失败 exit %d" % rc_gen
    elif drift:
        status, gen_part = "fail", "mcp personas 漂移（重生成后字节不一致）"
    else:
        status, gen_part = "pass", "mcp personas 无漂移"
    result = (("pass" if (rc_api == 0 and status == "pass") else "fail"),
              "%s · %s（全局门）" % (api_part, gen_part))
    if cache is not None:
        cache["a6"] = result
    return result


# ── C-3 机检 ──────────────────────────────────────────────────────────────────
def check_c3(skill_dir: Path) -> tuple[str, str]:
    files = [skill_dir / "SKILL.md"] + sorted(
        (skill_dir / "references" / "research").glob("*.md"))
    hits: list[str] = []
    scanned = 0
    for f in files:
        if not f.is_file():
            continue
        scanned += 1
        rel = to_repo_rel(f)
        for ln, kind, line in scan_c3_text(f.read_text(encoding="utf-8")):
            hits.append("%s:%d [%s] %s" % (rel, ln, KIND_LABEL.get(kind, kind), line))
    if hits:
        shown = "；".join(hits[:3]) + (" 等 %d 处" % len(hits) if len(hits) > 3 else "")
        return "warn", "正则清单初版命中 %d 处：%s" % (len(hits), shown)
    return "pass", "正则清单初版 0 命中（扫 %d 个文件：SKILL.md + references/research/*.md）" % scanned


# ── 报告 ──────────────────────────────────────────────────────────────────────
SUGGEST_P0 = {
    "A-1": "补齐 structure-spec 要求的 5 个必需 H2 区",
    "A-2": "按 quality_check 输出修对应子项（≥6 模型 / DNA ≥3 facet / 边界 ≥3 / 张力 ≥2 行等）",
    "A-3": "修正引用或补回语料：SKILL 引用必须逐字存在于本套 references/research",
    "A-4": "补 Self-Conflict Rule 的 --panel-drop <own-slug> 声明 / 修 self-conflict.yaml",
    "A-5": "按 validate_panels / tests 输出修 panel yaml 或评委档案",
    "A-6": "重跑 build_agents_api.py 与 generate-personas.py 并提交派生产物（坑#2）",
}


class JudgeNotFound(ValueError):
    pass


def judge_report(judge_arg: str, cache: dict | None = None) -> tuple[str, dict]:
    """对单个评委产出报告。返回 (报告文本, 摘要 dict)。共享 cache 仅在同进程批次内
    复用全局门结果（A-4/A-5/A-6 与具体评委无关）；--selftest 的 10 次复跑不传
    cache，保证逐次真实重跑。"""
    resolved = resolve_judge(judge_arg)
    if resolved is None:
        raise JudgeNotFound(judge_arg)
    slug, skill_dir, is_fixture = resolved
    exemptions = load_exemptions().get(slug, [])

    results: dict[str, tuple[str, str]] = {}
    results["A-1"] = check_a1(slug, skill_dir, is_fixture)
    results["A-2"] = check_a2(skill_dir)
    results["A-3"] = check_a3(skill_dir)
    results["A-4"] = check_a4(slug, cache)
    results["A-5"] = check_a5(slug, cache)
    results["A-6"] = check_a6(slug, cache)
    results["C-3"] = check_c3(skill_dir)
    for iid in MANUAL_ITEMS:
        results[iid] = ("warn", "人工/待查（T2 不机检）")

    # 豁免覆盖（仅 P1；T1 §五.2 P0 不设豁免；已机检 pass 的条目无需豁免）
    exempt_ids: list[str] = []
    for iid in exemptions:
        if iid in P1_IDS and results.get(iid, ("pass", ""))[0] != "pass":
            results[iid] = ("exempt", "豁免登记（docs/quality/exemptions.yaml）")
            exempt_ids.append(iid)

    verdict = "FAIL" if any(results[iid][0] == "fail" for iid in P0_IDS) else "PASS"
    pass_count = sum(1 for iid, _, _ in ITEMS if results[iid][0] == "pass")
    warn_count = sum(1 for iid, _, _ in ITEMS if results[iid][0] == "warn")
    exempt_count = sum(1 for iid, _, _ in ITEMS if results[iid][0] == "exempt")

    lines: list[str] = []
    lines.append("PRD-151 评委工程质量门报告 · gate_version=%s" % GATE_VERSION)
    origin = "fixture，不入 perspectives/" if is_fixture else "真实评委"
    lines.append("评委: %s（%s · %s）" % (slug, origin, to_repo_rel(skill_dir)))
    lines.append("结论: %s · PASS %d/13 · warn %d · exempt %d"
                 % (verdict, pass_count, warn_count, exempt_count))
    lines.append("─" * 64)
    lines.append("[P0 机检 · A 组（任一 fail ⇒ FAIL；CI 已全量硬门，此处收拢防退步）]")
    for iid, level, title in ITEMS:
        if level == "P0":
            status, detail = results[iid]
            lines.append("  %s %s  %-5s %s" % (iid, title, status.upper(), detail))
    lines.append("[P1 · B/C 组（过渡期 warn-only；除 C-3 外 T2 输出人工/待查标记）]")
    for iid, level, title in ITEMS:
        if level == "P1":
            status, detail = results[iid]
            lines.append("  %s %s  %-5s %s" % (iid, title, status.upper(), detail))
    lines.append("─" * 64)
    lines.append("缺口表（ID / 现状 → 建议动作）:")
    gap = 0
    for iid, level, title in ITEMS:
        status, detail = results[iid]
        if status in ("pass", "exempt"):
            continue
        gap += 1
        if iid in MANUAL_ITEMS:
            now, action = MANUAL_ITEMS[iid]
        elif iid in SUGGEST_P0:
            now, action = detail, SUGGEST_P0[iid]
        else:  # C-3 命中
            now, action = detail, "改为白名单占位写法（<API_KEY> / akm-xxx / example.com 等）或移除真实形态"
        lines.append("  %s [%s] %s → %s" % (iid, title, now, action))
    if gap == 0:
        lines.append("  （无 fail/warn 条目）")
    if exempt_ids:
        lines.append("豁免: %d 条（%s；登记见 docs/quality/exemptions.yaml）"
                     % (exempt_count, "、".join(sorted(exempt_ids))))
    else:
        lines.append("豁免: 0 条（docs/quality/exemptions.yaml 未配置豁免）")
    lines.append("─" * 64)
    payload = {
        "gate_version": GATE_VERSION,
        "judge_slug": slug,
        "items": [{"id": iid, "level": level, "status": results[iid][0]}
                  for iid, level, _ in ITEMS],
        "pass_count": pass_count,
        "warn_count": warn_count,
        "exempt_count": exempt_count,
    }
    lines.append("机器可读 JSON 行（T1 §四.2 契约，T3 元评审只读不解释）:")
    lines.append(json.dumps(payload, ensure_ascii=False))
    report = "\n".join(lines)
    return report, {"slug": slug, "verdict": verdict, "results": results,
                    "payload": payload, "report": report}


# ── CLI 子命令 ────────────────────────────────────────────────────────────────
def cmd_judge(judge_arg: str) -> int:
    try:
        report, summary = judge_report(judge_arg)
    except JudgeNotFound:
        print("quality_gate.py: 找不到评委 %r（--judge 接 slug 或含 SKILL.md 的目录）"
              % judge_arg, file=sys.stderr)
        return 2
    print(report)
    return 0 if summary["verdict"] == "PASS" else 1


def cmd_sample(round_no: int) -> int:
    slugs = list_slugs()
    if not slugs:
        print("quality_gate.py: perspectives/ 下没有 *-perspective/", file=sys.stderr)
        return 2
    picked = sample_slugs(round_no, slugs)
    print("PRD-151 确定性抽样 · 轮次 %d · gate_version=%s" % (round_no, GATE_VERSION))
    print("公式: 字典序 slugs[(5*%d+i) mod %d], i=0..4 → %s"
          % (round_no, len(slugs), "、".join(picked)))
    print("═" * 64)
    cache: dict = {}  # 同批 5 套共享全局门结果（A-4/A-5/A-6 与评委无关）
    worst = 0
    for slug in picked:
        report, summary = judge_report(slug, cache=cache)
        print(report)
        print("═" * 64)
        if summary["verdict"] != "PASS":
            worst = 1
    return worst


def _expect(label: str, ok: bool, detail: str) -> bool:
    print("  %s %s  %s" % ("✅" if ok else "❌", label, detail))
    return ok


def cmd_selftest() -> int:
    print("PRD-151/T2 quality_gate 自测（金样例回归 + 确定性验收，F8 先例）")
    print("=" * 64)
    all_ok = True

    # 1) 金正样例：satyanadella（T1 §六主选）——P0 六条全过 + C-3 机检过。
    #    注：B/C 其余 6 条 T2 输出「人工/待查」(warn)，故满贯形态是
    #    PASS 7/13 · warn 6；13/13 全绿留给 T4 示范过门时达成。
    _, pos = judge_report("satyanadella")
    pos_items = {i["id"]: i["status"] for i in pos["payload"]["items"]}
    all_ok &= _expect(
        "金正样例 satyanadella 结论 PASS",
        pos["verdict"] == "PASS",
        "结论 %s · PASS %d/13 · warn %d · exempt %d"
        % (pos["verdict"], pos["payload"]["pass_count"],
           pos["payload"]["warn_count"], pos["payload"]["exempt_count"]))
    all_ok &= _expect(
        "金正样例 P0 六条全 pass",
        all(pos_items[iid] == "pass" for iid in P0_IDS),
        "A-1..A-6 = %s" % [pos_items[iid] for iid in P0_IDS])
    all_ok &= _expect("金正样例 C-3 机检 0 命中", pos_items["C-3"] == "pass",
                      "C-3 = %s" % pos_items["C-3"])

    # 2) 金负样本：合成 fake-judge（tests/quality/fixtures/，不入 perspectives/）。
    #    期望 A-2 / A-3 / C-3 必拦（3 模型 + DNA 同 facet / 伪造 blockquote / 合成密钥形态）。
    _, neg = judge_report(FIXTURE_JUDGE)
    neg_items = {i["id"]: i["status"] for i in neg["payload"]["items"]}
    all_ok &= _expect("金负样本 fake-judge 结论 FAIL", neg["verdict"] == "FAIL",
                      "结论 %s" % neg["verdict"])
    all_ok &= _expect("金负样本 A-2 必拦", neg_items["A-2"] == "fail", "A-2 = %s" % neg_items["A-2"])
    all_ok &= _expect("金负样本 A-3 必拦", neg_items["A-3"] == "fail", "A-3 = %s" % neg_items["A-3"])
    all_ok &= _expect("金负样本 C-3 必拦", neg_items["C-3"] == "warn", "C-3 = %s" % neg_items["C-3"])

    # 3) 确定性：金正样例连跑 10 次，报告 sha256 逐字节一致（T1 §三.3 / PRD-063 T5 同款）。
    shas = []
    for _ in range(SELFTEST_RUNS):
        report, _ = judge_report("satyanadella")  # 不传 cache：逐次真实重跑全链
        shas.append(hashlib.sha256(report.encode("utf-8")).hexdigest())
    all_ok &= _expect(
        "确定性 %d 次复跑 sha256 一致" % SELFTEST_RUNS,
        len(set(shas)) == 1,
        "sha256=%s…（%d 种）" % (shas[0][:16], len(set(shas))))

    print("=" * 64)
    print("✅ 自测通过：门禁对金正样例零误报、对合成负样本有牙、报告逐字节可复现。"
          if all_ok else "❌ 自测失败：见上方 ❌ 条目。")
    return 0 if all_ok else 1


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="PRD-151/T2 评委工程质量门抽检（最小）")
    ap.add_argument("--judge", metavar="SLUG|PATH",
                    help="单个评委（slug 或含 SKILL.md 的目录路径）")
    ap.add_argument("--sample", metavar="ROUND", type=int,
                    help="确定性抽 5 套（字典序 + 轮次偏移取模）")
    ap.add_argument("--selftest", action="store_true",
                    help="金样例回归 + 10 次 sha256 一致性验收")
    args = ap.parse_args(argv)

    modes = [bool(args.judge), args.sample is not None, args.selftest]
    if sum(modes) != 1:
        print("quality_gate.py: --judge / --sample / --selftest 三选一", file=sys.stderr)
        return 2
    if args.judge:
        return cmd_judge(args.judge)
    if args.sample is not None:
        if args.sample < 0:
            print("quality_gate.py: --sample 轮次须 ≥0", file=sys.stderr)
            return 2
        return cmd_sample(args.sample)
    return cmd_selftest()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
