# PRD-178/T1：消费者评委人设与题组草案

> trend issue #890。对应 PRD-178（中央仓库 zhanglunet/trend）。
>
> 定位：给 43 位专家评委补"非专家大众"视角——模拟消费者人设 + 消费者题组，
> 与专家评委形成"专业 vs 市场"双视角。T1 只出人设与题组草案（人设卡 + 题组 +
> 集成方式设计），不写实现代码；不改 5 镜头评分口径与专家评委业务逻辑；消费者
> 分数与专家分数**不换算、不平均**（报告分开展示）。
>
> 依据（仓库现状，2026-10-25 实测）：`perspectives/` 下 43 套 `*-perspective/`
> 全部是真实行业人物扮演；5 镜头尺子（Origin / Category / Leverage / Identity /
> Signal，各 1–10）由 judge-prompt-template STEP 3 固定；panels/README 明言
> "5 镜头是固定的尺子，坐在尺子后面打分的人是可换的"，并给出加评委端到端 6 步；
> panel yaml 仅 `name` + `judges[*].slug` 必填（language/portrait/weight 可选）；
> perspective-structure-spec.md 冻结 5 个必需 H2；tier 体系 seed / full（docs/10）。
>
> 非目标纪律：本阶段用**模拟人设**，不做真实人群众包；不收集真实用户 PII。
>
> 借鉴：anthropics/knowledge-work-plugins（Apache-2.0，Copyright © Anthropic PBC）——
> 只借鉴其"面向职业角色的 skill 插件封装形态"（SKILL.md frontmatter 显式触发 /
> 不激活描述 + references/ 支撑材料渐进披露 + 单目录自包含），用于消费者评委的
> 组织方式；原项目：<https://github.com/anthropics/knowledge-work-plugins>。
> 本文档全部人设、题组、字段、措辞均为本仓库自研，未复制其文本。

## 一、现状与缺口：为什么消费者评委不能直接套 5 镜头

| 既有资产 | 为专家视角设计 | 对"非专家大众"的问题 |
|---|---|---|
| 5 镜头（1–10 × 5 维） | Origin authenticity / Category coinage / Leverage quality 是行业分析与创业判断概念 | 普通消费者不做品类定义、不评杠杆结构——题面本身在邀请扮演专家 |
| 43 套人设 | 全部真实行业人物，有公开语料可考 | "大众"没有可扮演的真实个体；虚构一个"真实人物"直接撞反捏造防火墙 |
| panel yaml（10 套） | 全行业 panel，无消费视角组 | 报告只有"专业 how"，缺"市场 first impression / 购买意愿"信号 |
| reviews/<slug>.md 格式 | Scores 表 / Verdict / Critical gap / Brand action | 消费者答卷形态不同（见 §三），但需保持 Lead 聚合管线可读 |

结论两条：① 消费者评委必须是**合成人设**（synthetic persona）——人设的"语料"是
场景设定文本，不是人物语录；这是与 43 套专家评委最大的结构差异，防火墙语义随之
适配（§四）；② 消费者评委用自己的题组（§三），与 5 镜头并排展示、不进同一平均。

## 二、消费者评委人设草案（5 套，T2 实现至少 3 套）

人设用"**决策风格 × 信息来源**"定义，不用人口学标签（年龄/性别/地域不写死，
留为场景参数）——防刻板印象是 PRD 风险项，T1 的多样性检查即验收线（§七.2）。
slug 沿仓库命名对齐规则：目录 `<slug>-perspective/`，slug 写法与目录前缀严格一致。

| slug（建议） | 人设卡一句话 | 决策风格 | 主信息来源 | 对营销话术的态度 |
|---|---|---|---|---|
| `first-glance-shopper` | 货架/商详页 3 秒扫描型：凭视觉与一句话价值主张做直觉判断 | 直觉快判 | 商详页、门店陈列 | 有好感但记不住就划走 |
| `homework-buyer` | 买前必做功课：第三方评测、差评区、横评对照，交叉验证宣传点 | 研究验证 | 评测内容、用户评价 | 宣传点必须能被第三方印证 |
| `brand-skeptic` | 默认不信：先问谁在背书、有没有翻车记录，反感话术 | 怀疑求证 | 第三方便评、舆情搜索 | 反感话术，信负面信息多于正面 |
| `early-adopter` | 新品即试：在乎新鲜感与社交分享价值，容忍早期瑕疵 | 尝鲜传播 | 新品发布、社区讨论 | 愿为"第一个用"买单 |
| `value-counter` | 精算型：算单次使用成本、比价格带、等促销，券敏感 | 精算比价 | 比价工具、历史价格 | 价格不是锚点就不进购物车 |

