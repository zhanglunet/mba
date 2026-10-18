#!/usr/bin/env python3
"""元评审 e2e 验收（PRD-063/T5，trend #337）。

对一份真实品牌报告走完全链路并断言：
  1. 确定性：同一份输入跑 N 次（缺省 10），输出逐字节一致（sha256 相同）；
  2. 全链路：meta_review.py → render_meta_report.py → ci_meta_review.py
     三步都跑通，产物非空且关键字段一致（评级 B、Top3 为
     Category/Identity/Origin）。

人工抽查（Top3 分歧点至少 2 个是真问题）不在本脚本内，
见 docs/plans/2026-10-18-meta-review-e2e.md 的抽查表，由人工打勾。

纯标准库，不调 LLM。

用法：
  python3 scripts/e2e_meta_review.py [--report PATH] [--runs N]

退出码：0=全部 PASS；1=任一 FAIL。
"""
import argparse
import hashlib
import pathlib
import subprocess
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent

EXPECTED_GRADE_LINE = "总体一致性评级：B"
EXPECTED_TOP3 = ("Category", "Identity", "Origin")


def run(cmd, cwd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                       cwd=str(cwd))
    return r


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="元评审 e2e 验收（确定性 + 全链路）")
    ap.add_argument("--report",
                    default=str(REPO_ROOT / "published" / "reports"
                                / "deepseek" / "report.md"),
                    help="真实品牌报告路径")
    ap.add_argument("--runs", type=int, default=10, help="确定性运行次数")
    args = ap.parse_args()

    report = pathlib.Path(args.report)
    results = []

    def check(name, passed, detail=""):
        results.append(passed)
        print("%s - %s%s" % ("PASS" if passed else "FAIL", name,
                             ("：%s" % detail) if detail else ""))

    if not report.is_file():
        check("输入报告存在", False, str(report))
        print("\nRESULT: FAIL")
        return 1
    check("输入报告存在", True, str(report.relative_to(REPO_ROOT))
          if REPO_ROOT in report.parents else str(report))

    meta = SCRIPTS_DIR / "meta_review.py"
    render = SCRIPTS_DIR / "render_meta_report.py"
    ci = SCRIPTS_DIR / "ci_meta_review.py"
    for p in (meta, render, ci):
        if not p.is_file():
            check("脚本在位 %s" % p.name, False)
            print("\nRESULT: FAIL")
            return 1

    with tempfile.TemporaryDirectory(prefix="e2e_meta_") as tmp:
        tmpdir = pathlib.Path(tmp)

        # ---- 1. 确定性：跑 N 次 ----
        shas, ok_runs = [], True
        for i in range(args.runs):
            out = tmpdir / ("audit_%d.md" % i)
            r = run([sys.executable, str(meta), str(report)], cwd=REPO_ROOT)
            if r.returncode != 0:
                check("确定性运行 #%d exit 0" % (i + 1), False,
                      "stderr: %s" % (r.stderr or "")[:200])
                ok_runs = False
                break
            out.write_text(r.stdout, encoding="utf-8")
            shas.append(sha256_of(out))
        if ok_runs:
            same = len(set(shas)) == 1
            check("N 次运行全部 exit 0", True, "%d 次" % args.runs)
            check("%d 次输出逐字节一致" % args.runs, same,
                  "sha256=%s…（%d 种）" % (shas[0][:16], len(set(shas))))
            audit_text = (tmpdir / "audit_0.md").read_text(encoding="utf-8")
            check("审计输出含评级 B", EXPECTED_GRADE_LINE in audit_text)

        # ---- 2. 全链路 ----
        linked = ok_runs
        html_p = tmpdir / "report.html"
        summ_p = tmpdir / "summary.md"
        if linked:
            r = run([sys.executable, str(render),
                     str(tmpdir / "audit_0.md"), "-o", str(html_p)],
                    cwd=REPO_ROOT)
            check("render_meta_report.py 跑通", r.returncode == 0)
            linked = r.returncode == 0 and html_p.is_file()
        if linked:
            r = run([sys.executable, str(ci), "--report", str(report)],
                    cwd=REPO_ROOT)
            (tmpdir / "summary.md").write_text(r.stdout, encoding="utf-8")
            check("ci_meta_review.py 跑通", r.returncode == 0)
            linked = r.returncode == 0
        if linked:
            html = html_p.read_text(encoding="utf-8")
            summ = summ_p.read_text(encoding="utf-8")
            check("HTML 产物非空", len(html) > 1000, "%d 字节" % len(html))
            check("HTML 含一致性评级", "一致性评级" in html)
            check("summary 产物非空", len(summ) > 200, "%d 字节" % len(summ))
            check("summary 评级 B", EXPECTED_GRADE_LINE in summ)
            top3_ok = all(t in summ for t in EXPECTED_TOP3)
            check("summary Top3 为 Category/Identity/Origin", top3_ok)
            grade_sync = (EXPECTED_GRADE_LINE in audit_text
                          and EXPECTED_GRADE_LINE in summ)
            check("三步评级一致", grade_sync)

    failed = sum(1 for p in results if not p)
    print("\nRESULT: %s（%d/%d 通过）"
          % ("PASS" if failed == 0 else "FAIL",
             len(results) - failed, len(results)))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
