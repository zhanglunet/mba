# 28 — 投资人维度(Investor Dimension)

> **一句话**:给**投资人**建可核验的档案,并让「创始人晚餐」支持**创始人 × 投资人**配对。
> 数据在 `investors/<slug>.yaml`,硬 gate 是 `scripts/investor-tools/validate_investors.py`。

## 1. 为什么单开一个维度(而不是塞进 founders)

`founders/` 是**按品牌建索引**的:校验器强制 `brand ∈ site/published-reports.txt`、
且**文件名 == brand**、brand 唯一。这套约束对创始人成立(一个被审品牌一位创始人),
但**投资人不隶属任何被审品牌** —— 徐新投过京东 / 网易 / 美团,却不是其中任何一家的创始人。

硬塞有两条路,都不可接受:

| 做法 | 为什么不行 |
|---|---|
| 伪造一个 brand 塞进 founders | **造假**,直接违反反捏造底线 |
| 放宽 founders 允许 brand 为空 | 把"创始人维度"的语义搞混:同一个目录里一半按品牌、一半按人 |

所以 **investors 按人建索引**:文件名 == 顶层 `slug` == 对应 perspective 的 slug。

## 2. Schema(与 founders 同构,差异已标注)

```yaml
slug: xuxin                      # == 文件名 == perspective slug
perspective_slug: xuxin          # 非空时必须存在 perspectives/<slug>-perspective/SKILL.md
investor:
  name_cn: 徐新                   # 必填
  name_en: Kathy Xu
  firm_cn: 今日资本                # ← founders 没有:投资人隶属机构而非品牌
  firm_en: Capital Today
  role: 创始人 / 总裁              # 必填
  status: 现任                    # 必填,枚举:现任/已离任/已退休/已故
career:                          # 必填,≥1 条
  - period: '2005'               # 必填
    milestone: 创办今日资本…        # 必填
    evidence: 21财经…(URL)        # **必填 —— 反捏造:里程碑必须带 provenance**
    lens: [origin, category]     # ⊆ 5 镜头
portfolio:                       # ← founders 没有:代表投资案例,可选
  - brand: meituan               # 必填;命中发布白名单会在页面互链,不命中也照常记录
    year: '2014'
    note: …
    evidence: …(URL)             # **必填**
relation:                        # 可选;key ⊆ 5 镜头
  origin: 分析:…                  # **每个值必须以「分析:」开头 —— 关系是标注分析,不冒充本人原话**
sources: [...]
```

**与 founders 的三处差异**:① 按人索引(不校验发布白名单);② 多了 `firm_*` 与 `portfolio`;
③ 增加「slug 不得与 `founders/` 的品牌 slug 撞名」的检查 —— 晚餐按 slug 找参与者,撞名会指错人。

## 3. 晚餐放宽:参与者 = 创始人 **或** 投资人

`validate_collabs.py` 原本要求 `brands` 两个都有 `founders/<slug>.yaml`。现改为
`participant_exists(slug) = founders/<slug>.yaml 或 investors/<slug>.yaml`。

渲染侧(`build_collab_dinners.py`)`founder_info()` 返回值从 `(name, role)` 扩成
`(name, role, kind)`;`kind == "investor"` 时互链走**评委视角**而不是 `/reports/<slug>/`
—— 投资人没有被审品牌页,照旧链过去会是死链。

**自测有牙**:`validate_collabs --selftest` 加了一条断言 —— 用真实存在的
`investors/*.yaml` + `founders/*.yaml` 各取一个组一场,**必须不报「缺档案」**;
否则"允许创始人×投资人"就是句空话。

## 4. 反捏造边界(与全项目一致)

- `career` / `portfolio` 每条**必须带 evidence**,机器强制。
- `relation` 是**标注分析**,强制以「分析:」开头,**不冒充本人原话**。
- 本人的逐字引语只存在于 `perspectives/<slug>-perspective/references/research/`,
  由 `firewall_check.py` 守着;**investors 档案里不放"引语"**。
- 晚餐里的 `say` 是 **AI 演绎公开立场**,页面有硬编码 disclaimer,规则同 docs/22。

## 5. 当前覆盖

| 投资人 | slug | 机构 | perspective |
|---|---|---|---|
| 徐新 | `xuxin` | 今日资本 | ✅ full tier |

**下一批候选**(vc-cn 面板其余四位,都已有 full tier perspective):张磊(高瓴)、
朱啸虎(金沙江)、沈南鹏(红杉中国)、雷军(顺为,兼创始人身份)。建一份档案的成本 ≈
6 条带 provenance 的履历 + 5 条镜头分析。

## 6. 命令

```bash
python3 scripts/investor-tools/validate_investors.py            # 校验全部投资人档案
python3 scripts/investor-tools/validate_investors.py --selftest # 12 组断言:每类违规都会被抓
python3 scripts/check_consistency.py                           # 第 15 格「投资人维度」委托上面这个
python3 scripts/build_collab_dinners.py                        # 晚餐页(投资人参与者已支持)
```
