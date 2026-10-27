# tests/quality/test_findings_t5_acceptance.py — PRD-177/T5 验收断言（trend #889）
"""PRD-177/T5 验收线硬测试：完整评审样例机读通过校验；无密钥。

对照对象（T1–T4 已合并交付，T5 只读不改动）：
  - T2 校验器   scripts/validate_findings.py（R-1…R-7，trend #886）
  - T2 适配层   scripts/adapt_findings.py（评委稿 → 三态投影，trend #886）
  - T4 契约文档 docs/quality/findings-export-contract.md（trend #888）

验收走查（与 docs/quality/t5-acceptance-findings-2026-10-26.md 一一对应）：
  1. test_complete_review_samples_pass_validator
     完整评审样例（confirmed/needs_validation/rejected 三态俱全）机读通过
     R-1…R-7 校验：meta-review 树（1/2/1）+ findings 树 findings-full（1/1/1）
     + consumer 树 findings-full（三态样例），附录 JSON 行违规清单为空。
  2. test_judge_draft_adapt_reproducible
     真实评委稿（fixtures/findings example-judge.md，judge-prompt-template
     STEP 5 形态）适配 → 与入库金样例逐字节一致（范例可复现，10 次复跑）；
     适配层产出全 needs_validation、confirmed=0（绝不默认 confirmed）；
     适配产物随后过校验器（契约「退出码 0 才算产出完成」）。
  3. test_consumers_read_per_contract
     消费面按契约可读（findings-export-contract.md「消费面」表逐口走查）：
     元评审 meta_review --findings（附录 F + 计数对账 + 四项审计照常）、
     CI 透传 ci_meta_review --findings（exit 0 + 线索行）、工程质量门
     quality_gate findings_annex（available/ok/recognized 全真，13 条口径外只读）、
     人工 review 口（claim + evidence.quote 在源文件逐字可命中）。
  4. test_no_secrets_in_findings_surfaces
     无密钥：R-7 复用的 C-3 扫描器对三棵 fixture 树全部文本文件与
     docs/quality 两份 findings 文档（契约 + T5 验收记录）0 命中。

纯静态检查 + 子进程，不调 LLM；不改评分业务逻辑与四项审计算法。
运行：python -m pytest tests/quality/test_findings_t5_acceptance.py -q
"""
import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
ADAPTER = REPO / "scripts" / "adapt_findings.py"
VALIDATOR = REPO / "scripts" / "validate_findings.py"
META_REVIEW = REPO / "scripts" / "meta_review.py"
CI_META_REVIEW = REPO / "scripts" / "ci_meta_review.py"
CONTRACT_DOC = REPO / "docs" / "quality" / "findings-export-contract.md"
T5_RECORD = REPO / "docs" / "quality" / "t5-acceptance-findings-2026-10-26.md"

sys.path.insert(0, str(REPO / "scripts" / "perspective-tools"))
import quality_gate  # noqa: E402

# 三棵自包含样例树（占位内容；互不引用）
FINDINGS_TREE = REPO / "tests" / "fixtures" / "findings"
META_TREE = REPO / "tests" / "fixtures" / "meta-review"
CONSUMER_TREE = REPO / "tests" / "fixtures" / "consumer-findings"

# 完整评审样例：三态俱全（confirmed / needs_validation / rejected 至少各 1）。
# root 口径沿各树 README：meta/findings 两棵是自包含 mini 树（--root 指树根）；
# consumer 树按其 README「--root 是真实仓库根」（source_ref 指真实仓库相对路径）。
COMPLETE_SAMPLES = [
    (META_TREE, "published/reports/example-meta-brand/versions/v1/findings.json",
     {"confirmed": 1, "needs_validation": 2, "rejected": 1}),
    (FINDINGS_TREE, "published/reports/example-brand/versions/v1/findings-full.json",
     {"confirmed": 1, "needs_validation": 1, "rejected": 1}),
    (REPO,
     "tests/fixtures/consumer-findings/published/reports/example-consumer-brand"
     "/versions/v1/findings-full.json",
     {"confirmed": 1, "needs_validation": 1, "rejected": 1}),
]

# 真实评委稿适配链路（PRD-177/T2 金样例：评委稿 → findings.json）
JUDGE_DRAFT = "published/reports/example-brand/versions/v1/reviews/example-judge.md"
GOLDEN_FINDINGS = "published/reports/example-brand/versions/v1/findings.json"


def run_py(script: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args], cwd=str(REPO), capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=600)


def validator_json(out: str) -> dict:
    lines = re.findall(r'^附录: (\{"tool":"validate_findings".*\})$', out, re.M)
    assert lines, "校验器输出没有附录 JSON 行"
    return json.loads(lines[-1])


# ── 1. 完整评审样例机读通过校验（PRD-177 T5 验收标准第一条）─────────────────

def test_complete_review_samples_pass_validator():
    """三态俱全的完整评审样例逐个过 R-1…R-7，退出码 0、违规清单为空。"""
    for root, rel, counts in COMPLETE_SAMPLES:
        r = run_py(VALIDATOR, rel, "--root", str(root))
        assert r.returncode == 0, "%s: %s%s" % (root, r.stdout, r.stderr)
        assert "结论: PASS" in r.stdout
        payload = validator_json(r.stdout)
        assert payload["ok"] is True and payload["violations"] == []
        doc = json.loads((root / rel).read_text(encoding="utf-8"))
        assert doc["counts"] == counts, \
            "%s 三态计数漂移：%s != %s" % (rel, doc["counts"], counts)
        assert doc["findings_version"] == "prd-177-v1"
        statuses = {f["status"] for f in doc["findings"]}
        assert statuses == {"confirmed", "needs_validation", "rejected"}, \
            "%s 不再是三态俱全的完整评审样例：%s" % (rel, statuses)


