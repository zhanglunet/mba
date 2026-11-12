# PRD-380/T1：评审结论验证台设计（低置信结论快照重放过才进复核）

> trend issue #1884。来源：2026-11-12 GitHub 趋势日报（digests/2026-11-12.md）第 8 条，用户 2026-11-13 指令「拍板」采纳。
> 设计日：2026-11-12 · 目标仓库：zhanglunet/mba
> 状态：T1 设计草案，待评审。仅设计文档（纯加法 .md）；验证台内核（T2）、闸门（T3）、划界断言（T4）、验收试运行（T5）按本设计后续落地。
> 示例全部虚构占位，不出现真实内部主机名、IP、账号或密钥。

## 0. PR 门槛自查（repos.yaml default_pr_gate）

| 门槛 | 落实 |
|---|---|
| require_integration_point | **接入点：`scripts/review_replay.py` 消费的评分推导产物（低置信评分项）之后、`scripts/verify_inbox.py::collect(low_confidence=…)`（PRD-366 收件箱）之前**——T2 验证台以注入式函数 `verify_score(review, work_snapshots, recheck_fn)` 供评审流程在 collect 前调用；只把 VERIFIED 的低置信结论喂给复核收件箱 |
| no_missing_channel | 只消费 review_replay 既有 review/work_snapshots 结构（score_fn 同形态注入）；复算=对同一作品快照重跑同一评分推导（recheck_fn 注入，复用 352 评分推导形态）；验证结论写本地 JSONL 账本（文件落库），零新外部渠道 |
| no_duplicate_module | main 上同类模块盘点：review_replay.py（352 重放——管"评分推导可重算"，本条管"低置信结论可复算后进复核"，粒度不同：重放比对决策序列，本条重算分数比对结论）/ judge_config_snapshot.py（282 配置可逆）/ verify_inbox.py（366 收件箱）。**本条不另起评分推导**：复算=注入式重跑评分推导，比对重算分数与结论分数一致才 VERIFIED |
| impl_requires_devlog | T2~T5 实现 PR 各附 docs/devlog/2026-11-13-prd-380-*.md 开发记录+合规核对；账本落 JSONL 文件（路径注入），不只存内存 |

## 1. 红线

| # | 红线 | 落地方式 |
|---|---|---|
| R1 | **结论快照重放过才进复核** | 低置信评分/评委包检出先按作品快照重放评分推导；重算分数与结论分数一致 → VERIFIED；不一致 → UNVERIFIED——误判拦在评审结论外，复核收件箱只审验证过的结论（不进 366 收件箱） |
| R2 | **验证不产生新评分** | 复算=重跑注入的同一评分推导（作品快照只读深拷贝），零新增评分逻辑、零人工改分入口；复现不出=UNVERIFIED 不猜不补 |
| R3 | **机器可读落账** | 每次验证 `{review_id, work_id, kind, source_ref, snapshots_fingerprint, review, reproduce, verdict}` 八件套落 JSONL 账本；缺任一 BENCH_INCOMPLETE 拒绝入账 |
| R4 | **账本 append-only + 修复二次验证才关闭** | 验证账本只增不删；作品快照/评委包变更后二次验证落新记录，关闭以最新 VERIFIED 为准 |
| R5 | 占位符纪律 | T5 检查覆盖本文件 |
| R6 | 实现 PR 只开不合并 | 等用户 review |

## 2. 借鉴对象、许可证与不复用红线

openai/codex-security（Apache-2.0，实测）+ cloudflare/security-audit-skill（MIT，实测）——只借鉴「发现→验证→修复→再验证」控制面形态；条目 schema 按本仓评审域自研，零代码复用，不引入原仓依赖。

## 3. 与既有机制划界

| 维度 | PRD-380（本条） | PRD-262 评委包安检 | PRD-177 findings 三态 | PRD-352 重放包 | PRD-366 收件箱 |
|---|---|---|---|---|---|
| 管什么 | 逐条 **结论可复算后进复核** | 进池扫 | 结论形态 | 评分推导可重算 | 等人复核 |
| 比对 | 重算分数 vs 结论分数 | 无 | 无 | 决策序列 vs 重演 | 无 |
| 关系 | 评分推导之后、collect 之前 | 被区分 | 被区分 | 被区分（粒度不同） | 下游：验证过才可进 |

## 4. 验证台设计

### 4.1 条目 schema（T2 预埋）

```json
{"schema": "review-verify-bench/v1",
 "items": [{"review_id": "r-001",
   "work_id": 42,
   "kind": "low_confidence_score",
   "source_ref": "review-replay-pack/v1（占位）",
   "snapshots_fingerprint": "sha16:…（作品快照，与 352 work_snapshots_digest 同族）",
   "review": {"score": "88（原样）", "why": "…（占位）"},
   "reproduce": {"score_match": true, "detail": "…（占位）"},
   "verdict": "VERIFIED|UNVERIFIED"}]}
```

### 4.2 流程（确定性）

低置信结论 → 逐条重跑同一评分推导（注入 recheck_fn，作品快照深拷贝）→ 重算分数与结论分数一致 → VERIFIED / 否则 UNVERIFIED → 落账 → 复核收件箱只收 VERIFIED。

## 5. 失败闸门（T3 落地）

| 错误码 | 触发 | 行为 |
|---|---|---|
| BENCH_INCOMPLETE | 八件套缺一/词表外 | 拒绝入账 |
| BENCH_REPRO_MISMATCH | 声称 VERIFIED 但重算分数与结论不一致（或反之） | 显形拒绝 |
| BENCH_STALE | 作品快照指纹与当前不符 | 拒绝复用旧验证 |

## 6. 衔接

T2 内核（verify_score + JSONL 账本）；T3 闸门（三码+零改分零网络 AST）；T4 划界（与 352 重放/366 收件箱/282 划界钉值+评分推导零 import 注入重跑）；T5 样例全链回放+UNVERIFIED 拦截演练+文档无密钥。

## 7. 开放问题（留待评审/T2）

1. 评委包检出的复现口径（倾向重放检出比对 rule_id+work_id——待 T2）；
2. snapshots_fingerprint 口径（倾向与 352 work_snapshots_digest 同族 sha16——待 T2）。
