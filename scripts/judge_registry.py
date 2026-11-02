#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-233/T3（trend #1167）：评委总登记册——检索 / 触发条件 / 验收例。

按 T1 设计（docs/plans/2026-10-26-judge-pack-layering.md）§四/§五/§六实现；
规范对齐 PRD-227《skill-pack-layering-spec》@1.0.0（分层五件套源头规范，
本仓只做适配，§七「引用 PRD-227 不自创」）：

  - parse_mapping()：解析 T1 §四.2 映射表（43 位专家：slug/中文名/归包理由/兼项）
    ——映射是数据不是代码（§4.2 同纪律）；consumers 3 位按 §四.3 单列横切组；
  - build_registry()：T1 映射 + site/api/judges/*.json → 规范合规总登记册——
    包条目 5 必填（name=`mba-<维度>`、positioning=§五 one-liner、version 0.1.0
    lockstep、spec_version 1.0.0、skills=成员评委）；评委条目 name=slug /
    triggers（Explicit triggers 段优先，缺省回退归包理由）/ mba 扩展字段
    （x-name_cn/x-role/x-panels/x-secondary_packs/x-positioning/x-acceptance_example/
    x-perspective_ref）；验收例按 §六.1 示例句式机械生成（「审计…期望…包召回
    包含 <slug>」），不虚构内容；consumer 横切组以 x-crosscut 单列（§四.3，
    pack_kind=cross-cutting），登记册覆盖全部 46 位；
  - validate_registry()：§4.2 必填 / §5 命名 / §6.3 semver / §6.4 对齐声明 /
    未知非 x- 字段拒 / 人数对账（26/8/4/5 + 3）/ 评委 slug 全库唯一；
  - search()：触发条件检索（triggers/定位/中文名/slug 大小写不敏感 OR）。

登记册权威源为仓库根 registry.json（§4.1）；REGISTRY.md 由其生成，双载体
同源机判（§7 防漂移）。零网络；只读；确定性（无墙钟）。
测试：tests/unit/test_prd233_t3_registry.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_DOC = REPO_ROOT / "docs" / "plans" / "2026-10-26-judge-pack-layering.md"
JUDGES_API_DIR = REPO_ROOT / "site" / "api" / "judges"
REGISTRY_PATH = REPO_ROOT / "registry.json"
REGISTRY_MD_PATH = REPO_ROOT / "REGISTRY.md"

SPEC_NAME = "skill-pack-layering-spec"
SPEC_VERSION = "1.0.0"
PACK_VERSION = "0.1.0"
PACK_PREFIX = "mba"
#: §五 四包一句话定位与典型召回场景（包级 trigger 来源）
PACK_INFO = {
    "brand": {
        "positioning": "先回答「这个品牌是谁、占什么位置」——看定位、心智占领与长期品牌资产的评委组。",
        "trigger": "新品牌定位审计、品类竞争、品牌资产与可投性评估",
    },
    "copy": {
        "positioning": "看品牌怎么说——名字、话术、发布会与内容表达能否把定位说清、说动人。",
        "trigger": "命名与 slogan 评审、发布会与直播话术、创始人 IP 表达",
    },
    "visual": {
        "positioning": "看品牌长什么样——产品与视觉识别是否配得上定位，第一眼是否成立。",
        "trigger": "产品设计与包装评审、视觉识别系统、高端 / 时尚品牌审计",
    },
    "compliance": {
        "positioning": "看品牌经不经得起查——安全、监管、危机与信任治理视角下的品牌成色。",
        "trigger": "政企与安全行业品牌、监管敏感行业、出海合规与危机议题",
    },
}
#: §四.3 消费者横切组（不进四包）
CROSSCUT_INFO = {
    "positioning": "受众侧的一面镜子——第一印象、购买意愿、价格直觉、信任犹豫与表达欲。",
    "members": ("first-glance-shopper", "homework-buyer", "brand-skeptic"),
    "trigger": "与任一 sub-pack 并行，给专家结论加消费者校验（C1–C5 题组）",
}
EXPECTED_COUNTS = {"brand": 26, "copy": 8, "visual": 4, "compliance": 5}
PACK_REQUIRED_FIELDS = ("name", "positioning", "version", "spec_version", "skills")
SKILL_REQUIRED_FIELDS = ("name", "triggers")
SPEC_OPTIONAL_FIELDS = ("description", "keywords", "stage", "roles", "depends_on",
                        "status", "license", "homepage", "examples")
RE_PACK_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)+$")
RE_JUDGE_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RE_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
PACK_HEADING_MAP = (("品牌包", "brand"), ("文案包", "copy"), ("视觉包", "visual"),
                    ("合规包", "compliance"))


class RegistryError(ValueError):
    """登记册输入/结构违规。"""


def parse_mapping(design_text: str) -> dict[str, dict]:
    """解析 T1 §四.2 映射表 → {slug: {pack, positioning, secondary}}。

    表头 `| slug | 中文名 | 归包理由 | 兼项 |`；包归属由最近的 `#### <X>包` 小节
    标题决定（映射是数据不是代码——文档为单一来源）。
    """
    mapping: dict[str, dict] = {}
    current_pack: str | None = None
    for line in design_text.splitlines():
        if line.startswith("#### "):
            heading = line[5:]
            current_pack = next((code for key, code in PACK_HEADING_MAP if key in heading),
                                None)
            continue
        if line.startswith("## ") and not line.startswith("###"):
            current_pack = None  # 出 §四
            continue
        if not current_pack or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[0] in ("slug", "---", "") or set(cells[0]) <= {"-", ":"}:
            continue
        slug, _name_cn, positioning, secondary = cells
        if slug == "slug" or slug.startswith("-"):
            continue
        secondary_packs = []
        for token in re.split(r"[、,，]", secondary or "—"):
            token = token.strip().rstrip("（.*?）").strip("()")
            for key, code in PACK_HEADING_MAP:
                if token and token.startswith(key[:2]):
                    secondary_packs.append(code)
                    break
        mapping[slug] = {"pack": current_pack, "positioning": positioning,
                         "secondary": secondary_packs}
    return mapping


def _explicit_triggers(description: str) -> str | None:
    """评委 description 的「Explicit triggers:」段（消费者人设带，逐字截取）。"""
    if "Explicit triggers:" not in description:
        return None
    segment = description.split("Explicit triggers:", 1)[1]
    segment = re.split(r"\n\s*\n|Do not activate", segment)[0]
    text = " ".join(part.strip() for part in segment.splitlines() if part.strip())
    return text.strip(" 　") or None


def load_judges(judges_dir: Path | str = JUDGES_API_DIR) -> dict[str, dict]:
    """site/api/judges/*.json → {slug: judge json}（缺 slug 拒绝）。"""
    root = Path(judges_dir)
    judges: dict[str, dict] = {}
    for file in sorted(root.glob("*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        slug = data.get("slug") or file.stem
        judges[slug] = data
    return judges


def build_registry(design_text: str, judges: dict[str, dict]) -> dict:
    """T1 映射 + 评委 JSON → 规范合规总登记册（确定性；人数对账不过即报错）。"""
    mapping = parse_mapping(design_text)
    errors: list[str] = []
    for slug in mapping:
        if slug not in judges:
            errors.append(f"{slug}: T1 映射表有但评委 JSON 缺（site/api/judges/）")
    for slug in judges:
        if slug not in mapping and slug not in CROSSCUT_INFO["members"]:
            errors.append(f"{slug}: 评委 JSON 有但 T1 映射表未登记（不得静默缺席）")
    counts: dict[str, int] = {}
    for slug, info in mapping.items():
        counts[info["pack"]] = counts.get(info["pack"], 0) + 1
    for pack, expected in EXPECTED_COUNTS.items():
        if counts.get(pack, 0) != expected:
            errors.append(f"{pack}: 实际 {counts.get(pack, 0)} 人 ≠ T1 设计 {expected} 人")
    crosscut_present = [s for s in CROSSCUT_INFO["members"]
                        if s in judges and s not in mapping]
    if len(crosscut_present) != len(CROSSCUT_INFO["members"]):
        errors.append(f"消费者横切组不全：{CROSSCUT_INFO['members']}（T1 §四.3）")
    if errors:
        raise RegistryError("; ".join(errors))

    packs_out: dict[str, list[dict]] = {}
    for slug in sorted(mapping):
        info = mapping[slug]
        judge = judges[slug]
        triggers = _explicit_triggers(judge.get("description", "")) \
            or info["positioning"]
        pack_code = info["pack"]
        entry = {
            "name": slug,
            "triggers": triggers,
            "x-name_cn": judge.get("name_cn", ""),
            "x-role": "consumer" if slug in CROSSCUT_INFO["members"] else "expert",
            "x-panels": list(judge.get("panels", [])),
            "x-secondary_packs": info["secondary"],
            "x-positioning": info["positioning"],
            "x-acceptance_example": (
                f"审计任务命中「{PACK_INFO[pack_code]['trigger']}」时，"
                f"期望 {PACK_PREFIX}-{pack_code} 包召回包含 {slug}"),
            "x-perspective_ref": f"perspectives/{slug}-perspective/",
        }
        packs_out.setdefault(pack_code, []).append(entry)
    crosscut_members = []
    for slug in CROSSCUT_INFO["members"]:
        judge = judges[slug]
        crosscut_members.append({
            "name": slug,
            "triggers": _explicit_triggers(judge.get("description", ""))
            or CROSSCUT_INFO["positioning"],
            "x-name_cn": judge.get("name_cn", ""),
            "x-role": "consumer",
            "x-panels": list(judge.get("panels", [])),
            "x-secondary_packs": [],
            "x-positioning": CROSSCUT_INFO["positioning"],
            "x-acceptance_example": (
                f"专家包结论产出后追加消费者校验时，期望 consumer 横切组召回 {slug}"),
            "x-perspective_ref": f"perspectives/{slug}-perspective/",
        })

    packs = []
    for code in ("brand", "copy", "visual", "compliance"):
        packs.append({
            "name": f"{PACK_PREFIX}-{code}",
            "positioning": PACK_INFO[code]["positioning"],
            "version": PACK_VERSION,
            "spec_version": SPEC_VERSION,
            "skills": packs_out.get(code, []),
            "x-pack_trigger": PACK_INFO[code]["trigger"],
            "x-pack_kind": "sub-pack",
        })
    return {
        "schema": "judge-pack-registry/v1",
        "alignment": f"{SPEC_NAME}@{SPEC_VERSION}",
        "alignment_note": (
            f"技能包分层规范：{SPEC_NAME}@{SPEC_VERSION}（livepowers PRD-227/T1 草案）。"
            "本登记册为评委归属与检索的单一事实源（规范 §7）；映射数据源为 T1 "
            "docs/plans/2026-10-26-judge-pack-layering.md §四.2（映射是数据不是代码）。"
        ),
        "borrowed_form": (
            "「分层 + 总登记册」组织形态借鉴 AgriciDaniel/claude-seo（MIT License，"
            "Copyright (c) Daniel Agrici，https://github.com/AgriciDaniel/claude-seo）："
            "只复用形态，未复用其代码与文本。"
        ),
        "version_policy": f"全库 lockstep {PACK_VERSION}（规范 §6.3 允许的本地政策；"
                          "包内评委增删或定位变更至少升 MINOR）",
        "packs": packs,
        "x-crosscut": {
            "name": f"{PACK_PREFIX}-consumer",
            "pack_kind": "cross-cutting",
            "positioning": CROSSCUT_INFO["positioning"],
            "trigger": CROSSCUT_INFO["trigger"],
            "skills": crosscut_members,
        },
    }


def validate_registry(registry: dict) -> list[str]:
    """PRD-227 §4/§5/§6 校验（packs 数组部分），返回错误清单（空 = 通过）。"""
    errors: list[str] = []
    if registry.get("alignment") != f"{SPEC_NAME}@{SPEC_VERSION}":
        errors.append(f"alignment 必须为 {SPEC_NAME}@{SPEC_VERSION}（§6.4）")
    packs = registry.get("packs")
    if not isinstance(packs, list) or not packs:
        errors.append("packs 必须为非空数组（§4.1）")
        return errors
    pack_names: set[str] = set()
    judge_names: set[str] = set()
    for pack in packs:
        label = f"包 {pack.get('name', '?')}"
        for field in PACK_REQUIRED_FIELDS:
            if field not in pack:
                errors.append(f"{label} 缺必填字段 {field}（§4.2）")
        name = pack.get("name")
        if not isinstance(name, str) or not RE_PACK_NAME.match(name or ""):
            errors.append(f"{label} 包名必须为 <库前缀>-<领域词>（§5.1）")
        elif name in pack_names:
            errors.append(f"包名重复: {name}")
        pack_names.add(name or "")
        if not (isinstance(pack.get("positioning"), str) and pack["positioning"].strip()):
            errors.append(f"{label} positioning 必须为一句话定位（§4.2）")
        if not RE_SEMVER.match(str(pack.get("version", ""))):
            errors.append(f"{label} version 必须为 semver（§6.3）")
        if pack.get("spec_version") != SPEC_VERSION:
            errors.append(f"{label} spec_version 必须为 {SPEC_VERSION}（§6.4）")
        allowed_pack = set(PACK_REQUIRED_FIELDS) | set(SPEC_OPTIONAL_FIELDS)
        for key in pack:
            if key not in allowed_pack and not key.startswith("x-"):
                errors.append(f"{label} 含未声明的非 x- 字段: {key}（§4.3）")
        for skill in pack.get("skills") or []:
            sname = skill.get("name")
            slabel = f"评委 {sname}"
            for field in SKILL_REQUIRED_FIELDS:
                if field not in skill:
                    errors.append(f"{slabel}（{label}）缺必填字段 {field}（§4.2）")
            if not isinstance(sname, str) or not RE_JUDGE_NAME.match(sname or ""):
                errors.append(f"{slabel} 名必须为全小写 kebab-case（§5.2）")
            elif sname in judge_names:
                errors.append(f"评委名重复: {sname}（§5.2 全库唯一）")
            judge_names.add(sname or "")
            triggers = skill.get("triggers")
            if not (isinstance(triggers, str) and triggers.strip()):
                errors.append(f"{slabel} triggers 必须为非空一句话（§4.2）")
            allowed_skill = set(SKILL_REQUIRED_FIELDS) | set(SPEC_OPTIONAL_FIELDS)
            for key in skill:
                if key not in allowed_skill and not key.startswith("x-"):
                    errors.append(f"{slabel} 含未声明的非 x- 字段: {key}（§4.3）")
    return errors


def total_judges(registry: dict) -> int:
    """覆盖数 = 四包成员 + 消费者横切组（验收：覆盖全部 46 位）。"""
    count = sum(len(p.get("skills", [])) for p in registry.get("packs", []))
    count += len((registry.get("x-crosscut") or {}).get("skills", []))
    return count


def search(registry: dict, query: str, min_len: int = 2) -> list[dict]:
    """触发条件检索：triggers/定位/中文名/slug 大小写不敏感 OR，按 (pack, name) 排序。"""
    terms = [t for t in re.split(r"[\s/／,，、]+", (query or "").strip()) if t]
    if not terms or min(len(t) for t in terms) < min_len:
        raise RegistryError(f"检索词至少 {min_len} 个字符")
    hits: list[dict] = []
    sources = [("packs", p) for p in registry.get("packs", [])]
    crosscut = registry.get("x-crosscut")
    if crosscut:
        sources.append(("x-crosscut", crosscut))
    for source, pack in sources:
        for skill in pack.get("skills", []):
            haystack = " ".join([
                skill.get("triggers", ""), skill.get("x-positioning", ""),
                skill.get("x-name_cn", ""), skill.get("name", ""),
            ]).lower()
            if any(term.lower() in haystack for term in terms):
                hits.append({"pack": pack.get("name", source), "name": skill["name"],
                             "name_cn": skill.get("x-name_cn", ""),
                             "triggers": skill.get("triggers", ""),
                             "positioning": skill.get("x-positioning", "")})
    return sorted(hits, key=lambda h: (h["pack"], h["name"]))


def render_md(registry: dict) -> str:
    """由权威源生成人读总表（REGISTRY.md 由此产出，禁止手改，双载体同源 §7）。"""
    lines: list[str] = []
    lines.append("# mba 评委包总登记册（REGISTRY）")
    lines.append("")
    lines.append(f"> PRD-233/T3（trend #1167）落地。机读权威源：[`registry.json`](registry.json)"
                 f"（{len(registry.get('packs', []))} 包 + 消费者横切组 / 共 {total_judges(registry)} 位评委）；"
                 "本文件由其生成——生成命令 `python3 scripts/judge_registry.py --render > REGISTRY.md`，"
                 "**禁止手改本文件**，两载体不一致即漂移（规范 §7，测试机判）。")
    lines.append(">")
    lines.append(f"> {registry.get('alignment_note', '')}")
    lines.append(">")
    lines.append(f"> {registry.get('borrowed_form', '')}")
    lines.append("")
    lines.append("检索：`python3 scripts/judge_registry.py <触发词…>`（例：`定位`、`slogan`、"
                 "`监管`、`消费者`）。")
    lines.append("")
    sections = [("packs", p) for p in registry.get("packs", [])]
    if registry.get("x-crosscut"):
        sections.append(("x-crosscut", registry["x-crosscut"]))
    for source, pack in sections:
        kind_note = "" if source == "packs" else "（横切组，非 sub-pack）"
        lines.append(f"## {pack['name']}{kind_note} — {pack['positioning']}")
        lines.append("")
        lines.append(f"version {pack.get('version', '—')} ｜ spec_version "
                     f"{pack.get('spec_version', '—')} ｜ 整包召回时机：{pack.get('x-pack_trigger', pack.get('trigger', '—'))}")
        lines.append("")
        lines.append("| 评委 | 触发条件 | 定位（T1 归包理由） | panels |")
        lines.append("|---|---|---|---|")
        for skill in pack.get("skills", []):
            lines.append(f"| **{skill['name']}**（{skill.get('x-name_cn', '')}） "
                         f"| {skill.get('triggers', '')} | {skill.get('x-positioning', '')} "
                         f"| {'、'.join(skill.get('x-panels', [])) or '—'} |")
        lines.append("")
    lines.append(f"版本政策：{registry.get('version_policy', '')}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    import sys
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if "--render" in argv:
        print(render_md(registry), end="")
        return 0
    if "--check" in argv:
        errors = validate_registry(registry)
        print("registry OK" if not errors else "; ".join(errors))
        return 0 if not errors else 1
    query = " ".join(argv)
    if not query:
        print("用法: python3 scripts/judge_registry.py <检索词…>（如: 定位 slogan 监管）")
        print(f"条目统计: {len(registry.get('packs', []))} 包 / {total_judges(registry)} 位评委")
        return 0
    try:
        hits = search(registry, query)
    except RegistryError as exc:
        print(f"检索失败: {exc}")
        return 2
    for hit in hits:
        print(f"[{hit['pack']}] {hit['name']}（{hit['name_cn']}）")
        print(f"  触发: {hit['triggers']}")
        print(f"  定位: {hit['positioning']}")
    print(f"命中 {len(hits)} 条")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
