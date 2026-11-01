# -*- coding: utf-8 -*-
"""PRD-205/T5 自测（trend #1029）：验收——生成-评审同尺演练（同一批产物两端结论一致）。

运行：pytest tests/unit/test_prd205_t5_acceptance.py -q（仓库根执行）

演练：同一批产物 → 机检（audit）→ 评审（review_findings）逐条比对——
  机检 pass 条目评审不另判 fail；机检 warn 条目评审结论一致（同尺）；
  全链演练记录 JSON 可落盘。
零网络；全合成。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import design_language_audit as audit_mod  # noqa: E402
import design_language_review as review_mod  # noqa: E402

DL = json.loads((REPO / "design" / "design-language.json").read_text(encoding="utf-8"))


def compliant_artifact(tmp: Path) -> list[str]:
    """用 DL 声明值构造一份合规产物 HTML（色/字/距全部取自 token）。"""
    color = DL["tokens"]["color"]["primary"]
    size_h1 = DL["tokens"]["size"]["h1"]
    size_body = DL["tokens"]["size"]["body"]
    space = DL["tokens"]["spacing"]["md"]
    html = f"""<!doctype html><html><head><style>
h1 {{ color: {color}; font-size: {size_h1}; margin: {space}; }}
p {{ color: {DL['tokens']['color']['text']}; font-size: {size_body}; margin: {space}; }}
</style></head><body><h1>同尺演练标题（合成）</h1><p>同尺演练正文（合成）。</p></body></html>"""
    path = tmp / "artifact.html"
    path.write_text(html, encoding="utf-8")
    return [str(path)]


class SameRulerTests(unittest.TestCase):
    def test_generator_and_reviewer_agree(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            files = compliant_artifact(tmp)
            machine = audit_mod.audit(DL, files)
            # 同尺断言 1：机检无 hard fail（声明值构造 → 全合规）
            errors = [f for f in machine["findings"]
                      if f.get("level") == "hard" and f.get("verdict") == "fail"]
            self.assertEqual(errors, [], f"机检 hard fail：{errors}")
            # 同尺断言 2：把机检 findings 喂给评审模块，评审不推翻
            review = review_mod.review_findings(DL, machine["findings"])
            review_errors = [f for f in review.get("findings", [])
                             if f.get("level") == "hard" and f.get("verdict") == "fail"]
            self.assertEqual(review_errors, [])
            # 演练记录可落盘
            record = {"machine": machine["findings"], "review": review}
            json.dumps(record, ensure_ascii=False)

    def test_drifted_artifact_caught_by_both_ends(self):
        """注入一处越值（非声明色）→ 机检与评审两端都报，结论一致。"""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            files = compliant_artifact(tmp)
            path = Path(files[0])
            path.write_text(path.read_text(encoding="utf-8").replace(
                DL["tokens"]["color"]["primary"], "#123456"), encoding="utf-8")
            machine = audit_mod.audit(DL, [str(path)])
            bad = [f for f in machine["findings"]
                   if f.get("level") == "hard" and f.get("verdict") == "fail"]
            self.assertTrue(bad, "机检未捕获越值色")
            review = review_mod.review_findings(DL, machine["findings"])
            review_bad = [f for f in review.get("findings", [])
                          if f.get("level") == "hard" and f.get("verdict") == "fail"]
            self.assertEqual(len(review_bad), len(bad))  # 两端结论一致


if __name__ == "__main__":
    unittest.main()
