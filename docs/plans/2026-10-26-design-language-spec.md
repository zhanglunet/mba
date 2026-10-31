# PRD-205/T1：共享设计语言文件规范（设计草稿）

> 依据：trend `adopted/PRD-205-mba-shared-design-language.md`（2026-10-26）；trend issue #1025（T1）
> 状态：设计草稿，只定规范，不写实现代码。实现分别归 T2（生成器接入，#1026）、T3（评委接入，#1027）、T4（确定性检查自动化，#1028）、T5（同尺演练验收，#1029）。
> 收敛起点：mba 现有三处设计资产的实测值——`dashboard.html`（指挥舱）、`ask.html`（生成式 UI 问答页，PRD-081 产出）、`site/index.html`（官网）与 `scripts/genui_charts.py`（图表组件常量）。本规范把这些已在代码里定版的值登记成"文件"，不另起一套、不推翻已定版 token。

## 借鉴声明（置顶）

- 本规范的**组织形态**借鉴 pbakaus/impeccable（github.com/pbakaus/impeccable）：「机器可读设计文件 + 确定性检测规则 + 生成/评审共用命令词汇」三件套。impeccable 为 **Apache-2.0** 许可。
- 借鉴边界：只借形态（文件结构、规则组织方式、检查思路），**不复制其规则条文与代码**。mba 的全部条目均由本仓库现有设计资产收敛而来，条文为本项目原创。
- 合规要求（写入本规范，T2–T5 必须遵守）：若后续任何任务需要复用 impeccable 的原文条目或代码，必须①在被复用文件头部保留 Apache-2.0 许可证文本与原版权声明（Copyright the impeccable contributors / pbakaus）；②在 `design/design-language.yaml` 的 `meta.attribution` 字段登记复用点。在此之前，`meta.attribution` 记为「form-only, no code or rule text reused」。

## 一、定位与原则

打个比方：PRD-132 是给人看的《评委手册》（讲道理、给例子），本文件是给 agent 的**量具**——每条规则有编号、有刻度、能判定过没过。生成器（画图的）和评委（挑毛病的）共用同一把量具，评审意见不再写「配色不太协调」，而是写「违反 DL-C04」，能定位、能复核、能统计。

四条原则：

1. **单一事实源**：设计语言只存一份文件（§二），生成器与评委都只读它。任何一方在文件之外另立标准，视为无效。
2. **收敛不发明**：条目的值全部来自现有代码实测（§三登记表逐项注明出处）。现状有分歧的（如两处红色值不同），登记为 canonical + legacy 并给出收敛机制，本规范不擅自改值——改值走 §2.5 的变更流程经评审决定。
3. **两级力度**：条目分「硬规则 / 建议」两级（§2.4）。硬规则管底线（品牌识别、诚实降级、只读场景的可读性），建议管品味。尺子过严压制创意是 PRD 明列风险，两级就是为此设的。
4. **能机检先机检**：每条条目标明可否确定性检查及判定方法（§五），T4 按此清单实现；机检判不了的明确标「人工」，不许用 LLM 感觉冒充机检（与 impeccable 把 deterministic detector 与 LLM-only critique 分开的形态一致）。

与相邻 PRD 的分工（详见 §六）：PRD-098 管生成式 UI 的**组件/协议标准对齐**（openui），本文件管**视觉尺子**，不重叠；PRD-099 已定版的图表样式 token 是本文件 token 区的上游来源，逐值复用不推翻。

## 二、设计语言文件格式定义

### 2.1 位置与形态

| 项 | 定案 |
|---|---|
| 路径 | `design/design-language.yaml`（仓库根新建 `design/` 目录，T2 落地时创建；本 T1 只定规范不建文件） |
| 格式 | YAML（与 mba 的 panel 配置同构，agent 易解析、可写注释、可 diff 评审） |
| 人读镜像 | `design/DESIGN-LANGUAGE.md`：由文件内容人工整理的速查版（条目编号与 YAML 严格一致；一致性由 T4 校验，见 §5.3）。镜像只供人看，**冲突时以 YAML 为准** |
| 消费方 | 生成器（T2）、评委（T3）、机检器（T4）。三方只读，不回写 |

为什么不用 impeccable 的 `design.json` 形态：JSON 不能写注释，而本文件的条文需要带「依据/出处」说明；且 mba 既有配置生态（panels）是 YAML，同一仓库不引入第二种配置方言。结构上借鉴其 `schemaVersion + 扩展元数据` 的做法（§2.2 的 `meta` 区即对应物）。

