# tests/test_validate_findings.py — findings.json 三态校验器回归（PRD-177/T2，trend #886）
"""scripts/validate_findings.py 的 R-1…R-7 规则回归 + 确定性 + 退出码断言。

样例树 = tests/fixtures/findings（mini 仓库树，全部占位内容，无真实品牌/主机/IP/密钥）。
设计依据：PRD-177/T1 §3.2 校验规则固定清单（trend #885）。纯静态检查，不调 LLM。

运行：python -m pytest tests/test_validate_findings.py -q
"""
import json
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR = REPO / "scripts" / "validate_findings.py"
FIXTURE_ROOT = REPO / "tests" / "fixtures" / "findings"
V1 = "published/reports/example-brand/versions/v1"
GOLDEN = FIXTURE_ROOT / V1 / "findings.json"
FULL = FIXTURE_ROOT / V1 / "findings-full.json"


def run_validator(target: pathlib.Path, root: pathlib.Path = FIXTURE_ROOT):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(target), "--root", str(root)],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120)


def appendix(out: str) -> dict:
    for line in out.splitlines():
        if line.startswith("附录: "):
            return json.loads(line[len("附录: "):])
    raise AssertionError("报告里没有附录 JSON 行: " + out)


def violations_by_rule(out: str, rule: str) -> list[dict]:
    a = appendix(out)
    assert a["ok"] is False and a["error_count"] > 0
    return [v for v in a["violations"] if v["rule"] == rule]


def write_variant(tmp_path: pathlib.Path, mutate) -> pathlib.Path:
    """以适配层金样例为底本，应用 mutate(dict) 后写到 tmp_path，返回路径。"""
    doc = json.loads(GOLDEN.read_text(encoding="utf-8"))
    mutate(doc)
    p = tmp_path / "findings.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


# ── 金样例（正样本）─────────────────────────────────────────────────────────

def test_golden_adapter_sample_passes():
    r = run_validator(GOLDEN)
    assert r.returncode == 0, r.stdout + r.stderr
    a = appendix(r.stdout)
    assert a["schema"] == "prd-177-v1" and a["ok"] is True and a["error_count"] == 0
    assert "结论: PASS" in r.stdout


def test_full_three_state_sample_passes():
    r = run_validator(FULL)
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(FULL.read_text(encoding="utf-8"))
    statuses = {f["status"] for f in doc["findings"]}
    assert statuses == {"confirmed", "needs_validation", "rejected"}


def test_deterministic_10_runs_byte_identical():
    outs = {run_validator(GOLDEN).stdout for _ in range(10)}
    assert len(outs) == 1, "同输入跑 10 次输出必须逐字节一致（PRD-063/T5 同款验收法）"


# ── R-1 顶层结构 / counts 对账 ──────────────────────────────────────────────

def test_r1_counts_mismatch(tmp_path):
    p = write_variant(tmp_path, lambda d: d["counts"].__setitem__("confirmed", 1))
    r = run_validator(p)
    assert r.returncode == 1
    hits = violations_by_rule(r.stdout, "R-1")
    assert any(v["path"] == "$.counts" and "不一致" in v["message"] for v in hits)


def test_r1_unknown_version_rejected(tmp_path):
    p = write_variant(tmp_path, lambda d: d.__setitem__("findings_version", "prd-999-v1"))
    r = run_validator(p)
    assert r.returncode == 1
    assert any("版本不识别" in v["message"] for v in violations_by_rule(r.stdout, "R-1"))


def test_r1_missing_top_field(tmp_path):
    def mutate(d):
        d.pop("report_ref")
    p = write_variant(tmp_path, mutate)
    r = run_validator(p)
    assert r.returncode == 1
    assert any("report_ref" in v["message"] for v in violations_by_rule(r.stdout, "R-1"))


def test_r1_unparseable_json(tmp_path):
    p = tmp_path / "broken.json"
    p.write_text("{oops", encoding="utf-8")
    r = run_validator(p)
    assert r.returncode == 1
    assert any("JSON 不可解析" in v["message"] for v in violations_by_rule(r.stdout, "R-1"))


def test_r1_empty_findings_requires_zero_counts(tmp_path):
    def mutate(d):
        d["findings"] = []
        d["counts"] = {"confirmed": 1, "needs_validation": 0, "rejected": 0}
    p = write_variant(tmp_path, mutate)
    r = run_validator(p)
    assert r.returncode == 1
    assert violations_by_rule(r.stdout, "R-1")


