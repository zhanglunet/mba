# tests/quality/test_ci_gate_status.py — PRD-151/T3 元评审挂钩（接口契约 + 金样例端到端）
"""ci_gate_status.py / quality_gate --json-out 测试（PRD-151/T3，trend #757）。

覆盖两组验收：
1. 接口契约可读性：quality_gate --json-out 产出的 JSONL 符合 T1 §四.2 契约
   （gate_version / judge_slug / items[id,level,status] / 三计数；status 四值枚举
   pass|warn|fail|exempt，level 固定 P0/P1），消费方 load_contract_lines 能读、
   能校验、能按"同 slug 取末行"去重；
2. 金样例端到端：金正样例 satyanadella 全链（diff/显式入口 → 门禁 → 契约 JSONL →
   summary 渲染 + §四.3 复核线索联动）；金负样本 fake-judge FAIL 也产出契约行。

纯静态检查 + 子进程，不调 LLM。设计见 docs/plans/2026-10-23-judge-quality-gate.md §四。
"""
import json
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
GATE = REPO / "scripts" / "perspective-tools" / "quality_gate.py"
CI_STATUS = REPO / "scripts" / "ci_gate_status.py"
FIXTURE_REL = "tests/quality/fixtures/fake-judge"

sys.path.insert(0, str(REPO / "scripts"))
import ci_gate_status  # noqa: E402

STATUSES = {"pass", "warn", "fail", "exempt"}  # T1 §四.2 四值枚举


def run_py(script: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args], cwd=str(REPO), capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=900)


# ── 1. 接口契约可读性 ─────────────────────────────────────────────────────────
def test_json_out_contract_on_golden_negative(tmp_path):
    """金负样本走 --json-out：FAIL（exit 1）也写契约行，字段全合规（T1 §四.2）。"""
    jsonl = tmp_path / "gate.jsonl"
    r = run_py(GATE, "--judge", FIXTURE_REL, "--json-out", str(jsonl))
    assert r.returncode == 1, r.stdout + r.stderr  # FAIL 也是正常产报告
    lines = jsonl.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    p = json.loads(lines[0])
    assert p["gate_version"] == "prd-151-v1"
    assert p["judge_slug"] == "fake-judge"
    assert {it["level"] for it in p["items"]} <= {"P0", "P1"}
    assert all(it["status"] in STATUSES for it in p["items"])
    assert all(set(it) == {"id", "level", "status"} for it in p["items"])
    for status, count in (("pass", p["pass_count"]), ("warn", p["warn_count"]),
                          ("exempt", p["exempt_count"])):
        assert count == sum(1 for it in p["items"] if it["status"] == status)
    items = {it["id"]: it["status"] for it in p["items"]}
    assert items["A-2"] == "fail" and items["A-3"] == "fail"  # 金负必拦
    assert items["C-3"] == "warn"


def test_json_out_selftest_rejected(tmp_path):
    """--selftest 不支持 --json-out（用法非法 exit 2，不产文件）。"""
    jsonl = tmp_path / "gate.jsonl"
    r = run_py(GATE, "--selftest", "--json-out", str(jsonl))
    assert r.returncode == 2
    assert not jsonl.exists()


def test_load_contract_lines_validate_and_dedupe(tmp_path):
    """消费方只读：合法行可读，坏行跳过记警告（不静默），同 slug 取末行。"""
    good = {"gate_version": "prd-151-v1", "judge_slug": "a",
            "items": [{"id": "A-1", "level": "P0", "status": "pass"}],
            "pass_count": 1, "warn_count": 0, "exempt_count": 0}
    good2 = dict(good, judge_slug="a",
                 items=[{"id": "A-1", "level": "P0", "status": "warn"}],
                 pass_count=0, warn_count=1, exempt_count=0)
    bad_status = dict(good, judge_slug="b",
                      items=[{"id": "B-2", "level": "P1", "status": "maybe"}])
    bad_version = dict(good, judge_slug="c", gate_version="prd-999-v9")
    bad_missing = dict(good, judge_slug="d")
    del bad_missing["warn_count"]
    jsonl = tmp_path / "gate.jsonl"
    jsonl.write_text("\n".join([
        json.dumps(good, ensure_ascii=False),
        "{not json",
        json.dumps(bad_status),
        json.dumps(bad_version),
        json.dumps(bad_missing),
        json.dumps(good2, ensure_ascii=False),  # a 的更新行（末行生效）
        "",
    ]) + "\n", encoding="utf-8")
    payloads, warnings = ci_gate_status.load_contract_lines(jsonl)
    assert set(payloads) == {"a"}  # 只有合法行进入；a 去重取末行
    assert payloads["a"]["warn_count"] == 1
    assert len(warnings) == 4  # 坏 JSON / 坏 status / 未知版本 / 缺字段，逐条显式
    assert any("prd-999-v9" in w for w in warnings)


