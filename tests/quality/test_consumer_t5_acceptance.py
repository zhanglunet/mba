# tests/quality/test_consumer_t5_acceptance.py — PRD-178/T5 验收断言（trend #894）
"""PRD-178/T5 验收线硬测试：假岗位样例被标 needs_validation；双视角对照报告演示
可读且数据只抄自 findings；无人真 PII；无密钥。

对照对象（T1–T4 已合并交付，T5 只读不改动）：
  - T2 交付   3 套消费者评委 skill + consumer-mixed panel（trend #891）
  - T3 适配层 scripts/adapt_consumer_findings.py（C1–C5 → 三态 findings，trend #892）
  - T4 模板   docs/quality/expert-consumer-comparison-template.md + 填写样例
              docs/quality/comparison-report-sample.md（trend #893）

T5 样例树：tests/fixtures/consumer-fake-position（自包含 mini 仓库树，全占位）——
  假岗位消费者 fake-title-buyer（开场白声称「持证采购顾问 / 替公司买过三次」，
  无任何可核对证据）走满 C1–C5 题组；专家侧 expert-judge（STEP 5 形态）提供
  双视角对照的另一侧。两侧 findings 均为适配层产出、逐字节可复现。

验收走查（与 docs/quality/t5-acceptance-consumer-2026-10-26.md 一一对应）：
  1. test_fake_position_walks_full_c1_c5        假岗位样例走满 C1–C5 题组
  2. test_fake_position_marked_needs_validation 适配层一律标 needs_validation
    （缺可验证证据：单条 kind=review 依据 + 降级 unresolved_fact；机器门不认岗位背书）
  3. test_both_findings_pass_validator          两侧 findings 过 R-1…R-7（退出码 0）
  4. test_adapter_reproducible_byte_identical   范例可复现（适配重生成逐字节一致）
  5. test_demo_report_rows_copy_from_findings   对照表逐行抄自两侧 findings（T4 纪律 1）
  6. test_demo_report_structure_and_disciplines 模板结构齐 + 诚实盒 + 不换算不平均
  7. test_no_real_pii_no_secrets                无人真 PII + 无密钥（C-3 同源扫描）

纯静态检查 + 子进程，不调 LLM；不改消费者评委 skill、适配层与专家评分业务逻辑。
运行：python -m pytest tests/quality/test_consumer_t5_acceptance.py -q
"""
import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
EXPERT_ADAPTER = REPO / "scripts" / "adapt_findings.py"
CONSUMER_ADAPTER = REPO / "scripts" / "adapt_consumer_findings.py"
VALIDATOR = REPO / "scripts" / "validate_findings.py"
TEMPLATE = REPO / "docs" / "quality" / "expert-consumer-comparison-template.md"
DEMO_REPORT = REPO / "docs" / "quality" / "comparison-report-t5-demo.md"
T5_RECORD = REPO / "docs" / "quality" / "t5-acceptance-consumer-2026-10-26.md"

sys.path.insert(0, str(REPO / "scripts" / "perspective-tools"))
import quality_gate  # noqa: E402

TREE = REPO / "tests" / "fixtures" / "consumer-fake-position"
V1 = TREE / "published" / "reports" / "example-dual-brand" / "versions" / "v1"
EXPERT_FINDINGS = V1 / "findings-expert.json"
CONSUMER_FINDINGS = V1 / "findings-consumer.json"
FAKE_REVIEW = V1 / "reviews" / "fake-title-buyer.md"

EXPERT_REL = "published/reports/example-dual-brand/versions/v1/findings-expert.json"
CONSUMER_REL = "published/reports/example-dual-brand/versions/v1/findings-consumer.json"


def run_py(script: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args], cwd=str(REPO), capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=600)


def validator_json(out: str) -> dict:
    lines = re.findall(r'^附录: (\{"tool":"validate_findings".*\})$', out, re.M)
    assert lines, "校验器输出没有附录 JSON 行"
    return json.loads(lines[-1])


# ── 1. 假岗位样例走满 C1–C5 题组 ─────────────────────────────────────────────

