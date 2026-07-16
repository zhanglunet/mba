# 23 · 产业维度(Industry Dimension)

> **Status:** v1 落地(2026-07-16)。17 品牌 6 大类。
> **单一真源:** `site/reports-meta.yaml` 每条目的 `industry:` 字段。

## 这是什么 / 为什么

MBA 已覆盖 17 个品牌,用户希望**按产业给品牌分类**(哪些属人工智能、哪些属消费…),便于按产业查看/对比。

现状澄清:`metric-brand-auditor/panels/industries.yaml` 只是**产业→panel** 映射(给 `/mba --industry` 选评委用),**不是品牌→产业**;各品牌的 `panel` 字段也**不能当产业**(anthropic/openai/spacex/nvidia 都用 vc-en panel,却分属 AI/航天/半导体)。所以产业维度需要一套**真正的品牌→产业分类**,落在品牌元数据里。

**呈现:** 首页(`site/index.html`)每张品牌卡片加**产业标签(ind-chip)**,顶部加**产业筛选条**(全部 + 6 产业带计数,点击只看该产业)。复用现有排序条(sort-bar)的交互与视觉。**只作导航/分组标签,不参与评分。**

## 产业分类(6 类)

| 产业(CN,reports-meta 值) | slug | 品牌 |
|---|---|---|
| 人工智能 | `ai` | anthropic · openai · kimichat · zhipu · deepseek · nvidia |
| 消费 | `consumer` | genki-forest · hermes · meituan |
| 硬科技·航天 | `deeptech` | spacex · yuanxin · dji |
| 智能制造·硬件 | `manufacturing` | lenovo · chengshi-auto |
| 企业服务·安全 | `enterprise` | qianxin · asiainfo |
| 教育 | `education` | tal-education |

判断说明(诚实标注):`nvidia` 归**人工智能**(AI 基础设施/半导体,归 AI 产业);`meituan` 归**消费**(本地生活消费平台)。归属可随品牌演化调整,改 reports-meta 的 `industry` 一处即可。

## 数据层 schema

`site/reports-meta.yaml` 每个品牌条目加一行(取上表 6 个 CN 标签之一):
```yaml
  - slug: nvidia
    ...
    panel: vc-en
    industry: 人工智能        # ← 产业维度单一真源
    ...
```

## 工具链

| 环节 | 位置 | 说明 |
|---|---|---|
| 生成 | `scripts/build_home_cards.py` | `INDUSTRIES` 常量(slug↔CN)+ `industry_of(m)`;卡片加 `data-industry` + `ind-chip`;`build_block` 生成产业筛选条(带计数)。产出 `site/index.html` REPORTS 块 |
| 交互 | `site/index.html` 手写 `<script>` | 产业筛选 JS(改 `display`)与排序 JS(改顺序)**共存互不冲突** |
| 样式 | `site/index.html` 手写 `<style>` | `.ind-filter` / `.ind-btn` / `.ind-chip` / `.bc-chips` |
| 硬 gate | `scripts/check_consistency.py`(第 10 格「产业维度」) | 每个发布白名单品牌都有 `industry` 且 ∈ 6 个合法 CN 标签;正则解析 reports-meta(零依赖) |

**加新品牌时**:在 reports-meta 补 `industry:`(6 类之一),否则 `check_consistency` 会红;`build_home_cards.py` 自动出产业 chip + 计数。

## 后续可扩(本期未做)

产业总览页 `/industries.html`(按产业分组 + 每类均分概览)、全局星图按产业着色/分组——用户本期只选了首页筛选 + 卡片标签,留后续。

---

## 附:开发计划存档(2026-07-16)

> 用户批准的开发计划(存档备复盘)。已按此落地。

**触发需求:** 「现在有这么多品牌,增加一个产业维度,比如哪些品牌属于人工智能,哪些属于消费。」

**用户确认:** 分 **6 大类**;呈现 = **首页产业筛选 + 卡片产业标签**(不做总览页/星图着色)。

**分三步(单 PR,squash):**
1. `reports-meta.yaml` 给 17 品牌各加 `industry`(6 类归属按锁定表)。
2. `build_home_cards.py`:`INDUSTRIES` 常量 + 卡片 `data-industry`/`ind-chip` + 产业筛选条(计数);`index.html` 手写区加 CSS + 筛选 JS(与排序共存)。
3. `check_consistency.py` 加第 10 格「产业维度」;docs/23 + docs 索引 + roadmap 存档。

**验证:** `build_home_cards --check` 无漂移 → `check_consistency`(10 格)全绿 → Playwright:首页 0 JS 错误、点产业只显该类卡片(AI→6/消费→3/全部→17)、计数正确、chip 渲染正常。

**明确不做:** 只首页筛选+标签;不做产业总览页/星图着色;产业仅作分组标签、不参与评分。
