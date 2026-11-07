#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-233/T4（trend issue #1168）：评审编排按包调用适配——现有评审流程可按包选择评委组装。

按 T1 设计（docs/plans/2026-10-26-judge-pack-layering.md §四.3/§五/§六）实现，
叠加 T3 总登记册（scripts/judge_registry.py，registry.json 单一事实源）：

  - assemble_panel(registry, packs, consumer=False)：按包组装评审团——
    pack 名（mba-brand/mba-copy/mba-visual/mba-compliance）→ 逐包展开成员；
    consumer=True 时并排附加消费者横切组（§四.3：与专家包并排互补、分开
    呈现、不换算不平均）；未知包拒绝；
  - 顺序纪律：包间按登记册固定顺序（brand→copy→visual→compliance→consumer），
    包内按登记册成员序（确定性，无墙钟无随机）；
  - preview_render()：人类可读组装预览（一行一包：包名/定位/成员数/成员清单）。

红线：本模块只做「按包选人」的纯读适配——不产分数、不写评分矩阵、不换算
消费者信号（PRD-178 口径不变）；全量 46 位组装等价于现行全量评审。零网络。
测试：tests/unit/test_prd233_t4_orchestration.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "registry.json"
PACK_ORDER = ("mba-brand", "mba-copy", "mba-visual", "mba-compliance",
              "mba-consumer")


class OrchestrationError(ValueError):
    """组装违规（未知包/空选择）。"""


def assemble_panel(registry: dict[str, Any], packs: list[str], *,
                   consumer: bool = False) -> dict[str, Any]:
    """按包组装评审团（§四.3：专家包必召回、消费者横切组并排可选）。

    packs 为包全名列表（mba-*）；consumer=True 附加 mba-consumer 横切组。
    返回 {panel_order, judges: [{pack, slug, name_cn}], totals}——成员序
    即建议发言序（确定性）。
    """
    known = {p["name"] for p in registry.get("packs", [])}
    known.add("mba-consumer")
    unknown = [p for p in packs if p not in known]
    if unknown:
        raise OrchestrationError(f"未知包：{unknown}（可用 {sorted(known)}）")
    if not packs and not consumer:
        raise OrchestrationError("至少选择一个包")
    index: dict[str, dict[str, Any]] = {}
    for pack in registry.get("packs", []):
        for skill in pack.get("skills", []):
            index[skill["name"]] = {"pack": pack["name"],
                                    "slug": skill["name"],
                                    "name_cn": skill.get("x-name_cn", ""),
                                    "positioning": skill.get("x-positioning", "")}
    crosscut = registry.get("x-crosscut") or {}
    for skill in crosscut.get("skills", []):
        index[skill["name"]] = {"pack": "mba-consumer", "slug": skill["name"],
                                "name_cn": skill.get("x-name_cn", ""),
                                "positioning": crosscut.get("positioning", "")}
    ordered_packs = [p for p in PACK_ORDER if p in packs] if packs else []
    judges: list[dict[str, Any]] = []
    for pack_name in ordered_packs:
        for skill_name, meta in sorted(index.items()):
            if meta["pack"] == pack_name:
                judges.append({"pack": pack_name, "slug": skill_name,
                               "name_cn": meta["name_cn"]})
    if consumer and crosscut:
        for skill in crosscut.get("skills", []):
            judges.append({"pack": "mba-consumer", "slug": skill["name"],
                           "name_cn": skill.get("x-name_cn", "")})
    slugs = [j["slug"] for j in judges]
    if len(slugs) != len(set(slugs)):
        raise OrchestrationError("组装出现重复评委（登记册数据异常）")
    return {
        "schema": "panel-assembly/v1",
        "panel_order": ordered_packs + (["mba-consumer"] if consumer else []),
        "judges": judges,
        "totals": {"packs": len(ordered_packs) + (1 if consumer else 0),
                   "judges": len(judges),
                   "consumer_parallel": consumer,
                   "note": "消费者信号与专家结论分开呈现、不换算不平均（PRD-178 口径）"},
    }


def preview_render(assembly: dict[str, Any]) -> str:
    """组装预览（人读）：一行一包。"""
    lines: list[str] = []
    last_pack = None
    for judge in assembly["judges"]:
        if judge["pack"] != last_pack:
            lines.append(f"[{judge['pack']}]")
            last_pack = judge["pack"]
        lines.append(f"  - {judge['slug']}（{judge['name_cn']}）")
    return "\n".join(lines)


def load_registry(path: Path | str = REGISTRY_PATH) -> dict:
    """读取登记册（T3 产物 registry.json）。"""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    import sys
    registry = load_registry()
    consumer = "--consumer" in argv
    packs = [a for a in argv if a.startswith("mba-")]
    if not packs and not consumer:
        print("用法: python3 scripts/judge_orchestration.py mba-brand [mba-copy…] [--consumer]")
        return 2
    assembly = assemble_panel(registry, packs, consumer=consumer)
    print(preview_render(assembly))
    print(f"共 {assembly['totals']['judges']} 位评委 / "
          f"{assembly['totals']['packs']} 包")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