def test_fake_position_walks_full_c1_c5():
    """假岗位答卷 C1–C5 逐题投影：lens 集合恰为 {c1..c5}；C2 低分（4≤5）被投影。"""
    doc = json.loads(CONSUMER_FINDINGS.read_text(encoding="utf-8"))
    lenses = [f["lens"] for f in doc["findings"]]
    assert sorted(lenses) == ["c1", "c2", "c3", "c4", "c5"], \
        "假岗位样例未走满 C1–C5 题组：%s" % lenses
    c2 = next(f for f in doc["findings"] if f["lens"] == "c2")
    assert c2["claim"] == "没有可核对凭证"  # C2=4 低分 → 主因投影（T1 §六.1）
    by_id = {f["id"] for f in doc["findings"]}
    assert len(by_id) == 5  # 题号 Cn ↔ lens cn 咬合，一题一条


# ── 2. 适配层一律标 needs_validation（缺可验证证据）─────────────────────────

def test_fake_position_marked_needs_validation():
    """机器门不认岗位背书：头衔/经历声明换不来 confirmed，全部 needs_validation。"""
    for path in (CONSUMER_FINDINGS, EXPERT_FINDINGS):
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc["findings_version"] == "prd-177-v1"
        assert doc["counts"] == {"confirmed": 0, "needs_validation":
                                 len(doc["findings"]), "rejected": 0}
        assert doc["counts"]["confirmed"] == 0 and doc["counts"]["rejected"] == 0
        for f in doc["findings"]:
            assert f["status"] == "needs_validation", \
                "%s: %s 被=%s（适配层绝不默认 confirmed）" % (
                    path.name, f["id"], f["status"])
            # 缺可验证证据的形态：仅单条评委落笔逐字引用（无 synthesis/research 佐证）
            assert len(f["evidence"]) == 1
            assert f["evidence"][0]["kind"] == "review"
            assert f["unresolved_fact"].strip()
            assert "未满足 confirmed 进入条件" in f["unresolved_fact"]
    review = FAKE_REVIEW.read_text(encoding="utf-8")
    assert "持证采购顾问" in review  # 假岗位声明在答卷中（样例内不可验证声明）
    doc = json.loads(CONSUMER_FINDINGS.read_text(encoding="utf-8"))
    assert all(f["status"] != "confirmed" for f in doc["findings"]), \
        "假岗位声明被采信为 confirmed——违反「机器门不认岗位背书」"


# ── 3. 两侧 findings 机读过校验 ──────────────────────────────────────────────

def test_both_findings_pass_validator():
    """两侧 findings 各过 R-1…R-7：退出码 0、违规清单为空。"""
    for rel in (EXPERT_REL, CONSUMER_REL):
        r = run_py(VALIDATOR, rel, "--root", str(TREE))
        assert r.returncode == 0, "%s: %s%s" % (rel, r.stdout, r.stderr)
        assert "结论: PASS" in r.stdout
        payload = validator_json(r.stdout)
        assert payload["ok"] is True and payload["violations"] == []


# ── 4. 范例可复现（适配重生成逐字节一致）────────────────────────────────────

def test_adapter_reproducible_byte_identical():
    """两侧 findings 重生成 2 次输出一致，且与入库文件逐字节一致。"""
    jobs = [
        (EXPERT_ADAPTER, ["published/reports/example-dual-brand/versions/v1"
                          "/reviews/expert-judge.md"], "example-dual-expert",
         EXPERT_FINDINGS),
        (CONSUMER_ADAPTER, ["published/reports/example-dual-brand/versions/v1"
                            "/reviews/fake-title-buyer.md"], "example-dual-consumer",
         CONSUMER_FINDINGS),
    ]
    for script, reviews, panel, golden in jobs:
        outs = set()
        for _ in range(2):
            r = run_py(script, *reviews, "--root", str(TREE), "--panel", panel)
            assert r.returncode == 0, r.stdout + r.stderr
            outs.add(r.stdout)
        assert len(outs) == 1, "%s 重生成输出不一致（确定性被破坏）" % script.name
        assert outs.pop() == golden.read_text(encoding="utf-8"), \
            "%s 重生成与入库文件不一致（范例不可复现）" % golden.name


