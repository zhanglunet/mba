# PRD-261/T5 验收试运行记录：样例评审看板端到端

- 日期：2026-10-28
- 仓库：zhanglunet/mba，分支 `trend/prd-261-t5-acceptance`（自 `trend/prd-261-t4-server-authz` 切出）
- issue：zhanglunet/trend#1309
- 全链：T1 #308（设计）→ T2 #310（review_widget_board.py 10 例）→ T3 #312（streaming 8 例）→ T4 #314（board_authz 9 例）→ 本任务 T5

## 验收标准（issue #1309）

无自由 HTML 直出；权限服务端生效；无密钥。
PRD 红线：非法属性丢弃；权限在服务端校验；不以自由 HTML 作为上线输出。

## 交付物

- `tests/unit/test_prd261_acceptance.py` —— 验收测试 9 例（不重复 T2–T4 单元路径，只验整体合同）
- 本验收记录

## 验收测试覆盖

| # | 用例 | 对应验收点 |
|---|---|---|
| 1 | test_sample_board_end_to_end_render | 样例评审数据端到端出板：parse→validate→权限过滤→净板结构符合组件合同 |
| 2 | test_no_free_html_in_board_output | 无自由 HTML 直出：净板全部字符串叶子无标签形态；组件库封闭清单无 html 组件 |
| 3 | test_injection_props_and_unknown_component_blocked | 注入非法属性（onclick/html `<script>`）+ 未知组件被拦：dropped_prop / replaced_warning 日志留痕，注入物零透传 |
| 4 | test_server_authz_dual_path_403_semantics | 服务端权限双路：渲染过滤剔除无权动作组件；绕过渲染直调 authorize_action 仍拒（403 语义）；有权会话两路一致放行；跨类型不互认 |
| 5 | test_streaming_redo_capped_at_two | 流式纠错 redo ≤ 2：重出一次成功路径 + 永远非法时 redo 封顶 2 次、整块替换 warning、非法内容零透传 |
| 6 | test_validation_log_machine_readable | 校验日志机读：逐条 dict 含 action、动作词表封闭、可 JSON 回放、node_rejected 缺必填留痕 |
| 7 | test_no_secrets_in_deliverables | 无密钥：实现两文件 + 验收测试 + 本记录对常见密钥形态（AKIA/ghp/sk-/xox/PRIVATE KEY/password 形赋值）扫描零命中 |
| 8 | test_deterministic_pipeline | 确定性：同输入两次端到端出板逐字节一致；系统提示词两次一致；输入树零副作用 |
| 9 | test_zero_network | 零网络：实现模块 AST 无网络库导入；socket 封禁（mock 抛错）下端到端照常出板 |

## 试运行结果（真实输出）

```
$ .venv/bin/python -m pytest tests/unit/test_prd261_acceptance.py -q
.........                                                                 [100%]
9 passed in 0.04s

$ .venv/bin/python -m pytest tests/unit/ -q   # 全量（含 T2–T4 前序）
....................................                                     [100%]
36 passed in 0.07s
```

## 结论

- 样例评审看板端到端走通：parse → validate → 服务端权限过滤 → 净板，样例数据零纠错。
- 无自由 HTML 直出：出板只含封闭清单组件，字符串叶子零标签形态，注入物零透传。
- 权限服务端生效：渲染过滤与 authorize_action 双路独立成立，绕过渲染直打端点默认拒。
- 无密钥：交付物密钥形态扫描零命中。
- 零网络、确定性成立。验收通过，PR 只开不合并等 review。
