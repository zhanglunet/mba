# OpenAI v1 调研留痕(FRESH · 2026-07-12)

**Cutoff:** 2026-07-12
**Mode:** FRESH / 250 分制(vc-en 5 评委 × 5 镜头 × 10)/ mba 0.4.3 / `--quick`(open-web,无 Wuying leg)
**Panel:** `vc-en`(pmarca / paulg / pthiel△ / naval / rhoffman△)
**品牌框定:** 统一评 **OpenAI**(公司/品牌整体:ChatGPT、GPT 系列、API、微软关系、治理史);**产品聚焦 Codex**(编码 agent 产品线)——Codex 在 Category(agentic coding 品类)与 Leverage(开发者生态)镜头下单列分析。

## 0. 调研方法与诚实声明

- 所有取数走本会话出口代理 curl(Chrome UA + `/root/.ccr/ca-bundle.crt`),未用 WebFetch;WebSearch 仅作线索,入证据的事实全部 curl 原文核对(HTTP 200 + `<title>` 命中 + 正文关键句逐字命中)。
- **openai.com 对本环境出口回 403**(源站拒绝,与 anthropic.com 同类),官方稿(introducing-codex / accelerating-the-next-phase-ai / openai-submits-confidential-s-1 等)未能直接核对,一律改用 URL 内嵌日期的权威媒体稿(CNBC / TechCrunch / Forbes / Guardian / NPR / Constellation),官方稿 URL 记于 §3 待回溯。
- **reuters.com 对本环境出口回 401**(付费墙),ChatGPT 100M 纪录改用 Guardian 同日稿(内文引 UBS 报告原句)。
- 竞争语境(Anthropic Series H / Fable 5 / 出口管制)直接复用 `watch/anthropic/events.yaml` 已核实事件(该文件建库时已逐字 curl 核对标题),不重复取数。
- 评委引语纪律:reviews 与报告中所有署名给评委本人语料的英文引文,均已 `grep -F` 逐字命中各自 `references/research/`(含 quotes.md);蒂尔语料一律按其 SKILL 规则标注 "Masters' notes of Thiel's lecture, 2012"。
- **未核实即未写入**:原 Codex 模型(2021,曾驱动 GitHub Copilot)的沿革,TechCrunch 2021 原文 URL 已失效(404),该叙述**不进报告**;Axios "GPT-5 landed with a thud" 未 curl 核对,不引用;"Claude Code #1 most-loved" 系开发者博客问卷(uvik / dev.to),权威性不足,不引用,竞品对比改用 The New Stack 已核对原文。

## 1. 已核对来源清单(fetch 日期均为 2026-07-12)

