# -*- coding: utf-8 -*-
"""PRD-205/T4 自测（trend #1028）：确定性检查自动化——可机检项先机检/人工项不冒充/退出码/镜像集。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from design_language_audit import (  # noqa: E402
    audit,
    build_registry,
    declarations,
    exit_code,
    mirror_set_check,
    style_fragments,
)
from design_language_loader import load_design_language  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DL_PATH = REPO / "design" / "design-language.json"


def load_dl():
    return load_design_language(DL_PATH)


def write(tmpdir, name, text):
    p = Path(tmpdir) / name
    p.write_text(text, encoding="utf-8")
    return str(p)


class TestRegistry(unittest.TestCase):
    def test_machine_manual_split(self):
        # 落地文件登记：4 条 machine + 1 条 manual（DL-C02 对比度为人工）
        reg = build_registry(load_dl())
        self.assertEqual(set(reg["machine"]), {"DL-C01", "DL-T01", "DL-S01", "DL-M01"})
        self.assertEqual(set(reg["manual"]), {"DL-C02"})
        self.assertEqual(reg["errors"], [])

    def test_unknown_check_method_fail_closed(self):
        dl = load_dl()
        dl["checks"]["DL-C01"] = "llm-guess"
        reg = build_registry(dl)
        self.assertTrue(any("未知判定方法" in e for e in reg["errors"]))

    def test_check_entry_not_in_rules_fail_closed(self):
        dl = load_dl()
        dl["checks"]["DL-Z99"] = "machine"
        reg = build_registry(dl)
        self.assertTrue(any("不存在" in e for e in reg["errors"]))

    def test_rule_without_check_entry_fail_closed(self):
        dl = load_dl()
        dl["checks"].pop("DL-S01")
        reg = build_registry(dl)
        self.assertTrue(any("缺少 checks 登记" in e for e in reg["errors"]))


class TestExtraction(unittest.TestCase):
    def test_style_blocks_and_inline_attrs(self):
        text = '<style>.a { color: #111; }</style><div style="font-size: 14px">x</div>'
        decls = declarations(style_fragments(text))
        self.assertIn(("color", "#111"), decls)
        self.assertIn(("font-size", "14px"), decls)

    def test_comments_stripped(self):
        text = "<style>/* color: #ff00ff */ .a { color: #1a73e8; }</style>"
        hits = [d for d in declarations(style_fragments(text)) if d[0] == "color"]
        self.assertEqual(hits, [("color", "#1a73e8")])


class TestMachineChecks(unittest.TestCase):
    def test_off_palette_color_fails(self):
        # DL-C01 hard：集合外色值 → fail
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "card.html",
                      '<style>.btn { background: #ff00ff; color: #1a73e8; }</style>')
            report = audit(load_dl(), [f])
        finding = next(x for x in report["findings"] if x["rule"] == "DL-C01")
        self.assertEqual(finding["verdict"], "fail")
        self.assertEqual(finding["level"], "hard")
        self.assertEqual(finding["file"], f)
        self.assertIn("#ff00ff", finding["evidence"])
        self.assertIn("#1a73e8", finding["evidence"])  # 期望集合摘要在证据里

    def test_registered_color_passes(self):
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "ok.html", '<style>.btn { background: #1a73e8; color: #202124; }</style>')
            report = audit(load_dl(), [f])
        finding = next(x for x in report["findings"] if x["rule"] == "DL-C01")
        self.assertEqual(finding["verdict"], "pass")
        self.assertIn("全部落在登记集合", finding["evidence"])

    def test_selector_hash_not_mistaken_for_color(self):
        # 选择器 #id 与色值同形不受影响（只查 color 系属性取值）
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "sel.html", '<style>#dec0de .btn { color: #1a73e8; }</style>')
            report = audit(load_dl(), [f])
        finding = next(x for x in report["findings"] if x["rule"] == "DL-C01")
        self.assertEqual(finding["verdict"], "pass")

    def test_off_ladder_font_size_fails(self):
        # DL-T01 hard：字号 15px 不在 12/14/18/22/28 阶梯
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "t.html", '<style>h4 { font-size: 15px; }</style>')
            report = audit(load_dl(), [f])
        finding = next(x for x in report["findings"] if x["rule"] == "DL-T01")
        self.assertEqual(finding["verdict"], "fail")
        self.assertIn("15px", finding["evidence"])

    def test_ladder_font_size_passes(self):
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "t.html", '<style>h1 { font-size: 28px; } p { font-size: 14px; }</style>')
            report = audit(load_dl(), [f])
        self.assertEqual(next(x for x in report["findings"] if x["rule"] == "DL-T01")["verdict"], "pass")

    def test_off_ladder_spacing_notes_not_fails(self):
        # DL-S01 soft：15px 不在 4/8/16/24/32 档 → note（建议级不判 fail）
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "s.html", '<style>.row { padding: 15px; }</style>')
            report = audit(load_dl(), [f])
        finding = next(x for x in report["findings"] if x["rule"] == "DL-S01")
        self.assertEqual(finding["verdict"], "note")
        self.assertEqual(finding["level"], "soft")

    def test_zero_and_ladder_spacing_pass(self):
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "s.html", '<style>.row { padding: 0 16px; margin: 8px auto; }</style>')
            report = audit(load_dl(), [f])
        self.assertEqual(next(x for x in report["findings"] if x["rule"] == "DL-S01")["verdict"], "pass")

    def test_off_preset_motion_notes(self):
        # DL-M01 soft：400ms 不在 150ms/300ms 档 → note
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "m.html", '<style>.modal { transition: opacity 400ms ease-in-out; }</style>')
            report = audit(load_dl(), [f])
        finding = next(x for x in report["findings"] if x["rule"] == "DL-M01")
        self.assertEqual(finding["verdict"], "note")
        self.assertIn("400ms", finding["evidence"])

    def test_motion_unit_normalization(self):
        # 0.3s 归一为 300ms 后落在档位；0 视为禁用不查
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "m.html", '<style>.a { transition: all 0.3s; } .b { transition-duration: 0s; }</style>')
            report = audit(load_dl(), [f])
        self.assertEqual(next(x for x in report["findings"] if x["rule"] == "DL-M01")["verdict"], "pass")


class TestManualChecks(unittest.TestCase):
    def test_manual_rule_skip_not_pass(self):
        # DL-C02 人工项 → skip-manual，不冒充通过
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "c.html", "<p>示例页</p>")
            report = audit(load_dl(), [f])
        finding = next(x for x in report["findings"] if x["rule"] == "DL-C02")
        self.assertEqual(finding["verdict"], "skip-manual")
        self.assertEqual(report["counts"]["skip_manual"], 1)
        self.assertEqual(report["judge"]["manual"], ["DL-C02"])


class TestReport(unittest.TestCase):
    def test_judge_skip_lists_passed_rules(self):
        # 机检报告供评委跳过已过项：全过的产物 → judge.skip 含全部 machine 条目
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "clean.html",
                      '<style>.btn { background: #1a73e8; font-size: 14px; padding: 16px; '
                      'transition: opacity 150ms; }</style>')
            report = audit(load_dl(), [f])
        self.assertEqual(report["counts"],
                         {"fail": 0, "note": 0, "pass": 4, "skip_manual": 1})
        self.assertEqual(sorted(report["judge"]["skip"]),
                         ["DL-C01", "DL-M01", "DL-S01", "DL-T01"])
        self.assertTrue(report["ok"])
        self.assertEqual(exit_code(report), 0)

    def test_note_only_still_exit_zero(self):
        # T1 §5.2：只有 note → 退出码 0
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "s.html", '<style>.row { padding: 15px; }</style>')
            report = audit(load_dl(), [f])
        self.assertEqual(report["counts"]["note"], 1)
        self.assertEqual(report["counts"]["fail"], 0)
        self.assertEqual(exit_code(report), 0)

    def test_fail_exit_nonzero(self):
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "bad.html", '<style>.btn { background: #ff00ff; }</style>')
            report = audit(load_dl(), [f])
        self.assertEqual(report["counts"]["fail"], 1)
        self.assertFalse(report["ok"])
        self.assertEqual(exit_code(report), 1)

    def test_unimplemented_checker_fail_closed(self):
        dl = load_dl()
        dl["checks"]["DL-C02"] = "machine"  # DL-C02 无判定器登记
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "x.html", "<p>x</p>")
            report = audit(dl, [f])
        self.assertTrue(any("未实现" in e for e in report["errors"]))
        self.assertFalse(report["ok"])
        self.assertEqual(exit_code(report), 1)

    def test_missing_file_fail_closed(self):
        report = audit(load_dl(), ["does-not-exist.html"])
        self.assertTrue(any("不存在" in e for e in report["errors"]))
        self.assertFalse(report["ok"])

    def test_report_version_stamped(self):
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "x.html", "<p>x</p>")
            report = audit(load_dl(), [f])
        self.assertEqual(report["dl_version"], "1.0.0")
        self.assertEqual(report["files"], [f])


class TestMirrorSet(unittest.TestCase):
    def test_absent_mirror_registered_not_failed(self):
        result = mirror_set_check(load_dl(), "/nonexistent/DESIGN-LANGUAGE.md")
        self.assertEqual(result["status"], "absent")
        self.assertTrue(result["ok"])

    def test_consistent_mirror_ok(self):
        dl = load_dl()
        with tempfile.TemporaryDirectory() as d:
            ids = "\n".join(f"- {r['id']}" for r in dl["rules"])
            mirror = write(d, "DESIGN-LANGUAGE.md", f"# 速查版\n{ids}\n")
            result = mirror_set_check(dl, mirror)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["ok"])

    def test_mismatched_mirror_fails(self):
        dl = load_dl()
        with tempfile.TemporaryDirectory() as d:
            ids = "\n".join(f"- {r['id']}" for r in dl["rules"][:-1])  # 少一条
            mirror = write(d, "DESIGN-LANGUAGE.md", f"# 速查版\n{ids}\nDL-X99\n")
            result = mirror_set_check(dl, mirror)
            self.assertEqual(result["status"], "mismatch")
            self.assertFalse(result["ok"])
            self.assertTrue(result["missing"])
            self.assertEqual(result["extra"], ["DL-X99"])
            # 计入报告 errors → 整体不通过
            f = write(d, "x.html", "<p>x</p>")
            report = audit(load_dl(), [f], mirror_path=mirror)
        self.assertFalse(report["ok"])
        self.assertTrue(any("mirror-set 不一致" in e for e in report["errors"]))


class TestCli(unittest.TestCase):
    def test_cli_exit_codes_and_json(self):
        import subprocess
        script = str(REPO / "scripts" / "design_language_audit.py")
        with tempfile.TemporaryDirectory() as d:
            clean = write(d, "clean.html",
                          '<style>.btn { background: #1a73e8; font-size: 14px; padding: 16px; '
                          'transition: opacity 150ms; }</style>')
            out = subprocess.run([sys.executable, script, clean],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            report = json.loads(out.stdout)
            self.assertEqual(report["counts"]["pass"], 4)

            bad = write(d, "bad.html", '<style>.btn { background: #ff00ff; }</style>')
            out = subprocess.run([sys.executable, script, bad],
                                 capture_output=True, text=True)
            self.assertNotEqual(out.returncode, 0)


if __name__ == "__main__":
    unittest.main()
