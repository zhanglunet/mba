# 02 — 产品设计

本文档描述 MBA 用户能看到、能感知、能交互的所有"前台"部分:用户旅程、报告产物、交互细节、评委卡片、维度语义。

## 1. 用户旅程图

```
[用户在 Claude Code 里说: "用 mba 审 OpenClaw"]
        │
        ▼
   [Phase 0 路由器]
   ├─ 已有报告 + 没传 --refresh → "Found v1, switching to EVOLUTION"
   └─ 没有 / 强制刷新           → "No prior report, fresh pipeline"
        │
        ▼
   [Phase 1 — Discovery / Diff plan]
   Lead 起草 PRD → 在对话里展示给用户
        │
        ▼
   [GATE 1 — 用户确认]
   用户可以:
   - "ok 跑吧"
   - "把维度 5(视觉)去掉,只关心商业部分"
   - "这次用 --panel vc-en"
   - "临时 --panel-drop jobs"
   - "改 brand-slug 为 openclaw-2026q2"
        │
        ▼
   [Phase 2 — 并行调研]   约 10-15 min
   用户看不到具体过程,只在 Claude Code 看到 sub-agent 数量 + 完成进度
        │
        ▼
   [Phase 3 — Lead 合成]
        │
        ▼
   [Phase 4 — N 位 panel 评委独立打分]   约 5-8 min
        │
        ▼
   [Phase 5 — Lead 合并 + HTML 渲染]
        │
        ▼
   [Lead 在对话里给出 TL;DR + 链接]
```

## 2. 报告产物的视觉设计

### 2.1 markdown 报告(`report.md`)

固定 8 个章节(顺序固定,任何品牌都一样):

```markdown
# {Brand} — Brand Influence Review (v{n})

**Date:** YYYY-MM-DD
**Mode:** FRESH | EVOLUTION
**Panel:** default | vc-en | ...
**Dimensions analyzed:** 1, 2, 3, 4, 5, 6, 7
**Judges:** {resolved panel judge slugs}

## TL;DR — How {Brand}'s influence is constructed
{4-6 bullets,Lead 自己的声音}

## Score Matrix
{5 镜头 × N 评委的打分表 + 均值}

## Where the judges agree
{跨评委共识 3-5 条}

## Where the judges disagree (最有价值的章节)
{评委 A vs 评委 B 在哪个镜头分歧最大,quote 各自原话}

## Lead's read
{Lead 综合判断:杠杆地图、脆弱边缘、未解之谜}

## Action recommendations (next 90 days)
{3-5 条具体建议,按 leverage 排序}

## Citations
{去重合并所有 sub-agent 的引用}

## Versions
- v1 — YYYY-MM-DD — initial review
- v2 — YYYY-MM-DD — delta on dimensions {3, 7}: {one-line summary}
```

### 2.2 HTML 报告(`report.html`)

自包含单文件(只引 Chart.js / Mermaid CDN,无其他依赖)。布局从上到下 9 块:

| # | 块 | 工具 | 关键设计 |
|---|---|---|---|
| 1 | Hero | 纯 HTML/CSS | 品牌名 / 版本 badge / mode 标 / 一句 TL;DR |
| 2 | Score Radar | Chart.js radar | 5 镜头为辐条,每评委一彩色多边形,共识区一眼可见 |
| 3 | Score Bar | Chart.js bar | 评委总分横向对比 |
| 3b | **Dissent Heatmap** | 纯 HTML+CSS grid | **5×5 + σ 列**,低 σ 行 = 共识、高 σ = 撕扯,最高价值的"扫一眼"surface |
| 4 | Influence Construction | Mermaid flowchart LR | 维度做源 → 放大器 → 可观察表面,边标 leverage 假设 |
| 5 | Brand Positioning Quadrant | Mermaid quadrantChart | Lead 选轴(如"founder-driven ↔ product-driven" × "domestic ↔ global"),品牌 + 3-5 竞品定位 |
| 6 | Judge Cards | 纯 HTML | 每评委一张折叠卡:portrait emoji + verdict 一句 + 金句引用 + 评分行 |
| 7 | Sentiment Trend | Chart.js line | 仅当 Phase 2 拿到时间序列时显示,否则 N/A |
| 8 | Brand Essence Mindmap | Mermaid mindmap | 品牌为根,7 维度为枝,每枝顶 2-3 finding |
| 9 | Action Recommendations | 纯 HTML | 编号 + leverage badge(high/med/low) |

