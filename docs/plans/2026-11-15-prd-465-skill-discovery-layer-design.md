# PRD-465/T1：mba skill 发现层 设计（锚点核查先行：可索引对象已钉死）

> trend issue [#2245](https://github.com/zhanglunet/trend/issues/2245)；来源 issue trend [#528](https://github.com/zhanglunet/trend/issues/528)（[待研究] mba：参考 ASPIRE 做 skill 发现层，保持 open）。来源：2026-11-15 GitHub 趋势日报（`digests/2026-11-15.md`）前置核查，用户 2026-11-15 采纳，口径：**先研究锚点、再定方案**，不直接按 ASPIRE 原样做；PRD 全文：`adopted/PRD-465-mba-skill-discovery-layer.md`。
> 设计日：2026-11-15 · 目标仓库：zhanglunet/mba
> 状态：T1 设计草案，待评审。仅设计文档（纯加法 .md）；最小实现（T2）、发现回路闸门（T3）、划界断言（T4）、验收试运行（T5）按本设计后续落地。
> 示例全部虚构占位，不出现真实内部主机名、IP、账号或密钥。

## 1. 锚点核查结论（T1 第一步，先钉死锚点）

### 1.1 原设想的锚点存疑，已核实

#528 原文把发现层挂在"能力索引（PRD-045）"上。核实结论：**PRD-045 是 SiliconForge 的能力/skill 索引页，不是 mba 的**——PRD-045 全文（`adopted/PRD-045-sf-capability-index.md`）相关仓库为 zhanglunet/SiliconForge（AgentNet），trend issues #218/#221/#226/#229/#232；日报核验将其定为 **B 类部分交付**。mba 自身的插件化是 **PRD-021**（按官方插件市场格式发布 skill）。

因此"能力索引"在 mba 语境下没有一个已确认的现成锚点——本节改用 mba 自身结构重新钉锚点。**PRD-045 只部分交付是既定事实，不反说已完成**；本设计只借其"分类浏览 + 关键词/标签搜索 + 能力卡片"的发现层形态作内部衔接参考。

### 1.2 mba 现有 skill 结构实测（2026-11-15，main 分支递归 tree 实测复核）

| 对象 | 实测结果 |
|---|---|
| `perspectives/*/SKILL.md` | **46 个**评委视角 skill（PRD 写作时写"约 40 个"，实测为 46 个，如 arnault-perspective、musk-perspective、jobs-perspective 等） |
| `plugins/mba-brand-audit` / `plugins/mba-compliance-check` | 各带 SKILL.md + manifest.json，在位 |
| 其余插件 | `plugins/mba`、`plugins/mba-copy-review`、`plugins/mba-market-sizing`、`plugins/mba-visual-review` 也在位（PRD 未列出，属新增发现） |
| `metric-brand-auditor/SKILL.md` | 在位 |
| `registry.json` | 在位，schema `judge-pack-registry/v1`：按 pack（评委组，如 mba-brand）登记 skill，含 `triggers`（触发句式）、`x-perspective_ref`（指向 perspectives/ 目录），是评委归属与检索的单一事实源 |
| `REGISTRY.md` | 在位 |
| `.claude-plugin/marketplace.json` | 在位，但只列出 **1 个**插件（mba v0.6.1）；其余 5 个插件尚未进 marketplace 清单 |
| PRD-234 T3 可发现性结构检查 | 全部在位：`docs/plans/prd234-t3-discoverability-report.json`、`scripts/check_perspective_discoverability.py`、`tests/unit/test_prd234_t3_discoverability.py`、`.github/workflows/watch-discover.yml` |

PRD-234 T3 查的是**单个 SKILL.md 的 frontmatter 合规性**（name/description/metadata.version/standard），不是"用户描述需求 → 推荐 skill"的发现层；报告显示已知缺口：个别 description 超 1024 字上限、个别 skill 缺 `metadata.version` / `standard` 声明。发现层设计须与这套元数据口径对齐，**不另起一套元数据口径**。

### 1.3 锚点结论：锚点存在，止损条件不触发

**发现层可索引的对象（已钉死）：**

1. **46 个评委视角 skill**（`perspectives/*/SKILL.md`）：索引键 = registry.json 的 `triggers` + SKILL.md frontmatter 的 name/description；
2. **6 个插件**（`plugins/*`，各带 SKILL.md + manifest.json）：索引键 = manifest 的 name/description/keywords；
3. **metric-brand-auditor**（独立 skill）：索引键 = SKILL.md frontmatter。

**缺口（发现层 T2 须先补齐或绕过，不硬做）：**

- marketplace 清单只含 1 个插件——发现层不依赖 marketplace.json 作唯一源，以 registry.json + 各 SKILL.md frontmatter 为准；
- PRD-234 T3 的 frontmatter 缺口（description 超长、缺 version/standard）——发现层只读合规字段，缺口由 PRD-234 T4 补齐，发现层不替它改数据；
- 尚无统一的"需求描述 → skill"关键词索引——这正是发现层 T2 要建的东西。

**止损结论：锚点存在，后续任务（T2–T5）不取消。** 若 T1 结论是锚点不存在才取消——本次不适用，结论同步回填 #528。

## 2. 背景与目标

mba 的 skill 现在散着，没有一层发现入口：用户描述想做的事，系统还不会推荐合适的 skill 或插件。发现层的目标：

- 用户描述想做的事，系统推荐合适的 skill 或插件；
- 推荐**可溯源**（为什么推这个：命中了哪个触发词 / 关键词 / 标签）；
- 推荐**可复核**（推错可纠：人可否决、反馈回流）。

先研究锚点、再定方案：§1 已钉死锚点，本节出方案。ASPIRE 只作形态借鉴，不直接套用。

## 3. 与既有机制划界（非目标）

| 维度 | PRD-465（本条：发现层） | PRD-021（mba 插件化） | PRD-234 T3（可发现性结构检查） | PRD-045（SF 能力索引页） |
|---|---|---|---|---|
| 管什么 | "用户描述需求 → 推荐 skill"的**发现** | skill 按官方插件市场格式**发布** | 单个 SKILL.md 的 frontmatter **合规检查** | SF 的能力**索引页**形态参考 |
| 不做什么 | 不做安装（安装走各 skill 自己的标准链路）；不碰评审流程与分数；不做评分、评论、付费等商店高级功能 | — | 发现层不另起一套元数据口径，与之对齐 | PRD-045 本身是 SF 的，不是 mba 的；且只部分交付 |

## 4. 红线

| # | 红线 | 落地方式 |
|---|---|---|
| R1 | **不碰 mba 现有评审流程与分数** | 发现层只做"发现"，评分、评委包、品牌审计报告均不动；推荐结果不写入评审分数 |
| R2 | **不重复造 skill 注册表** | 发现层只做"发现"，安装走各 skill 自己的标准链路；索引源复用 registry.json + 各 SKILL.md frontmatter，不新建注册表 |
| R3 | **PRD-045 只部分交付是既定事实，不反说已完成；T1 止损结论可取消后续任务** | 本次锚点存在，止损不触发（§1.3）；若后续发现锚点失效，结论写进设计文档并回填 #528 |
| R4 | 只借鉴形态，代码复用需署名；ASPIRE 代码复用须保留 Apache-2.0 许可证声明 | 见 §5 |
| R5 | 占位符纪律 | 本文件及后续实现文档、示例中不得出现真实内部主机名、IP、账号或密钥，一律用占位符；T5 检查覆盖本文件 |
| R6 | 实现类 PR 只开不合并 | 等用户 review；#528 是来源 issue，立项后保持 open 直到用户另行决定 |

## 5. 借鉴对象、许可证与不复用红线

- NVlabs/ASPIRE（Apache-2.0）——"Agentic Skills Discovery for Robotics"的 skill 发现与组合机制，**形态借鉴为主**；代码复用需署名、保留许可证声明。注意：ASPIRE 面向机器人领域，概念迁移到品牌审计知识工作需验证；本设计先用关键词匹配起步（T2），语义推荐留待后续评估。
- trend PRD-045（SiliconForge 能力/skill 索引页）——内部衔接参考：分类浏览 + 关键词/标签搜索 + 能力卡片的"发现层"形态；**注意：PRD-045 本身是 SF 的，不是 mba 的；且只部分交付（B 类），T1 已核实其实际落地程度**。
- trend PRD-021（mba 按官方插件市场格式发布 skill）——内部衔接：发现层索引的对象来自插件化后的 skill 结构。
- trend PRD-234 T3（视角 skill 可发现性结构检查）——内部衔接：单个 SKILL.md 的 frontmatter 合规检查已存在，发现层设计须与之对齐，不另起一套元数据口径。

本设计草稿为原创文字；借鉴形态只借思路，不引入原仓依赖，不复制原仓文本或代码。

## 6. 发现层设计

### 6.1 索引：先建关键词索引，不先上语义推荐

索引源（只读，不改源数据）：

- `registry.json`：pack → skill 映射、`triggers` 触发句式、`x-perspective_ref`；
- 各 `SKILL.md` frontmatter：name（= 目录名，kebab-case）、description（≤1024 字合规者为准）；
- 各插件 `manifest.json`：name / description / keywords。

T2 先用关键词匹配起步：用户需求描述分词后匹配 triggers + description + keywords，命中即候选；语义推荐留待后续评估（ASPIRE 的机器人领域组合机制迁移到品牌审计需先验证，不在 T2 做）。

### 6.2 推荐记录 schema（T2 预埋）

```json
{"schema": "mba-skill-discovery/v1",
 "request": {"request_id": "r-001", "text": "我想看看这个品牌在年轻人里什么位置（占位）"},
 "candidates": [{"skill": "perspectives/first-glance-shopper-perspective",
   "score": 0.8, "matched": ["年轻人", "位置"],
   "reason": "触发句式命中：triggers 含「年轻人视角」（占位）"}],
 "recommendation": {"skill": "perspectives/first-glance-shopper-perspective",
   "trace": "matched triggers + description 关键词（占位）"},
 "review": {"verdict": "accepted|rejected", "reviewer": "reviewer（占位）", "note": "推错可纠（占位）"}}
```

### 6.3 发现回路：推荐可溯源、可复核

1. 用户描述需求 → 关键词匹配出候选（带 matched 词与 reason）。
2. 推荐呈现给人：每个推荐附溯源（命中了哪个触发词 / 关键词 / 标签）。
3. 人复核：接受（accepted）则推荐生效；否决（rejected）则反馈回流（记入 review.note，供后续调关键词权重）。
4. 推荐只做"发现"：安装走各 skill 自己的标准链路，发现层不替 skill 安装、不改评审分数。

### 6.4 接入点

| 接入点 | 说明 |
|---|---|
| 索引构建 | 离线读 registry.json + SKILL.md frontmatter + manifest.json，生成关键词索引（T2） |
| 推荐调用 | 用户描述需求时调用，发现层返回带溯源的候选清单（T2） |
| 人工复核 | 推荐呈现后由人接受 / 否决，否决反馈回流（T3） |
| 出口 | 推荐结果不进评审流程、不进分数；只作为"建议用什么 skill"的入口 |

## 7. 验收标准（T1 设计评审通过的条件）

- [ ] 锚点结论写明：可索引对象清单 + 缺口（§1），止损结论写明（本次不触发，§1.3）；
- [ ] 发现层可索引的对象与 mba 现有 skill 结构对齐（46 个视角 skill + 6 个插件 + metric-brand-auditor），与 PRD-234 T3 元数据口径对齐，不另起一套口径；
- [ ] 设计覆盖索引、推荐 schema、溯源与复核回路（§6），关键词匹配起步、语义推荐留待后续评估的取舍写清；
- [ ] 与 PRD-021 / PRD-234 T3 / PRD-045 的划界写清（§3），PRD-045 的归属与交付状态表述准确；
- [ ] 红线章节在位（§4），借鉴声明与许可证口径在位（§5）；
- [ ] 全文无真实内部主机名、IP、账号或密钥，示例均为占位符；
- [ ] 本 PR 只开不合并，等 review；结论同步回填 #528；T2–T5 按本设计落地时各附 devlog 与测试。

## 8. 后续任务

T2 最小实现：关键词匹配起步（有测试）→ T3 发现回路闸门：推荐可溯源、可复核（有测试）→ T4 划界断言：不碰评审流程与分数、不绕过 skill 自己的标准安装链路（有测试）→ T5 验收试运行：真实需求描述 → 推荐 → 人工复核，全链跑通。依赖关系：T1 → T2 → T3 → T4 → T5；T1 的止损结论可取消 T2–T5（本次不触发）。
