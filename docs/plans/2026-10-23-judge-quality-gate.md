# PRD-151/T1：评委工程质量 checklist 草案

> trend issue #755。对应 PRD-151（中央仓库 zhanglunet/trend）。
>
> 定位：PRD-022 管住了 panel 结构（"考卷印刷没印错"），PRD-063 管住了打分一致性（"另一位老师
> 改卷"）；本草案补第三层——**每位评委这个交付物本身的工程质量**（测试 / 示例 / 文档完备度），
> 作为元评审的下一级输入。T1 只出设计，不写实现代码；不改评分业务逻辑本身
> （不动 5 镜头口径、judge-prompt-template、panel yaml 字段语义、meta_review 四项审计算法）。
>
> 依据（仓库现状，2026-10-23 实测）：`perspectives/` 下 43 套 `*-perspective/`，
> `references/research/` 目录 43/43、`references/research/quotes.md` 43/43；
> CI `panel-validation.yml` 已有 8 类与评委直接相关的机器门禁；元评审 job（PRD-063/T4）
> 已挂在同一 workflow。
>
> 借鉴：EveryInc/compound-engineering-plugin（MIT，Copyright © EveryInc）——只借鉴其
> "工程质量 checklist 按维度分组、每条带机器可执行验收方式"的结构思路，
> 原项目：<https://github.com/EveryInc/compound-engineering-plugin>。
> 本文档全部条目、ID、阈值、措辞均为本仓库自研，未复制其文本。

## 一、现状盘点：收拢已有门禁，不重复造轮子

评委质量在仓库里已有大量机器门禁，问题是**散**——信号分布在 6 个脚本 + 2 个测试目录，
没有"单个评委一页视图"。本 checklist 的 P0 层就是把这些既有门禁按评委粒度收拢；增量全在
P1 层（示例可复制性、URL 锚定率、cutoff 日期、占位符纪律、tier 如实标注）——这些今天没有
机器门禁。

| 既有资产 | 覆盖范围 | 收拢为 |
|---|---|---|
| `scripts/perspective-tools/check_structure.py`（对 H2 结构 spec） | 43 套，CI 硬门 | A-1 |
| `scripts/perspective-tools/quality_check.py`（6 项内容质量，全量 6/6 硬 gate） | 43 套，CI 硬门 | A-2 |
| `scripts/perspective-tools/firewall_check.py`（反捏造逐字引用防火墙） | 43 套，CI 硬门 | A-3 |
| `scripts/check_self_conflict.py`（+ `--smoke`） | 43 套，CI 硬门 | A-4 |
| `scripts/validate_panels.py` + `tests/panels`(70) + `tests/_contract`(2)（PRD-022） | 10 panel / 43 slug | A-5 |
| `scripts/build_agents_api.py --check` + mcp-ci personas 生成（CLAUDE.md 坑#2） | 派生产物漂移 | A-6 |
| `scripts/check_consistency.py`（版本 / docs 索引 / 评委数 / 工具数 / 维度口径） | 全仓一致性 | A-5/A-6 旁路依赖 |
| `scripts/ci_meta_review.py`（PRD-063/T4，PR-only、continue-on-error、只报告） | 打分一致性 | §四挂钩点 |

结论三条：

1. P0 六项今天已全量 43/43 绿（CI 硬门保证）——checklist 不新增 P0 负担，只防退步。
2. PRD-151 的真实增量是 B/C 两组共 7 项 P1：全部是"交付物完备度"，与打分逻辑零接触。
3. "评委工程质量"的操作定义：把散在上述脚本里的信号，聚合为 per-judge 的
   `PASS n/13 · warn m · exempt k` 一页视图。

## 二、评委工程质量 checklist 条目表（13 条，P0 六条 + P1 七条）

每条字段：条目 ID / 要求 / 验收方式 / 现状。验收方式尽量给机器可执行命令（P0 全部已是
仓库既有命令，本草案不新造）。

### 维度 A：测试与机器门禁（P0，任何一项 fail 即 FAIL）

| ID | 要求 | 验收方式 | 现状（2026-10-23） |
|---|---|---|---|
| A-1 | SKILL.md H2 结构符合 `metric-brand-auditor/references/perspective-structure-spec.md`（5 个必需 section 及其内容 rubric） | `python3 scripts/perspective-tools/check_structure.py --perspective <slug>` exit 0 | 43/43 过（CI 硬门） |
| A-2 | 内容质量 6/6：心智模型 ≥6、模型局限性、表达 DNA ≥3 个不同 facet、诚实边界 ≥3 条、内在张力 ≥2 行、一手来源占比 >50% | `python3 scripts/perspective-tools/quality_check.py perspectives/<slug>-perspective/SKILL.md` exit 0 | 43/43 过（CI 全量硬 gate） |
| A-3 | 反捏造防火墙：SKILL 内声称的逐字引用（blockquote + 带署名代表句式）必须在本套 `references/research/` 语料逐字存在 | `python3 scripts/perspective-tools/firewall_check.py`（全量）exit 0 | 43/43 过（CI 硬门） |
| A-4 | self-conflict 声明完整（`--panel-drop <own-slug>` + 关联表 slug 真实） | `python3 scripts/check_self_conflict.py && python3 scripts/check_self_conflict.py --smoke` exit 0 | 43/43 过（CI 硬门） |
| A-5 | panel 引用完整：任一引用该 slug 的 panel yaml 字段合法、portrait 存在 | `python3 scripts/validate_panels.py` + `python -m pytest tests/panels tests/_contract -q` exit 0 | 10 panel 全过（CI 硬门） |
| A-6 | 派生产物同步（坑#2）：SKILL.md 改动后 `site/api/*.json` 与 mcp-server personas 已重生成 | `python3 scripts/build_agents_api.py --check` exit 0；mcp-ci 里 `git diff --quiet` | 已入两条 CI workflow |