def test_verdict_of_p0_fail_implies_fail():
    """结论按契约字段机械推导（T1 §二）：P0 任一 fail ⇒ FAIL，否则 PASS。"""
    def payload(statuses):
        return {"items": [{"id": i, "level": lvl, "status": st}
                          for i, (lvl, st) in statuses.items()]}
    assert ci_gate_status.verdict_of(payload(
        {"A-1": ("P0", "pass"), "A-2": ("P0", "fail"), "C-3": ("P1", "warn")})) == "FAIL"
    assert ci_gate_status.verdict_of(payload(
        {"A-1": ("P0", "pass"), "C-3": ("P1", "warn")})) == "PASS"


def test_slugs_from_paths():
    """受影响评委推导：perspectives/<slug>-perspective/** → slug；其余路径不命中。"""
    paths = [
        "perspectives/satyanadella-perspective/SKILL.md",
        "perspectives/xuxin-perspective/references/research/02-conversations.md",
        "perspectives/satyanadella-perspective",  # 目录路径本身（git diff 给文件，防御）
        "scripts/ci_gate_status.py",
        "metric-brand-auditor/panels/default.yaml",
        "tests/quality/fixtures/fake-judge/SKILL.md",  # 不在 perspectives/ 下，不命中
    ]
    assert ci_gate_status.slugs_from_paths(paths) == ["satyanadella", "xuxin"]
    assert ci_gate_status.slugs_from_paths([]) == []


# ── 2. §四.3 联动的纯函数 ─────────────────────────────────────────────────────
AUDIT_SNIPPET = """# 元评审审计报告（PRD-063/T2）
## 附录

### C. 松紧度画像（bias = 评委均值 − 全体均值）

- 甲：bias=0.48（偏松）；Judge Total 交叉验证：松
- 乙：bias=-0.12（偏紧）
- 丙：bias=0.00（居中）

### D. 解析备注
"""


def test_parse_bias_portrait():
    portrait = ci_gate_status.parse_bias_portrait(AUDIT_SNIPPET)
    assert portrait == [("甲", "0.48", "偏松"), ("乙", "-0.12", "偏紧"),
                        ("丙", "0.00", "居中")]
    assert ci_gate_status.parse_bias_portrait("# 无画像\n") == []


def test_display_to_slugs_real_panels():
    """真实 panel yaml（行级解析）→ 周鸿祎/杨植麟 等 display_name_cn 映射到 slug。"""
    mapping = ci_gate_status.display_to_slugs(
        REPO / "metric-brand-auditor" / "panels")
    assert mapping.get("周鸿祎") == ["zhouhongyi"]
    assert mapping.get("杨植麟") == ["yangzhilin"]
    assert mapping.get("傅盛") == ["fusheng"]


def test_latest_archived_picks_newest(tmp_path):
    d = tmp_path / "judges"
    d.mkdir()
    (d / "zhouhongyi-2026-10-01.md").write_text(
        "报告旧\n结论: FAIL · PASS 4/13 · warn 6 · exempt 0\n", encoding="utf-8")
    (d / "zhouhongyi-2026-10-20.md").write_text(
        "报告新\n结论: PASS · PASS 7/13 · warn 6 · exempt 0\n", encoding="utf-8")
    (d / "zhouhongyi-extra-2026-10-30.md").write_text("另一位评委\n", encoding="utf-8")
    arch = ci_gate_status.latest_archived("zhouhongyi", d)
    assert arch is not None
    date, verdict_line, _ = arch
    assert date == "2026-10-20"  # 取文件名最新；前缀撞名文件（extra）不误收
    assert verdict_line.startswith("结论: PASS")
    assert ci_gate_status.latest_archived("noone", d) is None
    assert ci_gate_status.latest_archived("zhouhongyi", tmp_path / "absent") is None


