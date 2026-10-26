# findings.json 导出与下游消费契约（PRD-177/T4）

> trend issue #888（中央仓库 zhanglunet/trend，PRD-177）。
> 设计文档：[docs/plans/2026-10-25-three-state-findings-json.md](../plans/2026-10-25-three-state-findings-json.md)（T1 schema）。
> 上游交付：T1 schema（#885）→ T2 校验器与适配层（#886）→ T3 元评审 / 工程质量门消费（#887）。
> 本文档是 T4（#888）交付：把 findings.json 的**导出面**与**下游消费契约**收拢成一篇，
> 供导出方（exec summary / 对比报告 / 对外导出）与消费方（PRD-151 / PRD-063）对照实现。
> 本文档全部示例均为占位，不指向任何真实品牌、人物、主机、IP、账号或密钥。

## 一、这是什么

每品牌每轮评审产出一份机读三态结论文件（schema `prd-177-v1`，T1 §二）：

```text
published/reports/<brand>/versions/vN*/findings.json
```

它是评委自然语言结论（`reviews/<slug>.md`）的**机读投影**——第 1.5 层增量，
不替代任何既有层：不改五镜头评分、不改 judge-prompt-template 评分流程、
不改 meta_review 四项审计算法与 A–F 阈值。下游一切消费都以本契约为准：
**只读、不回写、版本不识别即拒读、三态计数全量呈现。**

## 二、导出面：文件的形态、产出与合法性判定

### 2.1 顶层字段（全部必填，T1 §2.1）

| 字段 | 说明 |
|---|---|
| `findings_version` | 固定 `prd-177-v1`；单字段版本化，schema 演进只加版本不改语义 |
| `brand_slug` | 与目录名一致 |
| `panel` | panel yaml 的 `name` |
| `report_ref` | 仓库相对路径，指向同轮 `report.md` |
| `counts` | 三态计数，与 `findings[]` 实际计数逐项对账 |
| `findings` | 逐条结论数组，可为空（空时 counts 全 0） |

每条 finding：`id`（`F-<judge-slug>-NNN`）/ `status`（`confirmed` / `needs_validation`
/ `rejected`，禁第四态）/ `judge_slug`（`lead` = Lead 聚合层保留字）/ `lens`
（专家域 `origin`/`category`/`leverage`/`identity`/`signal`；消费者题组域 `c1`–`c5`，
PRD-178/T3 起使用；`null` = 跨口径）/ `claim`（≤80 字）/ `evidence`（≥1 条，
`{source_ref, quote, kind}`，quote 逐字引用反捏造）/ 条件必填 `unresolved_fact`
（needs_validation）与 `rejected_reason`（rejected，留痕不删）。
不设 `severity`（品牌审计结论无 likelihood×impact 口径，照搬即伪精确）。

### 2.2 产出链路（谁写这份文件）

| 环节 | 工具 | 说明 |
|---|---|---|
| 评委落笔 | `reviews/<slug>.md`（judge-prompt-template STEP 5） | 自然语言原始层，不本契约管辖 |
| 投影适配 | `scripts/adapt_findings.py`（专家，PRD-177/T2） | 从 reviews 投影，**默认 needs_validation，绝不默认 confirmed** |
| 消费者投影 | `scripts/adapt_consumer_findings.py`（PRD-178/T3） | C1–C5 答卷行 → `lens=c1`–`c5`；C2 只投影 ≤5 低分主因 |
| 合法性判定 | `scripts/validate_findings.py`（R-1…R-7，**唯一判定权**） | 任何导出 / 消费前先过校验；exit 0 = 合法 |

金样例（全占位，可直接跑通）：`tests/fixtures/findings/`（专家树）、
`tests/fixtures/consumer-findings/`（消费者树）、`tests/fixtures/meta-review/`
（元评审消费树）。

### 2.3 三态操作语义（T1 §2.3 摘录）

| status | 进入条件 | 导出方呈现要求 |
|---|---|---|
| `confirmed` | 依据链完整（evidence ≥2 条且覆盖 ≥2 种 kind，或含 ≥1 条 synthesis 逐字引用） | 可引用 claim，须保留 evidence 可回指 |
| `needs_validation` | 有明确未决事实（`unresolved_fact` 非空） | **不得**写成定论；须带"待复核"语义 |
| `rejected` | 被证伪 / 撤回，`rejected_reason` 必填，条目留痕不删 | 不得静默丢弃；留痕本身就是导出内容 |

## 三、下游消费契约

### 3.1 统一纪律（四条，全部消费方一致）

1. **版本纪律**：只认 `findings_version=prd-177-v1`；未知版本**拒读不猜测语义**
   （与 quality_gate `gate_version=prd-151-v1` 同款纪律）。
2. **只读不解释**：findings 是线索与呈现输入，不参与任何判定、不回写分数、
   不改任何既有业务逻辑；三态合法性判定权只在 `validate_findings.py`。
3. **三态透明化**：凡渲染 findings，必须渲染三态计数**全量**
   （confirmed + needs_validation + rejected），不得只渲染 confirmed 而隐去其余两态
   （沿 PRD-169 §6 计数透明化纪律）。
