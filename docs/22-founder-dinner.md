# 22 · 创始人晚餐(Founder Dinner · 品牌 × 品牌合作推演)

> **Status:** v1 落地(2026-07-16)。首场:田溯宁(亚信)× 唐杰(智谱)。
> **单一真源:** `collabs/<a>--<b>.yaml`。生成物 `site/collabs/`(gitignore)。

## 这是什么 / 为什么

用户想要「把两个品牌组合、推断和假想它们的合作机会」,并定了呈现形式:**两位创始人一起吃饭聊合作**。本功能把两个品牌的创始人放到一张饭桌上,按 **5 镜头**逐"道菜"讨论潜在合作,接上**创始人维度**(`founders/*.yaml`)。

**呈现:** 每场晚餐一张页 `site/collabs/<a>--<b>.html`(house style);索引页 `site/collabs/` 带**组合器**(选两位创始人 → 有则开饭、无则「待推演」)。入口:首页 nav/intro、创始人页(「🍽️ 与 X 共进晚餐 →」)、创始人索引。

## ⚠️ 反捏造(本功能的立身红线)

晚餐对话是把话放进**真人**嘴里,而 MBA 禁止「LLM 凭空生成的风格化引言」。调和方式 = 与 MBA 立身机制**同源**:「人物评委」本就是 **AI 模拟真人视角**打分(页脚:"评分为 AI 评委模拟,非本人观点")。所以晚餐 = 同一套 AI 演绎,并守以下红线:

- **醒目 disclaimer 横幅**(生成器硬编码,每页顶部):🍽️ 假想晚餐 · AI 演绎 · 非本人真实发言 · 非双方证实的真实合作。
- **发言 `say` = AI 演绎其公开记录在案的立场**,**paraphrase 不冒充逐字原话**;基于每人 `founders/<slug>.yaml` 的 `relation`/`career` + 公开观点(评委创始人另据其 perspective 表达 DNA;非评委创始人据 curl 一手的公开言论)。**逐字原句**仅在确有据时引用,并落在已验证来源上;不生成新引言。
- **锁年 / 留白**:不替本人就 cutoff 外事项发言(如王慧文 2023 健康/退隐、张邦鑫双减后一律不臆测)。
- **合作点 = 基于两品牌真实属性的假想推演**,标「(假想)」;**绝不谎称真实合作存在**。
- **诚实盒 `tensions`(强制,校验器硬 gate)**:每场必须列出合作的张力/不搭之处——反炒作平衡,承 MBA「诚实边界」。
- **只作调研启发,不改评分**。

## 数据层 schema:`collabs/<a>--<b>.yaml`

文件名 = 两个 brand slug **字母序**用 `--` 连(规范化;校验器强制)。

```yaml
brands: [asiainfo, zhipu]           # 恰 2 个;都必须 ∈ founders/*.yaml
title: "..."                        # 晚餐标题
scene: "假想场景一句(标注非真实发生)"
courses:                            # 「五道菜」= 5 镜头(可取子集)
  - lens: origin                    # ⊆ origin/category/leverage/identity/signal
    exchange:                       # 双方发言(每个 who ∈ brands,say 非空)
      - { who: asiainfo, say: "AI 演绎的立场(paraphrase 非逐字原话)" }
      - { who: zhipu,    say: "..." }
    idea: "该镜头下的合作点假想"
takeaways: ["合作机会1", ...]        # 非空
tensions:  ["合作张力1", ...]        # 非空(诚实盒,强制)
sources:   ["founders/... · 公开来源 URL", ...]
```

## 工具链

| 环节 | 脚本 | 说明 |
|---|---|---|
| 校验(硬 gate) | `scripts/collab-tools/validate_collabs.py` | brands 恰 2 且都有创始人档案 · 文件名规范序 · lens 合法 · who ∈ brands · idea/say 非空 · takeaways/**tensions 非空** · 12 组 `--selftest`;接入 `panel-validation.yml` |
| 生成 | `scripts/build_collab_dinners.py` | `collabs/*.yaml` → `site/collabs/<a>--<b>.html` + 组合器索引;复用 `build_founder_pages` 的 house-style 骨架;disclaimer 横幅硬编码 |
| 一致性 | `check_consistency.py`(第 9 格) | 委托 validate_collabs |
| 入口 | `build_founder_pages.py`(`dinners_for`)/ `site/index.html` | 创始人页/首页/创始人索引挂「创始人晚餐」入口 |

**提交前必跑**(在 CLAUDE.md 清单基础上):
```bash
python3 scripts/collab-tools/validate_collabs.py            # 场次合规
python3 scripts/collab-tools/validate_collabs.py --selftest # 门禁有牙
python3 scripts/build_collab_dinners.py                     # 本地预览 site/collabs/
```

## 后续扩展 SOP(加一场晚餐)

1. 双方都得先有 `founders/<slug>.yaml`(缺则先按 docs/21 补创始人,评委复用 perspective、非评委 curl 一手)。
2. 读双方 `founders` 的 `relation`/`career`;评委创始人再读 perspective 表达 DNA,非评委据 curl 公开言论给立场定调。
3. 写 `collabs/<字母序a>--<b>.yaml`:5 镜头 courses(每道两 turn + idea)+ takeaways + **tensions 诚实盒** + sources。
4. `validate_collabs.py` 通过;`say` 保持 paraphrase(不冒充逐字原话)。
5. `build_collab_dinners.py <stem>` 渲染,Playwright 自检 0 JS 错误。入口生成器按数据自动挂链接。

---

## 附:开发计划存档(2026-07-16)

> 用户批准的开发计划(存档备复盘)。已按此落地。

**触发需求:** 「如果一个品牌和另一个品牌合作,会有什么创意/合作点?做一个把两品牌组合、推断和假想合作机会的东西。」→ 呈现形式:「以两个品牌的创始人一起晚餐的形式讨论潜在合作。」

**用户确认:** 生产方式 = 策划式精编晚餐(人手编写、有据、标 AI 演绎);首批 = 先做 1-2 场样板;**首场 = 田溯宁(亚信)× 唐杰(智谱)**。

**分三步(单 PR,squash):**
1. **数据层 + 校验器** —— `collabs/` + 晚餐 yaml;先补 `founders/asiainfo.yaml`(田溯宁,curl 一手);`validate_collabs.py`(照 validate_founders),接入 `panel-validation.yml`。
2. **生成器 + build.sh** —— `build_collab_dinners.py` → 晚餐页 + 组合器索引(复用 founder house-style,disclaimer 硬编码);`site/collabs/` gitignore;接入 build.sh。
3. **各处入口 + 一致性 + docs** —— 创始人页/首页/创始人索引加晚餐入口;`check_consistency` 第 9 格;本文档 + docs 索引 + CLAUDE.md + roadmap 存档。

**验证:** validate_collabs `--selftest` 全绿 → yaml 通过 → 反捏造自查(say paraphrase、disclaimer/tensions 在位)→ `build_collab_dinners.py` 生成 + Playwright 0 JS 错误 → 组合器/入口跳转正确 → `check_consistency`(9 格)/ `build_home_cards --check` / `build_agents_api --check` 无漂移。

**明确不做:** 首批只样板场次;不做 LLM-at-build 生成对话(全人手精编、标 AI 演绎);不谎称真实合作;不改已发布报告 HTML。
