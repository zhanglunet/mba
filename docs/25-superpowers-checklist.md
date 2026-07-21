# docs/25 — Superpowers 本地 checklist(每次开发自检)

> **这是什么**:用户 standing rule 要求「每次开发都验证是否遵守 Superpowers」。**Superpowers = obra
> 的 Claude Code 插件**([github.com/obra/superpowers](https://github.com/obra/superpowers),一套软件开发
> 方法论 + 可组合技能)。但本项目常在 **web/远程 Claude Code** 里开发,`/plugin` 不可用、插件装不上——
> 所以把它的**方法论与铁律蒸馏成这份本地 checklist**,每次开发收尾逐条对照,并在过程记录里写明
> 「Superpowers 自检:通过 / 偏离哪条」。**不是插件本体,是可对照的规则副本。**
>
> **来源(2026-07-21 curl 抓取,走出口代理)**:`raw.githubusercontent.com/obra/superpowers/main/README.md`
> 与 `skills/{using-superpowers,brainstorming,writing-plans,test-driven-development,
> verification-before-completion,requesting-code-review}/SKILL.md`。铁律为原文转写(见各条引号)。
> 插件更新后本文可能滞后——以上游为准,装得上时优先用真插件。

---

## 0. 总铁律(using-superpowers)

> 原文:「If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY
> MUST invoke the skill. … Invoke relevant or requested skills **BEFORE any response or action** — including
> clarifying questions, exploring the codebase, or checking files.」

- **先查技能,再动手**:动手/回答/提澄清问题**之前**先想「有没有适用的 skill/规范」。
- **优先级**:流程技能(brainstorming、systematic-debugging)先定方法,实现技能后落地。
- **红旗**(以下念头=正在给自己找借口,STOP):「这题太简单」「先探探代码」「我记得这技能」「这不算任务」
  「这技能小题大做」「就先做这一件」。
- **用户指令 > 技能 > 默认**:CLAUDE.md 与用户直接要求**压过**技能;只有用户明说跳过时才跳过。

## 1. 七阶段基本工作流(README「The Basic Workflow」)

| # | 阶段(skill) | 触发时机 | 要点 |
|---|---|---|---|
| 1 | **brainstorming** | 任何创作/加功能/改行为**之前** | 苏格拉底式追问意图→提 2-3 个方案→分块给设计→**拿到批准**再动。**一次只问一个问题**。「太简单不用设计」是反模式——设计可短(几句),但**必须给且获批**。 |
| 2 | **using-git-worktrees** | 设计获批后 | 新分支上开隔离工作区、跑项目 setup、确认测试基线干净。 |
| 3 | **writing-plans** | 有获批设计时 | 拆成 **2-5 分钟一个的 bite-sized 任务**,每个任务写明**确切文件路径 + 完整代码 + 验证步骤**;假设执行者「零上下文、品味存疑、讨厌测试」。**No placeholders**。DRY / YAGNI / TDD / 频繁提交。 |
| 4 | **subagent-driven-development / executing-plans** | 有计划、说「go」后 | 每任务派新 subagent,两段式审查(先合规、再质量);或分批执行 + 人工检查点。 |
| 5 | **test-driven-development** | 实现期 | 见下「Iron Law」。RED-GREEN-REFACTOR,**MANDATORY, never skip**。 |
| 6 | **requesting-code-review** | 任务之间 | 派**独立** reviewer subagent(只给精心裁剪的上下文、不给会话历史)按严重度报问题;critical 阻断。 |
| 7 | **finishing-a-development-branch** | 任务完成时 | 验证测试→给选项(merge/PR/keep/discard)→清理 worktree。 |

## 2. 两条最硬的 Iron Law(逐字)

**verification-before-completion**:
> `NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE` — 「If you haven't run the verification
> command in this message, you cannot claim it passes.」「Claiming work is complete without verification is
> **dishonesty, not efficiency**. Evidence before claims, always.」
- 门函数:声称任何「通过/修好/完成/Done/Perfect」之前 → ①指出哪条命令能证明 → ②**当场跑完整命令** →
  ③读全输出+退出码+失败数 → ④确认 → 才能声称,且**带证据**。跳任何一步 = 撒谎。
- 红旗:用「should / probably / seems」、还没跑就说「Great!/Done!」、没验证就 commit/push/PR、信 subagent 的
  「success」报告(要独立看 VCS diff 核实)。

**test-driven-development**:
> `NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST` — 「Write code before the test? Delete it. Start over.
> … Delete means delete.」回归测试要走 **Red → Green**:写→跑(过)→回滚修复→跑(**必须红**)→恢复→跑(过)。

## 3. MBA 适配(本项目怎么落地)

MBA 是**内容型仓库**(审计报告 / YAML / 生成物为主),不是经典应用代码,所以要分清哪些直接套、哪些改写:

- **直接套**:brainstorming(动手前对齐意图/方案——尤其新品牌、新维度、发版口径)· writing-plans(大改动先出
  bite-sized 计划)· **verification-before-completion(最硬,永远套)** · requesting-code-review(复杂改动)·
  finishing-a-development-branch(收尾走 PR/merge 决策)。
- **改写 TDD**:`scripts/` 与 `packages/mcp-server/` 是真代码 → **改逻辑先补/跑测试**(mcp-server 有单测;脚本可
  加 selftest,如 `validate_*.py --selftest`、本次 `new_daily.py` 的保留逻辑就先写了验证脚本再改)。
  **审计报告 / YAML 数据不写单元测试**,但它们有等价的「测试」=**本项目门禁**(见 CLAUDE.md「提交前必跑」):
  `check_report_integrity` / `validate_report` / `validate_html_report` / `check_consistency` / `firewall_check`
  / `check_self_conflict` / `build_agents_api --check`。**这些门禁就是 MBA 版的 verification-before-completion**。
- **反捏造 = Superpowers 的「Evidence over claims」在 MBA 的形态**:引文逐字命中语料、分数只经评委重打、
  dim/severity 标 model-judged——本质都是「证据先于声称」。

## 4. 每次开发收尾:逐条自检(贴进过程记录)

```
Superpowers 自检(vs docs/25):
□ 0  动手前是否先想过「有无适用规范/skill」?(brainstorming/systematic-debugging 先行)
□ 1  改行为/加功能前,是否与用户对齐了意图与方案(brainstorming),而非直接开写?
□ 3  大改动是否有 bite-sized 计划(writing-plans),还是边想边改?
□ 5  动了 scripts/ 或 mcp-server/:是否先跑/补了测试(TDD)?报告/YAML:是否跑了对应门禁?
□ 2  verification:每一句「通过/修好/完成」是否都在本条消息里**当场跑过命令**、贴了证据?
□ 6  复杂改动是否请了 code review(或至少自审 diff + 反捏造 grep)?
□ 7  收尾是否走了 PR/merge 决策、清理分支?
→ 结论:通过 / 偏离了第 __ 条(说明原因)
```

配合 CLAUDE.md「提交前必跑」门禁一起用。**未装真插件时,以本文为对照;如实写「以 docs/25 checklist 自检」,
不假称「已用 Superpowers 插件」。**
