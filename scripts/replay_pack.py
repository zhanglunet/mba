#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD-310/T2 评审结论重放包·replay-pack/v1 最小实现（trend issue #1562）。

设计依据 docs/plans/2026-11-07-prd-310-mba-review-replay-pack-t1.md（T1，PR #344）：
实现其 §1 统一 schema（输入快照指纹 + 决策 + 输出 + 重放记录）、§3 重放校验判据
与 append-only 账本。纯加法：不改动 judge_orchestration / judge_registry 的任何
行为，调用方在评审编排出口自行落包。

覆盖边界（诚实声明）：
- **本模块重放面 = 确定性编排面**：评审批次由登记册 + 包选择确定性决定
  （assemble_panel，PRD-233 已并），同登记册同选择必得同一 panel——这部分
  完全可重放。
- **评分与理由由评委技能（LLM）产出**，不属于逐字节可重放面；mba 红线
  「口径走快照」：评审结论落档后，重放对照走评审记录快照比对（T3/T5 的
  闸门与验收在此口径上钉死）。本模块不为评分伪造确定性。

核心纪律（T1 §1 字段纪律）：
- **append-only**：账本只追加，成败都记，不提供删除/截断面。
- **二值重放结论**：MATCH / MISMATCH；MISMATCH 不静默。
- **错误码封闭词表**：穷举于 ``ERROR_CODES``。
- **重放面只读**：零写盘、零网络、不改评审记录与 findings。
- **指纹算法版本化**：fpv1 = 规范化 JSON 的 SHA-256 前 16 位。

示例作品/评委全为占位。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

#: 重放包 schema（T1 §1，固定）
REPLAY_PACK_SCHEMA_VERSION = "replay-pack/v1"

#: 指纹算法标识（版本化；算法变更即换新标识，历史账本不重算为一致）
FINGERPRINT_ALGO = "fpv1"

#: 重放期望与状态（封闭）
REPLAY_EXPECT_BYTE_IDENTICAL = "byte-identical"
REPLAY_MATCH = "MATCH"
REPLAY_MISMATCH = "MISMATCH"
REPLAY_NOT_RUN = "NOT_RUN"

#: 封闭错误码词表（穷举；新增必须改本表）
ERROR_CODES = (
    "REPLAY_INPUT_REQUIRED",
    "REPLAY_DECISION_FIELDS_REQUIRED",
    "REPLAY_OUTPUT_REQUIRED",
    "REPLAY_COMMAND_INVALID",
    "REPLAY_INPUT_MISMATCH",
    "REPLAY_MISMATCH",
    "REPLAY_LEDGER_NOT_APPENDABLE",
    # T3 闸门码（trend #1563）：重放产物进决策面前的唯一放行口径
    "REPLAY_GATE_REFUSED",
)


class ReplayPackError(ValueError):
    """replay-pack/v1 纪律错误；``code`` 必须取自封闭词表 ERROR_CODES。"""

    def __init__(self, code: str, message: str) -> None:
        if code not in ERROR_CODES:
            raise ValueError(f"未登记错误码：{code}（词表={ERROR_CODES}）")
        super().__init__(f"{code}: {message}")
        self.code = code


def canonical_bytes(payload: Any) -> bytes:
    """规范化 JSON 字节（sort_keys + 紧凑分隔符 + UTF-8）；指纹与逐字节比对都用它。"""
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def fingerprint(payload: Any) -> str:
    """fpv1 指纹：canonical_bytes 的 SHA-256 前 16 位，前缀带算法标识。"""
    return f"{FINGERPRINT_ALGO}:" + hashlib.sha256(canonical_bytes(payload)).hexdigest()[:16]


