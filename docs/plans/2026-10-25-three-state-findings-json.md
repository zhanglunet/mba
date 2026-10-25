# PRD-177/T1：评审 findings.json 三态 schema

> trend issue #885。对应 PRD-177（中央仓库 zhanglunet/trend）。
>
> 定位：给每条评审结论（Verdict / Critical gap / Why）一个机读载体——三态 findings.json，
> 供元评审、工程质量门、导出契约等下游消费。T1 只出 schema 设计（字段定义 + 三态语义 +
> 校验规则 + 样例），不写实现代码；不改评分业务逻辑本身（不动 5 镜头口径、
> judge-prompt-template 评分流程、meta_review 四项审计算法与 A–F 阈值）。findings 是
> 评委结论的机读投影，不替代 `reviews/<slug>.md`。
>
> 依据（仓库现状，2026-10-25 实测）：
> ① 评委原始输出 = `published/reports/<brand>/versions/vN*/reviews/<slug>.md`
>   （judge-prompt-template STEP 5：`## Scores` 五镜头 1–10 表 + `## Verdict` +
>   `## Critical gap` + `## Brand action (90 days)`），聚合层 = `report.md` 的
>   `## Score Matrix`（评委×维度矩阵，单元格带版本 delta 标记）与 `## Dissent Heatmap`；
> ② 机读消费方已有两处：`scripts/meta_review.py`（PRD-063/T2，只解析 Score Matrix，
>   四项审计确定性输出）与 `scripts/perspective-tools/quality_gate.py --json-out`
>   （PRD-151/T3 契约 JSONL，`gate_version=prd-151-v1`）；
> ③ 缺口：评委的"结论"只有自然语言形态，机读只能拿到分数矩阵——下游拿不到
>   "谁、对什么、下了什么结论、依据是什么"。
>
> 借鉴：cloudflare/security-audit-skill（MIT，Copyright (c) 2025-2026 Cloudflare, Inc.）——
> 只借鉴其"三态 verdict（confirmed / needs_validation / rejected）逐条 findings 机读文件 +
> schema 校验脚本分离 + needs_validation 不带定论与 severity"的结构思路（其 Phase 4
> Structured output / report-schema.json / validate-findings.cjs 三层分离形态），
> 原项目：<https://github.com/cloudflare/security-audit-skill>。
> 本文档全部字段、枚举、阈值、措辞均为本仓库自研，未复制其文本。

## 一、现状盘点：三态 findings 补的是哪一层

| 层 | 既有资产 | 形态 | 缺口 |
|---|---|---|---|
| 评委原始结论 | `reviews/<slug>.md`（Scores 表 / Verdict / Critical gap / Brand action） | 自然语言 markdown | 机器只能拿到分数，拿不到"结论 + 依据" |
| 聚合报告 | `report.md` 的 Score Matrix / Dissent Heatmap | 表格（分数 + delta 标记） | 只有机读分数矩阵，无逐条结论 |
| 一致性审计 | `scripts/meta_review.py`（四项审计，PRD-063） | 纯计算，输入 Score Matrix | 分歧定位输出"谁和谁在哪差多少"，无法回指到具体结论条目 |
| 交付物质量门 | `scripts/perspective-tools/quality_gate.py`（PRD-151） | JSONL 契约行（gate_version / items / pass_count） | 管交付物完备度，不管结论内容 |

结论：findings.json 是**第 1.5 层增量**——把每位评委的自然语言结论投影为逐条机读记录，
向下衔接 meta_review（分歧可回指）、向下衔接导出契约（T4）。不新增第五层、不改任何
既有层的业务逻辑。三态词表 `confirmed / needs_validation / rejected` 沿 trend 家族
已实现词表（PRD-169 合同域已定稿、PRD-187 awards 域同款），mba 域按自身语境定字段。

## 二、findings.json schema（findings_version = prd-177-v1）

### 2.1 文件位置与顶层字段

每品牌每轮评审一份：`published/reports/<brand>/versions/vN*/findings.json`
（与 `reviews/` 同级，纯加法新文件，不改动 report.md 任何章节）。