# ── 3. 金样例端到端 ───────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def real_audit_md(tmp_path_factory):
    """用真实报告跑一次元评审引擎（纯计算），产出审计 Markdown（含松紧度画像）。"""
    report = REPO / "published" / "reports" / "deepseek" / "report.md"
    if not report.is_file():  # 防御：published/ 内容变化时跳过而非误报
        pytest.skip("published/reports/deepseek/report.md 不存在")
    out = tmp_path_factory.mktemp("audit") / "meta-review-audit.md"
    r = run_py(REPO / "scripts" / "meta_review.py", str(report))
    assert r.returncode == 0, r.stderr
    out.write_text(r.stdout, encoding="utf-8")
    return out


def test_end_to_end_golden_positive(tmp_path, real_audit_md):
    """金正样例全链：satyanadella 门禁 → 契约 JSONL → summary + §四.3 联动。"""
    jsonl = tmp_path / "gate.jsonl"
    archived = tmp_path / "judges"
    archived.mkdir()
    (archived / "zhuxiaohu-2026-10-18.md").write_text(
        "归档报告\n结论: PASS · PASS 7/13 · warn 6 · exempt 0\n", encoding="utf-8")
    r = run_py(CI_STATUS, "--judges", "satyanadella",
               "--gate-results", str(jsonl), "--audit-md", str(real_audit_md),
               "--judges-dir", str(archived))
    assert r.returncode == 0, r.stdout + r.stderr  # 只报告，永不阻断
    out = r.stdout
    assert "## 🚦 评委工程质量门禁状态（PRD-151/T3）" in out
    assert "不设合并门禁" in out
    # 表格行由契约 JSONL 渲染：金正样例 P0 六条 + C-3 过，P1 其余 6 条 warn
    row = re.search(r"\| `satyanadella` \| PASS \| 7/13 \| 6 \| 0 \|", out)
    assert row, out
    # 联动：deepseek 画像偏紧的朱啸虎命中入库归档（含过门日期），傅盛本次运行
    assert "朱啸虎" in out and "2026-10-18" in out
    assert "傅盛" in out and "本次运行门禁" not in out  # 傅盛未受影响 → 走归档/未见
    assert "四项审计算法与 A–F 阈值未动" in out
    # 契约 JSONL 确实产出且被消费（接口文件存在）
    assert jsonl.is_file()
    payloads, warnings = ci_gate_status.load_contract_lines(jsonl)
    assert set(payloads) == {"satyanadella"} and warnings == []


def test_end_to_end_golden_negative_and_degrade(tmp_path):
    """金负样本 fake-judge 走消费方（受影响路径形态）；不存在的评委降级不阻断。"""
    jsonl = tmp_path / "gate.jsonl"
    r = run_py(CI_STATUS, "--judges", FIXTURE_REL,
               "--gate-results", str(jsonl), "--judges-dir", str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "| `fake-judge` | FAIL |" in r.stdout  # FAIL 也照常展示（只报告）
    r2 = run_py(CI_STATUS, "--judges", "no-such-judge",
                "--gate-results", str(jsonl), "--judges-dir", str(tmp_path))
    assert r2.returncode == 0  # 找不到评委 → 降级说明，不抛错
    assert "降级说明" in r2.stdout and "`no-such-judge`" in r2.stdout
    # audit-md 缺失时联动略（不误报）
    r3 = run_py(CI_STATUS, "--judges", FIXTURE_REL, "--gate-results", str(jsonl),
                "--audit-md", str(tmp_path / "absent.md"),
                "--judges-dir", str(tmp_path))
    assert r3.returncode == 0
    assert "复核线索联动（§四.3）略" in r3.stdout and "不存在" in r3.stdout