### 2.2 顶层结构（四区）

```yaml
meta:    # 文件元信息：version / schema / 来源 / 借鉴声明
tokens:  # 定版值登记区：颜色 / 字体栈 / 字号阶梯 / 间距档 / 圆角 / 动效参数
rules:   # 规则条目数组：每条一个对象，字段见 §2.3
checks:  # 机检登记区：条目编号 → 判定方法代号（§五的清单在此落字段）
```

`meta` 必填字段：`version`（语义化版本，§2.5）、`schema: 1`、`updated`（日期）、`sources`（收敛来源文件清单）、`attribution`（借鉴登记，初始值见文首借鉴声明）、`compat`（与 PRD-098/099、PRD-217 的衔接版本注记，见 §六、§七）。

### 2.3 条目结构与编号体系

编号格式：`DL-<类><两位序号>`，类字母：`T` 字体层级（Typography）、`C` 配色（Color）、`S` 留白（Spacing）、`M` 动效（Motion）。例：`DL-T01`、`DL-C04`。

编号稳定性承诺（评审可定位的前提）：

- 编号一经发布**永不复用、永不改号**；条目废止时标 `status: deprecated` 保留占位，不删除、不把号给新条目。
- 条文措辞可修订（走 §2.5 流程并升版本），但编号指向的规则主题不变；主题变了就是新条目、新编号。

每条条目的字段：

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 编号，如 `DL-C04` |
| `level` | 是 | `hard`（硬规则）/ `advice`（建议），语义见 §2.4 |
| `title` | 是 | 一句话标题 |
| `statement` | 是 | 条文：可判定的表述，禁止「协调」「美观」这类不可判定词单独出现 |
| `basis` | 是 | 依据：现有资产出处（文件 + 实测值），或借鉴来源 |
| `check` | 是 | 机检代号（§五）或 `manual`（人工）；`check` 非 `manual` 时必须同时给出判定参数 |
| `applies_to` | 是 | 适用面：`deck`（指挥舱）/ `ask`（问答页）/ `site`（官网）/ `charts`（图表组件）/ `all` |
| `status` | 否 | `active`（默认）/ `deprecated` / `pending-converge`（值待收敛，见 §3.2） |

### 2.4 两级的语义与评审后果

| 级别 | 生成器（T2）义务 | 评委（T3）权限 | 机检（T4）输出 |
|---|---|---|---|
| `hard` 硬规则 | 必须遵守；确需偏离时按 §6.1 格式声明豁免理由，否则产物不合格 | 违反可判 fail，意见必须带条目编号与证据 | `fail` |
| `advice` 建议 | 应尽量遵守，偏离无需声明 | 只能记 note，**不得**据此判 fail | `note` |

### 2.5 版本与变更治理

- 文件版本语义化：新增条目 → minor +1；条文/定版值变更 → minor +1 并在 PR 说明中逐条列出；删除或改号（原则上禁止）→ major +1。
- 变更只走 PR + 人工 review（与 mba 现有纪律一致：只开 PR 不合并，等用户逐个批）。
- 评审意见必须记录所依据的文件版本（§6.2），版本变了旧意见不自动失效，但复核时以意见所记版本为准。

### 2.6 文件骨架示例（节选，值为 §三定版真值）

```yaml
meta:
  version: 0.1.0
  schema: 1
  updated: 2026-10-26
  sources: [dashboard.html, ask.html, site/index.html, scripts/genui_charts.py]
  attribution: "form-only, no code or rule text reused (impeccable, Apache-2.0)"
tokens:
  color:
    paper: "#faf8f3"
    accent: "#c1440e"
    ink: "#111111"
    muted: "#6b6760"
    positive: "#1a7a4a"
    negative: "#b3261e"        # canonical，见 §3.2 收敛表
    neutral: "#b9b2a6"
    chart_palette: ["#c1440e", "#1a4a7a", "#1a7a4a", "#7c3aed", "#d97706"]
rules:
  - id: DL-C04
    level: hard
    title: 图表系列色按调色板顺序取色
    statement: 多系列图表的系列色必须按 tokens.color.chart_palette 的顺序依次取用，不得跳序、不得使用调色板之外的颜色。
    basis: scripts/genui_charts.py PALETTE 常量及现有渲染实现（按 index mod 取色）
    check: css-value-set
    applies_to: [charts, ask, deck]
```

