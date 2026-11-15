# -*- coding: utf-8 -*-
"""PRD-465/T2（trend issue #2246 的 T2 环节）：mba skill 发现层 最小实现。

按 T1 设计（docs/plans/2026-11-15-prd-465-skill-discovery-layer-design.md）
§6 落地，先用关键词匹配起步（语义推荐留待后续评估）：
  - 索引（只读，不改源数据）：registry.json（pack→skill 映射、triggers
    触发句式、x-perspective_ref）+ 各 SKILL.md frontmatter（name/
    description，description 只读 ≤1024 字合规字段，T1 §1.3）+
    各插件 manifest.json（name/description/keywords——实测 manifest
    无 keywords 字段，按缺失容忍处理）+ metric-brand-auditor；不依赖
    marketplace.json 作唯一源（T1 §1.3：它只含 1 个插件）；
    registry 未覆盖的 3 个消费者视角（实测）由 perspectives/ 目录补齐，
    索引键取其 frontmatter 的 Explicit triggers 行；
  - 推荐：需求描述分词后匹配 triggers + description + keywords，命中
    即候选；分数=触发句式整句命中×2 + 部分命中（≥3 字词落进触发句式）×1
    + 插件关键词命中×2 + 描述关键词命中×1（描述至多 2 分，≥3 字词才计），
    归一到 [0, 1]（raw/4 封顶），按分数降序、skill 名升序确定性排序；
  - 推荐记录按 T1 §6.2 schema 落 DiscoveryLedger（JSONL append-only，
    路径注入）；review.verdict 在 T2 为 "pending"（待人工复核，接受/
    否决回路归 T3）；推荐结果不进评审流程、不进分数（R1），只作
    “建议用什么 skill”的入口。
零网络零子进程；示例全虚构占位。ASPIRE（Apache-2.0）只作形态借鉴，
本模块为原创实现，未复用其代码。
测试：tests/unit/test_prd465_t2_skill_discovery.py
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = "mba-skill-discovery/v1"
DESCRIPTION_MAX = 1024
REVIEW_VERDICTS = ("pending", "accepted", "rejected")
ERROR_CODES = ("DISCOVERY_INCOMPLETE", "DISCOVERY_SCORE_MISMATCH")
# 触发句式分隔符：registry triggers 字符串与 frontmatter Explicit triggers
# 行混用中英文引号、顿号、逗号、句号分隔
_TRIGGER_SEPS = re.compile(r"[\"\"「」『』、，,；;。.\n]+")
# 分词：连续中文 / 连续字母数字；单字词噪声大，只留 ≥2 字


class DiscoveryError(ValueError):
    """发现层违规——显形拒绝。"""


def _frontmatter_block(text: str) -> str | None:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return match.group(1) if match else None


def _block_description(frontmatter: str) -> str:
    """description 块标量（| 形态），与 PRD-234 T3 检查器同一口径。"""
    match = re.search(r"^description:\s*\|?\s*\n((?:[ \t]+.*\n?|\n)*)",
                      frontmatter, re.MULTILINE)
    if match:
        return match.group(1).strip()
    match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _scalar_name(frontmatter: str) -> str | None:
    match = re.search(r"^name:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
    return match.group(1) if match else None


def parse_triggers(raw: str) -> list[str]:
    """触发句式字符串 → 去重短语列表（保序，<2 字片段丢弃）。"""
    seen: list[str] = []
    for part in _TRIGGER_SEPS.split(raw or ""):
        phrase = part.strip().strip("\"'“”.")
        if len(phrase) >= 2 and phrase not in seen:
            seen.append(phrase)
    return seen


def _explicit_triggers(description: str) -> list[str]:
    idx = description.find("Explicit triggers:")
    if idx < 0:
        return []
    rest = description[idx + len("Explicit triggers:"):]
    # 只取触发句式所在段落：到下一个空行（或 Do not activate when 段）为止，
    # 不把后续段落文字误当触发句式
    for stop in ("\n\n", "\nDo not activate when:"):
        cut = rest.find(stop)
        if cut >= 0:
            rest = rest[:cut]
    return parse_triggers(rest)


def tokenize(text: str) -> list[str]:
    """需求描述分词：中文无空格，需 n-gram 切分才可命中关键词。

    中文连续串取全部 2–4 字子串（长串优先、同位置按长度降序），字母数字
    串整词保留；去重保序。无分词器依赖，纯确定性切分（T2 起步口径）。
    """
    seen: list[str] = []

    def add(term: str) -> None:
        if len(term) >= 2 and term not in seen:
            seen.append(term)

    for run in re.findall(r"[\u4e00-\u9fff]+|[A-Za-z0-9][A-Za-z0-9\-]*",
                          text or ""):
        if re.match(r"^[\u4e00-\u9fff]+$", run):
            for start in range(len(run)):
                for length in (4, 3, 2):
                    if start + length <= len(run):
                        add(run[start:start + length])
        else:
            add(run.strip("-"))
    return seen


def load_index(repo_root: str | Path) -> dict[str, Any]:
    """离线建索引（只读）：registry + perspectives + plugins + metric。"""
    root = Path(repo_root)
    entries: dict[str, dict[str, Any]] = {}
    registry_loaded = False

    registry_path = root / "registry.json"
    if registry_path.is_file():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            registry = {}
        for pack in registry.get("packs") or []:
            for skill in pack.get("skills") or []:
                ref = str(skill.get("x-perspective_ref", "")).strip()
                skill_id = ref.rstrip("/").split("/")[-1] if ref else \
                    str(skill.get("name", ""))
                if not skill_id:
                    continue
                entries[skill_id] = {
                    "skill": skill_id, "kind": "perspective",
                    "source": ref or f"registry.json:{pack.get('name', '')}",
                    "triggers": parse_triggers(
                        str(skill.get("triggers", ""))),
                    "description": "",
                    "description_compliant": False,
                    "keywords": [],
                    "positioning": str(skill.get("x-positioning", "")),
                }
        registry_loaded = True

    perspectives_dir = root / "perspectives"
    if perspectives_dir.is_dir():
        for skill_dir in sorted(d for d in perspectives_dir.iterdir()
                                if d.is_dir()):
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            text = skill_md.read_text(encoding="utf-8")
            frontmatter = _frontmatter_block(text)
            if frontmatter is None:
                continue
            description = _block_description(frontmatter)
            entry = entries.setdefault(
                skill_dir.name,
                {"skill": skill_dir.name, "kind": "perspective",
                 "source": f"perspectives/{skill_dir.name}/",
                 "triggers": [], "description": "",
                 "description_compliant": False, "keywords": [],
                 "positioning": ""})
            entry["description"] = description
            entry["description_compliant"] = bool(description) and \
                len(description) <= DESCRIPTION_MAX
            if not entry["triggers"]:
                entry["triggers"] = _explicit_triggers(description)

    plugins_dir = root / "plugins"
    if plugins_dir.is_dir():
        for plugin_dir in sorted(d for d in plugins_dir.iterdir()
                                 if d.is_dir()):
            manifest_path = plugin_dir / "manifest.json"
            if not manifest_path.is_file():
                continue
            try:
                manifest = json.loads(
                    manifest_path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            name = str(manifest.get("name", "") or plugin_dir.name)
            keywords = manifest.get("keywords") or []
            entries[name] = {
                "skill": name, "kind": "plugin",
                "source": f"plugins/{plugin_dir.name}/manifest.json",
                "triggers": [],
                "description": str(manifest.get("description", "")),
                "description_compliant": True,
                "keywords": [str(k) for k in keywords],
                "positioning": "",
            }

    metric_md = root / "metric-brand-auditor" / "SKILL.md"
    if metric_md.is_file():
        frontmatter = _frontmatter_block(
            metric_md.read_text(encoding="utf-8"))
        description = _block_description(frontmatter) if frontmatter else ""
        entries["metric-brand-auditor"] = {
            "skill": "metric-brand-auditor", "kind": "metric",
            "source": "metric-brand-auditor/SKILL.md",
            "triggers": _explicit_triggers(description),
            "description": description,
            "description_compliant": bool(description) and
            len(description) <= DESCRIPTION_MAX,
            "keywords": [],
            "positioning": "",
        }

    kinds = {"perspective": 0, "plugin": 0, "metric": 0}
    for entry in entries.values():
        kinds[entry["kind"]] = kinds.get(entry["kind"], 0) + 1
    return {"schema": SCHEMA, "registry_loaded": registry_loaded,
            "counts": kinds, "total": len(entries),
            "entries": [entries[k] for k in sorted(entries)]}


def _match_entry(entry: dict[str, Any],
                 query: str, terms: list[str]) -> dict[str, Any] | None:
    """单条索引匹配：触发句式整句×2 / 部分×1 / 插件关键词×2 / 描述×1（至多 2 分）。"""
    matched: list[str] = []
    reasons: list[str] = []
    trigger_points = 0
    for phrase in entry["triggers"]:
        if phrase in query:
            trigger_points += 2
            matched.append(phrase)
            reasons.append(f"触发句式命中：{phrase}")
        elif any(len(t) >= 3 and t in phrase for t in terms):
            trigger_points += 1
            matched.append(phrase)
            reasons.append(f"触发句式部分命中：{phrase}")
    keyword_hits = 0
    for keyword in entry["keywords"]:
        if any(t in keyword or keyword in t for t in terms):
            keyword_hits += 1
            matched.append(keyword)
            reasons.append(f"插件关键词命中：{keyword}")
    desc_terms: list[str] = []
    description = entry["description"] if entry["description_compliant"] \
        else ""
    for term in terms:
        # 已命中触发句式的子串不再重复计为描述命中（去噪）
        if len(term) >= 3 and term in description \
                and not any(term in p for p in matched) \
                and term not in desc_terms:
            desc_terms.append(term)
    desc_hits = min(len(desc_terms), 2)  # 描述命中至多贡献 2 分：触发 > 描述
    matched.extend(desc_terms[:5])
    reasons.extend(f"描述关键词命中：{t}" for t in desc_terms[:3])
    if not (trigger_points or keyword_hits or desc_hits):
        return None
    raw = trigger_points + 2 * keyword_hits + desc_hits
    score = round(min(1.0, raw / 4.0), 2)
    return {"skill": entry["skill"], "score": score, "matched": matched,
            "reason": "；".join(reasons)}


def recommend(index: dict[str, Any], text: str, *,
              request_id: str = "", top_n: int = 3) -> dict[str, Any]:
    """用户描述需求 → 带溯源的候选清单（T1 §6.2 schema，T2 预埋）。"""
    query = str(text or "")
    terms = tokenize(query)
    candidates = []
    for entry in index.get("entries") or []:
        hit = _match_entry(entry, query, terms)
        if hit is not None:
            candidates.append(hit)
    candidates.sort(key=lambda c: (-c["score"], c["skill"]))
    candidates = candidates[:max(0, top_n)]
    top = candidates[0] if candidates else None
    return {"schema": SCHEMA,
            "request": {"request_id": request_id, "text": query},
            "candidates": candidates,
            "recommendation": (
                {"skill": top["skill"],
                 "trace": top["reason"]} if top else None),
            "review": {"verdict": "pending", "reviewer": None,
                       "note": "待人工复核（T3 落地接受/否决回路）"}}


class DiscoveryLedger:
    """推荐记录账本：JSONL append-only（路径注入），缺件拒绝入账。"""

    _REQUIRED = ("request", "candidates", "recommendation", "review")

    def __init__(self, path: str | Path | None = None) -> None:
        self._records: list[dict[str, Any]] = []
        self._path = Path(path) if path else None

    def record(self, rec: dict[str, Any]) -> dict[str, Any]:
        if rec.get("refused"):
            raise DiscoveryError(f"{rec['refused']}：{rec['detail']}")
        missing = [k for k in self._REQUIRED if k not in rec]
        if missing:
            raise DiscoveryError(f"DISCOVERY_INCOMPLETE：账目缺 {missing}")
        if rec["review"].get("verdict") not in REVIEW_VERDICTS:
            raise DiscoveryError("DISCOVERY_INCOMPLETE：review 词表外")
        for cand in rec["candidates"]:
            score = cand.get("score")
            if not isinstance(score, (int, float)) or not 0 <= score <= 1:
                raise DiscoveryError(
                    "DISCOVERY_SCORE_MISMATCH：候选分数不在 [0, 1]")
        if rec["candidates"] and rec["recommendation"] is None:
            raise DiscoveryError("DISCOVERY_INCOMPLETE：有候选无推荐")
        if not rec["candidates"] and rec["recommendation"] is not None:
            raise DiscoveryError("DISCOVERY_INCOMPLETE：无候选却有推荐")
        stored = copy.deepcopy(rec)
        self._records.append(stored)
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(stored, ensure_ascii=False,
                                    sort_keys=True) + "\n")
        return copy.deepcopy(stored)

    def entries(self) -> list[dict[str, Any]]:
        return [copy.deepcopy(r) for r in self._records]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="mba skill 发现层（关键词匹配）")
    parser.add_argument("query", nargs="?", default="",
                        help="用户需求描述")
    parser.add_argument("--root", default=None,
                        help="mba 仓库根目录（默认脚本所在仓根）")
    parser.add_argument("--top-n", type=int, default=3)
    parser.add_argument("--request-id", default="")
    parser.add_argument("--list", action="store_true",
                        help="只打印索引规模统计")
    args = parser.parse_args(argv)
    root = Path(args.root) if args.root else \
        Path(__file__).resolve().parents[1]
    index = load_index(root)
    if args.list:
        print(json.dumps({"schema": SCHEMA, "counts": index["counts"],
                          "total": index["total"],
                          "registry_loaded": index["registry_loaded"]},
                         ensure_ascii=False, indent=2))
        return 0
    if not args.query:
        parser.error("需提供需求描述（位置参数）或 --list")
    print(json.dumps(recommend(index, args.query,
                               request_id=args.request_id,
                               top_n=args.top_n),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