**配色 / 排版规则:**

- CSS 变量调色板顶部统一管理(`--c-judge-1..5` 给 5 评委区分色)
- `prefers-color-scheme` 自动深色模式
- 最大宽度 960px(对抗"AI 生成式无脑全宽"的反例)
- 系统字体(`system-ui` stack),离线可读
- `@media print` 友好,合并到一页可打印

### 2.3 中间产物(`_raw/`)

不给最终用户主动看,但是 EVOLUTION 模式必读:

- `dimension_<n>_<slug>.md` — 每个 sub-agent 的原始输出
- `wuying_browse.md` — 云浏览器观察日志(含 session metadata、teardown 状态)
- `synthesis.md` — Lead 在 Phase 3 写的合成草稿(评委的输入)

## 3. 评委卡片的人格化设计

每位评委有 4 个"用户可见信号":

1. **portrait emoji**(无真人头像)—— 一个能联想到的字符:
   - 🐆 傅盛(猎豹)
   - 🍎 Steve Jobs
   - 🦞 李可佳(BotLearn 龙虾)
   - 📚 吴俊东(教育/书)
   - 🐘 张一鸣(字节跳动 logo 演化)
2. **verdict 一句话**(in character)—— "这个品牌的杠杆是渠道,不是产品,渠道断了就归零。"
3. **金句**(签名风格的一句)—— "卷不动的时候不是再卷一点,是换一个不卷的池子。"(傅盛风)
4. **5 镜头分数行**(整数 1-10)—— 配合卡片边框颜色按总分四分位染色

**反过度卡通化的纪律:**

不写"傅盛认为...",而是评委自己第一人称说话。这要求每个 perspective skill 的 SKILL.md 顶部明确"以第一人称表达"。如果评委卡片读起来像"AI 在模仿傅盛",就是坏迹象 —— 应该读起来像傅盛自己写的短评。

## 4. 维度的语义边界

7 默认维度的设计原则:**互斥但不穷尽,可选 5-7 条**。

| # | 维度 | 一句话 | 易混淆边界 |
|---|---|---|---|
| 1 | 创始 & 起源叙事 | 谁讲、讲了什么、回避了什么 | vs 5(视觉) — 起源是文字层,视觉是符号层 |
| 2 | 产品 & 定位 | 一句话定位 + 新品类宣称 | vs 6(竞品) — 定位是自我宣称,竞品是外部对照 |
| 3 | 分发 & 渠道 | 第一次被看到的地方 + paid/owned/earned 比例 | vs 4(社区) — 渠道偏 acquisition,社区偏 retention |
| 4 | 社区 & PR | 谁站台、谁攻击 | vs 7(情绪) — 社区偏定性,情绪偏定量 |
| 5 | 视觉 & 语言 | 命名、slogan、元符号(如 OpenClaw 的 🦞) | 是 |
| 6 | 竞品 & 格局 | 谁让出地盘、谁借用了它的语言 | 是 |
| 7 | 接收 & 情绪 | 量化信号:搜索趋势、增长、媒体口径 | 是 |

**为什么是 7 不是 10 不是 5:**

- 5 太少,会塞不进"竞品"或"视觉"
- 10 太多,sub-agent 数 ≥ Anthropic 并发限制,要分批拖慢
- 7 刚好 1 批跑 5 个 + 1 批跑 2 个,流水线不切片

## 5. 5 镜头的设计原则

5 个镜头**不是按 7 维度拍照**,而是评委从这 7 维度里**抽出**自己看重的信号。每个评委给同一镜头打不同分,正是因为他们各自有不同的"看重哪个维度"。

| 镜头 | 在问什么 | 谁会给低分 |
|---|---|---|
| Origin authenticity | 创始故事是真的吗 | 看穿 PR 的评委(傅盛) |
| Category coinage | 是否真命名了一个新东西并粘住 | 在意品类定义的评委(Jobs / 李可佳) |
| Leverage quality | 主导渠道是否结构性可持续 | 看渠道的评委(张一鸣) |
| Identity coherence | 视觉/语言/产品是否同一感觉 | 设计敏感的评委(Jobs) |
| Real-world signal | 你愿意为之下注吗 | 投资人逻辑的评委(吴俊东) |