每人设 = 一个自包含目录 `perspectives/<slug>-perspective/`（沿 knowledge-work-plugins
的单目录自包含形态，但落位与专家评委同构，复用既有 panel resolver 与
`${PERSPECTIVES_PATH}` 探测，不新开插件包装层）：

```text
perspectives/<slug>-perspective/
├── SKILL.md                      # 过 5 段结构规范（§四的变体）
└── references/
    └── scenario.md               # 场景设定 + 消费者口吻样例句（替代专家的 quotes.md）
```

SKILL.md frontmatter 沿仓库现役格式（参照 satyanadella-perspective）：
`name` / `description`（含 `Use as` + `Explicit triggers`，如"用普通消费者视角看"、
"第一印象/购买意愿"；`Do not activate when`：需要行业专业判断、真实市场数据时
不激活）+ 5 个必需 H2。

## 三、消费者题组设计（C1–C5，替代 5 镜头）

| 题号 | 题面 | 输出形态 | 机读去处 |
|---|---|---|---|
| C1 | 第一印象：看到品牌名 + 一句主张，你记住了什么、感觉是什么 | 一句话 + 3 个印象关键词 | findings（lens=c1） |
| C2 | 购买意愿：会买吗 | **0–10 分**（消费者域唯一数值分）+ 一句主因 | findings（lens=c2） |
| C3 | 价格直觉：贵了 / 值了 / 说不清 | 三选一 + 可接受价格带（占位描述，不编造真实市场价） | findings（lens=c3） |
| C4 | 信任与犹豫：哪里让你犹豫？会不会推荐给家人 | 逐条列犹豫点 | findings（lens=c4） |
| C5 | 表达欲：会转发 / 吐槽吗 | 会 / 不会 + 消费者口吻一句话 | findings（lens=c5） |

输出格式对齐 `reviews/<slug>.md` 表格形态（Lead 聚合管线零改动可读）：

```text
# <人设名>（模拟消费者） on <brand>

## Consumer Answers
| Question | Answer | Key phrase | Why |
|----------|--------|------------|-----|
| C1 第一印象 | ... | <3 关键词> | ... |
| C2 购买意愿 | 6 | <一句主因> | ... |
| ...

## One-liner verdict
（消费者口吻一句话）

## Would I share it?
（C5 的会/不会 + 原话）
```

纪律三条：① C2 是消费者域唯一数值分，**与专家 5 镜头不换算、不平均、不进
Score Matrix**；② 语言沿 panel yaml `judges[*].language`（与专家同规）；
③ 人设不编造购买经历——场景设定里没发生的"我买过"一律不说（§四防火墙）。

## 四、结构规范与防火墙适配（合成人设的防捏造语义）

1. **structure spec 变体**（T2 改 `perspective-structure-spec.md`，文档增补
   "消费者人设变体"一节，不改专家必需集）：5 个必需 H2 全部沿用，语义映射——
   - `Core Mental Models` → 消费决策心智模型（价格锚、口碑传导、社交货币等，
     引用 scenario.md 设定而非人物语录）；
   - `Honest Boundary` → 必写"**我是模拟人设，非真实人物；无真实购买经历与
     人口学身份**"+ 研究截止日期；
   - `Anti-Fabrication 红线` → 不虚构销量、市场份额、真实用户数、具体价格事实；
     不虚构"我买过/我朋友用过"的经历；场景设定没有的细节说"不知道"；
   - `Self-Conflict Rule` → 场景设定关联品类主动申请 `--panel-drop`；
   - `Sources` → 指向 `references/scenario.md`（逐条列场景设定条目）。
