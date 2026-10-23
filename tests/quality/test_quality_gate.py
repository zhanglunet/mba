# tests/quality/test_quality_gate.py — PRD-151/T2 金样例回归（pytest 包装）
"""quality_gate.py 金正/金负样例断言（PRD-151/T2，trend #756）。

脚本自带 `--selftest`（金样例 + 10 次 sha256 一致性验收，PRD-063/T5 同款）；
本文件把金样例断言落成 pytest 用例，便于本地 / CI 直接跑。纯静态检查，
不调 LLM。设计见 docs/plans/2026-10-23-judge-quality-gate.md §三。
"""
import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
GATE = REPO / "scripts" / "perspective-tools" / "quality_gate.py"
FIXTURE_REL = "tests/quality/fixtures/fake-judge"

sys.path.insert(0, str(REPO / "scripts" / "perspective-tools"))
import quality_gate  # noqa: E402


def run_gate(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GATE), *args], cwd=str(REPO), capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=900)


def json_payload(out: str) -> dict:
    lines = re.findall(r'^\{.*"gate_version".*\}$', out, re.M)
    assert lines, "报告里没有机器可读 JSON 行"
    return json.loads(lines[-1])


def test_golden_positive_satyanadella():
    """金正样例（T1 §六主选）：P0 六条全过 + C-3 机检 0 命中，结论 PASS。"""
    r = run_gate("--judge", "satyanadella")
    assert r.returncode == 0, r.stdout + r.stderr
    p = json_payload(r.stdout)
    assert p["gate_version"] == "prd-151-v1"
    assert p["judge_slug"] == "satyanadella"
    items = {i["id"]: i["status"] for i in p["items"]}
    for iid in ("A-1", "A-2", "A-3", "A-4", "A-5", "A-6"):
        assert items[iid] == "pass", (iid, items[iid])
    assert items["C-3"] == "pass"
    # P1 其余条目 T2 输出人工/待查（warn），不计 fail —— 结论仍 PASS。
    assert p["warn_count"] == 6 and p["exempt_count"] == 0


def test_golden_negative_fixture():
    """金负样本（F8 先例）：A-2 / A-3 / C-3 必拦，结论 FAIL，退出码 1。"""
    r = run_gate("--judge", FIXTURE_REL)
    assert r.returncode == 1, r.stdout + r.stderr
    p = json_payload(r.stdout)
    items = {i["id"]: i["status"] for i in p["items"]}
    assert items["A-2"] == "fail", "3 模型 + DNA 同 facet 应被 A-2 拦"
    assert items["A-3"] == "fail", "伪造 blockquote 应被 A-3 拦"
    assert items["C-3"] == "warn", "合成密钥形态应被 C-3 拦（P1 warn-only）"
    assert items["A-1"] == "pass", "负样本只埋三类违规，结构应仍合规"
    assert "结论: FAIL" in r.stdout


def test_sample_formula_deterministic():
    """确定性抽样：字典序 + 轮次偏移取模，同轮次可复现，跨轮次环绕。"""
    slugs = ["a", "b", "c", "d", "e", "f", "g"]
    assert quality_gate.sample_slugs(0, slugs) == ["a", "b", "c", "d", "e"]
    assert quality_gate.sample_slugs(1, slugs) == ["f", "g", "a", "b", "c"]
    assert quality_gate.sample_slugs(3, slugs) == quality_gate.sample_slugs(3, slugs)
    assert len(set(map(tuple, (quality_gate.sample_slugs(r, slugs)
                               for r in (0, 1, 2))))) == 3  # 不同轮次不同抽样


def test_c3_scanner_whitelist_and_hits():
    """白名单占位形态不报；四类命中形态（合成串）各拦一处。"""
    clean = ("api_key: <API_KEY>\n"
             "token: ${NOT_A_REAL_SECRET_REF}\n"
             "see https://example.com/x and akm-xxx and sk-ant-...\n")
    assert quality_gate.scan_c3_text(clean) == []
    dirty = ("api_key: SYNTHETICfake0000000\n"
             "alias_prefix: akm-SYNTHETICfake000\n"
             "internal_example_host: http://10.99.77.5:8080\n"
             "-----BEGIN SYNTHETIC PRIVATE KEY-----\n")
    kinds = {kind for _, kind, _ in quality_gate.scan_c3_text(dirty)}
    assert kinds == {"cred", "keyprefix", "ip", "privkey"}
