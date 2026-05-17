# Auto Industry Panel — Judge Build PRD

**Status:** Implemented v0.2.20 — auto panel 5 位 perspective 已落地
**Created:** 2026-05-17
**Decision:** Path A 先建雷军已完成;随后补齐 4 位 production-seed v1。Stage 2
基础深调研已于 2026-05-18 落地。

---

## 1. Goal

把 `panels/auto.yaml` 从 SKELETON 状态升级到可用 —— 给 5 位汽车评委
(马斯克 / 雷军 / 李想 / 何小鹏 / 李斌)各建一份 `<slug>-perspective/` skill,
使得 `/mba <auto-brand> --industry auto` 能跑完整的 5 评委 Phase 4。

截至 2026-05-18,这个目标已完成。`leijun` 是 full v1;`musk` / `lixiang` /
`hexiaopeng` / `libin` 是 production-seed v1,均已有 6/6 路研究材料和
`quotes.md` URL-anchor bank。后续只剩 timestamp quote pass / 头像等增强项。

## 2. 为什么不能直接用 default panel

汽车品牌是个独立赛道。默认 5 评委(傅盛 / Jobs / 李可佳 / 吴俊东 / 张一鸣)
给汽车打分会有两个结构性短板:

1. **制造 / 供应链 / 资本密集度** 不在他们的高频心智模型里 —— 给小米 SU7、理想 MEGA、
   蔚来 ET9 打"leverage quality"时,会下意识用 SaaS / Agent 的杠杆框架硬套硬件公司,
   出来的判断对创始人没参考价值。
2. **品类边界** —— 默认 5 位主要在"软件产品 / 教育 / 字节系"打转,对车这个
   "消费 + 工业 + 出行服务 + 自动驾驶赌注" 的混合体没有第一人称判断。

5 位汽车创始人 CEO 都在用自己的方式回答"硬件公司怎么做影响力",他们的对照可比性
比硬塞乔布斯回答小米 SU7 显著更高。

## 3. 单评委 baseline —— 跑现有 5 位实际花了多少

按当前仓库 `<judge>-perspective/` 的实际产出量(2026-05-17 snapshot):

| 评委 | SKILL.md 行数 | references/research/ 文件 × 行数 | 备注 |
|---|---|---|---|
| fusheng | 495 | 6 × 1683 | 中等密度 |
| jobs | 486 | 6 × 2100 | 高密度(英文长 transcript 多) |
| likejia | 482 | 6 × 765 | 最低(本人公开材料相对少) |
| wu-jundong | 587 | 7 × 1884 | 多一份 EdTech Insiders 英文长访谈 |
| zhang-yiming | 488 | 6 × 2414 | 最高(38000+ 字) |

**单评委工程量 baseline**:SKILL.md ~500 行 + 6 路调研 ~1500-2400 行 = 一份认真做的
perspective skill。**3-5 天**是合理估计(单人,熟悉 /research --persona-mode 模板)。

## 4. 候选评委评估

谁先建?按"源密度 × 第一人称占比 × 与现有 perspective 的差异度"排序:

| 评委 | 源密度 | 第一人称比例 | 差异度 | 总评 |
|---|---|---|---|---|
| 雷军 | ★★★★★ (年度演讲 11 年连续脚本 + 微博 + 抖音直播 + 早期金山访谈) | ~70% | 中(产品/营销跟现有有重叠,但加了硬件工业) | ★★★★★ |
| 马斯克 | ★★★★★ (X / Rogan / Lex Fridman / Isaacson 传记) | ~80% | 极高(全英文 + 工业 + 太空 + 政治杠杆) | ★★★★ |
| 李想 | ★★★★ (微博 6800+ 条 / 内部信泄露 / 财报会 / B 站 vlog) | ~75% | 高(智能驾驶 + 用户社区 + 增程派) | ★★★★ |
| 李斌 | ★★★ (NIO Day 主题演讲 / 用户面对面 Q&A / NIO House transcripts) | ~60% | 中(高端服务 + 换电体系 + 资本紧绷) | ★★★ |
| 何小鹏 | ★★ (财报会 / 知乎专栏 / 公司发布会 / 不爱长文) | ~50% | 中(智驾派 + 出海 + 工程派) | ★★★ |