# ── R-2 id / 枚举 ───────────────────────────────────────────────────────────

def test_r2_bad_id_format_and_duplicate_and_slug_mismatch(tmp_path):
    def mutate(d):
        d["findings"][0]["id"] = "F-example-judge-1"    # 序号非三位数字
        d["findings"][2]["id"] = "F-example-judge-002"  # 与 findings[1] 重复
        d["findings"][3]["id"] = "F-other-judge-004"    # 评委段 != judge_slug
    p = write_variant(tmp_path, mutate)
    r = run_validator(p)
    assert r.returncode == 1
    hits = violations_by_rule(r.stdout, "R-2")
    assert any("格式必须" in v["message"] for v in hits)
    assert any("重复" in v["message"] for v in hits)
    assert any("不一致" in v["message"] for v in hits)


def test_r2_bad_status_lens_kind(tmp_path):
    def mutate(d):
        d["findings"][0]["status"] = "suppressed"   # 第四态，禁
        d["findings"][1]["lens"] = "momentum"       # lens 枚举外
        d["findings"][2]["evidence"][0]["kind"] = "hearsay"
    p = write_variant(tmp_path, mutate)
    r = run_validator(p)
    assert r.returncode == 1
    hits = violations_by_rule(r.stdout, "R-2")
    assert any(v["path"] == "findings[0].status" for v in hits)
    assert any(v["path"] == "findings[1].lens" for v in hits)
    assert any(v["path"].endswith(".kind") for v in hits)


# ── R-3 条件必填 ────────────────────────────────────────────────────────────

def test_r3_needs_validation_requires_unresolved_fact(tmp_path):
    def mutate(d):
        for f in d["findings"]:
            if f["status"] == "needs_validation":
                f.pop("unresolved_fact")
                break
    p = write_variant(tmp_path, mutate)
    r = run_validator(p)
    assert r.returncode == 1
    assert any("unresolved_fact" in v["path"] for v in violations_by_rule(r.stdout, "R-3"))


