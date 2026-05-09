# 08 — 扩展指南(添加品牌 / 评委 / 维度 / 模板)

本文档面向想往 MBA 里加东西的贡献者。

## 1. 添加新品牌报告(最简,日常使用)

不用改任何代码。直接:

```
/mba <new-brand-name>
```

Lead 自动:

- 在 `metric-brand-auditor/reports/<brand-slug>/` 下建目录
- 跑全流程
- 落 report.md / report.html / versions/v1_<date>.{md,html}

如果想用自定义 slug(默认是 brand 名小写化):

```
/mba "字节豆包"
> 在 GATE 1 时 Lead 会问 slug,你回 "bytedance-doubao"
```

## 2. 添加新评委

新评委 = 一个新的 `*-perspective/` 目录,跟现有 5 个同结构。

### 2.1 复制模板

```bash
cd ~/mba
cp -r fusheng-perspective my-judge-perspective
cd my-judge-perspective
```

### 2.2 改 SKILL.md

**至少改:**

- frontmatter `name: my-judge`
- frontmatter `description:` 完全重写,描述 TA 是谁、什么时候触发、什么时候不触发
- "## 核心心智模型" / "## 决策启发式" 全部重写(≥ 5 条)
- "## 表达 DNA" 全部重写(带样例,展示 ≥ 3 句"这就是 TA 会说的话")
- **"## Anti-fabrication 红线" 必须有**(否则未来 MCP add_judge 会 reject)

### 2.3 替换 references/research/01-06.md

这 6 个文件是 TA 的"调研材料"。要么:

- **手动写**:你自己读够 TA 的访谈/文章,自己整理 6 个文件
- **跑研究脚本**:每个 perspective 目录有 `scripts/`,内含 `merge_research.py` 之类工具,但需要你先用 Claude Code 跑一轮调研拿到 raw 资料

理想流程(MVP):

```
1. 在 Claude Code 里说: "调研 X 这个人,用 perspective skill 的 6 路并行模板"
2. Claude 跑 6 个 sub-agent,各自落到 my-judge-perspective/references/research/01-06.md
3. 跑 scripts/quality_check.py 校验占位符 / 一手来源比例(如果存在)
4. 把 01-06 的结论手动归纳进 SKILL.md 的"核心心智模型"和"表达 DNA"
```

### 2.4 注册到 MBA(可选)

如果想让 `/mba <brand>` 默认带上 TA,改 `metric-brand-auditor/SKILL.md`:

- 找到 `**Judge panel:** 5 perspectives — fusheng, jobs, likejia, wu-jundong, zhang-yiming`
- 加上 `, my-judge`
- 找到 Phase 4F 的 mapping table,加一行 `my-judge → ~/mba/my-judge-perspective/SKILL.md`
- 找到 HTML 模板的 Score Matrix 章节,把 5 列改 6 列
- 找到 "5 judges = 1 batch" 的并发说明,改成 "6 judges = 2 batches"

> 6+ 评委 = Phase 4 一批跑不完(超 Anthropic 5 并发上限)。Lead 会自动分两批,但要在 SKILL.md 里加一句说明。

### 2.5 试跑

```
/mba <某个 demo 品牌> --judges my-judge
```

只让你的新评委参与,看输出符合不符合预期(in-character / 没编造 / score 解释成立)。

## 3. 添加新维度

### 3.1 改 dimensions.md

`metric-brand-auditor/references/dimensions.md` 加一条:

```markdown
## 8. 创始人 Twitter 阵地
- 创始人发推频率 / 互动率
- 一周内最高互动推文 + topic
- ...

Search seeds: <founder> twitter; <founder> X; ...
```

### 3.2 改 SKILL.md 的 Default Dimensions 表

把 7 改 8,把表格新增一行,确保新维度的 sub-question 描述清晰。

### 3.3 留意并发上限

7 维度 + wuying = 8 → 5 + 3。
8 维度 + wuying = 9 → 5 + 4。仍然 2 批,但第二批从 3 涨到 4,稍慢。

> 维度多于 9 的 brand 是设计味儿太重的信号 —— 多半你应该把多余维度合并而不是保留。

### 3.4 历史 brand 的 EVOLUTION 兼容性

新加维度后,跑历史 brand 的 EVOLUTION 时 Lead 会发现"上版没有 dim 8",要决定:

- 把它当 brand new dim,跑全调研补上
- 或在 GATE 1E 显式跳过新维度,保持向后兼容

## 4. 修改 HTML 报告模板

模板在 `metric-brand-auditor/references/html-report-template.md`,被 SKILL.md Phase 5F.b 引用。

### 4.1 改样式

CSS 变量集中在 `<style>` 块顶部:`--c-bg` / `--c-text` / `--c-accent` / `--c-judge-1..5`。改这些就好,不要散落在元素 inline style 里。

### 4.2 加新图表