**推荐先建雷军**:

1. **源材料最齐** —— 11 年小米年度演讲连续脚本是一份"思维博物馆",可以做时间序列
   voice drift 分析(2010 工程师 → 2020 营销天才 → 2024 价值观主义者)
2. **跨界判断最丰富** —— WPS / 卓越亚马逊 / 顺为 / 小米 / 玄戒 / SU7 给"杠杆质量"
   这条镜头有充足的发挥空间
3. **三轴清晰** —— "工程师 / 营销天才 / 价值观主义者"三角适合提炼成 3 个核心心智模型
4. **跟傅盛 voice 共振但不重叠** —— 都有"反共识"姿态(雷军"感动人心 / 价格厚道"
   vs 傅盛"反共识断言"),工程上能复用部分表达 DNA 模板,但落点很不同
5. **2024-2025 SU7 上市这段汽车-互联网跨界判断** —— 对小米品牌审计的命中率最高,
   建完立即有 dogfood 价值(Path A 第 4 步)

## 5. Path A — 先建 1 个(推荐 ★)

先单独建 1 个,验证 perspective 模板能不能套到"汽车创始人"这个新声音上。
完成 + dogfood 后再决定剩下 4 个。

| Step | Time | 产出 |
|---|---|---|
| 0. 候选锁定 | 0.5 day | 决定建谁(本 PRD 第 4 节已经推荐了雷军) |
| 1. 6 路并行调研 | 1-2 days | `/research 雷军 --persona-mode` 拉出 references/research/01-06.md(~1500-2000 行) |
| 2. 综合 → SKILL.md | 1 day | 6 个心智模型 + 8-10 决策启发式 + anti-fab 边界 + 触发规则 |
| 3. 单跑测试 | 0.5 day | `/leijun-perspective <随机话题>` 单独调用,验证 voice 不串调 |
| 4. 整合测试 | 0.5 day | 把 auto.yaml 改成"只列他一人 + 删 status: skeleton",跑 `/mba xiaomi --industry auto` 看 1-of-5 降级路径 |
| 5. 提交 + dogfood | 0.5 day | 提交 perspective skill + 调整 panel yaml + 在小米品牌报告里把雷军的金句单独拎一节 |

**总计**: **3-5 days**

### Path A 完成后的三种产出

1. 一个可调用的雷军 perspective skill —— 小米/红米/玄戒等品牌审计立刻能用上单视角
2. 一份 **"auto judge build 模板增量"** —— 把汽车维度对原 perspective 模板的修正
   沉淀下来(比如硬件公司的 anti-fab 类目新增什么),后面 4 个直接套
3. 决策点:跑完这一轮再判断 "投不投剩下 4 个 vs 跳到别的行业(教育/消费品)"

## 6. Path B — 5 个并行

5 个一起跑。看上去并行能省时,实际上会踩三个坑:

1. **模板没验证就批量** —— 5 个 SKILL.md 都基于"现有 perspective 是好模板"的假设。
   如果汽车判断里有结构性的新维度(比如"对工业制造规模化的态度"),5 个全要返工。
2. **判分相似度** —— 4 位中国新势力都被资本市场训练成"用户至上 + 智驾 + 出海",
   批量造容易出 5 张高度相似的分数表,Phase 5 异议热力图直接趴平。先建 1-2 个看清
   差异度,再决定后面 3 个怎么写出区分镜头。
3. **/research --persona-mode 并行容量** —— 6 路并行 × 5 评委 = 30 个 sub-agent,
   远超平台 5 agent ceiling,会被强制串行成 6 个批次,实际省时间有限。