## 三、token 定版登记（复用已定版值，不推翻）

### 3.1 定版值全表（出处为实测）

| token | 定版值 | 出处 |
|---|---|---|
| paper 页面底 | `#faf8f3` | dashboard / ask / site 三处一致（`--paper`） |
| accent 主强调 | `#c1440e` | 三处一致（`--accent`）；genui `ACCENT` 同值 |
| ink 正文墨色 | `#111` | 三处一致（`--ink`） |
| muted 次要文字 | `#6b6760` | 三处一致（`--muted`） |
| rule 分隔线（深） | `#1a1a1a` | dashboard / site（`--rule`） |
| card 卡面 | `#ffffff` | site（`--card`） |
| missing-bg 数据暂缺底 | `#f0ede7` | dashboard / ask（`--missing-bg`） |
| warn 警告 | `#d97706` / 底 `#fef3e2` | dashboard（`--warn` / `--warn-bg`） |
| positive 正向 | `#1a7a4a` | genui `POSITIVE`；site `--up` 同值 |
| negative 负向 | `#b3261e` | genui `NEGATIVE`（canonical，见 §3.2） |
| neutral 中性 | `#b9b2a6` | genui `NEUTRAL` |
| accent-soft 强调浅底 | `rgba(193,68,14,0.10)` | genui `ACCENT_SOFT` |
| chart.js 版本 | `4.4.4`（CDN 固定） | dashboard / ask / genui `CHART_JS_CDN` 三处一致 |
| 图表调色板 | `#c1440e, #1a4a7a, #1a7a4a, #7c3aed, #d97706` | genui `PALETTE` |
| 标题字体栈 | `ui-serif, "Noto Serif SC", "Songti SC", "Noto Serif", Georgia, serif` | 三处一致（serif 栈，细节变体见 DL-T01） |
| 正文字体栈 | `ui-sans-serif, "Inter", "PingFang SC", "Hiragino Sans GB", "Noto Sans SC", "Microsoft YaHei", -apple-system, sans-serif` | site 定版（最完整版，见 DL-T02） |
| 数字字体栈 | `ui-monospace, "JetBrains Mono", SFMono-Regular, Menlo, monospace` | site / genui 系（登记两变体，见 DL-T03） |
| 字号阶梯 | 正文 11 / 11.5 / 12 / 12.5 / 13 / 14 / 15；小标题 18 / 20 / 24；展示 32 / 44 / 52 / 64（仅 site） | 三处 font-size 分布实测主导值 |
| 间距档 | 4 / 8 / 12 / 16 / 20 / 24 / 32（px，主导 8 / 16 / 20） | 三处 padding/margin 实测 |
| 圆角档 | 3 / 4 / 6 / 8 / 999（胶囊）px | 三处 border-radius 实测全集 |

### 3.2 待收敛差异（登记，不擅自改值）

现状有三处同义不同值。本规范的裁决机制：文件里登记 canonical（现行准）+ legacy（存量别名），T2/T3 在迁移期双认，机检对 legacy 只报 `note` 不判 `fail`；最终收敛（改哪边）由后续独立 PR 经 review 决定，不在本 T1 范围。

| 差异 | canonical | legacy | 出处 |
|---|---|---|---|
| 负向红 | `#b3261e`（genui `NEGATIVE`，图表/问答在用） | `#b5341a`（site `--down`） | 两值并存，色差极小 |
| 浅分隔线 | `#e0ddd8`（ask `--line`） | `#e2ddd3`（site `--hair`） | 同义命名都叫「发丝线」 |
| 正文字体栈完整度 | site 全量栈（含 Hiragino / YaHei） | ask 简版栈 | ask 为 demo 页从简 |


## 四、规则条目（四类，值以 §三为准）

条文里的 token 名指 §3.1 登记值；数值只在 §三出现一次，条文不重复写死——改值只改 §三，条文自动跟随。

### 4.1 字体层级 DL-T