def build_replay_pack(
    *,
    action: str,
    inputs: dict[str, Any],
    decision: dict[str, Any],
    output: dict[str, Any],
    replay_command: str,
) -> dict[str, Any]:
    """组装 replay-pack/v1 包；字段纪律不满足即报错不猜（错误码封闭）。"""
    if not inputs:
        raise ReplayPackError("REPLAY_INPUT_REQUIRED", "inputs 为空，没有可指纹化的输入")
    missing = [
        k
        for k in ("chosen", "why", "rules_version")
        if k not in decision or decision[k] in (None, "")
    ]
    if missing:
        raise ReplayPackError(
            "REPLAY_DECISION_FIELDS_REQUIRED", f"decision 缺字段：{missing}"
        )
    if "result" not in output or "key_numbers" not in output:
        raise ReplayPackError("REPLAY_OUTPUT_REQUIRED", "output 需要 result 与 key_numbers")
    if not isinstance(replay_command, str) or not replay_command:
        raise ReplayPackError("REPLAY_COMMAND_INVALID", "replay.command 必须是非空字符串")
    return {
        "schema_version": REPLAY_PACK_SCHEMA_VERSION,
        "action": action,
        "input": {"snapshot_fingerprint": fingerprint(inputs), "inputs": inputs},
        "decision": dict(decision),
        "output": {"result": output["result"], "key_numbers": output["key_numbers"]},
        "replay": {
            "command": replay_command,
            "expect": REPLAY_EXPECT_BYTE_IDENTICAL,
            "status": REPLAY_NOT_RUN,
        },
    }


class ReplayLedger:
    """append-only 账本：JSONL 只追加，不提供修改/删除/截断面。"""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def append(self, pack: dict[str, Any]) -> None:
        """追加一包；成败都记。"""
        try:
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(canonical_bytes(pack).decode("utf-8") + "\n")
        except OSError as exc:
            raise ReplayPackError("REPLAY_LEDGER_NOT_APPENDABLE", str(exc)) from exc

    def read_all(self) -> list[dict[str, Any]]:
        """按追加序读全部包；文件不存在视为空账本。"""
        try:
            raw = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        return [json.loads(line) for line in raw.splitlines() if line]

    def bytes_now(self) -> bytes | None:
        """当前账本字节（供审计/测试断言 verify 零写盘）。"""
        try:
            return self._path.read_bytes()
        except FileNotFoundError:
            return None