### 维度 B：示例与语料（P1，T2 起机器化，过渡期 warn-only）

| ID | 要求 | 验收方式 | 现状 |
|---|---|---|---|
| B-1 | `references/research/01-06.md` 六路齐全、每份非空 | 目录列举 + 文件字节数 > 0 | 目录 43/43（实测）；非空性 T2 出基线 |
| B-2 | `references/research/quotes.md` 存在，且 ≥90% 条目带 URL 锚定（`…](http…)` 形态） | T2 脚本解析锚定行占比 | 存在性 43/43（实测）；锚定率未测，T2 先测基线再定阈值 |
| B-3 | 每套含 ≥1 个可复制调用示例（"用 <slug> 视角看…"整行，用户可原样粘贴） | grep SKILL.md / references 命中调用句式；过渡期先人工抽检 | 未测 |
| B-4 | Honest Boundary 含研究截止日期（cutoff，"此后不可代言"） | 该 section 内匹配 `cutoff`/`截止`/`截稿` | 未测 |

### 维度 C：文档与纪律（P1，T2 起机器化，过渡期 warn-only）

| ID | 要求 | 验收方式 | 现状 |
|---|---|---|---|
| C-1 | frontmatter `description:` 非空且含 ≥1 条显式触发短语（"用 X 视角"类） | yaml 解析 + 长度 / 触发句式匹配 | `validate_panels.py` 只查 slug 存在性，触发词未查 |
| C-2 | `docs/10-deepening-perspectives.md` tier 追踪表如实：slug 集合与 `perspectives/` 实际一致、seed/full 标注与语料规模相符（不许虚标） | 对照表 slug 集合 vs 目录实际；tier 与研究文件规模抽核 | `check_consistency.py` 未覆盖 tier 列 |
| C-3 | 无真实内部主机名 / IP / 账号 / 密钥，示例一律占位符 | 正则清单扫描（§三.4），白名单内占位形态不报 | 未测 |

计分口径：P0 六项任一 fail ⇒ 结论 FAIL；P1 七项只产出 warn。单评委结论形如
`PASS 13/13 · warn 0 · exempt 0`。

## 三、抽检机制设计（T2 预告：金样例）

1. **两种运行模式**（T2 脚本，建议 `scripts/perspective-tools/quality_gate.py`，纯标准库，
   只调用 A 组既有脚本、不改它们）：
   - `--judge <slug>`：单评委跑全部 13 条，产出报告——即 PRD-151 对 T2 的验收线"可对单个评委产出报告"；
   - `--sample <轮次>`：每轮确定性抽 5 套（slug 字典序 + 轮次偏移取模），不用时间、不用随机，同轮次可复现。
2. **触发**：过渡期只做两件事——① PR 改动 `perspectives/**` 时跑受影响评委（复用 meta-review job
   的 `git diff --name-only` 检测模式，PRD-063/T4 先例）；② 手动全量。不新增 cron。
3. **金样例（防误报的回归基线，仓库 F8 负样本自测先例）**：
   - 金正样例：`satyanadella`——期望 13 项全过（选它的理由见 §六）；
   - 金负样本：`tests/quality/fixtures/fake-judge/` 下的合成 SKILL（不入 `perspectives/`），
     内置已知违规：3 个心智模型、表达 DNA 同 facet 重复、无署名的伪造 blockquote、
     形如真实密钥的合成占位串——期望 A-2 / A-3 / C-3 必拦；
   - 验收：金样例连跑 10 次，报告 sha256 逐字节一致（PRD-063/T5 e2e 同款验收法）。
4. **C-3 正则清单（初版，随 T2 入库）**：`(api[_-]?key|token|secret|password)\s*[:=]`；
   内网网段 `\b(10|172\.(1[6-9]|2\d|3[01])|192\.168)\.\d+\.\d+\b`；
   已知密钥前缀形态 `akm-`、`sk-ant-` 后接占位串；`-----BEGIN` 私钥块。
   白名单（不报）：`<API_KEY>`、`akm-xxx`、`sk-ant-...`、`example.com`、`example.internal`
   等显式占位写法。