| 编号 | 级别 | 条文 | 依据 | 机检 |
|---|---|---|---|---|
| DL-T01 | 硬 | 标题与品牌字必须使用标题字体栈（serif 系，见 §3.1）；栈内字体缺失时按栈顺序回退，不得改用未登记字体 | 三处 serif 栈一致 | css-value-set |
| DL-T02 | 硬 | 正文必须使用正文字体栈（sans 系，§3.1 canonical 全量栈）；存量简版栈按 §3.2 迁移期双认 | site 定版全量栈 | css-value-set |
| DL-T03 | 硬 | 数字、分数、代码必须使用数字字体栈（mono 系，§3.1）；两个登记变体双认 | site / genui | css-value-set |
| DL-T04 | 硬 | 字号只许取 §3.1 字号阶梯的登记值；正文区 11–15（0.5 步进），展示档（32+）仅限 site | 三处字号分布实测；22/23/26/30 等散值登记为 legacy，机检只报 note | css-value-set |
| DL-T05 | 硬 | 正文行高不低于 1.5；标题行高不低于 1.1 | 现状主导 1.5–1.75 | css-numeric-range |
| DL-T06 | 建议 | 同一页面内字号档位不超过 5 档，避免层级噪声 | 层级收敛惯例；现状各页均在 5 档内 | css-value-count |

### 4.2 配色 DL-C

| 编号 | 级别 | 条文 | 依据 | 机检 |
|---|---|---|---|---|
| DL-C01 | 硬 | 页面底色只用 paper，卡面只用 card；禁止纯黑（#000）作背景 | §3.1；现状 ink 为 #111 非纯黑 | css-value-set |
| DL-C02 | 硬 | 主强调色只有 accent 一个；新页面不得引入第二个强调色 | 三处一致 | css-value-set |
| DL-C03 | 硬 | 语义着色只用 positive / negative / neutral 三值（negative 取 canonical，legacy 双认）；涨跌、达标与否、delta 正负必须用这三值，不得自选红绿 | genui 渲染实现现状 | css-value-set |
| DL-C04 | 硬 | 图表系列色按 chart_palette 顺序依次取用，不得跳序、不得用调色板外颜色 | genui `PALETTE` + 按序取色实现 | css-value-set / chart-config |
| DL-C05 | 硬 | 文字色只用 ink / muted 两档；彩色背景上不得使用 muted 文字 | §3.1；借 impeccable anti-pattern 形态（灰字不上彩底），条文为本项目自拟 | 半机检（§五 note） |
| DL-C06 | 硬 | 状态底色各就其位：数据暂缺用 missing-bg，警告用 warn-bg + warn；两者不得互换、不得挪作装饰底色 | dashboard 现状（缺失与警告双通道） | css-value-set |
| DL-C07 | 建议 | accent-soft 只用于趋势线填充与 hover 底，不作大面积铺底 | genui 现状用法 | 人工 |

### 4.3 留白 DL-S

| 编号 | 级别 | 条文 | 依据 | 机检 |
|---|---|---|---|---|
| DL-S01 | 硬 | padding / margin 取值必须落在 §3.1 间距档内（0 除外） | 三处实测主导 8/16/20 | css-value-set |
| DL-S02 | 硬 | 卡片内边距只用两档：通栏卡 20px、紧凑行 10px 14px | dashboard / ask 实测两档 | css-value-set |
| DL-S03 | 建议 | 正文阅读宽度不超过 72ch；通栏容器宽度以 960px 为登记档 | site 72ch、dashboard 系 960px 实测 | css-numeric-range |
| DL-S04 | 硬 | 圆角只用 §3.1 圆角档（3/4/6/8/999） | 三处实测全集 | css-value-set |
| DL-S05 | 硬 | 默认无阴影；全站唯一允许的阴影为 `0 2px 14px rgba(193,68,14,.10)`，其余 box-shadow 一律禁止 | dashboard / ask 实测零阴影；site 仅此一处 | pattern-match |

### 4.4 动效 DL-M

