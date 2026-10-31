# -*- coding: utf-8 -*-
"""PRD-206/T4 自测（trend #1033）：破例留痕——无理由破例不可放行/Floor 不可破例/自批无效/留痕对账。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from slop_gate_exception import (  # noqa: E402
    EXCEPTIONS_VERSION,
    apply_exceptions,
    basis_cited,
    compute_verdict,
    exception_report,
    normalize_hits,
    validate_exception,
)
from slop_gate_floor import GATE_VERSION, gate_floors  # noqa: E402


def reflex_hit(**over):
    hit = {"entry_id": "SLOP-S-03", "tier": "reflex", "locus": "report.md#L30",
           "evidence_quote": "（占位：原句）", "note": "同句空转词 4 个（占位）",
           "exception_ref": None}
    hit.update(over)
    return hit


def valid_exception(**over):
    exc = {"entry_id": "SLOP-S-03", "locus": "report.md#L30",
           "reason": "品牌规范明文要求该句式形态（依据: DL-C05）",
           "proposer": "<proposer-id>", "approver": "<approver-lead>",
           "date": "2026-10-31", "scope": "single-round"}
    exc.update(over)
    return exc


class TestBasisCited(unittest.TestCase):
    def test_dl_entry_counts_as_basis(self):
        # 与设计语言 waivers 对齐：waiver 式理由（引 DL 条目编号）机判可查
        self.assertTrue(basis_cited("品牌规范明文收录该渐变（依据: DL-C05）"))

    def test_repo_path_and_gate_entry_count(self):
        self.assertTrue(basis_cited("延续已审资产 published/reports/example/v1/report.md 的既定形态"))
        self.assertTrue(basis_cited("出处: SLOP-G-02 条目正例允许该用法"))

    def test_personal_feeling_is_not_basis(self):
        self.assertFalse(basis_cited("我觉得没问题"))
        self.assertFalse(basis_cited("感觉还行，就这样吧"))
        self.assertFalse(basis_cited(""))
        self.assertFalse(basis_cited(None))


class TestValidateException(unittest.TestCase):
    def test_valid_reflex_exception(self):
        result = validate_exception(valid_exception(), [reflex_hit()])
        self.assertTrue(result["valid"], result["reasons"])
        self.assertEqual(result["hit_index"], 0)

    def test_floor_cannot_be_excepted(self):
        # Floor 不可破例：字段再齐全也无效（只能改稿或误报复核）
        floor_hit = reflex_hit(entry_id="SLOP-S-01", tier="floor", locus="report.md#L12")
        exc = valid_exception(entry_id="SLOP-S-01", locus="report.md#L12")
        result = validate_exception(exc, [floor_hit])
        self.assertFalse(result["valid"])
        self.assertTrue(any("Floor 不可破例" in r for r in result["reasons"]))

    def test_no_reason_not_valid(self):
        # 验收线：无理由破例不可放行——"我觉得没问题"不算理由
        exc = valid_exception(reason="我觉得没问题")
        result = validate_exception(exc, [reflex_hit()])
        self.assertFalse(result["valid"])
        self.assertTrue(any("无依据引用" in r for r in result["reasons"]))

    def test_missing_field_invalid(self):
        exc = valid_exception()
        del exc["approver"]
        result = validate_exception(exc, [reflex_hit()])
        self.assertFalse(result["valid"])
        self.assertTrue(any("缺少字段" in r and "approver" in r for r in result["reasons"]))

    def test_self_approval_invalid(self):
        # 自批无效（沿 PRD-177 防"自己查自己"思路）
        exc = valid_exception(approver="<proposer-id>")
        result = validate_exception(exc, [reflex_hit()])
        self.assertFalse(result["valid"])
        self.assertTrue(any("自批无效" in r for r in result["reasons"]))

    def test_bad_date_invalid(self):
        for bad in ("tomorrow", "2026-13-40", "2026/10/31"):
            result = validate_exception(valid_exception(date=bad), [reflex_hit()])
            self.assertFalse(result["valid"], bad)
            self.assertTrue(any("YYYY-MM-DD" in r for r in result["reasons"]))

    def test_scope_must_be_single_round(self):
        exc = valid_exception(scope="forever")
        result = validate_exception(exc, [reflex_hit()])
        self.assertFalse(result["valid"])
        self.assertTrue(any("single-round" in r for r in result["reasons"]))

    def test_entry_not_in_hits_invalid(self):
        result = validate_exception(valid_exception(entry_id="SLOP-C-02"), [reflex_hit()])
        self.assertFalse(result["valid"])
        self.assertTrue(any("不在本轮 hits" in r for r in result["reasons"]))

    def test_locus_mismatch_invalid(self):
        result = validate_exception(valid_exception(locus="report.md#L99"), [reflex_hit()])
        self.assertFalse(result["valid"])
        self.assertTrue(any("locus" in r for r in result["reasons"]))

    def test_unknown_tier_not_exceptable(self):
        hit = reflex_hit(tier="unknown")
        result = validate_exception(valid_exception(), [hit])
        self.assertFalse(result["valid"])
        self.assertTrue(any("可破例词表" in r for r in result["reasons"]))


class TestApplyExceptions(unittest.TestCase):
    def test_valid_exception_links_hit_and_counts(self):
        result = apply_exceptions([reflex_hit()], [valid_exception()])
        self.assertEqual(result["hits"][0]["exception_ref"], "exceptions[0]")
        self.assertEqual(result["counts"]["exceptions"], 1)
        self.assertEqual(result["verdict"], "passed_with_warnings")
        self.assertTrue(result["ok"])

    def test_invalid_exception_treated_as_nonexistent(self):
        # 无理由破例：不可放行——exception_ref 不回填，counts.exceptions=0，
        # hit 原文保留（不回写、不洗白），verdict 按未破例计算
        hit = reflex_hit()
        result = apply_exceptions([hit], [valid_exception(reason="我觉得没问题")])
        self.assertIsNone(result["hits"][0]["exception_ref"])
        self.assertEqual(result["counts"]["exceptions"], 0)
        self.assertEqual(result["verdict"], "passed_with_warnings")
        self.assertFalse(result["ok"])
        self.assertEqual(result["invalid_count"], 1)
        self.assertEqual(result["hits"][0]["evidence_quote"], hit["evidence_quote"])
        self.assertEqual(result["hits"][0]["note"], hit["note"])

    def test_floor_hit_stays_blocked_even_with_perfect_exception(self):
        floor_hit = reflex_hit(entry_id="SLOP-S-02", tier="floor", locus="report.md#L5")
        exc = valid_exception(entry_id="SLOP-S-02", locus="report.md#L5")
        result = apply_exceptions([floor_hit], [exc])
        self.assertEqual(result["verdict"], "blocked")
        self.assertIsNone(result["hits"][0]["exception_ref"])
        self.assertEqual(result["counts"]["exceptions"], 0)
        self.assertEqual(result["counts"]["floor"], 1)

    def test_preset_exception_ref_without_valid_record_is_stripped(self):
        # 预置"已放行"标记未经有效破例背书 → 剥除（无理由破例不可放行）
        hit = reflex_hit(exception_ref="exceptions[0]")
        result = apply_exceptions([hit], [])
        self.assertIsNone(result["hits"][0]["exception_ref"])
        self.assertEqual(result["counts"]["exceptions"], 0)

    def test_duplicate_exception_second_invalid(self):
        result = apply_exceptions([reflex_hit()], [valid_exception(), valid_exception()])
        self.assertTrue(result["exceptions"][0]["valid"])
        self.assertFalse(result["exceptions"][1]["valid"])
        self.assertIn("已有生效破例", result["exceptions"][1]["invalid_reasons"][0])
        self.assertEqual(result["counts"]["exceptions"], 1)

    def test_overturned_floor_hit_excluded(self):
        # 误报复核 overturned → 命中撤销，不计入 counts 与 verdict
        floor_hit = reflex_hit(entry_id="SLOP-S-02", tier="floor",
                               review={"result": "overturned", "reviewer": "<gate-maintainer>",
                                       "date": "2026-10-31", "note": "数字实有出处（占位）"})
        result = apply_exceptions([floor_hit], [])
        self.assertEqual(result["verdict"], "passed")
        self.assertEqual(result["counts"]["floor"], 0)


class TestVerdict(unittest.TestCase):
    def test_three_state_verdict(self):
        self.assertEqual(compute_verdict([]), "passed")
        self.assertEqual(compute_verdict([reflex_hit()]), "passed_with_warnings")
        self.assertEqual(
            compute_verdict([reflex_hit(entry_id="SLOP-S-01", tier="floor")]), "blocked")
        # unknown tier 按 Floor 保守处理（放行不可默认）
        self.assertEqual(compute_verdict([reflex_hit(tier="unknown")]), "blocked")


class TestNormalizeHits(unittest.TestCase):
    def test_t2_output_maps_to_schema(self):
        # T2 门输出 {rule_id, evidence} → T1 schema；Floor 五条依 T3 互引登记表定档
        raw = gate_floors("该产品引领未来新篇章，带来极致体验")
        hits = normalize_hits(raw["hits"])
        self.assertEqual({h["entry_id"] for h in hits}, {"SLOP-S-01", "SLOP-T-02"})
        self.assertTrue(all(h["tier"] == "floor" for h in hits))
        self.assertTrue(all(h["locus"] for h in hits))
        self.assertTrue(all(h["exception_ref"] is None for h in hits))

    def test_t1_schema_passthrough(self):
        hit = reflex_hit()
        self.assertEqual(normalize_hits([hit])[0]["entry_id"], "SLOP-S-03")


class TestReport(unittest.TestCase):
    def test_report_schema_and_versions(self):
        result = exception_report([reflex_hit()], [valid_exception()], advisory=[
            {"entry_id": "SLOP-C-04", "tier": "finish", "locus": "report.md",
             "note": "全篇区块边距同一规格（占位）"}])
        self.assertEqual(result["gate_version"], GATE_VERSION)
        self.assertEqual(result["exceptions_version"], EXCEPTIONS_VERSION)
        self.assertEqual(result["counts"],
                         {"floor": 0, "reflex": 1, "finish": 1, "exceptions": 1})
        self.assertTrue(result["ok"])

    def test_counts_reconcile_with_entries(self):
        # 机判对账：counts.exceptions 只计生效破例，无效破例留痕但不算数
        result = exception_report(
            [reflex_hit()],
            [valid_exception(), valid_exception(reason="我觉得没问题"),
             valid_exception(approver="<proposer-id>")])
        self.assertEqual(result["counts"]["exceptions"], 1)
        self.assertEqual(result["invalid_count"], 2)
        self.assertEqual(len(result["exceptions"]), 3)
        # 无效破例全量渲染（条目/无效原因在案可查），不得静默丢弃
        for e in result["exceptions"]:
            self.assertIn("valid", e)
            if not e["valid"]:
                self.assertTrue(e["invalid_reasons"])


if __name__ == "__main__":
    unittest.main()
