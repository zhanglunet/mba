#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-098/T4：上游标准版本跟踪检查脚本（docs/32-standard-tracking.md）。

用法：
  python3 scripts/check_standard_updates.py --check            # 与快照比对（变更 exit 1）
  python3 scripts/check_standard_updates.py --update-snapshot  # 确认消化后更新基线
  python3 scripts/check_standard_updates.py --check --offline  # 只读快照自检（CI/离线）

零第三方依赖；网络不可达 exit 2（inconclusive，非阻断）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "docs" / "standards-snapshot.json"
UA = "mba-standard-tracker/1.0 (PRD-098/T4)"
TIMEOUT = 20


def _fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def collect_heads() -> dict[str, dict[str, str]]:
    """抓四个来源的轻量指纹（不落全文，快照只存 head + sha）。"""
    heads: dict[str, dict[str, str]] = {}
    # S1 openui：pushed_at + 最新 release tag
    repo = json.loads(_fetch("https://api.github.com/repos/thesysdev/openui"))
    pushed = repo.get("pushed_at", "")
    try:
        release = json.loads(_fetch("https://api.github.com/repos/thesysdev/openui/releases/latest"))
        tag = release.get("tag_name", "")
    except Exception:
        tag = ""
    readme = _fetch("https://raw.githubusercontent.com/thesysdev/openui/main/README.md")
    heads["S1_openui"] = {"head": f"pushed={pushed} release={tag}",
                          "content_sha256": _sha256(readme),
                          "fetched_at": pushed}
    # S2 skills 文档：页面里的 Updated 标记行 + frontmatter 字段表关键行
    skills_doc = _fetch("https://code.claude.com/docs/en/skills")
    updated = re.search(r"Updated[^\n<]{0,40}", skills_doc)
    heads["S2_skills_doc"] = {"head": updated.group(0).strip() if updated else "",
                              "content_sha256": _sha256(skills_doc),
                              "fetched_at": ""}
    # S3 cursor plugins reference：提交清单关键行
    cursor_doc = _fetch("https://cursor.com/docs/reference/plugins")
    keyline = re.search(r"Skill identifier[^\n<]{0,60}", cursor_doc)
    heads["S3_cursor_plugins"] = {"head": keyline.group(0).strip() if keyline else "",
                                  "content_sha256": _sha256(cursor_doc),
                                  "fetched_at": ""}
    # S4 claude-plugins-official README（marketplace 淘汰动态）
    official = _fetch("https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/README.md")
    heads["S4_official_readme"] = {"head": f"phased-out={'marketplace.json' in official}",
                                   "content_sha256": _sha256(official),
                                   "fetched_at": ""}
    return heads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="与快照比对")
    parser.add_argument("--update-snapshot", action="store_true", help="更新基线快照")
    parser.add_argument("--offline", action="store_true", help="只读快照自检，不抓网络")
    args = parser.parse_args()

    if not SNAPSHOT_PATH.exists() and not args.update_snapshot:
        print("快照不存在——先跑 --update-snapshot 建基线。", file=sys.stderr)
        return 2

    snapshot = (json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
                if SNAPSHOT_PATH.exists() else {})
    if args.offline or not (args.check or args.update_snapshot):
        print(f"快照自检 OK：{len(snapshot)} 个来源基线在位（"
              + ", ".join(sorted(snapshot)) + "）")
        return 0

    try:
        heads = collect_heads()
    except Exception as error:  # 网络不通/限流：inconclusive 非阻断
        print(f"INCONCLUSIVE：抓取失败（{error}）——稍后重试。", file=sys.stderr)
        return 2

    changed = [name for name, head in heads.items()
               if snapshot.get(name, {}).get("content_sha256") != head["content_sha256"]]
    if args.update_snapshot:
        SNAPSHOT_PATH.write_text(json.dumps(heads, ensure_ascii=False, indent=1,
                                            sort_keys=True) + "\n", encoding="utf-8")
        print(f"快照已更新：{sorted(heads)}")
        return 0
    if changed:
        print("标准有变更，来源：" + ", ".join(changed))
        print("按 docs/32-standard-tracking.md §3 走评估→排期流程。")
        return 1
    print("无变更（" + ", ".join(sorted(heads)) + "）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
