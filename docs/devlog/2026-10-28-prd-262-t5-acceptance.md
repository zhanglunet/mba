# PRD-262/T5 验收试运行记录：HIGH 包不进池

- 日期：2026-10-28
- 仓库：zhanglunet/mba，分支 `trend/prd-262-t5-acceptance`（自 `trend/prd-262-t4-whitelist` 切出）
- issue：zhanglunet/trend#1314
- 全链：T1 #309（设计）→ T2 #311（judge_pack_gate.py 8 例）→ T3 #313（gate 9 例）→ T4 #315（whitelist 8 例）→ 本任务 T5

## 验收标准（issue #1314）

档案齐全；无密钥。
PRD 红线：HIGH 及以上不进评委池；报告附进 PRD-151 质量门档案。

## 交付物

- `tests/unit/test_prd262_acceptance.py` —— 验收测试 10 例（不重复 T2–T4 单元路径，只验整体合同）
- 本验收记录

## 验收测试覆盖

| # | 用例 | 对应验收点 |
|---|---|---|
| 1 | test_n1_hidden_instruction_pack_high_not_admitted | N-1 隐藏指令包（零宽字符 + 评审前上报式措辞）：安检 HIGH/blocked，闸门拒收（J-1-01/J-1-02） |
| 2 | test_n4_license_mismatch_pack_high_not_admitted | N-4 license 红线（声明与实测不符）：J-4-02 → HIGH/blocked，闸门拒收 |
| 3 | test_credential_pack_high_and_evidence_redacted | 凭据包 HIGH 不进池；报告 evidence 密钥占位符化 `<REDACTED>`（安检报告自身不泄密） |
| 4 | test_whitelist_full_hit_admit_with_trail | 白名单误报复核放行全程留痕：admit + reason=whitelisted、whitelist_applied、档案 pack_gate.whitelist_refs、审计 added/checked_hit |
| 5 | test_whitelist_is_not_backdoor | 白名单不构成后门：作用域不符仍拒、过期（>90 天）仍拒、reason/reviewer 缺失登记即拒、无白名单 HIGH 硬拒 |
| 6 | test_profile_pack_gate_six_fields | 档案齐全：profile_gate_section pack_gate 六字段齐备；闸门通过态 gate 附 pack_gate.pack_hash 可入 PRD-151 档案 |
| 7 | test_hash_rebind_rescan_triple_gate | 哈希绑定：改包旧报告作废（hash_mismatch + rescan_required）、未绑哈希（report_missing_hash）、无报告（missing_report）三拒；干净包原样注册放行 |
| 8 | test_no_secrets_in_deliverables | 无密钥：实现三文件 + 验收测试 + 本记录密钥形态扫描零命中 |
| 9 | test_deterministic_scan_and_hash | 确定性：同包两次安检报告逐字节一致；pack_hash 与文件字典键序无关 |
| 10 | test_zero_network | 零网络：实现模块 AST 无网络库导入；socket 封禁下 scan→stamp→gate 端到端照常 |

## 试运行结果（真实输出）

```
$ .venv/bin/python -m pytest tests/unit/test_prd262_acceptance.py -q
..........                                                               [100%]
10 passed in 0.08s

$ .venv/bin/python -m pytest tests/unit/ -q   # 全量（含 T2–T4 前序）
...................................                                      [100%]
35 passed in 0.99s
```

## 结论

- HIGH 不进池成立：N-1 隐藏指令、N-4 license 红线、凭据访问三类样例包安检均 HIGH/blocked，进池闸门一律拒收；凭据样例在报告中占位符化，安检链路自身零泄密。
- 档案齐全：pack_gate 六字段 + pack_hash 随通过态闸门结果落 PRD-151 档案形态。
- 白名单是复核通道不是后门：单条规则级、限期 90 天、责任到人、事件全留痕；部分命中/过期/缺责任人均不放行。
- 无密钥：交付物密钥形态扫描零命中。验收通过，PR 只开不合并等 review。