| # | 来源 | URL(日期自证) | 核对状态 |
|---|------|----------------|----------|
| S1 | TechCrunch 2015-12-11 · OpenAI 创立 | https://techcrunch.com/2015/12/11/non-profit-openai-launches-with-backing-from-elon-musk-and-sam-altman/ | 200,关键句逐字命中 |
| S2 | The Guardian 2023-02-02 · ChatGPT 100M/2 个月 | https://www.theguardian.com/technology/2023/feb/02/chatgpt-100-million-users-open-ai-fastest-growing-app | 200,UBS 引语逐字命中 |
| S3 | CNBC 2023-03-03 · Hoffman 退出 OpenAI 董事会 | https://www.cnbc.com/2023/03/03/reid-hoffman-steps-down-from-openai-board-to-avoid-potential-conflicts.html | 200,本人引语逐字命中 |
| S4 | NPR 2023-11-22 · Altman 复职 | https://www.npr.org/2023/11/22/1214621010/openai-reinstates-sam-altman-as-its-chief-executive | 200,OpenAI X 声明逐字命中 |
| S5 | CNBC 2025-01-21 · Stargate 白宫发布 | https://www.cnbc.com/2025/01/21/trump-ai-openai-oracle-softbank.html | 200,金额句命中 |
| S6 | TechCrunch 2025-04-16 · Codex CLI 开源 | https://techcrunch.com/2025/04/16/openai-debuts-codex-cli-an-open-source-coding-tool-for-terminals/ | 200 |
| S7 | TechCrunch 2025-05-16 · Codex 云端 agent 发布 | https://techcrunch.com/2025/05/16/openai-launches-codex-an-ai-coding-agent-in-chatgpt/ | 200,codex-1/沙箱句命中 |
| S8 | CNBC 2025-08-07 · GPT-5 全量发布 | https://www.cnbc.com/2025/08/07/openai-launches-gpt-5-model-for-all-chatgpt-users.html | 200,700M 周活预期句命中 |
| S9 | TechCrunch 2025-09-15 · GPT-5-Codex | https://techcrunch.com/2025/09/15/openai-upgrades-codex-with-a-new-version-of-gpt-5/ | 200,"几秒到七小时"句命中 |
| S10 | CNBC 2025-10-28 · PBC 重组 · 微软 27% | https://www.cnbc.com/2025/10/28/open-ai-for-profit-microsoft.html | 200,26%/47%/$135B/$250B 句命中 |
| S11 | CNBC 2026-03-31 · $122B 轮 · $852B 估值 | https://www.cnbc.com/2026/03/31/openai-funding-round-ipo.html | 200,收入/Sora 关停句命中 |
| S12 | Forbes 2026-04-27 · 微软独家关系终止 | https://www.forbes.com/sites/aliciapark/2026/04/27/openai-and-microsoft-end-exclusive-partnership-and-revenue-sharing/ | 200,"ends exclusivity / caps revenue"句命中 |
| S13 | CNBC 2026-05-28 · Anthropic $965B 超越 OpenAI | https://www.cnbc.com/2026/05/28/anthropic-open-ai-startup-value.html | 复用 watch `2026-05-28-anthropic-001`(标题已逐字核对) |
| S14 | Constellation Research 2026-06-02 · Codex 5M 周活 | https://www.constellationr.com/insights/news/openai-touts-broadening-codex-usage-5-million-weekly-active-users | 200,OpenAI 引语逐字命中 |
| S15 | CNBC 2026-06-05 · Hoffman 离开微软董事会 | https://www.cnbc.com/2026/06/05/linkedin-co-founder-reid-hoffman-leaving-microsoft-board-after-decade.html | 200,"early funder of OpenAI"句逐字命中 |
| S16 | CNBC 2026-06-08 · OpenAI 秘密递交 S-1 | https://www.cnbc.com/2026/06/08/openai-confidentially-files-for-ipo-prepping-wall-street-for-ai-debut.html | 200,官方声明全文命中 |
| S17 | TechCrunch 2026-06-08 · 跟随 Anthropic 递交 IPO | https://techcrunch.com/2026/06/08/following-anthropic-openai-files-confidentially-for-ipo/ | 200 |
| S18 | The New Stack 2026-06(6/1 首发)· 四大编码 agent 六个月对比 | https://thenewstack.io/claude-code-vs-cursor-vs-codex-vs-antigravity-2026/ | 200,Codex 分发/AGENTS.md/定价句命中 |
| S19 | TechCrunch 2026-06-09 · Claude Fable 5 发布 | https://techcrunch.com/2026/06/09/anthropic-released-claude-fable-5-its-most-powerful-model-publicly-days-after-warning-ai-is-getting-too-dangerous/ | 复用 watch `2026-06-09-anthropic-002` |
| S20 | Fortune 2026-06-13 · Fable/Mythos 出口管制下线(6/30 解除,CNBC) | https://fortune.com/2026/06/13/anthropic-disables-fable-mythos-export-controls-national-security-threat/ | 复用 watch `003`/`004` |

官方稿待回溯(openai.com 403):`openai.com/index/introducing-codex/`、`openai.com/index/accelerating-the-next-phase-ai/`、`openai.com/index/openai-submits-confidential-s-1/`、`openai.com/our-structure/`。

## 2. 核心事实(全部可溯源至 §1)