def test_r3_confirmed_forbids_unresolved_fact(tmp_path):
    full = json.loads(FULL.read_text(encoding="utf-8"))
    for f in full["findings"]:
        if f["status"] == "confirmed":
            f["unresolved_fact"] = "占位：不应出现"
    p = tmp_path / "findings.json"
    p.write_text(json.dumps(full, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    r = run_validator(p)
    assert r.returncode == 1
    assert any("必须缺省" in v["message"] for v in violations_by_rule(r.stdout, "R-3"))


def test_r3_rejected_requires_reason(tmp_path):
    full = json.loads(FULL.read_text(encoding="utf-8"))
    for f in full["findings"]:
        if f["status"] == "rejected":
            f.pop("rejected_reason")
    p = tmp_path / "findings.json"
    p.write_text(json.dumps(full, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    r = run_validator(p)
    assert r.returncode == 1
    assert any("rejected_reason" in v["path"] for v in violations_by_rule(r.stdout, "R-3"))


# ── R-4 judge 归属 / source_ref 路径 ────────────────────────────────────────

def test_r4_unknown_judge_slug(tmp_path):
    def mutate(d):
        d["findings"][0]["judge_slug"] = "not-in-panel"
    p = write_variant(tmp_path, mutate)
    r = run_validator(p)
    assert r.returncode == 1
    assert any("not-in-panel" in v["message"] for v in violations_by_rule(r.stdout, "R-4"))


def test_r4_lead_is_reserved_and_legal(tmp_path):
    full = json.loads(FULL.read_text(encoding="utf-8"))
    p = tmp_path / "findings.json"
    p.write_text(json.dumps(full, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    r = run_validator(p)
    assert r.returncode == 0, r.stdout  # findings-full.json 含 judge_slug=lead，合法


def test_r4_unknown_panel(tmp_path):
    def mutate(d):
        d["panel"] = "no-such-panel"
    p = write_variant(tmp_path, mutate)
    r = run_validator(p)
    assert r.returncode == 1
    assert any(v["path"] == "$.panel" for v in violations_by_rule(r.stdout, "R-4"))


def test_r4_source_ref_missing_file(tmp_path):
    def mutate(d):
        d["findings"][0]["evidence"][0]["source_ref"] = \
            "published/reports/example-brand/versions/v1/_raw/no-such.md#L1"
    p = write_variant(tmp_path, mutate)
    r = run_validator(p)
    assert r.returncode == 1
    assert any("不存在" in v["message"] for v in violations_by_rule(r.stdout, "R-4"))


def test_r4_source_ref_escape_root(tmp_path):
    def mutate(d):
        d["findings"][0]["evidence"][0]["source_ref"] = \
            "../../../../etc/passwd#L1"
    p = write_variant(tmp_path, mutate)
    r = run_validator(p)
    assert r.returncode == 1
    assert any("`..`" in v["message"] or "逃出" in v["message"]
               for v in violations_by_rule(r.stdout, "R-4"))


# ── R-5 逐字引用（反捏造防火墙）────────────────────────────────────────────

def test_r5_quote_not_verbatim(tmp_path):
    def mutate(d):
        d["findings"][0]["evidence"][0]["quote"] = \
            "这句话在任何样例文件里都不存在（捏造演示）。"
    p = write_variant(tmp_path, mutate)
    r = run_validator(p)
    assert r.returncode == 1
    assert any("逐字" in v["message"] for v in violations_by_rule(r.stdout, "R-5"))


def test_r5_applies_to_all_three_states(tmp_path):
    """三态无一例外：confirmed / rejected 的引用同样必须逐字命中。"""
    full = json.loads(FULL.read_text(encoding="utf-8"))
    for f in full["findings"]:
        f["evidence"][0]["quote"] = "捏造句（样例演示）。"
    p = tmp_path / "findings.json"
    p.write_text(json.dumps(full, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    r = run_validator(p)
    assert r.returncode == 1
    hits = violations_by_rule(r.stdout, "R-5")
    assert len(hits) >= 3


# ── R-6 claim / evidence 数量 ───────────────────────────────────────────────

def test_r6_claim_over_80_chars(tmp_path):
    def mutate(d):
        d["findings"][0]["claim"] = "长" * 81
    p = write_variant(tmp_path, mutate)
    r = run_validator(p)
    assert r.returncode == 1
    assert any("80" in v["message"] for v in violations_by_rule(r.stdout, "R-6"))


def test_r6_empty_evidence(tmp_path):
    def mutate(d):
        d["findings"][0]["evidence"] = []
    p = write_variant(tmp_path, mutate)
    r = run_validator(p)
    assert r.returncode == 1
    assert any("evidence" in v["path"] and "≥1" in v["message"]
               for v in violations_by_rule(r.stdout, "R-6"))


# ── R-7 占位符纪律（复用 PRD-151 C-3 正则清单）─────────────────────────────

def test_r7_private_ip_hit(tmp_path):
    def mutate(d):
        d["findings"][0]["claim"] = "内网演示地址 10.1.2.3 出现在结论里"
    p = write_variant(tmp_path, mutate)
    r = run_validator(p)
    assert r.returncode == 1
    assert any("内网网段" in v["message"] for v in violations_by_rule(r.stdout, "R-7"))


def test_r7_credential_assignment_hit(tmp_path):
    def mutate(d):
        d["findings"][0]["claim"] = "演示: api_key = abcdefg12345"
    p = write_variant(tmp_path, mutate)
    r = run_validator(p)
    assert r.returncode == 1
    assert violations_by_rule(r.stdout, "R-7")


def test_r7_whitelist_placeholder_not_reported(tmp_path):
    def mutate(d):
        d["findings"][0]["claim"] = "演示: api_key = <API_KEY>"
        d["findings"][0]["unresolved_fact"] = "演示: token = ${ENV_VAR}"
    p = write_variant(tmp_path, mutate)
    r = run_validator(p)
    assert r.returncode == 0, r.stdout  # 白名单占位形态不报（PRD-151 C-3 同款）


# ── 退出码 ──────────────────────────────────────────────────────────────────

def test_exit_2_missing_file():
    r = run_validator(FIXTURE_ROOT / "no-such.json")
    assert r.returncode == 2 and "不存在" in (r.stdout + r.stderr)


def test_exit_2_no_args():
    r = subprocess.run([sys.executable, str(VALIDATOR)], cwd=str(REPO),
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 2
