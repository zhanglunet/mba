# tests/test_findings_consumers.py — PRD-177/T3 findings 消费方回归（trend #887）
"""三处消费方（PRD-151/063 可消费 findings.json）的只读消费回归：

  1. scripts/meta_review.py --findings（PRD-063 消费）：Top3 分歧点行内 finding id
     回指线索 + 附录 F 线索段 + 版本字段纪律（只认 prd-177-v1）+ 降级不阻断；
     不带 --findings 时输出不含任何 findings 段（四项审计与 A–F 阈值零改动）。
  2. scripts/ci_meta_review.py --findings（PRD-063 CI 透传）：线索行 + 降级说明。
  3. scripts/perspective-tools/quality_gate.py --findings（PRD-151 消费）：只读附件段
     + 契约 JSON 行 findings_readonly 键；不计入 13 条 checklist、不改 PASS/FAIL。

样例树：tests/fixtures/meta-review（本 T3 自包含 mini 仓库树，全占位）+
       tests/fixtures/findings（PRD-177/T2 金样例，作 quality_gate 附件正样本）。
纯静态检查，不调 LLM。运行：python -m pytest tests/test_findings_consumers.py -q
"""
import json
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
META_REVIEW = REPO / "scripts" / "meta_review.py"
CI_META_REVIEW = REPO / "scripts" / "ci_meta_review.py"
GATE = REPO / "scripts" / "perspective-tools" / "quality_gate.py"
VALIDATOR = REPO / "scripts" / "validate_findings.py"

FIXTURE_ROOT = REPO / "tests" / "fixtures" / "meta-review"
V1 = FIXTURE_ROOT / "published" / "reports" / "example-meta-brand" / "versions" / "v1"
REPORT = V1 / "report.md"
FINDINGS = V1 / "findings.json"

# PRD-177/T2 金样例树（quality_gate 附件正样本复用；两棵样例树相互独立）
FIXTURE_177 = REPO / "tests" / "fixtures" / "findings"
GOLDEN_177 = (FIXTURE_177 / "published" / "reports" / "example-brand"
              / "versions" / "v1" / "findings.json")

sys.path.insert(0, str(REPO / "scripts" / "perspective-tools"))
import quality_gate  # noqa: E402


def run_py(script: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args], cwd=str(REPO), capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=600)


def json_payload(out: str) -> dict:
    lines = re.findall(r'^\{.*"gate_version".*\}$', out, re.M)
    assert lines, "报告里没有机器可读 JSON 行"
    return json.loads(lines[-1])


def write_variant(tmp_path: pathlib.Path, mutate) -> pathlib.Path:
    """以 findings 样例为底本，应用 mutate(dict) 后写到 tmp_path，返回路径。"""
    doc = json.loads(FINDINGS.read_text(encoding="utf-8"))
    mutate(doc)
    p = tmp_path / "findings.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                 encoding="utf-8")
    return p


# ── 1. meta_review --findings（PRD-063 消费）─────────────────────────────────

def test_fixture_findings_pass_t2_validator():
    """消费的前提：样例 findings.json 本身过 PRD-177/T2 校验器 R-1…R-7。"""
    r = run_py(VALIDATOR, str(FINDINGS), "--root", str(FIXTURE_ROOT))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "结论: PASS" in r.stdout


def test_without_findings_flag_no_findings_sections():
    """不带 --findings：输出不含任何 findings 段（向后兼容，审计零改动）。"""
    r1 = run_py(META_REVIEW, str(REPORT))
    r2 = run_py(META_REVIEW, str(REPORT))
    assert r1.returncode == 0 and r2.returncode == 0, r1.stderr + r2.stderr
    assert "findings 线索" not in r1.stdout
    assert "### F." not in r1.stdout
    assert r1.stdout == r2.stdout  # 无 findings 参数路径同样逐字节可复现
    assert "总体一致性评级" in r1.stdout