```json
{
  "findings_version": "prd-177-v1",
  "brand_slug": "<brand-slug>",
  "panel": "default",
  "report_ref": "published/reports/<brand-slug>/versions/vN/report.md",
  "counts": {"confirmed": 2, "needs_validation": 1, "rejected": 1},
  "findings": []
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `findings_version` | string | ✓ | 固定 `prd-177-v1`；schema 演进只加版本不改语义（与 quality_gate 的 `gate_version=prd-151-v1` 同款纪律） |
| `brand_slug` | string | ✓ | 与目录名一致 |
| `panel` | string | ✓ | panel yaml 的 `name` |
| `report_ref` | string | ✓ | 仓库相对路径，指向同轮 report.md |
| `counts` | object | ✓ | 三态计数，必须与 `findings[]` 实际计数一致（机判对账，沿 PRD-169 coverage 纪律） |
| `findings` | array | ✓ | 可为空数组（本轮无结论也是合法输出，但校验器要求 `counts` 全 0） |

### 2.2 finding 对象字段表

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `id` | string | ✓ | 格式 `^F-(<judge-slug>\|lead)-\d{3}$`，文件内唯一；序号按评委内出现顺序，稳定可引用 |
| `status` | enum | ✓ | `confirmed` / `needs_validation` / `rejected`，三态固定禁第四态（suppressed/留痕态是合同域概念，mba 域不引入——rejected 本身即留痕） |
| `judge_slug` | string | ✓ | panel judges 之一；Lead 聚合层结论用保留字 `lead` |
| `lens` | enum\|null | ✓ | 专家域：`origin` / `category` / `leverage` / `identity` / `signal`（Score Matrix 行短名）；消费者题组域预留 `c1`–`c5`（PRD-178/T3 起使用）；`null` = 跨口径结论 |
| `claim` | string | ✓ | 一句话结论，≤80 字，自然语言，与该评委 `reviews/<slug>.md` 的 Scores/Why 语义不矛盾 |
| `evidence` | array | ✓ | ≥1 条；每条 `{source_ref, quote, kind}`；**空数组校验失败**（PRD 风险"空依据"即拦在此） |
| `evidence[].source_ref` | string | ✓ | 仓库相对路径 + 行锚，如 `published/reports/<brand>/versions/vN/_raw/synthesis.md#L40-52`；路径必须真实存在 |
| `evidence[].quote` | string | ✓ | 逐字引用，必须在 source_ref 指向文件中逐字存在（沿用 firewall_check 的反捏造纪律） |
| `evidence[].kind` | enum | ✓ | `synthesis` / `report` / `review` / `research`（分别对应 _raw 综合、report.md、reviews/*.md、perspectives 语料） |
| `unresolved_fact` | string | 条件必填 | `status=needs_validation` 时必填：一句"卡在哪个未决事实"（对齐 PRD-169 的 blocker 语义；needs_validation 不带定论、不带 severity） |
| `rejected_reason` | string | 条件必填 | `status=rejected` 时必填：为何证伪 / 撤回；条目保留不删除（留痕纪律） |
| `severity` | — | **不设** | 品牌审计结论没有 likelihood×impact 口径，照搬安全域字段只会造成伪精确；借鉴对象自身也不给 needs_validation 定级 |

### 2.3 三态操作语义（mba 域定义）

| status | 进入条件 | 防滥用约束 |
|---|---|---|
| `confirmed` | claim 有完整依据链：evidence ≥2 条且至少覆盖 2 种 kind，或含 ≥1 条 synthesis 逐字引用；且与该评委 Scores/Why 不矛盾 | 「没找到反例」不等于 confirmed；只有 1 条弱引用的结论最高只能 needs_validation（沿 PRD-169 §3 硬约束 6 的防"自己查自己"思路） |
| `needs_validation` | 有明确未决事实（unresolved_fact 非空）：synthesis 缺数据、口径存疑、需下一轮复核 | 评委对某镜头标 withheld（judge-prompt-template STEP 2 纪律）时，对应结论必须落此态 |
| `rejected` | 候选结论被 synthesis / 后续事实证伪，或评委自行撤回；rejected_reason 必填 | 保留在文件中，不得删除后重写（留痕可复盘） |

## 三、校验规则与旧格式兼容（T2 工具形态预告，本 T1 不写代码）

### 3.1 校验器设计约束

- 位置 `scripts/validate_findings.py`（与 meta_review.py 平级），纯标准库，无网络 I/O，
  确定性：同输入跑 10 次输出逐字节一致（PRD-063/T5 e2e 同款验收法）。
- 用法形态：`python3 scripts/validate_findings.py <findings.json>`；退出码 0 = 合法 /
  1 = 校验失败 / 2 = 用法或 IO 错误（沿 quality_gate 惯例）；报告 120 秒可读：
  结论行 → 违规清单（字段级路径，如 `findings[2].evidence` 为空）→ 附录 JSON 行。

### 3.2 校验规则固定清单（R-1…R-7）

| ID | 规则 |
|---|---|
| R-1 | JSON 可解析；顶层字段齐（§2.1）；`counts` 与 `findings[]` 实际三态计数逐项一致 |
| R-2 | 每 finding：`id` 格式且文件内唯一；`status` / `lens` / `evidence[].kind` 枚举合法 |
| R-3 | 条件必填：needs_validation ⇒ `unresolved_fact` 非空；rejected ⇒ `rejected_reason` 非空；confirmed ⇒ `unresolved_fact`/`rejected_reason` 必须缺省 |
| R-4 | `judge_slug` ∈ panel judges ∪ {`lead`}；`source_ref` 路径在仓库内真实存在 |
| R-5 | `evidence[].quote` 在 `source_ref` 文件中逐字存在（反捏造防火墙联动，三态无一例外） |
| R-6 | `claim` ≤80 字；evidence ≥1 条 |
| R-7 | 占位符纪律：全文无真实内部主机名 / IP / 账号 / 密钥（复用 PRD-151 C-3 正则清单，白名单占位形态不报） |

### 3.3 旧格式兼容（PRD 风险"评委拒改输出 → 适配层"）

- 适配层职责（T2 随校验器交付）：从既有 `reviews/<slug>.md` 投影 findings——
  `## Scores` 的 Why 段 + `## Verdict` / `## Critical gap` 映射为 finding 候选；
  **默认落 `needs_validation`，绝不默认 `confirmed`**（evidence 不足时宁可三态降级，
  不造假确认）；`## Brand action` 不入 findings（是建议不是结论）。
- `findings_version` 单字段版本化：v1 消费方遇未知版本报"版本不识别"并拒读，
  不猜测语义（与 quality_gate JSONL 消费方同款纪律）。

## 四、与元评审 / 工程质量门 / 下游的挂钩点（T3/T4 预告）

1. **meta_review（T3，#887）**：输入仍以 Score Matrix 为准，四项审计算法与 A–F 阈值
   **一字不动**；可选 `--findings <path>` 参数只在审计项 4（分歧定位）的输出行附
   finding id 线索（"该分歧对应 F-<slug>-003"）——只加线索、不改判定，沿 PRD-151/T3
   "消费方只读不解释"纪律。
2. **quality_gate（T3 起，可选）**：findings.json 的 R-1…R-7 可作为 quality_gate 的
   新增检查项候选，但本 PRD 不把它计入 13 条 checklist（避免口径膨胀）；只要求
   `findings_version` 与 `gate_version` 的版本字段纪律一致。
3. **导出契约（T4，#888）**：exec summary / 对比报告 / 对外导出引用 findings.json
   路径 + `findings_version`；导出必须渲染三态计数全量（不得只渲染 confirmed 而隐去
   rejected / needs_validation，沿 PRD-169 §6 计数透明化纪律）。

## 五、最小合法样例（三态各一条，全占位符）

```json
{
  "findings_version": "prd-177-v1",
  "brand_slug": "example-brand",
  "panel": "default",
  "report_ref": "published/reports/example-brand/versions/v1/report.md",
  "counts": {"confirmed": 1, "needs_validation": 1, "rejected": 1},
  "findings": [
    {"id": "F-example-judge-001", "status": "confirmed",
     "judge_slug": "example-judge", "lens": "identity",
     "claim": "示例结论：该品牌的视觉与语言在合成材料中保持一致（占位）",
     "evidence": [
       {"source_ref": "published/reports/example-brand/versions/v1/_raw/synthesis.md#L40-52",
        "quote": "（占位：synthesis 中的逐字引用句）", "kind": "synthesis"},
       {"source_ref": "published/reports/example-brand/versions/v1/reviews/example-judge.md",
        "quote": "（占位：评委落笔原文句）", "kind": "review"}]},
    {"id": "F-example-judge-002", "status": "needs_validation",
     "judge_slug": "example-judge", "lens": "signal",
     "claim": "示例结论：真实使用信号不足以下定论（占位）",
     "evidence": [
       {"source_ref": "published/reports/example-brand/versions/v1/_raw/synthesis.md#L60-64",
        "quote": "（占位：synthesis 中表明数据缺失的原句）", "kind": "synthesis"}],
     "unresolved_fact": "占位：缺哪一项可核对的事实"},
    {"id": "F-lead-001", "status": "rejected",
     "judge_slug": "lead", "lens": null,
     "claim": "示例结论：Lead 层撤回的候选结论（占位）",
     "evidence": [
       {"source_ref": "published/reports/example-brand/versions/v1/report.md",
        "quote": "（占位：报告中与该候选矛盾的原句）", "kind": "report"}],
     "rejected_reason": "占位：与 Score Matrix 实测分差矛盾，故撤回"}
  ]
}
```

## 六、非目标与边界

1. 不改 5 镜头评分公式、judge-prompt-template 评分流程、meta_review 四项审计算法与
   A–F 阈值；findings 只投影结论，不回写分数。
2. findings 不写客户密钥、不含 PII；evidence 只允许引用仓库内文件（source_ref 校验
   拦仓库外引用）。
3. 不做"自然语言→findings"的抽取质量承诺——T2 验收线是"样例评委可产出 + 机器校验
   通过"，确定性优先；抽取遗漏不判 FAIL（那是 needs_validation 的正常来源）。
4. 不引入合同域的全套证伪编排（falsification / verifier 隔离 / reproducible_by）——
   那是 PRD-169 合同审计域的多阶段流程；mba 域单轮评审没有独立证伪方，强行照搬
   只会产出永远过不了 confirmed 的流水线。三态词表对齐、字段自研。

## 七、下一步

确认后进 T2（#886）：评委输出适配为三态 + 依据引用——`reviews/<slug>.md` 投影适配层
（§3.3）+ `scripts/validate_findings.py`（R-1…R-7）+ 样例评委（建议 default panel 任一
production 参考 shape）产出第一份全占位符合法 findings.json。T1 验收线：本 schema
评审通过（#885）。