### 2.1 起源与治理史
- 2015-12-11 以**非营利**形式创立;资金方:Altman、Brockman、Musk、Jessica Livingston、**Peter Thiel**、AWS、Infosys、YC Research,承诺 $1B(S1 原句:"The organization is being funded by Altman, Brockman, Musk, Jessica Livingston, Peter Thiel, Amazon Web Services, Infosys and YC Research. Those funders have contributed $1 billion thus far.")。
- 2018 Musk 退出董事会(避免与 Tesla AI 冲突);2019 转为利润封顶(capped-profit)结构(S3 内文)。
- **Reid Hoffman 是 OpenAI 早期捐赠人、前董事**,2023-03-03 因利益冲突退出董事会(S3;S15 单句:"Hoffman was an early funder of OpenAI and sat on the board until 2023, when he left to avoid conflicts.")。其本人解释(S3 逐字):"But by stepping off the board, I can proactively put to rest any downstream potential issues for both OpenAI and all Greylock portfolio companies I've backed."
- 2023-11-17 董事会解雇 Altman → 2023-11-22 复职,新初始董事会 Bret Taylor(Chair)、Larry Summers、Adam D'Angelo(S4 逐字引 OpenAI X 声明)。
- 2025-10-28 完成重组:营利实体改为 **OpenAI Group PBC**(利润封顶取消);OpenAI Foundation 持 26%,现/前员工与投资人 47%,微软持 $135B ≈ **27%**(此前 as-converted 口径 32.5%);OpenAI 承诺增购 **$250B Azure**;微软失去算力优先购买权;AGI declared 需独立专家小组认定,revenue share 持续至该认定(S10)。
- 2026-04-27 微软-OpenAI **独家关系终止**、revenue share 封顶(S12;微软累计投资 $13B:2019 起,2023 追加 $10B)。

### 2.2 规模与信号
- ChatGPT 2022-11-30 上线,**2 个月 100M 用户**;UBS(S2 逐字):"In 20 years following the internet space, we cannot recall a faster ramp in a consumer internet app."
- 2025-08-07 GPT-5 面向全部用户(含免费档)发布;当周预期 700M 周活;彼时正洽谈 ~$500B 估值股份出售(S8)。
- 截至 2026-03:ChatGPT **>900M 周活**、订阅者 >50M(S11)。
- 2026-03-31 关闭 **$122B** 融资(史上最大私募科技轮),投后 **$852B**;SoftBank 与 a16z、D. E. Shaw Ventures 共同领投;锚定投资:Amazon(至多 $50B)、Nvidia($30B)、SoftBank($30B);**月收入 $2B**(≈$24B 年化),2025 全年收入 **$13.1B**;**仍在烧钱、未盈利**;近月收缩开支、**关停短视频应用 Sora** 等产品(S11)。
- 2025-01-21 Stargate:与 Oracle/SoftBank 的 AI 基建合资公司,首期 $100B、四年至多 $500B(S5)。
- 2026-05-28 **Anthropic Series H 以 $965B 投后超越 OpenAI($852B)成为最有价值 AI 初创**(S13)。
- 2026-06-08 秘密递交 S-1(晚 Anthropic 一周、早 SpaceX 上市数日);官方声明(S16 逐字):"We recently submitted a confidential S-1. We expect it to leak so we're just announcing it. We have not decided on timing yet; it may be a while because there are things we want to do that are likely easier as a private company...";同步计划按 $852B 估值为员工做要约收购;投行 Goldman Sachs + Morgan Stanley(S16)。