# ── 5. 双视角对照报告演示：对照表逐行抄自 findings（T4 模板纪律 1）───────────

ROW_RE = re.compile(r"^\| (专家|消费者) \| (\S+?)（[^）]*） \| (.+?) \| "
                    r"(confirmed|needs_validation|rejected) \| 「(.+?)」\s*\|\s*$")


def _demo_table_rows() -> list[tuple[str, str | None, str, str, str]]:
    rows = []
    for line in DEMO_REPORT.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        domain, lens, claim, status, quote = m.groups()
        rows.append((domain, None if lens == "null" else lens, claim, status, quote))
    assert rows, "对照报告演示未解析到对照表数据行"
    return rows


def test_demo_report_rows_copy_from_findings():
    """每行 (域, lens, claim, 状态, evidence 摘录) 都能在对应侧 findings 中逐字命中。"""
    docs = {"专家": json.loads(EXPERT_FINDINGS.read_text(encoding="utf-8")),
            "消费者": json.loads(CONSUMER_FINDINGS.read_text(encoding="utf-8"))}
    rows = _demo_table_rows()
    assert sum(1 for r in rows if r[0] == "专家") == 4
    assert sum(1 for r in rows if r[0] == "消费者") == 5
    for domain, lens, claim, status, quote in rows:
        hits = [f for f in docs[domain]["findings"]
                if f.get("lens") == lens and f["claim"] == claim
                and f["status"] == status
                and any(ev["quote"] == quote for ev in f["evidence"])]
        assert hits, "对照表行不是 findings 逐字抄录：%s/%s %s" % (domain, lens, claim)


def test_demo_report_structure_and_disciplines():
    """模板结构齐（报告头/对照表/差异解读/纪律复核）+ 诚实盒 + 不换算不平均。"""
    demo = DEMO_REPORT.read_text(encoding="utf-8")
    for needle in ("## 报告头", "## 诚实盒", "## 对照表", "## 差异解读", "## 纪律复核",
                   "不做合成", "跨域换算", "needs_validation", "模拟人设", "不可验证声明"):
        assert needle in demo, "对照报告演示缺要点：%r" % needle
    template = TEMPLATE.read_text(encoding="utf-8")
    for needle in ("## 报告头", "## 对照表", "## 差异解读", "不换算"):
        assert needle in template, "T4 模板缺结构（T5 演示对照基线）：%r" % needle
    # 纪律复核四项全勾（演示自检完成）
    boxes = re.findall(r"^- \[ \]", demo, re.M)
    assert boxes == [], "纪律复核存在未勾选项"


# ── 6. 无人真 PII + 无密钥 ───────────────────────────────────────────────────

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")


def test_no_real_pii_no_secrets():
    """C-3 扫描（无密钥）+ 邮箱/手机号形态扫描（无真人 PII）双 0 命中。"""
    targets = [p for p in sorted(TREE.rglob("*"))
               if p.is_file() and p.suffix in (".md", ".json", ".yaml")]
    targets += [DEMO_REPORT, T5_RECORD]
    assert T5_RECORD.is_file(), \
        "T5 验收记录应入库：docs/quality/t5-acceptance-consumer-2026-10-26.md"
    hits = []
    for f in targets:
        text = f.read_text(encoding="utf-8")
        for ln, kind, line in quality_gate.scan_c3_text(text):
            hits.append("%s:%d [C-3/%s] %s" % (
                f.relative_to(REPO).as_posix(), ln, kind, line))
        for ln, line in enumerate(text.splitlines(), 1):
            if EMAIL_RE.search(line) or PHONE_RE.search(line):
                hits.append("%s:%d [pii] %s" % (
                    f.relative_to(REPO).as_posix(), ln, line.strip()[:80]))
    assert hits == [], "样例/文档出现疑似真实 PII 或凭据形态：\n" + "\n".join(hits)
    # 诚实标签在位：答卷自述模拟人设，演示报告置顶诚实盒
    assert "模拟人设" in FAKE_REVIEW.read_text(encoding="utf-8")
    assert "合成角色" in FAKE_REVIEW.read_text(encoding="utf-8")
