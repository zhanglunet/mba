# tests/test_adapt_findings.py — 评委输出适配层回归（PRD-177/T2，trend #886）
"""scripts/adapt_findings.py（reviews/<slug>.md → 三态 findings.json 投影）断言。

T1 §3.3 投影纪律的机器验收：
  - 默认落 needs_validation，绝不默认 confirmed；
  - `## Brand action` 不入 findings；
  - evidence 逐字引用评委落笔原文，校验器（R-1…R-7）必须放行；
  - 适配层重生成结果与入库金样例逐字节一致。

样例树 = tests/fixtures/findings（全部占位内容）。纯静态检查，不调 LLM。
运行：python -m pytest tests/test_adapt_findings.py -q
"""
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
ADAPTER = REPO / "scripts" / "adapt_findings.py"
VALIDATOR = REPO / "scripts" / "validate_findings.py"
FIXTURE_ROOT = REPO / "tests" / "fixtures" / "findings"
V1 = "published/reports/example-brand/versions/v1"
REVIEWS = FIXTURE_ROOT / V1 / "reviews" / "example-judge.md"
GOLDEN = FIXTURE_ROOT / V1 / "findings.json"


def run_adapter(reviews_rel: str, out: pathlib.Path | None,
                root: pathlib.Path = FIXTURE_ROOT, extra: list[str] | None = None):
    cmd = [sys.executable, str(ADAPTER), reviews_rel,
           "--root", str(root), "--panel", "example"]
    if out is not None:
        cmd += ["-o", str(out)]
    if extra:
        cmd += extra
    return subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=120)


def run_validator(target: pathlib.Path):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(target), "--root", str(FIXTURE_ROOT)],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120)


def regenerate(tmp_path: pathlib.Path) -> pathlib.Path:
    out = tmp_path / "findings.json"
    r = run_adapter("published/reports/example-brand/versions/v1/reviews/example-judge.md", out)
    assert r.returncode == 0, r.stdout + r.stderr
    return out


def test_projection_defaults_to_needs_validation(tmp_path):
    doc = json.loads(regenerate(tmp_path).read_text(encoding="utf-8"))
    assert doc["findings_version"] == "prd-177-v1"
    assert doc["brand_slug"] == "example-brand"
    assert doc["panel"] == "example"
    assert doc["report_ref"] == f"{V1}/report.md"
    assert doc["counts"] == {"confirmed": 0, "needs_validation": len(doc["findings"]),
                             "rejected": 0}
    for f in doc["findings"]:
        assert f["status"] == "needs_validation", "适配层绝不默认 confirmed"
        assert f["judge_slug"] == "example-judge"
        assert f["unresolved_fact"].strip(), "needs_validation 必带未决事实"
        assert len(f["claim"]) <= 80
        assert len(f["evidence"]) >= 1
        for ev in f["evidence"]:
            assert ev["kind"] == "review"
            assert ev["quote"] in REVIEWS.read_text(encoding="utf-8"), \
                "evidence 逐字引用必须命中评委落笔原文"


def test_projection_maps_scores_verdict_critical_gap(tmp_path):
    doc = json.loads(regenerate(tmp_path).read_text(encoding="utf-8"))
    lenses = [f["lens"] for f in doc["findings"]]
    assert lenses == ["identity", "signal", None, None], \
        "Scores 两镜头映射行短名；Verdict / Critical gap 为跨口径 null"
    ids = [f["id"] for f in doc["findings"]]
    assert ids == [f"F-example-judge-{n:03d}" for n in range(1, len(ids) + 1)], \
        "id 按评委内出现顺序稳定编号"
    claims = " ".join(f["claim"] for f in doc["findings"])
    assert "Brand action" not in claims and "90 天" not in claims and "90 days" not in claims, \
        "Brand action 是建议不是结论，不入 findings"


def test_regenerated_matches_checked_in_golden_byte_for_byte(tmp_path):
    out = regenerate(tmp_path)
    assert out.read_bytes() == GOLDEN.read_bytes(), \
        "适配层重生成结果必须与入库金样例逐字节一致（改样例后需重跑适配层同步）"


def test_adapter_output_passes_validator(tmp_path):
    out = regenerate(tmp_path)
    r = run_validator(out)
    assert r.returncode == 0, r.stdout + r.stderr


def test_empty_why_rows_are_skipped(tmp_path):
    root = tmp_path / "mini-root"
    reviews_dir = root / "published" / "reports" / "mini-brand" / "versions" / "v1" / "reviews"
    reviews_dir.mkdir(parents=True)
    reviews = reviews_dir / "example-judge.md"
    reviews.write_text(
        "# 示例评委（example-judge）on mini-brand\n"
        "\n"
        "## Scores\n"
        "| Lens | Score | Tooltip | Why |\n"
        "|------|-------|---------|-----|\n"
        "| Identity coherence | 7 | 占位短评 | 占位理由：非空，应收进 findings。 |\n"
        "| Real-world signal | 3 |  |  |\n"
        "\n"
        "## Verdict\n"
        "占位结论：判定行。\n",
        encoding="utf-8")
    out = tmp_path / "findings.json"
    r = run_adapter("published/reports/mini-brand/versions/v1/reviews/example-judge.md",
                    out, root=root)
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert len(doc["findings"]) == 2, "Why/Tooltip 全空的行跳过；Verdict 仍投影"
    assert doc["findings"][0]["lens"] == "identity"
    assert doc["findings"][1]["lens"] is None
    assert "Why/Tooltip 全空" in r.stderr, "跳过必须显式留痕，不静默"


def test_long_why_truncated_to_80_chars_with_note(tmp_path):
    doc = json.loads(regenerate(tmp_path).read_text(encoding="utf-8"))
    for f in doc["findings"]:
        assert len(f["claim"]) <= 80


def test_adapter_exit_2_missing_file(tmp_path):
    r = run_adapter("published/reports/example-brand/versions/v1/reviews/no-such.md", None)
    assert r.returncode == 2 and "不存在" in (r.stdout + r.stderr)