def verify_replay(
    pack: dict[str, Any],
    rerun: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """原样重跑：``rerun(inputs, decision)`` 的输出视图与账本 output 逐字节比对。

    只读：不改 pack、不写任何文件。契约：``rerun`` 返回与账本 output 同形状的
    视图（{"result", "key_numbers"}）——动作出口用同一套 view 函数规范化
    （见 ``output_view_of_panel_assembly``），保证记录与重放同口径。
    """
    rerun_output = rerun(pack["input"]["inputs"], pack["decision"])
    expected = canonical_bytes(
        {"result": pack["output"]["result"], "key_numbers": pack["output"]["key_numbers"]}
    )
    actual = canonical_bytes(
        {"result": rerun_output.get("result"), "key_numbers": rerun_output.get("key_numbers")}
    )
    matched = expected == actual
    return {
        "action": pack["action"],
        "input_snapshot_fingerprint": pack["input"]["snapshot_fingerprint"],
        "status": REPLAY_MATCH if matched else REPLAY_MISMATCH,
        "expect": pack["replay"]["expect"],
        "fingerprint_algo": FINGERPRINT_ALGO,
        "evidence": None if matched else {"ledger": pack["output"], "rerun": rerun_output},
    }


def output_view_of_panel_assembly(assembly: dict[str, Any]) -> dict[str, Any]:
    """评审批次产出 → 重放包 output 视图；记录与重放共用同一规范化。"""
    return {
        "result": {
            "schema": assembly.get("schema"),
            "panel_order": list(assembly.get("panel_order") or []),
            "judge_slugs": [j["slug"] for j in (assembly.get("judges") or [])],
        },
        "key_numbers": dict(assembly.get("totals") or {}),
    }


def pack_from_panel_assembly(
    registry: dict[str, Any],
    work_snapshot: Any,
    packs: list[str],
    consumer: bool,
    assembly: dict[str, Any],
) -> dict[str, Any]:
    """把一次 ``assemble_panel`` 的产出装订成重放包（PRD-310 关键动作接入）。

    input 存作品快照指纹（作品原文不贴整包）+ 评委登记册指纹（评委包版本）；
    decision.chosen = 包选择与横切开关；rules_version 取登记册 schema。
    零改动 judge_orchestration 模块本身。
    """
    if not (assembly.get("judges") or []):
        raise ReplayPackError("REPLAY_OUTPUT_REQUIRED", "本次组装无评委可装订")
    return build_replay_pack(
        action="panel_assembly",
        inputs={
            "work_snapshot_fingerprint": fingerprint(work_snapshot),
            "registry_fingerprint": fingerprint(registry),
            "packs": list(packs or []),
            "consumer": bool(consumer),
        },
        decision={
            "chosen": f"packs={','.join(assembly.get('panel_order') or [])}",
            "why": "按包组装（PRD-233 §四.3：专家包必召回、消费者横切组并排可选）；"
                   "评分与理由属 LLM 面，重放对照走评审记录快照（口径走快照红线）",
            "rules_version": str(registry.get("schema") or "mba-judge-registry/v1"),
        },
        output=output_view_of_panel_assembly(assembly),
        replay_command=(
            "rerun: judge_orchestration.assemble_panel(原登记册, 账本 packs, "
            "consumer=账本开关)——先验登记册/作品快照指纹一致"
        ),
    )


def verify_panel_replay(
    pack: dict[str, Any],
    registry: dict[str, Any],
    work_snapshot: Any,
    assemble_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """编排重放专用：先验登记册/作品快照双指纹一致，再原样重跑并逐字节比对。

    任一指纹不一致 → REPLAY_INPUT_MISMATCH 显形（重放的不是当时的登记册或
    作品快照）；一致 → assemble_fn(registry, packs, consumer=…) 过同一视图
    规范化后与账本逐字节比对。全程只读、不改评审记录。
    """
    inputs = pack["input"]["inputs"]
    checks = (
        ("registry_fingerprint", fingerprint(registry)),
        ("work_snapshot_fingerprint", fingerprint(work_snapshot)),
    )
    for name, actual in checks:
        if inputs.get(name) != actual:
            return {
                "action": pack["action"],
                "input_snapshot_fingerprint": pack["input"]["snapshot_fingerprint"],
                "status": REPLAY_MISMATCH,
                "expect": pack["replay"]["expect"],
                "fingerprint_algo": FINGERPRINT_ALGO,
                "evidence": {
                    "reason": "REPLAY_INPUT_MISMATCH",
                    "field": name,
                    "ledger": inputs.get(name),
                    "rerun": actual,
                },
            }
    assembly = assemble_fn(registry, list(inputs.get("packs") or []),
                           consumer=bool(inputs.get("consumer")))
    view = output_view_of_panel_assembly(assembly)
    return verify_replay(pack, lambda _inputs, _decision: view)

# ---------------------------------------------------------------------------
# T3 重放校验闸门（trend 1563）：消费 T2 verify 产物，一票否决进决策面
# ---------------------------------------------------------------------------

#: 闸门放行的唯一状态
GATE_ALLOWED_STATUS = REPLAY_MATCH


def replay_gate(verify_result: dict[str, Any]) -> dict[str, Any]:
    """重放校验闸门：**决策面在消费账本/重放产物前必须过本闸**。

    规则（一票否决）：status == MATCH → 放行；其余（MISMATCH/被篡改/未知
    status）→ 拒绝，且拒绝时**不得使用任何账本或重放数据**（调用方改走人工
    或拒绝路径）。拒绝本身显形（code=REPLAY_GATE_REFUSED + 原始 evidence），
    不静默给新数——账本/重放对不上时，失败证据就是失败证据，不伪造成功。
    """
    if not isinstance(verify_result, dict) or "status" not in verify_result:
        return {"allow": False, "code": "REPLAY_GATE_REFUSED",
                "status": None,
                "evidence": {"reason": "verify 产物缺失或非 dict（闸门宁拒勿漏）"}}
    status = verify_result.get("status")
    if status == GATE_ALLOWED_STATUS:
        return {"allow": True, "code": None, "status": status,
                "action": verify_result.get("action"),
                "fingerprint": verify_result.get("input_snapshot_fingerprint")}
    return {"allow": False, "code": "REPLAY_GATE_REFUSED", "status": status,
            "evidence": verify_result.get("evidence"),
            "fingerprint": verify_result.get("input_snapshot_fingerprint")}


def require_gate(verify_result: dict[str, Any]) -> dict[str, Any]:
    """闸门的异常形态：拒绝即抛 ReplayPackError(REPLAY_GATE_REFUSED)——
    供以异常为纪律的决策面使用；放行原样返回 verify_result。"""
    verdict = replay_gate(verify_result)
    if not verdict["allow"]:
        raise ReplayPackError("REPLAY_GATE_REFUSED",
                              json.dumps({"status": verdict.get("status"),
                                          "evidence": verdict.get("evidence")},
                                         ensure_ascii=False))
    return verify_result