5. **报告格式**（120 秒可读，PRD-063 同款纪律）：结论行 → 缺口表（条目 ID / 现状 / 建议动作）→
   豁免列表（显式列出，不静默）→ 附录机器可读 JSON 行（§四.2 的接口契约）。T2 只报告不阻断；
   P1 转 hard gate 另立议题，本 PRD 不做。

## 四、与 PRD-063 元评审流程的挂钩点

1. **CI 位置**：复用 `panel-validation.yml` 的 `meta-review` job（`needs: validate-panels`、
   PR-only、`continue-on-error`）。T3 在该 job 末尾追加"评委工程质量门禁状态"段，并把
   `git diff` 检测范围从 panel yaml 扩展到 `perspectives/**`——不改"只报告、不设合并门禁"的
   既有纪律（PRD-063 §四.3）。
2. **接口契约（T1 定，T3 实现）**：机器可读行，元评审只读不解释——

   ```json
   {"gate_version": "prd-151-v1", "judge_slug": "<slug>",
    "items": [{"id": "B-2", "level": "P1", "status": "warn"}],
    "pass_count": 12, "warn_count": 1, "exempt_count": 0}
   ```

   `status` 枚举固定 4 值：`pass` / `warn` / `fail` / `exempt`；`level` 固定 `P0`/`P1`。
3. **复核线索联动**：元评审审计项 3（同号 bias 序列 K≥3 且 `|mean(bias)| ≥ 0.5` ⇒ 疑似系统性
   偏见）命中某评委时，T3 在该行附"该评委最近一次 checklist 结论 + 过门日期"——若偏松 / 偏紧
   伴随 B/C 维度缺口（语料陈旧、quotes 缺锚定），人工复核优先级提高。**只加线索，不改元评审
   四项审计算法与 A–F 评级阈值。**
4. **措辞纪律沿用 PRD-063 §四**：缺口不叫"错误"；先报告后门禁；"工程质量缺口"≠"打分错误"
   （评委视角本该有分歧，checklist 管交付物完备度，不管分数）。
5. **产物入库位置（T3 起）**：报告 `docs/quality/judges/<slug>-<YYYY-MM-DD>.md`
   （纯加法新目录）；豁免登记 `docs/quality/exemptions.yaml`（§五）。T1/T2 阶段报告只走
   stdout / PR summary，不入库。

## 五、过渡期与豁免标注设计

1. **时钟锚**：T0 = 本设计文档合入 main 的 commit 日期（git log 可查，不依赖运行时钟）。
   T0 + 60 天为过渡期。
2. **过渡期规则**：P1 七项全部 warn-only；P0 六项任何时刻 fail 即 FAIL——**P0 不设豁免**
   （它们今天已全绿，退步即回归，没有豁免的理由）。过渡期结束后 P1 是否转 hard gate，
   另开议题决策，不自动收紧（PRD-151 非目标：不一次要求 43 个评委全绿）。
3. **豁免登记**（`docs/quality/exemptions.yaml`，集中单文件，便于 diff review）：

   ```yaml
   - slug: <judge-slug>          # 一位评委
     item_id: B-2                # 只允许 P1 条目
     reason: <一句话，必填>
     expires: 2026-12-31         # 必填，按日期判断，过期自动失效
     issue: zhanglunet/trend#755 # 追踪链接
   ```

4. **约束**：每位评委同时有效豁免 ≤3 条；改豁免文件的 PR 必须人工 review（人工闸门，与仓库
   "合并 = 人工闸门"惯例一致）；T2 报告中豁免项显式列出并计入 `exempt_count`，不静默。

## 六、1 个评委过门示范的选取计划

**选取标准**（可核查）：① 属 default 或 security panel（代表性）；② 是
perspective-structure-spec 点名的 reference shape；③ 补缺只动文档 / 示例层，不动语料正文与
打分相关文件；④ 过门过程可复现（T2 脚本一条命令出报告）。

- **主选：`satyanadella`**——structure spec 明示其为目标形态、最短 production 参考（~140 行），
  A 组六项预期零缺口；示范聚焦"补 P1 文档缺口"这条最常见路径。
- **备选：`jobs`**——default panel 成员、诚实边界 reference shape、被文档引用最多；
  若 satyanadella 一步全绿（失去示范价值），改选 jobs，预期有 1–2 条 P1 缺口，
  可完整演示"缺口 → 修复 → 复跑 → 全绿"流程。
- **验收线（T4，#758）**：对选定位跑 `--judge <slug>` 得 `PASS 13/13 · warn 0 · exempt 0`；
  过程记录为 `docs/plans/` 示范文档（含修复前后两份报告 diff），保证"范例可复现"（T5 验收项）。

## 七、下一步

确认后进 T2（#756）：抽检/门禁脚本（最小）——`scripts/perspective-tools/quality_gate.py`，
纯标准库、只调用现有脚本不改其业务逻辑；支持 `--judge` / `--sample` / `--selftest`；
金样例回归（§三.3）与确定性验收（10 次 sha256 一致）随脚本交付；C-3 正则清单（§三.4）
作为初版随脚本入库。T1 验收线：本草案评审通过（#755）。