### Worst-case 工作量

| Step | Time | What |
|---|---|---|
| 0. 5 个候选并排建 candidate doc | 1 day | 同时设计 5 份调研框架 |
| 1-3. 5 × (调研 + 综合 + SKILL.md) | 12-20 days | 即使 2 个并行也要 6-10 天 |
| 4. 跨人 voice 区分测试 | 2-3 days | 5 个 perspective 互相对照"会不会一锅粥" |
| 5. 整合 + dogfood + 修 | 2-3 days | 真跑一次 5 评委 auto panel,看异议是否健康 |

**总计**: **17-27 days(2-3 周到一个月)** ,且返工概率不低。

## 7. Risks(两条路都适用)

| Risk | 描述 | 缓解 |
|---|---|---|
| Persona drift across time | Musk 2018 vs 2024 几乎是两个人;雷军 2010 金山 vs 2024 造车 voice 漂移明显 | 在 SKILL.md 顶部明确锚定 "as of 2026-05",更早期论述列在"历史立场"段而非主立场 |
| Dynamic numbers 多 | SU7 月销 / NIO 现金流 / 理想交付 / 小鹏出海销量 / Tesla FSD ARR 都会变 | anti-fab 段加新条:"不在 perspective 文件里嵌任何 2026 年后的具体数字" |
| 跨评委判断雷同 | 4 位中国新势力对小米的判断容易指向同一种焦虑 | Path A 单独建 1 个能更早识别"需要强行植入差异化镜头"这件事;Path B 把这个发现推迟到第 12 天 |
| 硬件/工业制造维度供给不足 | 现有 5 perspective 主要软件视角。Phase 3 synthesis 可能没给硬件杠杆/工业摊销/电池工厂留足够信息位,汽车评委拿不到能咬的肉 | 可能需要在 `references/dimensions.md` 加汽车专用维度补丁(供应链 / 制造 / 监管)。Path A 是验证这件事的好场合 |
| 评委对应公司有利益冲突 | 雷军给小米打分、李想给理想打分,扣分很难 | Phase 0 加入"如果 brand-slug 命中评委所属公司,跳过该评委或者强制给出 disclaimer"(本 PRD 暂不解,留 follow-up) |

## 8. Recommendation

**Path A,先建雷军**。3-5 天投入,完了能拿到:

1. 一个真实可调用的雷军 perspective skill
2. 一份模板增量,把汽车维度对原 perspective 模板的修正沉淀
3. 一个"投不投剩下 4 个"的决策点

不推荐 Path B 的核心原因不是工作量,是 **"在没验证模板时批量造 5 个,返工的成本
远高于串行的成本"** 。

## 9. Out of scope

本 PRD 不解的事项,留各自的 follow-up:

- 评委-公司利益冲突 gate(Phase 0 自动 disclaimer 或跳过)
- `references/dimensions.md` 的汽车专用维度补丁
- perspective skill 完全自动化生成(/research --persona-mode 已经半自动,完全自动是另一个工程)
- panel 推荐器(根据品牌名自动建议 --industry)
- 不同行业 panel 之间的 cross-judge composability(选 auto 的雷军 + default 的傅盛)

## 10. Next decision

跑完这份 PRD 后,下一步改为 Stage 2:

- [x] 接受 Path A,开始建雷军 perspective
- [x] 发布 `leijun-perspective` full v1
- [x] 补齐 4 位汽车评委 production-seed v1
- [x] 为 `musk` / `lixiang` / `hexiaopeng` / `libin` 补 Stage 2 深调研基础包
- [x] 给 4 位 production-seed auto judge 补 `quotes.md` URL-anchor bank
- [x] 为 self-conflict 补 panel 文档和 `auto.yaml` 默认 drop 规则
- [ ] 给每位 auto judge 补 portrait
- [ ] 为 self-conflict 做 Phase 0 runtime 自动提示 / 默认 drop
