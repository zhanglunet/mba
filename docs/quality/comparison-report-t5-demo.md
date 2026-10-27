# 双视角对照报告演示：example-dual-brand（全虚构，PRD-178/T5）

> 依据 `expert-consumer-comparison-template.md`（PRD-178/T4，trend #893）对同一
> 虚构项目 example-dual-brand 首次填写：专家侧
> `tests/fixtures/consumer-fake-position/.../findings-expert.json`（adapt_findings.py
> 产出）× 消费者侧同目录 `findings-consumer.json`（adapt_consumer_findings.py 产出，
> 假岗位样例）。对照表数据**只准抄自**两侧 findings.json（模板纪律 1），
> 逐行由 `tests/quality/test_consumer_t5_acceptance.py` 机检。

## 报告头

| 字段 | 值（示例占位） |
|---|---|
| 项目 | example-dual-brand（虚构） |
| 专家面板 | `example-dual-expert`（5 镜头，本轮投影 5 条 findings） |
| 消费者面板 | `example-dual-consumer`（1 模拟人设 × C1–C5，本轮投影 5 条 findings） |
| 对照说明 | 两组独立评分域，本报告只并排呈现差异，不做合成 |

## 诚实盒

消费者评委 fake-title-buyer 为**模拟人设（合成角色）**：其开场白中的「持证采购
顾问」头衔与「替公司买过三次」经历是样例内的**不可验证声明**，无任何可核对证据；
非真实人物、非真实市场调研，不代表任何真实人群统计。

## 对照表（逐 lens 并排）

| 域 | lens | 结论（claim 摘录） | 状态 | evidence 摘录 |
|---|---|---|---|---|
| 专家 | origin（起源叙事） | 占位理由：样例设定中的起源叙事自洽，但缺第三方印证。 | needs_validation | 「占位理由：样例设定中的起源叙事自洽，但缺第三方印证。」 |
| 专家 | identity（身份系统） | 占位理由：样例设定中视觉与语言保持同一主张。 | needs_validation | 「占位理由：样例设定中视觉与语言保持同一主张。」 |
| 专家 | signal（真实信号） | 占位理由：样例设定没有可核对的真实使用数据。 | needs_validation | 「占位理由：样例设定没有可核对的真实使用数据。」 |
| 专家 | null（跨口径） | 占位结论：样例设定中叙事自洽、真实信号不足，结论留待复核。 | needs_validation | 「占位结论：样例设定中叙事自洽、真实信号不足，结论留待复核。」 |
| 消费者 | c1（第一印象） | 看着内行 | needs_validation | 「样例设定里这句话像我工作台上的工具该说的话。」 |
| 消费者 | c2（购买意愿） | 没有可核对凭证 | needs_validation | 「我替公司买过三次的经验没法在材料里核对，凭证缺失就不下单。」 |
| 消费者 | c3（价格直觉） | 没有可比价 | needs_validation | 「材料没给同行对照价，价格带说不清。」 |
| 消费者 | c4（信任与犹豫） | 担保不了 | needs_validation | 「我的头衔证明不了产品好坏，推荐家人等于我担保。」 |
| 消费者 | c5（表达欲） | 没意思转发 | needs_validation | 「没有可核对的实锤，转发它会显得我不专业。」 |

（专家侧另一条跨口径结论 F-expert-judge-005「占位缺口：样例设定没有提供与竞品的
对照数据。」与上表第五行同形态，为控表宽不单列；数据同抄自 findings-expert.json。）

## 差异解读（人工撰写，非机产）

- **一致处**：专家 signal（真实信号不足）与消费者 c2/c4（凭证缺失不买、担保不了
  不推荐）同向——同一实质问题「缺可核对证据」在两域以不同语言出现，并排呈现，
  不合并计数。
- **分叉处**：专家 identity 在样例设定内自洽（占位 7 分口径）而消费者 c1 只记
  「看着内行」——两域无共同量纲，只描述分叉事实，不裁决谁对。
- **盲区**：本轮两侧 findings **全部 needs_validation**——适配层不判三态升级；
  假岗位样例的头衔/经历声明无任何可验证证据，机器门不认岗位背书（confirmed=0）。
  三态升级留待评委复核或下一轮 synthesis 交叉验证。

## 纪律复核

- [x] 对照表数据全部抄自两侧 findings（无新增结论）
- [x] 未做跨域换算（消费者域唯一数值分是 C2 的 0–10 自评分，未与专家镜头分数平均或相减）
- [x] 盲区如实标注（全部 needs_validation，不补位）
- [x] 诚实盒置顶：模拟人设（假岗位样例），非真实市场调研，不代表任何真实人群统计