2. **tier 适配**：消费者人设 seed tier = SKILL.md（过 5 段结构规范）+
   `references/scenario.md`（场景设定 + ≥10 条消费者口吻样例句，URL 锚定不适用，
   以设定条目编号锚定替代）；不做 full tier 6 路调研（无真实语料可查）。
3. **防火墙语义适配**（T2 落地，T1 只定语义）：firewall_check 的"SKILL 内逐字引用
   必须在语料中逐字存在"对消费者人设生效，但引用对象 = 该人设自己的
   `scenario.md`；PRD-177 findings 的 `evidence[].quote` 同理（kind 增
   `scenario` 候选，随 T3 定稿——本 T1 不改 PRD-177 schema）。

## 五、panel 集成设计（向后兼容的最小扩展）

1. **panel yaml 新增可选字段** `judges[*].role: expert|consumer`（缺省 `expert`，
   全部 10 套既有 panel 零改动；`validate_panels.py` 校验扩展为枚举检查 +
   consumer 评委必须解析到对应人设目录）。
2. **新 panel** `consumer-mixed.yaml`（T2 入库）：4–5 位消费者评委（§二至少 3 套
   已实现者上场），`name: consumer-mixed`，描述写明"模拟消费者视角，非真实
   市场调研"；`tests/panels/test_consumer-mixed.py` 沿 PRD-022 逐 panel 测试惯例。
3. **混合同场**：既有行业 panel 可追加 `role: consumer` 行实现"专家+消费者"同场；
   Lead 聚合时按 role 分组，消费者组独立成表（`## Consumer Panel`），不进
   专家 Score Matrix。
4. **judge-prompt-template 适配**（T2）：STEP 3 按 `role` 分支——`expert` 走既有
   5 镜头（一字不动），`consumer` 走 C1–C5 题组；STEP 5 按 role 选输出格式
   （§三模板）。专家分支零改动，风险面收敛在新增分支。

## 六、与 PRD-177 三态 findings 的对齐及对比报告预告

1. **findings 对齐（T3，#892）**：消费者结论逐条进 findings.json——C1/C3/C4/C5 的
   定性结论与 C2 低分主因映射为 finding；`lens` 字段使用 PRD-177/T1 已预留的
   `c1`–`c5` 枚举；三态判定沿 PRD-177 §2.3（evidence 指向 synthesis 或该人设
   scenario.md；"我说不清"类答案天然落 needs_validation，不带定论）。
2. **对比报告模板（T4，#893 预告）**：report.md 新增 `## Expert vs Consumer` 章节，
   固定结构——① 诚实盒置顶："消费者评委为模拟人设（N≤5），非真实市场调研，
   不代表任何真实人群统计"；② 专家表与消费者答卷表并排，**不平均**；
   ③ 共识区（专家低分 ∩ 消费者低购买意愿）/ 分歧区（专家高分 ∩ 消费者无感）
   各列 Top3；④ 措辞纪律：只说"模拟消费者视角信号"，不说"市场验证"。

## 七、T1 验收自检与下一步

1. **题组自检**：C1–C5 覆盖 PRD 目标两个关键词——第一印象（C1）、购买意愿
   （C2）；输出对齐 findings 机读 + reviews 表格双载体。
2. **多样性检查（PRD 风险项验收线）**：5 人设决策风格互斥（直觉/研究/怀疑/尝鲜/
   精算各一）；信息来源覆盖 ≥5 种渠道（商详/评测/便评/新品社区/比价）；无人口学
   刻板印象绑定（年龄/性别/地域未写入人设卡，留为场景参数）；无真实 PII。
3. **非目标复核**：不做真实众包；不收集 PII；专家 5 镜头与分数管线零改动；
   消费者分数不与专家平均。
4. **下一步**：确认后进 T2（#891）：实现至少 3 个消费者评委 skill——按 §二目录
   形态入库（建议首批 `first-glance-shopper` / `homework-buyer` / `brand-skeptic`）、
   scenario.md、structure spec 变体节、`consumer-mixed.yaml` + panel 测试、
   judge-prompt-template role 分支。T1 验收线：本草案评审通过（#890）。
