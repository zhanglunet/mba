# tests/test_consumer_findings_alignment.py — PRD-178/T3 消费者输出对齐三态 findings 回归（trend #892）
"""消费者评委（PRD-178/T2 交付的 3 套模拟人设 + consumer-mixed panel）的输出对齐
PRD-177 三态 findings 的回归：

  1. 适配层：scripts/adapt_consumer_findings.py 投影与入库金样例逐字节一致、
     确定性（10 次复跑）、C2 低分阈值规则（>5 跳过）、总结性表态不入 findings；
  2. 咬合：题号 Cn ↔ lens cn 严格对应；judge_slug ∈ 真实 consumer-mixed panel
     （PRD-178/T2 交付）；scenario 引用逐字命中（反捏造防火墙，kind=research）；
  3. schema 子集自检（不依赖 PRD-177/T2 校验器也能跑）：counts 对账、条件必填、
     quote 逐字存在、三态全样例；
  4. 全量 R-1…R-7：scripts/validate_findings.py 属 PRD-177/T2（#295）——在本分支
     存在时必须 PASS，不存在时显式 skip（分支叠加依赖，合入后自动生效）。

样例树：tests/fixtures/consumer-findings（占位内容，无真实品牌/主机/IP/账号/密钥；
panel 与 scenario 引用真实 T2 交付物，证明咬合）。
运行：python -m pytest tests/test_consumer_findings_alignment.py -q
"""
import json
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
ADAPTER = REPO / "scripts" / "adapt_consumer_findings.py"
VALIDATOR = REPO / "scripts" / "validate_findings.py"
PANEL_YAML = REPO / "metric-brand-auditor" / "panels" / "consumer-mixed.yaml"

FIXTURE_ROOT = REPO / "tests" / "fixtures" / "consumer-findings"
V1 = FIXTURE_ROOT / "published" / "reports" / "example-consumer-brand" / "versions" / "v1"
GOLDEN = V1 / "findings.json"
FULL = V1 / "findings-full.json"
REVIEWS = sorted((V1 / "reviews").glob("*.md"))
# 适配层金样例的 CLI 顺序（fixture README 用法一致）：答卷顺序决定 findings 排序
ORDERED_REVIEWS = [V1 / "reviews" / f"{slug}.md"
                   for slug in ("first-glance-shopper", "homework-buyer",
                                "brand-skeptic")]

CONSUMER_SLUGS = ("brand-skeptic", "first-glance-shopper", "homework-buyer")
EXPERT_LENSES = {"origin", "category", "leverage", "identity", "signal"}
C_LENSES = {f"c{i}" for i in range(1, 6)}


def run_py(script: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args], cwd=str(REPO), capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=300)


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def panel_slugs() -> list[str]:
    """真实 consumer-mixed panel 的 judges slug（行级解析，纯标准库）。"""
    slugs = []
    for line in PANEL_YAML.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*-\s*slug:\s*(\S+)", line)
        if m:
            slugs.append(m.group(1))
    assert slugs, "consumer-mixed panel 解析不到 judges"
    return slugs


# ── 1. 适配层（投影与金样例逐字节一致）───────────────────────────────────────

def test_adapter_gold_byte_identical():
    """适配层重生成结果与入库金样例逐字节一致（改 reviews 后必须重跑适配层）。"""
    r = run_py(ADAPTER, *[str(p) for p in ORDERED_REVIEWS], "--root", str(REPO),
               "-o", str(pathlib.Path("/dev/null")))
    assert r.returncode == 0, r.stderr
    regenerated = run_py(ADAPTER, *[str(p) for p in ORDERED_REVIEWS], "--root", str(REPO))
    assert regenerated.returncode == 0, regenerated.stderr
    assert regenerated.stdout == GOLDEN.read_text(encoding="utf-8")