def test_with_findings_clues_and_appendix_f():
    """带 --findings：审计项 4（Top3 分歧点）行内回指线索 + 附录 F 全量计数。"""
    r = run_py(META_REVIEW, str(REPORT), "--findings", str(FINDINGS))
    assert r.returncode == 0, r.stdout + r.stderr
    out = r.stdout
    # 审计本身照常：评级行在、离群/偏见段不受影响
    assert re.search(r"1\. \*\*总体一致性评级：[A-F]\*\*", out)
    # identity 分歧行（Top1）附两条 finding id 线索；无命中的镜头不加线索
    assert "findings 线索：F-alpha-judge-001、F-beta-judge-002" in out
    assert out.count("findings 线索：F-") == 1  # 只有 identity 命中
    # 附录 F：版本/panel、三态透明化全量计数、回指、needs_validation/rejected 留痕
    assert "### F. findings 线索（PRD-177/T3，只读）" in out
    assert "findings_version=prd-177-v1，panel=example-meta" in out
    assert ("三态计数（透明化全量）：confirmed 1 · needs_validation 2 · "
            "rejected 1，共 4 条") in out
    assert "Top3 分歧镜头回指：identity → F-alpha-judge-001、F-beta-judge-002" in out
    assert "needs_validation（建议复核）：F-beta-judge-002（beta-judge：" in out
    assert "F-gamma-judge-003（gamma-judge：" in out
    assert "rejected（留痕）：F-lead-001（lead：" in out
    assert "四项审计算法与 A–F 阈值未动" in out
    assert "scripts/validate_findings.py" in out  # 判定权归属声明


def test_with_findings_deterministic_10_runs():
    """同输入跑 10 次输出逐字节一致（PRD-063/T5 e2e 同款验收法）。"""
    outs = {run_py(META_REVIEW, str(REPORT), "--findings", str(FINDINGS)).stdout
            for _ in range(10)}
    assert len(outs) == 1


def test_unknown_version_degrades_reject_read(tmp_path):
    """版本不识别 → 拒读不猜测语义；降级说明可见，审计照常产出，退出码 0。"""
    p = write_variant(tmp_path, lambda d: d.__setitem__("findings_version", "prd-999-v9"))
    r = run_py(META_REVIEW, str(REPORT), "--findings", str(p))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "版本不识别" in r.stdout and "拒读不猜测语义" in r.stdout
    assert "降级：findings_version=" in r.stdout
    assert re.search(r"1\. \*\*总体一致性评级：[A-F]\*\*", r.stdout)  # 审计未受影响
    assert "### F." in r.stdout  # 降级说明进附录 F


def test_unparseable_json_degrades(tmp_path):
    p = tmp_path / "broken.json"
    p.write_text("{not-json", encoding="utf-8")
    r = run_py(META_REVIEW, str(REPORT), "--findings", str(p))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "findings JSON 不可解析" in r.stdout
    assert re.search(r"1\. \*\*总体一致性评级：[A-F]\*\*", r.stdout)


def test_counts_mismatch_reported_as_clue_level_note(tmp_path):
    """counts 与实际不一致：只记线索级对账差异，不判审计 FAIL（判定权在校验器）。"""
    p = write_variant(tmp_path, lambda d: d["counts"].__setitem__("confirmed", 7))
    r = run_py(META_REVIEW, str(REPORT), "--findings", str(p))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "计数对账差异" in r.stdout and "confirmed counts=7 vs 实际=1" in r.stdout


# ── 2. ci_meta_review --findings（PRD-063 CI 透传）───────────────────────────

def test_ci_passthrough_with_findings():
    r = run_py(CI_META_REVIEW, "--report", str(REPORT), "--findings", str(FINDINGS))
    assert r.returncode == 0, r.stdout + r.stderr  # 永远 exit 0
    assert "**findings 线索**：" in r.stdout
    assert "F-alpha-judge-001" in r.stdout  # Top3 条目行内带回指 id
    assert "**总体一致性评级" in r.stdout


