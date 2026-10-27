# 专家 vs 消费者对比报告模板（PRD-178/T4，trend #893）

> 用法：同一参赛项目跑完 expert 五镜头 panel 与 consumer-mixed 面板后，把两组
> findings（PRD-177 三态）按下表逐行抄录对照。模板只做对照呈现——**不换算、
> 不平均、不合并**：专家 5 镜头（business_value 等）与消费者 C1–C5 是两套
> 独立评分域，任何"加权合成"都属跨域编造。样例数据全虚构。

## 报告头

| 字段 | 值（示例占位） |
|---|---|
| 项目 | proj-demo-001（虚构） |
| 专家面板 | `<expert-panel-name>`（5 镜头，三态 findings 各 1 条/镜头） |
| 消费者面板 | `consumer-mixed`（3 人设 × C1–C5，三态 findings） |
| 对照说明 | 两组独立评分域，本报告只并排呈现差异，不做合成 |

## 对照表（逐 lens 并排）

| 域 | lens | 结论（claim 摘录） | 状态 | evidence 摘录 |
|---|---|---|---|---|
| 专家 | business_value | （抄 findings claim） | confirmed/needs_validation/rejected | （evidence 逐字摘录） |
| 专家 | closed_loop | … | … | … |
| 消费者 | c1 第一印象 | 「记住了 X，感觉 Y」 | … | 口吻样句 |
| 消费者 | c2 购买意愿 | 7/10，主因… | … | 一句主因 |
| 消费者 | c3 价格直觉 | 值了；可接受带（占位） | … | … |
| 消费者 | c4 信任与犹豫 | 犹豫点逐条 | … | … |
| 消费者 | c5 表达欲 | 会转发；口吻一句话 | … | … |

## 差异解读（人工撰写，非机产）

- **一致处**：专家与消费者结论同向的维度（例：专家 business_value 高、消费者
  c2 愿买）——如实写，不夸大。
- **分叉处**：同向相反或一方 needs_validation——只描述分叉事实，不裁决谁对
  （两域无共同量纲）。
- **盲区**：某 lens 无 findings（全部 needs_validation 等）——如实标注「该域
  本轮无可用结论」，不补位。

## 纪律

1. 对照表数据**只准抄自**两侧 findings.json（三态与 evidence 逐字），新增解读
   只写「差异解读」节且标明人工撰写。
2. 消费者 C2 的 0–10 分是消费者域唯一数值分：报告中不得与专家镜头的任意分数
   平均或相减。
3. 样例报告（`docs/quality/comparison-report-sample.md`）用全虚构项目与占位
   人设，作为首次填写的参照。
