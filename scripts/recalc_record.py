#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
recalc_record.py — PRD-282/T3 复算记录正式化（trend #1413）。

把 T2 recalc_diff（judge_config_snapshot.py，trend #1412）产出的双口径差异
固化为机读的 recalc-record-v1 复算记录，并 JSONL 追加落档、全量读回——
复算留痕（红线：对照不评审，记录只入库留痕与可视化，不回写任何正式
评审结论、不触发重评）。

设计依据：docs/plans/2026-10-29-prd-282-judge-config-snapshot.md（PRD-282/T1，
trend #1411，T1 PR #318）§3.4。本最小实现覆盖 T3 验收面（复算记录字段齐全、
有测试）；漂移可视化（维度 × 样例热力表）与三类记录对账导出归 T4–T5。

接口（与 T2 的衔接面）：
- write_recalc_record(diff, old_fp, new_fp, at) → recalc-record-v1 记录：
  diff 即 T2 recalc_diff 的返回 {diffs: [...], max_abs_delta, n}；
  记录 {schema, old_fingerprint, new_fingerprint, n, max_abs_delta, diffs, at}，
  其中 diffs 截断至前 50 条（DIFFS_LIMIT，防超长样例集撑爆档案行；
  n 仍为全量样例数，截断不丢总数）；
- append_recalc(record, audit_path)：记录以 JSONL 追加落档（单行一记录，
  UTF-8、键排序、ensure_ascii=False——确定性字节序，append-only 只增不改）；
- read_recalcs(audit_path)：全量读回记录列表（空/不存在 → []）。

红线（T1 §4，本模块逐条遵守）：
- 对照不评审：本模块只做记录固化与落档，零评分判定、零结论回写、零重评触发；
- fail-close：diff/record 结构非法即抛错，绝不写半截记录；审计行损坏读回时
  抛错（带行号），绝不静默跳过——审计完整性优先；
- 纯标准库、零网络、零外联；不真调 LLM（评分由调用方注入，见 T2 recalc_diff）；
- 示例全虚构（评委包口径 / 样例品牌 / 分数），无真实主机名 / IP / 账号 / 密钥。
"""

import copy
import json
import os

RECALC_RECORD_SCHEMA = "recalc-record-v1"

# diffs 截断上限：档案行只留前 50 条逐样例差异（n 仍记全量样例数）
DIFFS_LIMIT = 50


class RecalcRecordError(ValueError):
    """复算记录结构非法（写入侧拒收 / 读回侧损坏）——fail-close。"""


def _require_str(value, name):
    if not isinstance(value, str) or value == "":
        raise RecalcRecordError("%s 须为非空字符串，收到：%r" % (name, value))
    return value


def write_recalc_record(diff, old_fp, new_fp, at):
    """把 T2 recalc_diff 产出固化为 recalc-record-v1 复算记录（纯函数，不落盘）。

    - diff：T2 recalc_diff 返回值 {diffs: [{sample, old_score, new_score, delta}],
      max_abs_delta, n}；结构非法即抛 RecalcRecordError（fail-close）；
    - old_fp / new_fp：新旧口径指纹（T2 config_fingerprint 的输出，16 位十六进制）；
    - at：复算完成时刻（ISO8601 字符串，由调用方显式传入保证确定性）；
    - diffs 深拷贝并截断至前 DIFFS_LIMIT(50) 条；n / max_abs_delta 取 diff 全量值。

    返回 {schema: "recalc-record-v1", old_fingerprint, new_fingerprint, n,
    max_abs_delta, diffs, at}——全部可 JSON 序列化；同输入产出逐字段全等
    （确定性：不掺任何当前时刻 / 随机源）。
    """
    _require_str(old_fp, "old_fingerprint")
    _require_str(new_fp, "new_fingerprint")
    _require_str(at, "at")
    if not isinstance(diff, dict):
        raise RecalcRecordError("diff 须为 recalc_diff 的返回 dict，收到：%s" % type(diff).__name__)
    raw_diffs = diff.get("diffs")
    if not isinstance(raw_diffs, list) or any(not isinstance(d, dict) for d in raw_diffs):
        raise RecalcRecordError("diff['diffs'] 须为对象列表（逐样例差异，空样例集允许为空列表）")
    if "n" not in diff or "max_abs_delta" not in diff:
        raise RecalcRecordError("diff 缺少 n / max_abs_delta 字段（须为 T2 recalc_diff 原始产出）")

    return {
        "schema": RECALC_RECORD_SCHEMA,
        "old_fingerprint": old_fp,
        "new_fingerprint": new_fp,
        "n": diff["n"],
        "max_abs_delta": diff["max_abs_delta"],
        "diffs": copy.deepcopy(raw_diffs[:DIFFS_LIMIT]),
        "at": at,
    }


def append_recalc(record, audit_path):
    """复算记录 JSONL 追加落档（append-only：只追加、不改不删既有行）。

    - record：write_recalc_record 的产出；schema 非 recalc-record-v1 拒收
      （fail-close，绝不写半截 / 非本 schema 的行）；
    - audit_path：JSONL 审计档路径；父目录不存在则自动创建（0700 语义交由
      调用方环境 umask，本模块不越权 chmod）；
    - 单行序列化：UTF-8、键排序、ensure_ascii=False、紧凑分隔符——同记录
      同字节（确定性），行尾一个 \\n。
    """
    if not isinstance(record, dict) or record.get("schema") != RECALC_RECORD_SCHEMA:
        raise RecalcRecordError("record 非 %s，拒绝落档" % RECALC_RECORD_SCHEMA)
    _require_str(audit_path, "audit_path")

    parent = os.path.dirname(os.path.abspath(audit_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    line = json.dumps(record, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    with open(audit_path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def read_recalcs(audit_path):
    """全量读回复算记录列表（append 顺序返回；空档 / 不存在 → []）。

    fail-close：任何一行损坏（非合法 JSON 或 schema 不符）即抛
    RecalcRecordError（带行号），绝不静默跳过——审计完整性优先。
    """
    _require_str(audit_path, "audit_path")
    if not os.path.exists(audit_path):
        return []
    records = []
    with open(audit_path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue  # 纯空行（末尾换行等）不算损坏
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise RecalcRecordError("审计档第 %d 行损坏（非合法 JSON）：%s" % (lineno, exc))
            if not isinstance(record, dict) or record.get("schema") != RECALC_RECORD_SCHEMA:
                raise RecalcRecordError(
                    "审计档第 %d 行 schema 非 %s，拒绝读回" % (lineno, RECALC_RECORD_SCHEMA))
            records.append(record)
    return records