Chart.js / Mermaid 都已经引入。加新图表 = 加一个 `<canvas>` 或 ` ```mermaid ` 块 + 一段 JS。

### 4.3 改完后

在 SKILL.md 的 Phase 5F.b 章节同步 9 块的列表(如果增减块),并在 Sanity-check 章节加上新块的校验规则。

## 5. 修改维度 Sub-agent 的 prompt

Sub-agent prompt 写在 `metric-brand-auditor/SKILL.md` 的 Phase 2F 章节。改 Method / Output sections 即可。

**注意**:prompt 改了之后,跑过的旧维度文件 (`_raw/dimension_*.md`) **格式会和新格式不一致**。EVOLUTION 模式重跑时,Lead 会按新格式重写,但混合的旧版本可能让 synthesis 困惑。

**建议**:重大格式改动后,跑一次 `--refresh` 全量重做。

## 6. 修改评委打分镜头

5 镜头(Origin authenticity / Category coinage / Leverage quality / Identity coherence / Real-world signal)写死在 SKILL.md 的 Phase 4F 和 Phase 5F 模板里。

要改 / 加 / 删一个镜头:

1. 改 SKILL.md Phase 4F prompt 模板里的镜头列表
2. 改 Phase 5F report.md 模板里的 Score Matrix 列
3. 改 HTML 模板里的 Score Radar / Dissent Heatmap 数据 binding
4. **历史报告 Score Matrix 不能跨版本对齐了** —— 所以这是 major 版本变动,不要轻易做

## 7. 在 Claude Code 里 dry-run / 调试

### 7.1 不真跑只看 PRD

```
/mba TestBrand --dry-run     # ← TODO 实现
```

当前没实现,workaround:`/mba TestBrand` 后在 GATE 1 回 "cancel",PRD 已经在对话里展示了。

### 7.2 只跑某一阶段

不支持。当前 SKILL.md 没暴露 phase 切片入口。MCP 化后会有 `start_audit` 起到任意 phase。

### 7.3 看 sub-agent 实时进度

Claude Code UI 里 sub-agent 是带进度条的。也可以 watch:

```bash
watch -n 5 'ls -la metric-brand-auditor/reports/<brand>/_raw/'
```

文件依次出现 = 进度推进。

### 7.4 调试单个评委

```
/mba list                                    # 看现有 brand
# 选一个有 _raw/synthesis.md 的
# 在 Claude Code 里说: "用 fusheng-perspective 重新评 <brand-slug>,只读 _raw/synthesis.md"
```

这绕开 MBA pipeline,直接用单 perspective skill 输出 review,适合调评委 prompt。

## 8. 提交贡献

### 8.1 PR 流程

1. fork → 改 → PR 到 main
2. PR 标题用 commit message 规范(`feat:` / `docs:` / `fix:` 等)
3. 改了 SKILL.md 必须同步改 docs/03 / docs/04 / docs/08 中相关章节
4. 改了 perspective skill 必须跑一次 `scripts/quality_check.py`(如果存在)
5. PR description 列出"做了什么 / 为什么"和"对存量影响"

### 8.2 Issue 流程

报 bug 时附:

- 触发命令
- 失败的 phase / sub-agent / 评委
- 报告路径(脱敏后的内容)
- Anthropic API 限流?是否 wuying leg?

### 8.3 Discussion(无需 PR)

模板优化、命名改名、范围讨论 → 开 GitHub Discussion 而不是 issue。

## 9. 不接受的扩展(明确边界)

- ❌ 把"评委市场"塞进仓库(过早抽象,等真有 3+ 第三方评委再说)
- ❌ 给评委加权重(隐式优先级 = 隐式偏见,不利于 outsider 视角)
- ❌ 加"评委协商"机制(评委趋同 = 价值丢失)
- ❌ 加 LLM provider 抽象(过早,等真有需求)
- ❌ 把 wuying 替换成"自动绕过反爬的爬虫框架"(法律风险,scope 也不对)
- ❌ 给 MBA 加任何"实时 dashboard / live sentiment"功能(超出 PRD §7 边界)

## 10. 从零起一个新 perspective skill 的完整 SOP

复合操作摘要(如果你想做一整套新人物视角):

```
Step 1. 决定人物 + cutoff date
        - 人物必须是真实公众人物(避法律风险)
        - 公开一手资料 ≥ 30 条(访谈/文章/播客 transcript)
        - cutoff date = 你愿意为之负责的最后日期

Step 2. 起一份 prescan.md(0-prescan)
        - 列举所有公开来源 URL
        - 标注一手 / 二手
        - 估算覆盖完整度

Step 3. 跑 6 路并行调研(在 Claude Code 里)
        - 01-writings:本人写作
        - 02-conversations:本人接受/主持的对话
        - 03-expression-dna:语言风格抽样
        - 04-external-views:外部对 TA 的评价
        - 05-decisions:可追溯的真实决策案例
        - 06-timeline:关键时间节点

Step 4. 归纳 SKILL.md
        - 5 条决策启发式(从 05-decisions 提炼)
        - 表达 DNA 抽样(从 03-expression-dna 提炼)
        - 触发规则
        - Anti-fabrication 红线(必须有,具体到"哪些话题不要替 TA 说")

Step 5. 与 MBA 联动测试
        - /mba <demo brand> --judges <new-judge>,jobs
        - 看新评委的 review 是否 in-character
        - 与 Jobs(已稳定的对照组)对比,确保新评委有独立观点而非趋同

Step 6. 提 PR
        - 合并到 main 之前,review research 文件的引用是否真实可访问
```

参考现成例子:`fusheng-perspective/` 是质量比较高的样本,可以照抄结构。