4. **降级不阻断**：findings 缺失 / 损坏 / 版本不识别 → 输出降级说明、主流程照常
   （退出码不受影响）；**不得编造**降级期间的"结论"。

### 3.2 已实现的消费口（T3 交付，#887）

| 消费方 | 调用形态 | 消费行为 | 纪律落点 |
|---|---|---|---|
| PRD-063 元评审 | `python3 scripts/meta_review.py <report.md> --findings <findings.json>` | 审计项 4（Top3 分歧点）行内附 finding id 回指线索；附录 F 渲染版本 / panel / 三态全量计数 / needs_validation 与 rejected 留痕清单 | 四项审计算法与 A–F 阈值一字不动；不带 `--findings` 时输出不含任何 findings 段（向后兼容） |
| PRD-063 元评审 CI 透传 | `python3 scripts/ci_meta_review.py --report <report.md> --findings <findings.json>` | 摘要行内回指线索 + 降级说明透传；永远 exit 0 | 同上 |
| PRD-151 工程质量门 | `python3 scripts/perspective-tools/quality_gate.py --judge <slug> --findings <findings.json> [--findings-root <repo-root>]` | 调 `validate_findings.py` 把结论作为**只读附件段**渲染；契约 JSON 行追加可选键 `findings_readonly`（`available` / `ok` / `schema` / `recognized` / `error_count`） | R-1…R-7 **不计入 13 条 checklist**（口径不膨胀）、不改 PASS/FAIL；仅 `--judge` 模式支持 |

### 3.3 导出面契约（导出方必须遵守，#888 新增）

凡把评审结论导出给"报告读者"的出口——exec summary（PRD-023）、对比报告
（PRD-178 `## Expert vs Consumer`，见
[metric-brand-auditor/references/expert-vs-consumer-template.md](../../metric-brand-auditor/references/expert-vs-consumer-template.md)）、
对外交付物——引用 findings 时必须：

1. **引用路径 + 版本**：写明 findings.json 仓库相对路径与 `findings_version`
   （例：`published/reports/<brand>/versions/v1/findings.json`（`prd-177-v1`）），
   读者可回指到机读文件。
2. **三态计数全量**：渲染 `counts` 三项（透明化），禁止只挑 confirmed 做"亮点摘要"。
3. **needs_validation 不写成定论**：导出文案必须保留"待复核 / 未决事实"语义；
   rejected 不得静默隐去（留痕纪律）。
4. **回指 finding id**：引用某条结论时给出 `F-<judge-slug>-NNN`，与 findings.json /
   meta_review 附录 F 的回指口径一致。
5. **降级呈现**：findings 不存在 / 版本不识别时，导出物标注"本轮无机读结论
   （findings 降级）"，不得编造结论，也不得阻断导出主体。
6. **只读**：导出过程不得改写 findings.json 本身；修正只能走评委 / 适配层再校验。

现状对照（诚实标注）：`scripts/generate_exec_summary.py`（PRD-023）**尚未**消费
findings——它当前只从 report.md 抽取（纯抽取原则）。本节是对导出方的**前向契约**：
未来任何出口接入 findings 时按上述 1–6 实现；已实现的两个消费口（§3.2）已合规。

## 四、版本演进

- `findings_version` 单字段版本化：语义演进 = 新版本号（如未来 `prd-177-v2`），
  不原地改语义；v1 消费方遇未知版本拒读并降级，不猜测。
- 新增枚举值（如 `lens`、`evidence[].kind`）属 schema 演进，须走版本号 + 本文档 +
  `validate_findings.py` 三处同步，禁止消费方私自放宽枚举。

## 五、边界与非目标

1. 不改五镜头评分口径、judge-prompt-template 评分流程、meta_review 四项审计算法
   与 A–F 阈值；findings 只投影结论，不回写分数。
2. findings 不写客户密钥、不含 PII；evidence 只允许引用仓库内文件（R-4 拦仓库外
   引用）；本文档与所有样例只用占位符，不出现真实主机名 / IP / 账号 / 密钥。
3. findings 是"结论 + 依据"层，不是分数层——导出分数仍以 `## Score Matrix` 为准。
4. 不引入合同域（PRD-169）的全套证伪编排；三态词表对齐、字段自研。

## 六、导出方自查清单

导出物合入前逐项自检（全 Yes 才算合规）：

- [ ] 写明 findings.json 仓库相对路径 + `findings_version`
- [ ] 三态计数全量渲染（confirmed / needs_validation / rejected 一个不隐）
- [ ] needs_validation 条目保留"待复核"语义，未写成定论
- [ ] rejected 条目留痕可见，未静默丢弃
- [ ] 引用结论处带 finding id（`F-<judge-slug>-NNN`）
- [ ] findings 缺失 / 版本不识别 → 降级标注，未编造、未阻断
- [ ] 未改写 findings.json 本身（只读）
- [ ] 全文占位符纪律：无真实主机名 / IP / 账号 / 密钥