def test_adapter_deterministic_10_runs():
    outs = set()
    for _ in range(10):
        r = run_py(ADAPTER, *[str(p) for p in ORDERED_REVIEWS], "--root", str(REPO))
        assert r.returncode == 0, r.stderr
        outs.add(r.stdout)
    assert len(outs) == 1


def test_adapter_skips_high_c2_and_summaries():
    """C2=7（>5 非低分）跳过；One-liner verdict / Would I share it 不入 findings。"""
    r = run_py(ADAPTER, *[str(p) for p in ORDERED_REVIEWS], "--root", str(REPO))
    assert "C2 购买意愿=7（>5 非低分）" in r.stderr
    assert r.stderr.count("不入 findings（避免重复计数）") == 6  # 3 份答卷 × 2 个总结区
    doc = load(GOLDEN)
    fgs_c2 = [f for f in doc["findings"]
              if f["judge_slug"] == "first-glance-shopper" and f["lens"] == "c2"]
    assert fgs_c2 == []  # first-glance-shopper C2=7 → 不投影
    assert len(doc["findings"]) == 14  # 4（fgs）+ 5（hb）+ 5（bs）


def test_adapter_never_defaults_to_confirmed():
    doc = load(GOLDEN)
    assert doc["counts"] == {"confirmed": 0, "needs_validation": 14, "rejected": 0}
    assert all(f["status"] == "needs_validation" for f in doc["findings"])


def test_adapter_exit_2_missing_file():
    assert run_py(ADAPTER, str(REPO / "no-such-review.md")).returncode == 2


# ── 2. 咬合（lens=c1–c5 / panel / scenario）─────────────────────────────────

@pytest.mark.parametrize("doc_path", [GOLDEN, FULL])
def test_lens_enum_meshing(doc_path):
    """lens 只用 c1–c5 或 null（跨口径）；绝不落专家 5 镜头（消费者域不进专家口径）。"""
    for f in load(doc_path)["findings"]:
        assert f["lens"] is None or f["lens"] in C_LENSES
        assert f["lens"] not in EXPERT_LENSES


def test_question_to_lens_meshing_c1_to_c5():
    """答卷数据行题号 Cn 与投影 lens cn 严格咬合（重解析答卷逐行核对）。"""
    doc = load(GOLDEN)
    by_judge: dict[str, list[str]] = {}
    for f in doc["findings"]:
        by_judge.setdefault(f["judge_slug"], []).append(f["lens"])
    for review in REVIEWS:
        slug = review.stem
        rows = []
        for ln in review.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\|\s*C([1-5])\s*第一印象|^\|\s*C([1-5])\s", ln)
            if m:
                q = next(g for g in m.groups() if g)
                num = re.search(r"\d+", ln.split("|")[2])
                low = num is None or int(num.group()) <= 5
                if slug != "first-glance-shopper" or q != "2" or low:
                    # C2>5 仅 first-glance-shopper（=7）被跳过；其余全投影
                    rows.append(f"c{q}")
        assert by_judge.get(slug) == rows, (slug, by_judge.get(slug), rows)


def test_judge_slugs_belong_to_real_consumer_panel():
    """所有 judge_slug ∈ 真实 consumer-mixed panel（PRD-178/T2 交付物）的 judges。"""
    allowed = set(panel_slugs())
    assert allowed == set(CONSUMER_SLUGS)  # T2 首批 3 套
    for doc_path in (GOLDEN, FULL):
        for f in load(doc_path)["findings"]:
            assert f["judge_slug"] in allowed | {"lead"}


def test_id_judge_segment_matches_and_unique():
    for doc_path in (GOLDEN, FULL):
        ids = []
        for f in load(doc_path)["findings"]:
            m = re.fullmatch(r"F-([a-z0-9][a-z0-9-]*)-(\d{3})", f["id"])
            assert m, f["id"]
            assert m.group(1) == f["judge_slug"]  # id 评委段与 judge_slug 一致
            ids.append(f["id"])
        assert len(ids) == len(set(ids))  # 文件内唯一