# ── 2. 真实评委稿适配 → 校验过（范例可复现）────────────────────────────────

def test_judge_draft_adapt_reproducible():
    """评委稿 STEP 5 形态适配：与金样例逐字节一致（10 次复跑），且过校验器。"""
    outs = set()
    for _ in range(10):
        r = run_py(ADAPTER, JUDGE_DRAFT, "--root", str(FINDINGS_TREE),
                   "--panel", "example")
        assert r.returncode == 0, r.stdout + r.stderr
        outs.add(r.stdout)
    assert len(outs) == 1, "适配层 10 次复跑输出不一致（确定性被破坏）"
    golden = (FINDINGS_TREE / GOLDEN_FINDINGS).read_text(encoding="utf-8")
    assert outs.pop() == golden, "适配重生成与入库金样例不一致（范例不可复现）"

    doc = json.loads(golden)
    assert doc["counts"]["confirmed"] == 0 and doc["counts"]["rejected"] == 0
    assert all(f["status"] == "needs_validation" for f in doc["findings"])
    assert all(f["unresolved_fact"].strip() for f in doc["findings"])

    r = run_py(VALIDATOR, GOLDEN_FINDINGS, "--root", str(FINDINGS_TREE))
    assert r.returncode == 0, r.stdout + r.stderr  # 契约：退出码 0 才算产出完成


# ── 3. 消费面按契约可读（findings-export-contract.md「消费面」表逐口）────────

def test_contract_doc_tables_intact():
    """契约文档的消费面表与读侧纪律仍在（T5 走查的对照基线，防漂移）。"""
    doc = CONTRACT_DOC.read_text(encoding="utf-8")
    for needle in ("元评审（PRD-063）", "工程质量门（PRD-151）", "人工 review",
                   "只读", "默认怀疑", "计数对账", "lens 路由"):
        assert needle in doc, "契约文档缺要点：%r" % needle


def test_meta_review_consumer_reads_per_contract():
    """元评审口：附录 F 全量计数对账 + Top3 回指；四项审计算法照常产出。"""
    r = run_py(META_REVIEW,
               "tests/fixtures/meta-review/published/reports/example-meta-brand"
               "/versions/v1/report.md",
               "--findings",
               "tests/fixtures/meta-review/published/reports/example-meta-brand"
               "/versions/v1/findings.json")
    assert r.returncode == 0, r.stdout + r.stderr
    out = r.stdout
    assert "三态计数（透明化全量）：confirmed 1 · needs_validation 2 · " \
           "rejected 1，共 4 条" in out  # 契约：计数对账
    assert "findings 线索：F-alpha-judge-001、F-beta-judge-002" in out  # 回指
    assert "四项审计算法与 A–F 阈值未动" in out
    assert re.search(r"1\. \*\*总体一致性评级：[A-F]\*\*", out)  # 审计本体照常


def test_ci_passthrough_consumer_reads_per_contract():
    """CI 透传口：exit 0、findings 线索行可见（信息展示，不设门禁）。"""
    r = run_py(CI_META_REVIEW, "--report",
               "tests/fixtures/meta-review/published/reports/example-meta-brand"
               "/versions/v1/report.md",
               "--findings",
               "tests/fixtures/meta-review/published/reports/example-meta-brand"
               "/versions/v1/findings.json")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "**findings 线索**：" in r.stdout
    assert "F-alpha-judge-001" in r.stdout


def test_quality_gate_consumer_reads_per_contract():
    """工程质量门口：findings_annex available/ok/recognized 全真，只读附件。"""
    lines, payload = quality_gate.findings_annex(
        str(FINDINGS_TREE / GOLDEN_FINDINGS), FINDINGS_TREE)
    assert payload["available"] is True
    assert payload["ok"] is True and payload["error_count"] == 0
    assert payload["recognized"] is True
    assert payload["schema"] == "prd-177-v1"
    assert "R-1…R-7 校验 PASS" in "\n".join(lines)


def test_human_review_consumer_quote_verbatim():
    """人工 review 口：每条 evidence.quote 在 source_ref 指向文件中逐字可命中。"""
    for root, rel, _ in COMPLETE_SAMPLES:
        doc = json.loads((root / rel).read_text(encoding="utf-8"))
        for f in doc["findings"]:
            for ev in f["evidence"]:
                src = root / ev["source_ref"].split("#", 1)[0]
                assert src.is_file(), "%s: %s 不存在" % (rel, ev["source_ref"])
                assert ev["quote"] in src.read_text(encoding="utf-8"), \
                    "%s %s: quote 未逐字命中" % (rel, f["id"])


# ── 4. 无密钥（R-7 同源 C-3 扫描器，密钥只放环境变量）───────────────────────

def test_no_secrets_in_findings_surfaces():
    """C-3 扫描三棵 fixture 树全部文本 + 两份 findings 文档：0 命中。"""
    targets: list[pathlib.Path] = []
    for tree in (FINDINGS_TREE, META_TREE, CONSUMER_TREE):
        targets += [p for p in sorted(tree.rglob("*"))
                    if p.is_file() and p.suffix in (".md", ".json", ".yaml")]
    targets += [CONTRACT_DOC, T5_RECORD]
    assert T5_RECORD.is_file(), "T5 验收记录应入库：docs/quality/t5-acceptance-findings-2026-10-26.md"
    hits = []
    for f in targets:
        text = f.read_text(encoding="utf-8")
        for ln, kind, line in quality_gate.scan_c3_text(text):
            hits.append("%s:%d [%s] %s" % (
                f.relative_to(REPO).as_posix(), ln, kind, line))
    assert hits == [], "findings 面出现疑似真实凭据/内网形态：\n" + "\n".join(hits)
