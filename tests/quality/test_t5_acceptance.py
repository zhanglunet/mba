# tests/quality/test_t5_acceptance.py — PRD-151/T5 验收断言（trend #759）
"""PRD-151/T5 验收线硬测试：门禁文档入库且无密钥；范例可复现；豁免台账纪律。

- test_gate_docs_no_secrets        门禁文档（docs/quality/** + 门禁 README）C-3 扫描 0 命中
- test_usage_doc_covers_essentials 使用文档覆盖四类运行方式 / 契约 JSONL / 豁免台账 / 归档路径（防漂移）
- test_exemptions_ledger_discipline 豁免台账只含 P1 条目、每评委 <=3 条（文件由 T5 建立）
- test_archived_golden_report_reproducible 范例可复现：归档金正报告的结论行与契约
  JSON 行 == 现场复跑 --judge satyanadella 的对应字段（13/13 全绿）

设计见 docs/plans/2026-10-23-judge-quality-gate.md §四/§五/§六；
验收记录见 docs/quality/t5-acceptance-2026-10-25.md。纯静态检查 + 子进程，不调 LLM。
"""
import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
GATE = REPO / "scripts" / "perspective-tools" / "quality_gate.py"
QUALITY_DIR = REPO / "docs" / "quality"
GATE_README = REPO / "scripts" / "perspective-tools" / "README.md"
ARCHIVED_NAME = re.compile(r"^satyanadella-(\d{4}-\d{2}-\d{2})\.md$")

sys.path.insert(0, str(REPO / "scripts" / "perspective-tools"))
import quality_gate  # noqa: E402


def _doc_files() -> list[pathlib.Path]:
    files = sorted(p for p in QUALITY_DIR.rglob("*")
                   if p.is_file() and p.suffix in (".md", ".yaml"))
    assert files, "docs/quality/ 下应有门禁文档（T5 验收：门禁文档入库）"
    return files + [GATE_README]


def test_gate_docs_no_secrets():
    """T5 验收「无密钥」：C-3 扫描器对门禁文档 0 命中（含归档报告与豁免台账）。"""
    hits = []
    for f in _doc_files():
        text = f.read_text(encoding="utf-8")
        for ln, kind, line in quality_gate.scan_c3_text(text):
            hits.append("%s:%d [%s] %s" % (
                f.relative_to(REPO).as_posix(), ln, kind, line))
    assert hits == [], "门禁文档出现疑似真实凭据/内网形态：\n" + "\n".join(hits)


def test_usage_doc_covers_essentials():
    """使用文档（docs/quality/judge-quality-gate.md）覆盖验收要求的用法要点。"""
    doc = (QUALITY_DIR / "judge-quality-gate.md").read_text(encoding="utf-8")
    for needle in (
        "--judge",            # 怎么跑单评委
        "--sample",           # 怎么抽样
        "--selftest",         # 自测回归
        "--json-out",         # 契约 JSONL
        "exemptions.yaml",    # 豁免台账用法
        "judges/",            # 报告归档约定
        "satyanadella",       # 范例指针
        "example.com",        # 白名单占位形态示例
    ):
        assert needle in doc, "使用文档缺要点：%r" % needle


def test_exemptions_ledger_discipline():
    """豁免台账纪律（T1 §五）：存在、只含 P1 条目、每评委同时 <=3 条。"""
    ledger = QUALITY_DIR / "exemptions.yaml"
    assert ledger.is_file(), "docs/quality/exemptions.yaml 应由 T5 建立"
    exemptions = quality_gate.load_exemptions()  # 与脚本同一条解析路径
    for slug, item_ids in exemptions.items():
        assert item_ids, "%s 的豁免段缺 item_id" % slug
        for iid in item_ids:
            assert iid in quality_gate.P1_IDS, \
                "%s 豁免了 %s：只允许 P1 条目（P0 不设豁免）" % (slug, iid)
        assert len(item_ids) <= 3, "%s 同时有效豁免 %d 条 > 3" % (slug, len(item_ids))


def _payload_of(out: str) -> dict:
    lines = re.findall(r'^\{.*"gate_version".*\}$', out, re.M)
    assert lines, "输出里没有机器可读 JSON 行"
    return json.loads(lines[-1])


def test_archived_golden_report_reproducible():
    """T5 验收「范例可复现」：归档金正报告与现场复跑一致（结论行 + 契约字段）。

    归档是日期快照（A-5 全局 pytest 计数 / C-2 评委总数会随仓库演进），故比对
    「结论: PASS」与契约 JSON 行的逐条状态与三计数，不逐字节比对全文。
    """
    judges_dir = QUALITY_DIR / "judges"
    archived = sorted(p for p in judges_dir.glob("satyanadella-*.md")
                      if ARCHIVED_NAME.match(p.name))
    assert archived, "docs/quality/judges/ 应归档金正范例报告"
    text = archived[-1].read_text(encoding="utf-8")  # 文件名最新的一份
    assert "结论: PASS · PASS 13/13 · warn 0 · exempt 0" in text
    old = _payload_of(text)

    r = subprocess.run(
        [sys.executable, str(GATE), "--judge", "satyanadella"],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=900)
    assert r.returncode == 0, r.stdout + r.stderr
    fresh = _payload_of(r.stdout)
    assert fresh["gate_version"] == old["gate_version"] == "prd-151-v1"
    assert fresh["judge_slug"] == old["judge_slug"] == "satyanadella"
    assert fresh["items"] == old["items"], "归档与复跑的 13 条状态不一致"
    assert (fresh["pass_count"], fresh["warn_count"], fresh["exempt_count"]) == \
           (old["pass_count"], old["warn_count"], old["exempt_count"]) == (13, 0, 0)