| 编号 | 级别 | 条文 | 依据 | 机检 |
|---|---|---|---|---|
| DL-M01 | 硬 | 交互过渡时长只用 0.15s / 0.25s 两档；入场动画仅限 site 品牌页且不超过 1.1s，deck / ask 两面不加入场动画 | site transition 实测两档；dashboard / ask 实测零入场动画 | css-value-set |
| DL-M02 | 建议 | 缓动曲线只用登记曲线（绘制 `cubic-bezier(.6,0,.25,1)`、弹入 `cubic-bezier(.2,1.4,.4,1)`）；弹入曲线带 overshoot，与 impeccable「不用 bounce/elastic」的口径差异在此显式登记，收敛与否留评审决定，本规范不假装一致 | site 动画实测；差异登记 | css-value-set |
| DL-M03 | 硬 | 必须响应 `prefers-reduced-motion`：该设置下禁用全部动画与过渡。现状三处均未实现——本条为规范先行，T2/T3 接入时落地，机检判「缺失即 fail」 | 无障碍底线；现状缺失如实登记 | pattern-match |
| DL-M04 | 硬 | chart.js 配置必须显式声明 `animation` 行为（交互页开启、导出/截图场景关闭），不得依赖库默认 | genui 渲染经 chart.js，导出场景需静帧 | chart-config |
| DL-M05 | 建议 | 动效只表达状态变化（hover / 展开 / 数据更新），不做纯装饰的循环动画 | 现状无循环动画 | 人工 |

## 五、确定性检查清单（T4 的输入）

### 5.1 判定方法代号

| 代号 | 方法 | 覆盖条目 |
|---|---|---|
| `css-value-set` | 解析产物 HTML/CSS（含 `<style>` 与内联样式），抽取目标属性的全部取值，与 §三登记集合比对；集合外取值即命中 | T01–T04、C01–C04、C06、S01、S02、S04、M01、M02 |
| `css-numeric-range` | 同上抽取数值，判上下界 | T05、S03 |
| `css-value-count` | 统计单页不同字号档数，超限命中 | T06 |
| `pattern-match` | 正则扫产物文本：box-shadow 非登记值、缺失 `prefers-reduced-motion` 媒体查询 | S05、M03 |
| `chart-config` | 解析 chart.js 配置对象（或 genui 渲染参数）：核对系列色顺序、`animation` 显式声明 | C04、M04 |
| `manual` | 不可机检，评委人工判断；机检器输出 `skip-manual` 不冒充通过 | C07、M05 |

半机检一项：DL-C05 的「彩底不用 muted 文字」需渲染后取计算样式配对判断，静态解析不可靠——T4 一期列 `manual`，二期有渲染通道后再升 `chart-config` 类的渲染检查。本清单先把判定边界写死，避免 T4 用近似冒充确定。

### 5.2 机检器接口约定（T4 实现时遵守）

- 输入：`design/design-language.yaml` 路径 + 待检产物文件列表。
- 输出：JSON findings 数组，每条含 `rule`（条目编号）、`level`、`verdict`（硬规则 `fail` / 建议 `note` / 人工 `skip-manual`）、`file`、`evidence`（属性名 + 实际值 + 期望集合摘要）。
- 退出码：存在任一 `fail` → 非 0；只有 `note` → 0。调用方（T2 生成后自检、T5 演练）以退出码 + findings 为准，不解析自然语言输出。
- findings 的 `rule` 编号必须能在当前版本 YAML 的 `rules` 中查到；查不到的编号视为机检器自身 bug，fail-closed 报错。

### 5.3 镜像一致性检查

`design/DESIGN-LANGUAGE.md` 与 YAML 的条目编号集合必须完全一致（增删条目两边同步），纳入 T4 检查项，代号 `mirror-set`。

## 六、生成器与评委的引用约定（T2 / T3 接口）

### 6.1 生成器（T2）

- 生成前把 `design-language.yaml` 全文加载进上下文；生成只许用 §三登记的 token 值。
- 产物（或其同名说明文件）必须附 `design_refs` 清单：本次实际用到的条目编号列表，供评委与机检对账。
- 偏离硬规则必须声明豁免，格式：`waive: DL-S01, reason: <一句话>`，出现在产物说明区；无声明的偏离按违反处理。建议级偏离无需声明。
- 生成后先跑机检（§5.2），`fail` 未清零不得交付评委。

### 6.2 评委（T3）

- 每条设计类评审意见必须引用条目编号，格式字段：`rule` / `level`（与文件登记一致）/ `evidence`（文件 + 选择器或行号 + 实际值）/ `expect`（期望值或登记集合）。
- 结论规则：任一硬规则违反 → 该产物设计维度判 fail；只有建议级 note → 不影响 pass/fail，只记录。
- 引用了不存在或已 `deprecated` 的编号 → 该条意见无效，元评审（PRD-063 通道）可直接驳回，不必进入人工裁量。
- 评审记录必须注明所依据的 `design-language.yaml` 版本号（§2.5）；同一批产物在 T5 演练中两端（生成自检与评委复检）必须用同一版本。

