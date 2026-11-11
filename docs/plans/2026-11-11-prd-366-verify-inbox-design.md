# PRD-366/T1：评审复核收件箱设计（复核待办的收口，零自动执行）

> trend issue #1645。对应 PRD-366（2026-11-11 日报第 9 条，用户「继续」按既定流水线立项）。
> 设计日：2026-11-11 · 目标仓库：zhanglunet/mba
> 状态：T1 设计草案，待评审。仅设计文档（纯加法 .md）；收件箱内核（T2）、批阅闸门（T3）、划界断言（T4）、全链验收（T5）按本设计后续落地。
> 示例全部虚构占位，不出现真实主机名、IP、账号、密钥。

## 0. 红线

| # | 红线 | 落地方式 |
|---|---|---|
| R1 | **收件箱零自动执行** | approve/reject 只改条目状态留痕——**零分数写、零撤回触发、零转换重跑**：复核结论是人定性，动作走既有流程；INBOX_AUTO_EXEC_ATTEMPT 拒绝动作载荷 |
| R2 | **只读汇聚** | 统一收口四类复核项：低置信评分项、作品撤回显形确认、slides 转换 verify_gate 失败复核（PRD-338 SLIDES_PAGE_MISMATCH/EXTERNAL_REF_FOUND）、外链检出处置——闸门继续各拦各的 |
| R3 | **每项带证据** | 逐条 `{item_id, kind, source_ref, work_snapshot_digest, judgepack_version, reason, state}` 缺一拒绝入箱——快照与 PRD-352 重放包同源 |
| R4 | **账本 append-only + 拒绝留痕** | reject 留 by/at/reason |
| R5 | 占位符纪律 | T5 检查覆盖本文件 |
| R6 | 实现类 PR 只开不合并 | 等用户 review |

## 1. 借鉴对象、许可证与不复用红线

backnotprop/plannotator（Apache-2.0，实测）+ pingdotgg/t3code（MIT，实测）——只借鉴「人工拍板收件箱」控制面形态；条目 schema 按本仓评审复核域自研，零代码复用，不引入原仓依赖。

## 2. 与既有机制划界

| 维度 | PRD-366（本条） | PRD-338 转换与校验 | PRD-177 三态 | PRD-262 安检 |
|---|---|---|---|---|
| 管什么 | 复核待办**收口** | 转换+双机判 | 结论形态 | 进池扫 |
| 操作语义 | 人批/拒（零自动） | 闸门拒绝 | 引擎判定 | 拦截 |
| 分数语义 | 零分数写（R1） | 零 | 零 | 零 |

## 3. 收件箱设计

### 3.1 schema（T2 预埋）

```json
{"schema": "review-verify-inbox/v1",
 "items": [{"item_id": "item-001",
   "kind": "low_confidence_score|withdraw_confirm|slides_gate_review|external_ref_review",
   "source_ref": "slides-gate/v1#checks[1]（占位）",
   "work_snapshot_digest": "sha16:…", "judgepack_version": "vN",
   "reason": "verify_gate SLIDES_PAGE_MISMATCH 复核（占位）",
   "state": "pending|approved|rejected", "decided_by": null, "decided_at": null}]}
```

### 3.2 状态机（确定性）

collect（四源只读汇聚）→ pending；人 approve/reject 留痕；重复裁决/未知 id 显形拒绝。approved 是「人已复核」记录——重转换/撤回/处置走既有流程。

## 4. 失败闸门（T3 落地）

| 错误码 | 触发 | 行为 |
|---|---|---|
| INBOX_ITEM_INCOMPLETE | 证据缺一 | 拒绝入箱 |
| INBOX_DOUBLE_DECIDE | 重复裁决 | 显形拒绝 |
| INBOX_AUTO_EXEC_ATTEMPT | 条目携带撤回/重转换/改分载荷 | 拒绝（R1） |

- kind 词表封闭四项。

## 5. 衔接

T2 内核；T3 闸门（三码+R1 零动作 AST）；T4 划界（快照与 352 同源+与 338/177/262 划界钉值）；T5 样例回放+文档无密钥。

## 6. 开放问题

1. 低置信评分项的判定来源（谁产出低置信标记——倾向 slides_gate/verify 检查失败项自动入箱，主观低置信人工加，待 T2 裁决）；
2. 撤回确认的双向语义（approve=撤回确认？——倾向 approve 仅记「确认撤回动议」，实际撤回走既有流程，待 T2）。
