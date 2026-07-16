# 21 · 创始人维度(Founder Dimension)

> **Status:** v1 落地(2026-07-16)。首批 4 位「创始人即评委」+ zhipu(首个非评委、curl 取一手)= 5 份。
> **单一真源:** `founders/<slug>.yaml`。生成物 `site/founders/`(gitignore)。

## 这是什么 / 为什么

给 MBA 增加一个**创始人维度**:梳理每个品牌**创始人的履历**,并从**人物角度**梳理
创始人↔品牌的关系(按 5 镜头拆)。此前 MBA 对创始人只有零散触及——`self-conflict.yaml`
的创始人→品牌别名表(只用于自检拦截)、报告 Origin 镜头的起源叙事、品牌星图连到 Origin
的边——但没有一个**结构化、可复盘、可导航**的创始人层。本维度把它补上。

**呈现:** 每品牌一张独立创始人页 `site/founders/<slug>.html`(house style),从**首页卡片 /
品牌星图 / 舆情驾驶舱 / watch 时间线页**加「创始人 →」入口。索引页 `site/founders/`。

**首批范围(4 位「创始人即评委」):** `spacex`→musk · `meituan`→wanghuiwen(联合创始人)·
`tal-education`→zhangbangxin · `kimichat`→yangzhilin。它们的创始人**本身就是 MBA 评委**,
直接复用其 perspective 的 `references/research/06-timeline.md` 一手调研(反捏造最稳)。

