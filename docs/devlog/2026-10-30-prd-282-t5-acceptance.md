# PRD-282/T5 验收试运行记录：评委包配置快照全流程演练 + 复算对照 + 文档无密钥

- 日期：2026-10-30
- trend issue：[zhanglunet/trend#1414](https://github.com/zhanglunet/trend/issues/1414)
- 中央 PRD：`trend/adopted/PRD-282-mba-judge-config-snapshot.md`
- 全链：T1 #1411（设计 `docs/plans/2026-10-29-prd-282-judge-config-snapshot.md`）→ T2 #1412（`judge_config_snapshot.py` 快照/还原/recalc_diff/审计）→ T3 #1413（`recalc_record.py` 复算记录落档）→ T4 #1414（审计断言）→ 本任务 T5
- 验收测试：`tests/unit/test_prd282_acceptance.py`（8 例，.venv/bin/python -m pytest）
- 状态：验收通过；实现类 PR 只开不合并，等用户 review

## 验收标准逐条核验（issue #1414）

### 1. 口径变更可回滚（全链通过）— 通过

虚构评委包配置全流程演练：take_snapshot（单槽指纹）→ 换口径（r1→r2）→
recalc_diff 新旧复算对照（max_abs_delta>0、逐样例差异）→ 差异写 recalc-record-v1
落档 → restore 回滚（weights/packs 与旧配置一致）。

### 2. 红线断言全过 — 通过

- 复算记录留痕：JSONL 落档可读（schema/old/new 指纹/at）
- 三类审计事件（config_changed/rolled_back/recalc_done）可导出
- 篡改检出（指纹不一致抛错）
- 零网络（交付模块无请求原语）

### 3. 文档无密钥 — 通过

交付面（judge_config_snapshot.py/recalc_record.py/验收测试）密钥形态扫描零命中
（needle 拼接构造避免自指）。

## 运行记录

`.venv/bin/python -m pytest tests/unit/test_prd282_acceptance.py -q` → 8 passed。

## 结论

PRD-282 全链（T1–T5）验收通过；只开不合并，等用户 review。
