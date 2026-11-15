# 评审监督台验收试运行记录（PRD-449/T5）

> 来源：trend issue [#2169](https://github.com/zhanglunet/trend/issues/2169)（[PRD-449/T5] 评审监督台验收试运行）；PRD 全文：`zhanglunet/trend` 仓库 `adopted/PRD-449-mba-review-supervision-bench.md`。
> 状态：验收试运行记录（T5），只开 PR 不合并，等 review。
> 依据：T1 设计（`docs/plans/2026-11-15-prd-449-review-supervision-bench-design.md` §4）+ T2 最小实现 + T3 闸门 + T4 划界断言；本轮未改 T1–T4 的设计与代码，只新增验收脚本与验收测试。

## 1. 验收结论

**全链跑通。**可疑评分在打分时就被批注发回重评，评审复核收件箱只审人点头过的评分。

## 2. 跑了什么

验收脚本 `scripts/review_supervision_acceptance.py`（仓库根执行，内存里的合成占位数据，零网络零子进程），5 个场景全过：

| 场景 | 结果 | 内容 |
|---|---|---|
| happy-path-full-chain | 通过 | sc-001：出炉 → 看 → 批注（锚定“视角A打分”步骤）→ 发回重评 → 改回 v2（视角A 8→7 分）重新待审 → 点头 → 过闸 → 划界证明 → 入账 → 进品牌审计报告；进度 7 条 / 批注 1 条 / 反馈 1 条，时间线三类齐全 |
| unapproved-blocked | 通过 | draft / in-review / sent-back / rejected 四态：闸门各抛 GATE_BLOCKED 一次，出口 passed 为空、blocked_count=4 |
| old-verdict-does-not-admit-new-version | 通过 | v1 放行裁决对 v1 有效、对 v2 失效；划界证明拒绝把 v1 裁决当 v2 的点头 |
| boundary-holds | 通过 | 已点头记录在界内；含 verified 声称的记录越界拒绝；版本不动改内容越界拒绝；批量划界 1 条在界内、1 条越界 |
| three-records-complete | 通过 | 进度 / 批注 / 反馈 / 双版本齐全；账本入账成功、最新一条为 approved v2；进度为空的记录拒绝入账 |

## 3. 测试结果

- 本地：`python3 -m pytest tests/unit/ -q`——**104 passed**（T2 + T3 + T4 + 本轮新增 T5 验收测试，含 T2–T4 回归；隔离目录跑新模块 + 新测试，全量套件以 CI 为准）。
- 验收脚本直接跑：`python3 scripts/review_supervision_acceptance.py`——退出码 0，verdict“全链跑通”，5/5 场景通过。
- 未发现本次改动引入的失败；未触碰 T1–T4 已有模块，无基线红需要说明。

## 4. 试运行记录（合成占位数据）

- 试运行对象：评分 sc-001（品牌占位，视角A/视角B 两路打分），全程走监督台：批注发回一次、改回一版、点头一次。
- 未点头的评分不进品牌审计报告：四种未点头状态在闸门与出口两处均被拦下留痕，无例外通道。
- 批注与反馈全程留痕：进度、批注、发回反馈三类记录齐全，账本 JSONL append-only（路径注入）。

## 5. 红线

- 监督台不碰分数：批注与裁决不改动评分内容与过程；分数改动只由 agent 在发回回路里完成、再回来重新待审。
- 未点头的评分不进品牌审计报告，无例外通道、无绕过开关。
- 人只批注和裁决，不下场改评分内容。
- 文档与示例全为合成占位，无真实内部主机名、IP、账号或密钥。
- 实现类 PR 只开不合并，等用户 review。

## 6. 借鉴声明

- backnotprop/plannotator（Apache-2.0）、ag-ui-protocol/ag-ui（MIT）：只借监督回路形态；本轮新增代码为原创，未复用其代码。
- Tencent/LoopForge（无 LICENSE）：只借人工批准门形态，绝不复用其文本或代码。