@pytest.mark.parametrize("doc_path", [GOLDEN, FULL])
def test_quotes_verbatim_in_source_files(doc_path):
    """R-5 子集（自检形态）：每条 quote 在 source_ref 文件中逐字存在（三态无一例外）。"""
    for f in load(doc_path)["findings"]:
        for ev in f["evidence"]:
            target = REPO / ev["source_ref"].split("#", 1)[0]
            assert target.is_file(), ev["source_ref"]
            assert ev["quote"] in target.read_text(encoding="utf-8"), (
                f"{f['id']} 引用不逐字: {ev['quote'][:30]}…")


def test_scenario_evidence_is_research_kind_and_verbatim():
    """scenario.md 引用 = kind research（T3 定稿口径）+ 逐字命中 + 指向本人设语料。"""
    for f in load(FULL)["findings"]:
        for ev in f["evidence"]:
            if ev["kind"] == "research":
                assert "perspectives/" in ev["source_ref"]
                slug = f["judge_slug"]
                assert f"{slug}-perspective/references/scenario.md" in ev["source_ref"]
                text = (REPO / ev["source_ref"].split("#", 1)[0]).read_text(encoding="utf-8")
                assert ev["quote"] in text
    kinds = {ev["kind"] for f in load(FULL)["findings"] for ev in f["evidence"]}
    assert "research" in kinds  # 样例确实覆盖了 scenario 引用形态


# ── 3. schema 子集自检（不依赖 PRD-177/T2 校验器）────────────────────────────

@pytest.mark.parametrize("doc_path", [GOLDEN, FULL])
def test_counts_reconcile(doc_path):
    doc = load(doc_path)
    tally = {"confirmed": 0, "needs_validation": 0, "rejected": 0}
    for f in doc["findings"]:
        tally[f["status"]] += 1
    assert doc["counts"] == tally


@pytest.mark.parametrize("doc_path", [GOLDEN, FULL])
def test_conditional_required_fields(doc_path):
    for f in load(doc_path)["findings"]:
        if f["status"] == "needs_validation":
            assert f.get("unresolved_fact", "").strip()
        if f["status"] == "rejected":
            assert f.get("rejected_reason", "").strip()
        if f["status"] == "confirmed":
            assert "unresolved_fact" not in f and "rejected_reason" not in f


def test_full_sample_covers_three_states():
    doc = load(FULL)
    assert {f["status"] for f in doc["findings"]} == {
        "confirmed", "needs_validation", "rejected"}
    assert doc["findings_version"] == "prd-177-v1"
    assert doc["panel"] == "consumer-mixed"


def test_reviews_carry_simulated_persona_disclosure():
    """答卷与人设同款诚实标注：每份答卷含「模拟」人设披露（PRD-178 非目标纪律）。"""
    for review in REVIEWS:
        text = review.read_text(encoding="utf-8")
        assert "模拟" in text
        assert "Consumer Answers" in text


def test_report_honesty_box_present():
    """报告诚实盒在场：模拟人设 / 非真实市场调研（rejected 留痕的引用锚）。"""
    text = (V1 / "report.md").read_text(encoding="utf-8")
    assert "模拟人设（合成角色），非真实市场调研" in text


# ── 4. 全量 R-1…R-7（PRD-177/T2 校验器，分支叠加依赖）────────────────────────

@pytest.mark.skipif(not VALIDATOR.is_file(),
                    reason="scripts/validate_findings.py 属 PRD-177/T2（mba#295）分支，"
                           "未叠入本分支；#295 合入或分支叠加后自动执行全量 R-1…R-7")
@pytest.mark.parametrize("doc_path", [GOLDEN, FULL])
def test_full_r1_to_r7_when_validator_available(doc_path):
    r = run_py(VALIDATOR, str(doc_path), "--root", str(REPO))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "结论: PASS" in r.stdout
