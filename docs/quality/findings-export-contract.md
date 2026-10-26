# findings.json 导出与下游消费契约（PRD-177/T4，trend #888）

> 下游（元评审 PRD-063、工程质量门 PRD-151）如何**读到** findings.json、读到什么、
> 出错怎么办——一份契约文档，让消费方与产出方不用互相读源码。schema 本体见
> `docs/plans/2026-10-25-three-state-findings-json.md`（T1）；校验器见
> `scripts/validate_findings.py`（T2）。

## 产出面（谁写 findings.json）

| 产出口 | 命令 | 产物 |
|---|---|---|
| 评委稿适配 | `python3 scripts/adapt_findings.py <reviews/slug.md> <out.json>` | 评委稿 → 三态 findings（默认 needs_validation，绝不默认 confirmed） |
| 消费者评委适配 | `python3 scripts/adapt_consumer_findings.py <…>` | 消费者视角（lens=c1–c5）同构投影 |

产出为 `findings_version = "prd-177-v1"`；写后必须过
`python3 scripts/validate_findings.py <out.json>`（退出码 0 才算产出完成）。

## 消费面（谁读、读什么）

| 下游 | 消费方式 | 依赖字段 | 排序不敏感 |
|---|---|---|---|
| 元评审（PRD-063） | 只读引用：按 `finding.id` 逐条引用，`needs_validation` 进人工清单（接线沿 `ci_gate_status.py` 的只读消费先例） | id / status / lens / claim | ✅ 任意顺序 |
| 工程质量门（PRD-151） | 门禁报告引用 `status` 计数（confirmed/needs_validation/rejected 三计数与 `counts` 对账） | counts 三计数 | ✅ |
| 人工 review | 直接阅读 claim + evidence | evidence（逐字引用评委稿） | — |

## 消费方契约（读侧纪律）

1. **只读**：消费方不回写 findings.json；修正走产出侧重跑。
2. **默认怀疑**：`needs_validation` 是缺省态——消费方看到 confirmed 也应抽查
   evidence 是否逐字成立（校验器已查，双层防御）。
3. **计数对账**：消费方如自行计数，须与 `counts` 字段一致；不一致按坏档处理
   （拒绝消费并报告，不静默取子集）。
4. **lens 路由**：`lens` ∈ expert（e1–e5）/ consumer（c1–c5）；下游按 lens 分组
   统计，不跨组平均（专家 5 镜头与消费者 C1–C5 不可互相换算）。

## 演进

- schema 演进只加不改：`findings_version` 升版时，旧版本消费方按 version 拒绝
  消费（不做隐式迁移）。
- 下游新增消费口：在本文件追加一行消费面登记（谁/怎么读/依赖哪些字段），
  不改 schema。

---
登记：2026-10-25（PRD-177/T4，trend #888）首版。消费面新增时在「消费面」表追加登记。