**设计意图:让评委的分歧本身成为产品价值。** 共识固然好,分歧才是 outsider 视角真正暴露真相的地方。

## 6. 异议热力图(Dissent Heatmap)— 高价值组件详解

5×5 grid + σ 列,是 HTML 报告里**最高价值的扫一眼界面**。

```
          fusheng  jobs  likejia  wu-jundong  zhang-yiming     σ
Origin    [  7  ]  [ 6 ]  [  8  ]  [    7   ]  [     6     ]  [ 0.7 ]   ← 共识
Category  [ 10 ]  [ 4 ]  [  9  ]  [    7   ]  [     5     ]  [ 2.3 ]   ← 撕扯
Leverage  [  6 ]  [ 5 ]  [  6  ]  [    5   ]  [     6     ]  [ 0.5 ]
Identity  [  4 ]  [ 9 ]  [  6  ]  [    5   ]  [     5     ]  [ 1.7 ]
Signal    [  8 ]  [ 5 ]  [  9  ]  [    7   ]  [     7     ]  [ 1.4 ]
```

**颜色规则:** 格子按 1-10 从红到绿;σ 列按 0-3 从浅到深。

**读图法:**

读者扫一眼 σ 列,看到 σ=2.3 的行,知道"评委对'范畴命名是否成立'有真实分歧",再点开评委卡片看 quote。这比单纯看均值有信息密度高得多 —— 共识告诉你"这个事儿大家都说",分歧告诉你"这里有故事"。

## 7. 交互细节

### 7.1 PRD 展示

PRD 以 markdown 形式直接打到对话里(不落盘到 `_raw/`),用户在对话框里读 + 编辑。Lead 接受这几种 user reply:

- "ok" / "go" / "确认" / "跑吧" → 进入 Phase 2,使用原 PRD
- 任何带"删除维度"/"加维度"/"改 slug"/"减评委"语义的回复 → Lead 应用编辑后进入 Phase 2
- "cancel" / "取消" / "停" → 终止,什么都不写

### 7.2 进度展示

Phase 2 / Phase 4 是 sub-agent 并行,每个 agent 在 Claude Code UI 里有自己的进度条。Lead 在 sub-agent 全部返回后才推进到下一 phase,不"边跑边讲"。

### 7.3 终态展示

Lead 给 4 件东西:

1. 一段 TL;DR(Lead 自己的声音,不是任何评委的)
2. Score Matrix 表格内联在对话里
3. `report.md` 和 `report.html` 路径
4. 后续建议("要深挖某个评委吗?要重点关注竞品 X 吗?")

不主动 `open` 文件,等用户决定要不要打开。

## 8. 多语言

报告以**中文为主,英文术语保留**:

- 章节标题英文(易于跨语言用户扫读)
- 正文中文
- 评委 quote 保持评委原语言(Jobs 是英文,其他评委是中文)
- 引用源 URL 不翻译

理由:目标用户是中国创投圈,但 Jobs 这位评委必须英文才地道。

## 9. 失败状态的产品体验

### 9.1 部分维度失败

报告 TL;DR 顶部显式说"维度 N 调研失败,Confidence: low",并在 Citations 章节给出已掌握信息的边界。**不假装数据完整**。

### 9.2 全部 sub-agent 失败

返回 partial report:只有 PRD + 失败原因 + 建议(retry / quick mode / 检查 API key)。不写 `report.md`(以免污染 EVOLUTION 入口)。

### 9.3 wuying leg 完全降级

报告里 X / RedNote / Bilibili 这几个维度的"first-person framing"会标 "N/A — wuying leg unavailable, web-only fallback used"。评委打分仍照常进行,但他们看到的素材确实是 web-only 的子集。

## 10. 设计反例(明确不做的)

- ❌ 不做"评委协商"(评委趋同 = 价值丢失)
- ❌ 不做"权重打分"(隐式优先级 = 隐式偏见)
- ❌ 不做"自动 publish 到博客"(用户决定要不要分享)
- ❌ 不做"实时 sentiment dashboard"(超出 scope,见 PRD §7)
