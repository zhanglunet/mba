#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
judge_config_snapshot.py — PRD-282/T2 评委包配置快照最小实现（trend #1412）。

快照存储与回滚的最小内存切片：单槽快照（最近一份即"上一版"一键回滚点）+
指纹校验还原 + 新旧口径复算对照 recalc_diff + 三类审计事件（变更/回滚/复算）。

设计依据：docs/plans/2026-10-29-prd-282-judge-config-snapshot.md（PRD-282/T1，
trend #1411，T1 PR #318）。本最小实现只覆盖 T2 验收面（样例可快照可回滚、
审计可查、有测试）；文件落盘 / archive 留档 / 三类记录对账导出归 T3–T5。

红线（T1 §4，本模块逐条遵守）：
- 评分引擎是真相：本模块对评分零判定权——recalc_diff 只逐样例调用注入的
  score_fn 采分留痕，不解释分数、不回写任何正式评审结论、不触发重评；
- fail-close：指纹对不上 ⇒ 还原失败抛错告警，绝不静默半还原；
- 回滚可再回滚：单槽快照在回滚后保留不覆盖，restore 只接受显式传入的快照；
- 纯标准库、零网络、零外联；示例全虚构，无真实主机名 / IP / 账号 / 密钥。

指纹算法：config 做 canonical JSON（键排序、紧凑分隔符、UTF-8）后取
sha256 十六进制前 16 位——两次指纹相同 ⇒ 口径语义面未变。
"""

import copy
import hashlib
import json
from datetime import datetime, timezone

SNAPSHOT_SCHEMA = "judge-config-snapshot-v1"

# 审计事件枚举（变更 / 回滚 / 复算三类，append-only，只增不减）
EVENT_CONFIG_CHANGED = "config_changed"
EVENT_ROLLED_BACK = "rolled_back"
EVENT_RECALC_DONE = "recalc_done"


class FingerprintMismatchError(ValueError):
    """快照指纹校验失败（快照被篡改或损坏）——fail-close，拒绝还原。"""


# ---------------------------------------------------------------- 内部状态

_SLOT = {"snapshot": None}   # 单槽：最近一份快照即"上一版"回滚点
_CURRENT = {"config": None}  # 模块跟踪的现行口径（快照 / 还原写这里）
_EVENTS = []                 # 审计事件（append-only，进程内）


def _canonical_json(obj):
    """canonical JSON：键排序、紧凑分隔符、保留非 ASCII 原文。"""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def config_fingerprint(config):
    """口径指纹：canonical JSON 的 sha256 前 16 位（确定性，可复算）。"""
    digest = hashlib.sha256(_canonical_json(config).encode("utf-8")).hexdigest()
    return digest[:16]


def _now_iso():
    """缺省时刻：UTC ISO8601（测试请显式注入 at，保证确定性）。"""
    return datetime.now(timezone.utc).isoformat()


def _emit(event, at, **fields):
    """追加一条审计事件（字段全部可 JSON 序列化）。"""
    record = {"event": event, "at": at if at is not None else _now_iso()}
    record.update(fields)
    _EVENTS.append(record)
    return record


# ------------------------------------------------------------ 快照 / 回滚

def take_snapshot(config, taken_at):
    """口径变更确认动作前调用：对现行口径留快照（单槽，覆盖即上一版）。

    返回 judge-config-snapshot-v1 快照对象：
      {schema, config（深拷贝）, fingerprint（canonical json sha256 前 16）, taken_at}
    同时登记一条 config_changed 审计事件（快照挂在变更前，快照即变更挂点），
    并把现行口径记为 config 的深拷贝。
    """
    snapshot = {
        "schema": SNAPSHOT_SCHEMA,
        "config": copy.deepcopy(config),
        "fingerprint": config_fingerprint(config),
        "taken_at": taken_at,
    }
    _SLOT["snapshot"] = snapshot                      # 单槽：覆盖旧槽
    _CURRENT["config"] = copy.deepcopy(config)
    _emit(EVENT_CONFIG_CHANGED, taken_at,
          fingerprint=snapshot["fingerprint"], schema=SNAPSHOT_SCHEMA)
    return copy.deepcopy(snapshot)


def latest_snapshot():
    """取单槽中最近一份快照（无快照返回 None）。"""
    snap = _SLOT["snapshot"]
    return copy.deepcopy(snap) if snap is not None else None


def restore(snapshot, at=None):
    """一键回滚：指纹校验通过后把现行口径还原为快照口径。

    - 指纹校验：对 snapshot["config"] 重算指纹，与 snapshot["fingerprint"]
      不一致 ⇒ FingerprintMismatchError（fail-close，绝不静默半还原）；
    - 还原写模块跟踪的现行口径，返回还原后口径的深拷贝；
    - 登记一条 rolled_back 审计事件；单槽快照保留不覆盖（回滚可再回滚）。
    at 为还原时刻，缺省取当前 UTC 时刻（测试请显式传入保证确定性）。
    """
    if not isinstance(snapshot, dict) or \
            snapshot.get("schema") != SNAPSHOT_SCHEMA or \
            "config" not in snapshot or "fingerprint" not in snapshot:
        raise FingerprintMismatchError(
            "快照对象不合法：缺少 schema/config/fingerprint 字段")
    actual = config_fingerprint(snapshot["config"])
    if actual != snapshot["fingerprint"]:
        raise FingerprintMismatchError(
            "快照指纹校验失败：记录 %s != 重算 %s（快照疑似被篡改，拒绝还原）"
            % (snapshot["fingerprint"], actual))
    restored = copy.deepcopy(snapshot["config"])
    _CURRENT["config"] = copy.deepcopy(restored)
    _emit(EVENT_ROLLED_BACK, at,
          to_fingerprint=actual,
          snapshot_taken_at=snapshot.get("taken_at"),
          schema=SNAPSHOT_SCHEMA)
    return restored


def current_config():
    """模块跟踪的现行口径（快照 / 还原后的状态），深拷贝返回。"""
    cfg = _CURRENT["config"]
    return copy.deepcopy(cfg) if cfg is not None else None


# ---------------------------------------------------------- 复算对照（T3 面）

def recalc_diff(old_config, new_config, samples, score_fn, at=None):
    """新旧口径在样例集上复算对照：逐样例调用注入的 score_fn(sample, config)。

    返回 {diffs: [{sample, old_score, new_score, delta}], max_abs_delta, n}。
    对照不评审（硬规则）：产物只留痕，不回写正式结论、不触发重评；
    score_fn 由调用方注入（测试注入假函数，本模块不真调 LLM）。
    at 为复算完成时刻，缺省取当前 UTC 时刻（测试请显式传入）。
    """
    diffs = []
    max_abs_delta = 0.0
    for sample in samples:
        old_score = score_fn(sample, old_config)
        new_score = score_fn(sample, new_config)
        delta = new_score - old_score
        diffs.append({
            "sample": sample,
            "old_score": old_score,
            "new_score": new_score,
            "delta": delta,
        })
        if abs(delta) > max_abs_delta:
            max_abs_delta = abs(delta)
    record = {"diffs": diffs, "max_abs_delta": max_abs_delta, "n": len(samples)}
    _emit(EVENT_RECALC_DONE, at,
          n=record["n"], max_abs_delta=max_abs_delta)
    return record


# ------------------------------------------------------------------ 审计

def export_events():
    """导出审计事件（append-only 只增不减；深拷贝防外部改写）。"""
    return copy.deepcopy(_EVENTS)


def reset_state():
    """清空单槽 / 现行口径 / 审计事件（测试隔离与运维重置用）。"""
    _SLOT["snapshot"] = None
    _CURRENT["config"] = None
    del _EVENTS[:]