### 6.3 与命令词汇的对应（借 impeccable 形态）

impeccable 用一组命令词让生成与评审共享词汇（typeset / colorize / layout / animate / audit / critique 等）。mba 沿用这个形态但只取四类，与条目类字母一一对应，供 T2/T3 在提示与报告中统一用词：`typeset`（DL-T）、`colorize`（DL-C）、`layout`（DL-S）、`animate`（DL-M）；全量机检称 `audit`，人工评审称 `critique`。词汇只作称呼，不改变 §6.1/§6.2 的字段约定。

## 七、与 PRD-098 / PRD-099 的衔接

| 事项 | 口径 |
|---|---|
| PRD-099（token 定版） | §三的全部定版值即 099 路线已在代码中定版的样式 token（配色/字体/图表系列色），本规范**逐值引用、一个不改**。099 的图表选型决策表管「什么数据用什么图」，本文件管「图长什么样」，互引不互覆盖。若 099 后续有新的定版变更，先改 §三登记并升文件版本，条文因引用 token 名而自动跟随 |
| PRD-098（生成式 UI 标准对齐） | 098 对齐 openui 的组件模型 / 协议 / 渲染契约，本文件只管视觉取值与条目判定，**不定义组件、不定义协议**。ask 页同时受两边约束：组件与消息格式从 098，视觉从本文件；两者冲突时先停手上报评审，不自行取舍（098 的 T2 差距报告流程同理适用） |
| chart.js 钉版 | 三处现状一致钉 `4.4.4`；升版属 098 的标准跟踪范围，本文件只登记现值，升版后改 §三并升版本 |

## 八、与 PRD-217（poster 版）的口径差异预留（T5 互通）

PRD-217 在 general-poster-workbench 做同一件事的海报版。两边**结构同构、取值可异**：

- 共用：编号体系（`DL-<类><序号>`、类字母 T/C/S/M）、条目字段、两级语义、findings 格式。poster 侧文件同理命名与分工。
- 可异：全部 token 值与条文细节。海报场景与审计报告场景诉求不同（如海报需要展示级大字号与更强对比），差异是正当的，**不强求值一致，只求差异显式**。
- 差异登记表（T5 互通时逐项对账，双方文件各存一份同格式表）：

| 字段 | 说明 |
|---|---|
| `rule_pair` | 两边对应条目编号（如 mba `DL-T04` ↔ poster 对应编号；无对应记 `none`） |
| `mba_value` / `poster_value` | 两边登记值或条文摘要 |
| `reason` | 差异理由（场景差异 / 品牌差异 / 历史存量） |
| `interop` | `shared`（应互通而未一致，需收敛）/ `by-design`（场景正当差异，长期保留） |

- T5 演练时以登记表为准：`by-design` 的差异不判任何一方违反；`shared` 未收敛项列入后续收敛 PR 候选。

## 九、验收对照与未决项

对照 trend #1025（T1）验收标准「规范评审通过」与 PRD-205 的 T1 内容要求：

- ✅ 设计语言文件格式定义：§二（位置/格式/四区结构/字段/编号/两级/版本治理/骨架示例）
- ✅ 四类规则条目（字体层级/配色/留白/动效），每条稳定编号 + 硬规则/建议两级：§四（T 6 条、C 7 条、S 5 条、M 5 条）
- ✅ 确定性检查清单（可机检项 + 判定方法）：§五（五种判定代号 + 机检器接口 + 一项半机检的边界声明）
- ✅ 生成器与评委引用条目编号的接口约定：§六
- ✅ 与 PRD-098/099 已有产出的衔接（复用定版 token 不推翻）：§三 + §七
- ✅ 与 PRD-217 口径差异预留（T5 互通）：§八
- ✅ 借鉴出处与许可证、保留原版权声明的要求：文首借鉴声明

未决项（留评审决定，不在本草稿擅自定案）：

1. §3.2 三处待收敛差异的最终取值（canonical 已定现行准，legacy 何时下线另开 PR）。
2. DL-M02 弹入 overshoot 曲线与 impeccable 口径的差异：收敛还是登记为 mba 品牌特征长期保留。
3. DL-C05 二期渲染级机检是否立项（取决于 T4 一期之后有无渲染通道）。