### 2.3 Codex 产品线(产品聚焦)
- 2025-04-16 **Codex CLI** 开源发布(本地终端 agent,接 o3/o4-mini)(S6)。
- 2025-05-16 **Codex 云端 agent** 在 ChatGPT 内发布(research preview):由 codex-1(o3 的软件工程优化版)驱动,云端沙箱虚机运行,GitHub 仓库预载(S7)。
- 2025-09-15 **GPT-5-Codex**:动态分配"思考"时长,"a few seconds to seven hours";专训代码评审(S9)。
- 后续型号线:GPT-5.1-Codex-Max(压缩跨上下文长任务)→ GPT-5.2-Codex(2025-12)→ GPT-5.3-Codex(2026-02,"beyond coding")——本段沿革以 WebSearch 线索 + openai.com 官方稿标题为据,官方稿正文未能 curl(403),报告中仅以"型号线快速迭代"概括,不引具体性能数字。
- 2026-06-02 **Codex >5M 周活**;知识工作者占 ~20% 且增速更快;桌面应用拉动使用;OpenAI 原句(S14 逐字):"The data suggests a broader shift is underway. Knowledge workers primarily use Codex to create reports, spreadsheets, presentations, contracts, and other work products.";Constellation 判断:"developer share for Codex has fallen off with gains in knowledge workers"、"Codex is often being used alongside of Claude Cowork and Code"(S14)。
- 竞争格局(S18,The New Stack 六个月复盘):Codex **打包进 ChatGPT 订阅、无独立价签**,"reached scale faster than anything else in the category";OpenAI 口径:2026-04 中 >3M 周活开发者,5 月末 >4M;"the real money coming from enterprise rollouts within ChatGPT Business and Enterprise";**AGENTS.md 规范由 OpenAI 发起**,Google/Cursor/Sourcegraph 跟进,2025-12 起归入 Linux Foundation 旗下 Agentic AI Foundation(与 MCP 并列);Codex/Cursor/Copilot/Windsurf 原生读取,Claude Code 仍读自己的 CLAUDE.md;截至 2026-05 中 SWE-bench Verified 头部分数已收敛到窄带——"模型被降级",差异化转向 harness/工作流/审批模型/分发;定价:Cursor Pro 与 Claude Code 入门档均 ~$20(2026-06),Anthropic Max 更高;衡量口径应为 "cost per accepted change"。
- 竞品动态:Google Antigravity 2.0(2026-05-19,I/O);GitHub Copilot(品类奠基者,坐拥 merge 场所);Meta 入局 AI 编码(S11 内文提及);Anthropic:Claude Cowork/Claude Code(S14/S18)。

### 2.4 竞争语境(watch/anthropic 复用)
- 2026-06-09 Anthropic 发布 Claude Fable 5(Mythos 级首个公开版);2026-06-13 美出口管制致 Fable/Mythos 全球下线 18 天,2026-06-30 解除;同日发布 Sonnet 5(agent 性价比档)。
- 2026-06-08(S16 内文):OpenAI 面临 Anthropic、Google 与 SpaceX(年内已并入 xAI)的竞争;AI IPO 管线:Anthropic、OpenAI、SpaceX。

## 3. Lead 增量判断(供打分参考,不替评委下结论)

1. **品类所有权是最强资产**:ChatGPT 即品类本身(100M/2 个月 → 900M 周活),Category 是五镜头中唯一接近封顶的。
2. **Codex 是"分发的翻盘"样本**:CLI(4 月)→ 云 agent(5 月)→ GPT-5-Codex(9 月)→ 5M 周活(2026-06),核心机制是**打包进 ChatGPT 订阅无独立价签**——分发赢了规模,但"无价签"同时意味着价值捕获未被证明;心智端 Claude Code 在深度/大库场景仍被 The New Stack 列为重心所在,Codex 的重心是 reach 与企业铺开。AGENTS.md 让 OpenAI 拿到了品类的"宪法起草权",但起草权是公共品,不是私有杠杆。
3. **Leverage 的两面**:900M 周活分发 + 万亿级算力锁定(Stargate/$250B Azure)是史上最大杠杆,也是史上最大固定成本承诺;模型层收敛(SWE-bench 窄带)侵蚀"模型即护城河"。
4. **Identity 是最弱镜头**:11 年三换结构(非营利→capped→PBC→IPO 进行时);"Open"之名与商业闭源的张力;Sora 高调发布→为控成本关停;Codex 从"编码 agent"扩张为"every role"的通用工作 agent——扩张给 Signal 加分、给身份一致性减分。
5. **Signal 硬但有裂缝**:$13.1B→$2B/月是真收入;未盈利 + 烧钱 + 估值王冠被 Anthropic 摘走($965B vs $852B)+ 关停 Sora——公开市场即将逐季定价这组矛盾。
6. **利益披露必须显性**:pthiel(创立期捐赠人,S1)与 rhoffman(早期捐赠人+前董事,S3/S15)均△;paulg 为邻近关联(其妻 Jessica Livingston 为创始捐赠人之一、Altman 为其钦点的 YC 继任者),不足△但 Legal 段如实披露。