def test_ci_passthrough_missing_findings_degrades(tmp_path):
    r = run_py(CI_META_REVIEW, "--report", str(REPORT),
               "--findings", str(tmp_path / "absent.json"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "**findings 降级说明**" in r.stdout and "不存在" in r.stdout
    assert "**总体一致性评级" in r.stdout  # 审计摘要照常
    assert "findings 线索**：`" not in r.stdout


# ── 3. quality_gate --findings（PRD-151 消费，只读附件）──────────────────────

def test_qg_annex_pass_on_t2_golden():
    """正样本：PRD-177/T2 金样例 → 附件 available/ok/recognized 全真。"""
    lines, payload = quality_gate.findings_annex(str(GOLDEN_177), FIXTURE_177)
    assert payload["available"] is True
    assert payload["ok"] is True and payload["error_count"] == 0
    assert payload["schema"] == "prd-177-v1" and payload["recognized"] is True
    assert "R-1…R-7 校验 PASS" in "\n".join(lines)


def test_qg_annex_fail_and_unrecognized_version(tmp_path):
    """负样本：版本不识别 → 校验 FAIL + recognized=false（拒读线索）。"""
    doc = json.loads(GOLDEN_177.read_text(encoding="utf-8"))
    doc["findings_version"] = "prd-999-v9"
    p = tmp_path / "findings.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines, payload = quality_gate.findings_annex(str(p), FIXTURE_177)
    assert payload["available"] is True
    assert payload["ok"] is False and payload["error_count"] > 0
    assert payload["recognized"] is False
    assert "版本不识别，拒读线索" in "\n".join(lines)


def test_qg_annex_validator_missing_degrades(tmp_path, monkeypatch):
    """校验器不可用（PRD-177/T2 未叠入的分支形态）→ 降级说明，不抛错。"""
    monkeypatch.setattr(quality_gate, "VALIDATE_FINDINGS",
                        tmp_path / "no-such-validator.py")
    lines, payload = quality_gate.findings_annex(str(GOLDEN_177), FIXTURE_177)
    assert payload["available"] is False and payload["ok"] is False
    assert "降级" in "\n".join(lines) and "validate_findings.py 不存在" in "\n".join(lines)


@pytest.fixture(scope="module")
def gate_out_with_annex():
    """金负样本 fake-judge + findings 附件：整报告跑一次（含 A 组全局门，较慢）。"""
    r = run_py(GATE, "--judge", "tests/quality/fixtures/fake-judge",
               "--findings", str(GOLDEN_177), "--findings-root", str(FIXTURE_177))
    return r


def test_qg_judge_annex_end_to_end(gate_out_with_annex):
    """附件段 + findings_readonly 键落进契约 JSON 行；13 条 checklist 口径不变。"""
    r = gate_out_with_annex
    assert "findings 附件（PRD-177/T3" in r.stdout
    assert "不计入 13 条 checklist、不改 PASS/FAIL" in r.stdout
    p = json_payload(r.stdout)
    assert len(p["items"]) == 13  # 13 条 checklist 口径未膨胀（T1 §四.2）
    assert not any("findings" in it["id"] for it in p["items"])
    ro = p["findings_readonly"]
    assert ro["available"] is True and ro["ok"] is True and ro["recognized"] is True


def test_qg_judge_annex_does_not_change_verdict(gate_out_with_annex):
    """金负样本结论仍是 FAIL（A-2/A-3 fail）：附件不改 PASS/FAIL 判定。"""
    r = gate_out_with_annex
    assert r.returncode == 1  # fake-judge 金负样本固有 FAIL，附件不改变它
    assert re.search(r"^结论: FAIL · PASS \d+/13", r.stdout, re.M)
    bare = run_py(GATE, "--judge", "tests/quality/fixtures/fake-judge")
    line_with = next(ln for ln in r.stdout.splitlines() if ln.startswith("结论:"))
    line_without = next(ln for ln in bare.stdout.splitlines() if ln.startswith("结论:"))
    assert line_with == line_without  # 结论行逐字节一致


def test_qg_findings_flag_guards():
    """--findings 仅支持 --judge 模式；--findings-root 需与 --findings 同用。"""
    assert run_py(GATE, "--selftest", "--findings", "x.json").returncode == 2
    assert run_py(GATE, "--sample", "0", "--findings", "x.json").returncode == 2
    assert run_py(GATE, "--judge", "satyanadella", "--findings-root", ".").returncode == 2