**已扩(非评委,curl 取一手):** `zhipu`→唐杰(创始人/首席科学家;CEO 张鹏、董事长刘德兵、总裁王绍兰)。
智谱创始人**不是** MBA 评委,无 perspective 可复用 → 履历经 `curl`(走 `$HTTPS_PROXY`+CA,坑 #1)
核实,每条里程碑带真实来源 URL(财联社 / 虎嗅 / 创业邦),`perspective_slug` 留空。这是**非评委
创始人的参照样板**:走 SOP 的 curl 分支。

其余 10 品牌留后续 PR(需先 `curl` 取一手履历再落库,见坑 #1)。

## 数据层 schema:`founders/<slug>.yaml`

```yaml
brand: spacex                     # 必须 ∈ site/published-reports.txt 白名单;文件名 == brand
founder:
  name_cn: 埃隆·马斯克
  name_en: Elon Musk              # 可选
  role: 创始人 / CEO / CTO         # 与品牌的职务关系
  status: 现任                     # 枚举:现任 / 已离任 / 已退休 / 已故
  perspective_slug: musk           # 可选;非空时必须存在 perspectives/<slug>-perspective/SKILL.md
career:                           # 履历时间线,≥1 条;每条必须带 evidence(provenance)
  - period: "2002"
    milestone: "创立 SpaceX,把软件财富转投硬核航天"
    evidence: "SpaceX / NASA 公开史;Isaacson 传记"   # provenance 标注 或 真实 URL(反捏造)
    lens: [origin, signal]                            # 可选;⊆ 5 镜头
relation:                         # 可选;创始人↔品牌关系(按 5 镜头),key ⊆ 5 镜头
  origin: "…标注为分析的文字…"
  category: "…"
sources:                          # 可选;复用的调研锚点 + 公开源(可复盘)
  - "perspectives/musk-perspective/references/research/06-timeline.md"
```

5 镜头 id:`origin`(起源叙事)/ `category`(品类定义)/ `leverage`(杠杆护城河)/
`identity`(身份系统)/ `signal`(真实信号)——与 events 的 `lens_map`、星图镜头一致。

## 反捏造约定(本维度立身之本,坑 #3)

- **履历里程碑 = 带 provenance 的事实**:每条 `career[].evidence` 必填(校验器硬 gate),
  照搬/改写自对应评委 `06-timeline.md` 的 `Public Evidence` 标注,或真实源 URL;**不新造来源**。
- **创始人↔品牌关系 = 标注的分析**:`relation` 文字**必须以「分析:」开头**(半/全角冒号均可),
  是 MBA 的判断(像报告 Origin 镜头),**不冒充本人原话**。**✅ 已机器强制**:`validate_founders.py`
  硬 gate 每个 relation 值须以「分析:」起头(缺前缀 = CI 红),把这条口头承诺升级成门禁。
- **逐字引语只能来自该评委 research 语料**:若 yaml 里出现引号内引语,写入前 `grep -F` 验证
  (中文去空格)在 `perspectives/<slug>-perspective/references/research/*` 里逐字存在。
  (创始人页不是 SKILL.md → 不进 `firewall_check`,这条纪律靠人工;首批 yaml 已避免嵌入声称引语。)
- **锁年 / cutoff 诚实留白**:时代性观点锁年份,cutoff 外(如 wanghuiwen 2023 健康退隐、
  zhangbangxin 2021 双减后战略、yangzhilin 2024 之后)一律留白,不臆测、不替本人延伸。
- **联合创始人如实标**:meituan 主创始人是王兴(无 perspective),王慧文是**联合创始人**且是评委
  → `role: 联合创始人`,文字点明王兴为主创始人/CEO,不包装成唯一创始人。
- **不改评分**:创始人维度作调研输入与叙事对照,**分数只能来自评委重审**。

## 工具链

| 环节 | 脚本 | 说明 |
|---|---|---|
| 校验(硬 gate) | `scripts/founder-tools/validate_founders.py` | schema + brand 对齐白名单 + 履历带 provenance + 镜头合法 + perspective 真实;`--selftest` 自证有牙。接入 `panel-validation.yml` |
| 生成 | `scripts/build_founder_pages.py` | `founders/*.yaml` → `site/founders/<slug>.html` + 索引;零依赖 house style;接入 `site/build.sh` |
| 一致性 | `scripts/check_consistency.py`(第 8 项) | 委托 validate_founders,跨源总览一格 |
| 入口 | `build_home_cards.py` / `build_brand_starmap.py` / `build_watch_cockpit.py` / `build_watch_pages.py` | 有 `founders/<slug>.yaml` 才挂「创始人 →」 |

**提交前必跑**(在 CLAUDE.md 清单基础上):
```bash
python3 scripts/founder-tools/validate_founders.py            # 4 份档案合规
python3 scripts/founder-tools/validate_founders.py --selftest # 门禁有牙
python3 scripts/build_founder_pages.py                        # 本地预览 site/founders/
```

## 后续扩展 SOP(新增一个品牌创始人)

1. 若创始人是评委 → 复用其 `06-timeline.md`(优先);否则 `curl` 走 `$HTTPS_PROXY`+CA 取一手履历
   (坑 #1,**不用 WebFetch**),每条里程碑带真实 URL/provenance。
2. 写 `founders/<slug>.yaml`:履历 `career` + 5 镜头 `relation`(标注分析)+ `sources`。
3. `validate_founders.py` 通过;若含引语 `grep -F` 核对源语料。
4. `build_founder_pages.py <slug>` 本地渲染,Playwright 自检 0 JS 错误。
5. 无需改各入口生成器——它们按 `founders/<slug>.yaml` 是否存在自动挂链接。

---

## 附:开发计划存档(2026-07-16)

> 本节存档本维度的原始开发计划(用户批准),便于复盘。实现已按此计划落地。

**触发需求:** 「增加一个维度,就是品牌的创始人,梳理创始人的履历,并且从人物的角度,梳理与品牌之间的关系。」

**用户确认的两个决策:** 呈现形式 = 独立创始人页 + 各处入口;首批范围 = 4 位「创始人即评委」。

**分三步(单 PR,squash):**
1. **数据层 + 校验器** —— `founders/` 目录 + 4 个 yaml(复用 06-timeline);`validate_founders.py`
   (照 `validate_watch.py` 写法:枚举校验 + `--selftest`),接入 `panel-validation.yml`。
2. **生成器 + build.sh** —— `build_founder_pages.py` → `site/founders/<slug>.html`(复用
   `build_watch_pages.py` house-style 骨架,零依赖);`site/founders/` gitignore;接入 `site/build.sh`。
3. **各处入口 + 一致性 + docs** —— 首页卡片/星图/驾驶舱/watch 页加「创始人 →」(仅有数据的品牌);
   `check_consistency.py` 加一格;本文档 + docs 索引 + CLAUDE.md 清单。

**验证(端到端):** validate_founders `--selftest` 全绿 → 4 yaml 通过 → 反捏造 `grep -F` 自查 →
`build_founder_pages.py` 生成 4 页 + Playwright 0 JS 错误 → 各入口跳转正确 → `check_consistency` /
`build_home_cards --check` / `build_agents_api --check` 无漂移。

**明确不做:** 首批 4 位 +（后扩)zhipu = 5 位;其余 10 品牌留后续(需 `curl` 取一手);
不改已发布报告 HTML;不做创始人自动传记生成(履历必须逐条带 provenance)。
