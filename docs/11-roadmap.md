# MBA 开发路线图与进度日志

> **文档定位**：本文件同时承担两个职责——  
> 1. **路线图**：记录下一步开发计划，优先级和理由  
> 2. **进度日志**：每次开发动作在此追加记录，形成可查历史

---

## 当前状态快照（2026-07-06）

| 维度 | 状态 | 备注 |
|------|------|------|
| 版本 | **v0.4.2** | 实时联网研究 + 断点续跑（v0.4.1 首发 npm） |
| 5阶段流水线 | ✅ 生产就绪 | Phase 0-5 + Phase 5M（panel-merge）稳定 |
| 评委面板数量 | ✅ 10/10 全部可运行 | default / auto / security-cn-global / ai-app-cn / edu-cn / vc-en / vc-cn / consumer-cn / cross-border / luxury-en |
| 评委全档进度 | ✅ **42/43 全档** | 1 人仍在 seed（`zhanglan` 已严格核算诚实留 seed）；权威名单见 `docs/10 §6`（本表曾长期滞后，勿再手抄 slug） |
| mbabrand.com | ✅ 上线 | Cloudflare Pages |
| 公开报告 | ✅ 10/10 全部发布 | 10 面板各 1 份；Hermès 8.64 创三项史上最高 |
| CI/CD | ✅ 全绿 | 面板校验 + 报告结构校验（硬/建议分级）+ 站点构建 |
| 集成测试 | ✅ 已建立 | report-validation.yml + MCP e2e（真实 MCP 协议层） |
| --dry-run / --panel-merge | ✅ 已实现 | Phase 0 §0.5 / Phase 5M |
| MCP Server 形态 | ✅ 已发布 npm | packages/mcp-server/ · **16 工具**(含舆情 `get_watch_events`/`record_watch_event`)· **10 面板 / 43 评委** · webhook 接收端 · `resume_audit` 续跑 · **实时联网研究**(`MBA_WEB_SEARCH`) · 220 tests · `npx -y mba-mcp-server@latest` |
| 演化追踪 | ✅ 完成 | 订阅 + cron + trigger_evolution + delta 报告 + 增量重跑 + webhook/email 通知 |

### 评委全档分布（按面板覆盖，更新 2026-07-10）

> 权威 FULL/seed slug 名单以 `docs/10 §6` 为准（本节只给面板覆盖概览,不再手抄易错的 slug 列表）。

**满档面板(9)**:`default` · `auto` · `security-cn-global` · **`vc-en`** · **`vc-cn`** · **`ai-app-cn`** · **`cross-border`** · **`luxury-en`** · **`edu-cn`**
(六个行业面板 vc-en/vc-cn/ai-app-cn/cross-border/luxury-en/edu-cn 本场全部 seed→full 收官;edu-cn 2026-07-10 由 `zhangbangxin` 收官。**10 个面板仅 consumer-cn 未满档**——因 `zhanglan` 经严格核算主动留 seed)。

| 面板 | 全档进度 | 下一步 |
|------|---------|--------|
| default / auto / security-cn-global / vc-en | ✅ 满档 | — |
| **luxury-en** | ✅ **5/5** | 整面板收官(2026-07-10):`cucinelli`(人文资本主义 report)+ `awintour`(署名 Editor's Letters + 悼念信)+ `burton`（**= Sarah Burton 麦昆/纪梵希**,干净标签访谈,atelier/fitting）+ `tomford`（Tom Ford,GQ+Interview Mag 干净标签访谈）+ `arnault`（Bernard Arnault,LVMH 署名年报董事长致辞+致股东信,一手 100%,30+ 条 verbatim,desirability/长期主义/eternal Maison）全 full。**4 路 scout 推翻"访谈=二手"+"arnault marginal";继 vc-en、vc-cn、ai-app-cn、cross-border 后第五个整面板 full** |
| edu-cn | ✅ **5/5** | 整面板收官(2026-07-10):`yuminhong`(俞敏洪)+ `salkhan`(Sal Khan,官方 TED transcript)+ `zhangbangxin`（张邦鑫,route-A 重扫达标——芥末堆 2016 年会+2019 AI教育大会**演讲实录** semi + 报道引述,39 条 verbatim,教不好=抢钱/管理增长/教育本质是爱,强锁双减前)全 full,+ `likejia`/`wu-jundong`(复用 default)。**推翻上轮"偏紧"判定;第六个 seed→full 收官的行业面板** |
| ai-app-cn | ✅ **5/5** | 整面板收官:`yangzhilin`/`wanghuiwen`/`zhuxiaohu` route-A 深化 + `zhouhongyi`/`fusheng`(复用 default)。王=纯一手演讲(源码/清华)+ semi-一手笔记侠整理产品课(类比 pthiel,健康/退隐留白)。继 vc-en、vc-cn 后第三个整面板 full |
| cross-border | ✅ **5/5** | 整面板收官:`huangzheng`(黄峥)+ `yangjianhui`(阳萌)+ `shouzichew`(周受资,2023 国会书面证词)+ `chennian`(陈年,2014 一件衬衫 828 实录)+ `zhuangshuai`(庄帅,署名专栏 self-writing 一手 100%,货场人/殊途同归,2026-07-10)全 full。继 vc-en、vc-cn、ai-app-cn 后第四个整面板 full |
| vc-cn | ✅ **5/5** | 整面板收官:`xuxin`/`zhanglei`/`shennanpeng`/`zhuxiaohu` route-A 深化 + `leijun`(复用 auto)。继 vc-en 后第二个整面板 full,首个中文行业整面板 full |
| consumer-cn | **4/5** | ✅ `yangjianhui`+`luoyonghao`+`jiangnanchun`+`zhongshanshan` 已 full;`zhanglan`(张兰)**经严格核算主动留 seed**——唯一干净一手仅澎湃深访 2114 字,凑不齐 ≥30 逐字/≥80% 一手,直播口语无实录、自传为版权书(守 §3 门槛,详见 docs/10) |

---

## 关键阻断项

| 阻断项 | 影响范围 | 解法 | 状态 |
|--------|----------|------|------|
| ~~沙箱 WebFetch 对 paulgraham.com 等返回 403~~ | ~~英文评委深化~~ | **CCR Network access 设 Full + `curl` 走 `$HTTPS_PROXY` 出口代理(带浏览器 UA + CA)** | ✅ **已解(2026-07-07)**;vc-en 5 位即用此法完成。**注意:WebFetch 本身仍 403(走 Anthropic 服务端出口),用 curl。** |
| 中文源站(知乎/百度百科/微博/澎湃)反爬/JS 墙 | 部分中文评委深化 | 36氪/新浪/腾讯新闻/企业官网/公众号可 curl;其余需 Wuying 或加 allowlist | ⚠️ 部分可绕 |
| Wuying 免费版 `GetLink` 返回 400 | 依赖 Wuying 的中文站抓取 | 升级到 Pro/Ultra(多数情况"Full + curl"已够,可不依赖 Wuying) | ⚠️ 降级 |

---

## 开发路线图

### 工程健壮化 backlog（2026-07-10 整体盘点 · 4 路并行深读结论）

内容侧已收尾(42/43 full + 1 诚实 seed;10 报告);真实短板集中在**质量自动化 / flagship 验证 / 一致性**。

- **E0-1 反捏造 firewall 进 CI ✅ 已完成(2026-07-10)** —— `scripts/perspective-tools/firewall_check.py`:校验每套 SKILL「心智模型/关键引用」区 `>` 逐字引用必须在本套 `references/research/*.md` 逐字命中;接 `panel-validation.yml` 硬 gate。**把反捏造从人工纪律升级成机器门禁**;上线即抓出并修复 jobs 2 条未锚定引用(no taste / cannibalize)。`quality_check.py` 同时接入 CI(仅对本 PR 改动的 SKILL 阻断 6/6)。
- **E0-2 报告渲染 QA 进 CI ✅ 已完成(2026-07-10)** —— `scripts/qa_report_render.mjs`(headless Chromium,抓 Chart.js 无限增高 / Mermaid 未渲染 / 零高 canvas,曾搞坏 kimichat/qianxin)接入 `report-validation.yml` 的 `render-qa` job;新增 `scripts/qa_fetch_libs.sh` 把 Chart.js 4.4.4 + Mermaid 11 确定性 vendored(`--offline-libs`,不依赖 jsdelivr 在线)。10 报告全过、负测试(注入 JS 报错)exit 1 验证过 gate 有牙。exit 1/3 阻断、exit 2(inconclusive)非阻断。
- **E0-3 self-conflict 静态拦截 ✅ 已完成(2026-07-10)** —— `metric-brand-auditor/self-conflict.yaml`(41 位评委 → 强关联品牌/机构别名表)+ `scripts/check_self_conflict.py`。**validate**(接 `panel-validation.yml` 硬 gate):每套 SKILL 的 Self-Conflict Rule 都声明了 `--panel-drop <own-slug>`、关联表 slug 全真实、orgs 非空;**query**(`--brand X [--panel P|--industry I]`):被审品牌命中评委强关联表 → 列冲突评委 + 建议 `--panel-drop` flags(把"评自家品牌"从人工记忆升级成可查/可拦);**smoke** 6 用例自测。匹配:去空白/标点后大小写不敏感子串,纯 ASCII 别名 ≥3 字才子串(X/YC/360 只精确匹配防误拦)、含 CJK 别名 ≥2 字即可(华为/苹果/小米 等中文品牌信息密度高)。负测试(注入未知 slug/空 orgs)exit 1 验证 gate 有牙。
- **E1-4 真跑一个 EVOLUTION v2 ✅ 已完成(2026-07-10)** —— 挑 **anthropic** 真跑通 v1→v2(14 天真实 delta:Sonnet 5 上市 + IPO 落定 + 安全护城河从"技术"迁移到"治理/分发")。**真管线**:4 个 delta 研究 sub-agent(Category/Leverage/Safety/Signal,各喂 v1 结论只找增量)→ Lead 写 `_raw/synthesis_v2.md` → 5 个评委 sub-agent 各 load 自己的 perspective SKILL 在角色内重评(带 v1 分卡,标 `↑↓↔`)→ Phase 5E 版本化合成。**产物**:`report.md`/`report.html` v2(内联 delta 分数表 `7→6 ↓1`/`↔`、delta banner、**Mermaid gitGraph 版本时间线**、v1-vs-v2 对比柱状图)+ `versions/v{1,2}_*.{md,html}` 快照 + `reviews/*_v2.md`(保留 v1)。**结果**:总分 191→190(−1)但组成旋转——Leverage ↑0.6(gateway 锁定,3 人↑1)、Signal ↓1.0(gross/net ARR 全员齐降)、Category 方向撕裂(Hoffman/Thiel ↑ vs PG ↓)。render QA 验证 `canvas=2 mermaid=1` 全渲染(gitGraph 出 svg、无 JS 报错、无无限增高)。**验证了 skill 最大卖点的整条 EVOLUTION 管线**,可宣传。
- **E1-5 MCP Phase 3/4/5 + 持久层单测 ✅ 已完成(2026-07-10)** —— 给此前零直测的最烧钱阶段与持久层补 **+37 单测**(vitest 121→158 全绿):`tests/orchestrator/phase-3-synthesis`(3:4096 budget / 写 `_raw/synthesis.md` header+body / 维度全喂进 prompt)、`phase-4-judging`(7:默认 5 评委并行、`options.judges` 覆盖、**单评委失败 allSettled 存活**、全失败抛 `JUDGING_FAILED`、可解析则写 `scores.json` 均值、不可解析跳过、自定义 persona 文件注入 system prompt)、`phase-5-merge`(5:8192 budget / report.md header+footer+legal / **HTML 转义**注入的 `<script>` / `versions/v1_<date>.md` 快照 = report.md / panel 评委进 merge prompt)。持久层用**真实 temp 目录**(mock fs 无意义):`tests/store/atomic`(7:建父目录 / 覆写 / 无 `.tmp` 残留 / 20 并发不串写 / unicode 保真)、`store/filesystem`(8:initAudit 脚手架 / state round-trip / 嵌套 writeFile / listAudits/listFiles / 审计隔离)、`store/subscriptions`(7:round-trip / 按 created_at 排序 / 忽略非 json / delete true|false / findByBrand 只返 active)。typecheck + build 均过、无 persona 漂移。
- **E2-6 一致性清账 ✅ 已完成(2026-07-10)** —— 8-agent 并行审计(7 轴 + completeness critic)→ 主循环逐条核实后落地:**版本对齐**(SKILL 面板模板 `mba_version` 0.2.38→0.4.2 —— 每份 FRESH 报告都拷这个模板;docs/01-prd `(当前)` 迁到 v0.4.2)、**docs 索引收 docs/14**(docs/README + README `01-14` + CLAUDE.md)、**工具数 11→14**(docs/13 §5 补 `resume_audit`/`list_panels`/`get_brand_trend` 三个真工具 + docs/README + site)、**dimensions**(build_agents_api 注释;7↔9 本已自洽:7 核心 + 2 高级 = 9)、**报告目录**(lenovo 补 `panel.yaml`,从 reports-meta 机械重建;md/reviews/_raw 从未提交、不捏造,已注明)、**`validate_panels` warn→error**(断链 perspective / 死 industry 映射;验证 0 面板会新失败)、**`print_report.sh` 跨平台**(改用 `$PLAYWRIGHT_BROWSERS_PATH/chromium` 发现,Linux/CI 可出 PDF)。critic 额外抓出 `site/roadmap.html` 停在 15/43 的旧状态板 → 更新为 42/43 + 各面板真实进度 + 测试数 158。**新增 `scripts/check_consistency.py`**(版本对齐 / docs 索引 / 评委数 / 工具数 / 维度口径 5 项不变量)接 `panel-validation.yml` 硬 gate,负测试验证有牙。
- **E2-7 早批 6 套 quality_check 补齐 6/6 ✅ 已完成(2026-07-10)** —— hexiaopeng/leijun/libin/lixiang/musk/zhanglan 补齐,**43/43 全过 6/6**,并把 `quality_check` 从"仅阻断 PR 改动的 SKILL"升为 `panel-validation.yml` **全量硬 gate**(任一套掉出 6/6 即红)。根因多为格式代理:`## 表达 DNA` 标题带空格(regex 需无空格)→ hexiaopeng/leijun/libin;内在张力 marker <2 → leijun/lixiang/zhanglan;musk(2/6 最重)缺 局限性/DNA marker/张力/一手占比。**全部靠诚实重格式化**——给已有英文 DNA 子节加 CJK gloss(节奏/词汇/句式)、把既有模型已隐含的失效模式/张力显式成 prose section、按真实归属给 Sources 路由打 Primary/Secondary 标签;**零新增 `>` 引用块**,firewall 167 quotes 不变(SKILL⊆research 仍成立)。诊断用 workflow 6 agent 并行出 firewall-safe edit plan,主循环校验唯一匹配后应用。

### F 系列 backlog(2026-07-11 · 6-agent survey workflow 结论)

E0–E2 工程硬化收官后,下一批短板集中在:**flagship 特性只证明 n=1(EVOLUTION / 从没跑过的 --panel-merge)、research 语料本身无人校验(信任链根部)、skill⇄MCP 从未同品牌对齐、网站没真正呈现 EVOLUTION**。按杠杆排序:

- **F1 报告数字自洽 gate ✅ 已完成(2026-07-11)** —— `scripts/check_report_integrity.py`:`validate_report` 只查结构,从不查算术;本 checker 校验每份 published 报告 Score Matrix 的 **① 维度 Mean == 评委均值 ② Judge Total == 列和 ③ Score Total == 全表之和 ④ Normalized == total/满分×10**(容差 0.05)。单元格含 v2 delta(`7→6 ↓1`/`↔`)取当前值;跨 9 份异构格式(σ 列 / `Total /10` 行 / `△` 竞争标记 / `总分`vs`Score Total`)**解析不出即跳过、不误伤**,只对明确算术错误 FAIL。接 `report-validation.yml` 硬 gate;负测试(改错 Mean / 评委总分 / Score Total)全部 exit 1 验证有牙。
- **F2 首跑 `--panel-merge`(Phase 5M)✅ 已完成(2026-07-11)** —— skill 第二大 flagship 章节此前 0 验证(0 个 `Panel Comparison`)。挑 **anthropic** 真跑:同一份简报(`_raw/synthesis.md` + `synthesis_v2.md`)由 **vc-en(硅谷 VC,取 v2 参照)** 与 **vc-cn(中国 VC,新评)** 独立打分。5 个 vc-cn 判官后台并行、各 load 自己 perspective 在角色内 FRESH 打分(带 flag 数字自标不当审计事实)。**产物**:`report.md`/`report.html` **v3 PANEL-MERGE**(双 Score Matrix + `## Panel Comparison`:side-by-side deltas / agree / diverge / panel fingerprints / cross-panel verdict + **panel 切换 toggle + 叠加雷达 + fingerprint 分组柱状图 + 5×2 delta 热力图** + gitGraph v1→v2→v3)+ `versions/v3_*_panel-merge.{md,html}` + `reviews/{5 vc-cn}.md`。**结果**:两面板方向惊人一致(所有镜头 |Δ|≤0.8,无一达 1.5),vc-cn 系统性偏严 −2.2(35.8 vs 38.0/50)集中在 Leverage/Identity;两面板共识裂缝重合(Signal 全 10 评委齐打 gross/net 折价、Identity 同为最弱)。**F1 report-integrity 在 v3 双矩阵上通过**、render QA `canvas=2 mermaid=1`。验证了 skill 两大 flagship 之一的整条 --panel-merge 管线。
- **F3 EVOLUTION 从 n=1 → n≥2 ✅ 已完成(2026-07-11)** —— 挑 **meituan(vc-cn 中文面板)** 真跑 v1→v2,证明 EVOLUTION 管线泛化(不只对 anthropic/vc-en/英文有效)。**真管线**:4 个 delta 研究 sub-agent(份额/财务/监管/前瞻杠杆,各带 WebSearch,**每条 fact 附真实来源 URL + 日期、`[未核实]` 单列不作打分依据**)→ Lead 写 `_raw/synthesis_v2.md` → 5 个 vc-cn 评委 sub-agent 各 load 自己 perspective 在角色内重评(带 v1 分卡,标 ↑↓↔)→ Phase 5E 版本化合成。**真实可溯源 delta**:v1 把 Signal(8.4)/Leverage(8.0) 锚在 **2023 旧口径**(营收¥276B、~70% 份额、盈利转正),FY2025 年报(2026-03-26,早于 v1 定稿)直接证伪——**由盈转亏净亏¥234亿、营销占比 19%→28.2%、淘宝闪购按 GTV 45.2% 反超美团 45.0%、¥7.46亿食安罚单**;窗口内(07-07 反内卷发布会 / 07-09 商务部意见)确认制度转向。**结果**:总分 **194→168(−26)、7.76→6.72**,美团**让出"MBA 审计史最高分"**;Signal 全员齐降 ↓2.8、Leverage ↓1.4、Category ↓1.0、Origin/Identity ↔。五评委角色内不约而同收敛到同一裁决——**"护城河没被攻破,是被打成了亏损;朱啸虎赢了这一回合,但没赢下整场"**(v1 未决的朱-张之争落地)。**产物**:`report.md`/`report.html` v2(内联 delta 分数表 `8→5 ↓3`、delta banner、gitGraph v1→v2 时间线、v1-vs-v2 对比柱状图)+ `versions/v1_2026-06-28.{md,html}` + `versions/v2_2026-07-11.{md,html}` 快照 + `reviews/*_v2.md`(保留 v1)+ v2 panel.yaml + 首页卡片挂上版本导航。**验证**:check_report_integrity 双数字自洽(means/judge-totals)、render-QA `canvas=2 mermaid=1` 全渲染、无 persona/site 漂移。**反捏造**:facts 全溯源、判官引语为角色内 present-tense 模拟(免责已注)、徐新未引入 v1 没有的新 ★ 冲突。(anthropic v3 的 3-commit gitGraph 已在 F2 panel-merge 完成。)[M/高]
- **F4 反捏造 firewall 扩到「带署名的代表句式」✅ 已完成(2026-07-11)** —— firewall 此前只抓 `>` blockquote,**22/43 套**把逐字引用放在行内或 ```代码块```(代表句式)里,是盲区。扩 `firewall_check.py`:「表达DNA / Expression DNA」等区代码块里**带来源署名**的代表句式(`… —— 致股东信,2018` / `… — Startup = Growth, 2012`)= 声称的真引语 → 必须逐字在 research;**无署名的「Representative lines / answer scaffold」句式模板**(合法风格演示,常带 `{占位符}`)豁免。解析做对(块级多行合并 + 只在有来源信号时才当署名、避免误吃句内破折号 + 句尾标点无关 + 逐句兜底)后 **43/43 全绿、覆盖 167→204 引用(+37)**;负测试(注入 `— Fake Essay, 2099` 假署名引语)exit 1 有牙。**诚实边界**——探索了另两条但判定**不可清洁 gate**、故不做:(a)行内 `"…"` 在这些 SKILL 里语义过载(强调/术语/转述,非只引语),naive 扩产 505 假失败;(b)纯 URL 的 research provenance gate 会大面积误伤(来源异构:arnault/awintour 0 URL 但靠具名书籍/访谈、expression-dna 本无 per-file 源锚);(c)跨 perspective 重复引用探测跑出 23 条全是模板 boilerplate、零真实错配。F4 交付「署名引语必须有据」这一层可清洁强制的地板。
- **F5 skill ⇄ MCP 分数层一致性 ✅ 已完成(2026-07-11)** —— **确认并修掉了格式漂移**:MCP `parseJudgeScores` 原来只认全称锚点 `/Origin authenticity[^\d\n]*?(\d)/i`,而 skill 真实产出的评审用的是**短镜头名 + 双语**——表格行 `| Origin / 起源叙事 | 9 | … |` / `| Origin 起源真实性 | 7 | … |`、分节标题 `### Origin — 8 ↔` / `### 1. Origin 起源真实性 — 7`——**全部解析成 `null`**(离线实测确认)。改法:锚点从全称 label 降到**英文短名**(Origin/Category/Leverage/Identity/Signal,每种观察到的格式里都逐字存在),**按行取值**、分数=短名后同一行内第一个 1–2 位整数(1–10);`↑1/↓1` delta 后缀、`grew 300% in 2024` 理由数字都在其后被 40 字上限挡掉。**防误吃**:仅信任「结构化行(表格/标题/引用/bullet)或短名靠近行首」的行,取首个命中行——挡住 panel-merge 分叉段里 `把 Signal 从 10 压到 7` 这类散文提及劫持分数。**验证**:4 份真实 published 评审(dji/genki 表格、anthropic v2 delta 标题、zhuxiaohu 编号双语标题)端到端解析正确,pthiel_v2 自报 `Net: 34/50` 与 parser `total=34` 吻合;+4 parity 单测(含"MCP bullet ⇄ skill 表格同 5 分产出同 JudgeScores"),vitest 158→162 全绿、typecheck/build 过、无 persona/site 漂移;既有 5 条 MCP 格式断言全部保留(向后兼容)。**留给 F7**:真 API 端到端往返(缺 `ANTHROPIC_API_KEY`,归 F7 的 env-gated live smoke)。[M/高]
- **F6 网站真正呈现 EVOLUTION ✅ 已完成(2026-07-11)** —— 三件事:**① 版本快照上线**:`site/build.sh` 原本 `! -path "*/versions/*"` 把 EVOLUTION 历史快照排除在外(v1/v2 根本访问不到),现改为把 `versions/*.html` 发布到 `/reports/<slug>/versions/`(anthropic 3 份、chengshi-auto 5 份)。**② 首页卡片收敛到单一真源**:卡片此前**手写在 index.html、与 `reports-meta.yaml` 双源**,正是 anthropic 卡片长期停在 `v1 · $965B IPO · 191/250 · 7.64` 的根因(reports-meta 早已是 v3/179/7.16)。新增 `scripts/build_home_cards.py` 从 reports-meta 生成 `<!-- REPORTS:START/END -->` 之间的卡片块(顺序随 `published-reports.txt`),takeaway 用 `tl_dr`(去掉此前字面渲染的 `**`,并去 YAML 折叠在 CJK 间的假空格),多版本品牌渲染「版本演化 EVOLUTION」导航链接。**修 anthropic 错值**由此自动完成(卡片直接读对的 reports-meta)。`--check` 漂移门禁接进 `check_consistency`(第 6 项,已在 `panel-validation.yml` 硬 gate,零改 workflow)。**③ 正确的可点卡片**:发现原卡片把 PDF/版本 `<a>` 嵌在整卡 `<a>` 里会触发 HTML5 adoption-agency 把 `.versions` 踢出 `.report-card`(headless 实测 DOM 脱离、样式失效),改用**拉伸链接**(卡片 `<div>` + 品牌名 `::after` 覆盖整卡 + meta/versions 链接 z-index 浮上)——headless 复验:卡体点击→报告、版本 chip→对应快照、`v3·当前`→线上报告,全部正确。**delta 视图**已内建在各报告(anthropic report.html 自带 delta 表 + gitGraph 时间线),版本快照可点开后即可复盘,故不另做单独 delta 页。[S–M/高]
- **F7 MCP 测试盲区 + 联网 smoke ✅ 已完成(2026-07-11)** —— **+36 单测(vitest 162→198,含 1 条 env-gated live smoke 默认 skip)**,补上此前零覆盖的关键面。**① `trigger-evolution` cadence/月度上限(烧钱逻辑,0 覆盖)** — 10 测:每个「跳过」路径都断言 `runAudit` **未被调用**(真正的防跑飞失控开销,`vi.mock` runner 保证不真跑 5 评委 LLM)、`force` 绕过两道 guard、cadence 边界(`elapsed===min` 放行 / 差 1 分钟拦截,`vi.useFakeTimers` 定死 now)、月度上限命中即跳过 / 跨月重置、proceed 路径(默认 panel、订阅 panel、计数器 +1、最近 done 审计连为 baseline)。**② `prompts.ts`(最大未测文件)** — 16 测:`judgeUserPrompt` 英文模板逐一断言含每个 `LENSES[].name_en`(这些正是 Phase-4 / F5 `parseJudgeScores` 锚点,防模板 ⇄ LENSES 表漂移)、中英模板语言分支、`changeProbeUserPrompt` 2000 字截断(成本护栏)、`synthesisUserPrompt` 未知 slug 回退不漏 `undefined`、`judgeSystemPrompt` 覆盖/`JUDGE_MISSING`、纯函数确定性。**③ `fetch-report`** — 7 测:三种 format 分支 + `AUDIT_NOT_FOUND`/`AUDIT_NOT_DONE`(带 phase)/`REPORT_MISSING`。**④ 版本 DRY** — `0.1.0` 原散在 `server.ts` + `phase-5-merge.ts`(报告页脚 + HTML meta)三处,抽成 `src/version.ts` 的 `SERVER_VERSION` 单一真源;`tests/version.test.ts` 用 `readFileSync` 读真 `package.json` 断言等值(bump 一处忘另一处即红)。**⑤ env-gated 真 API smoke** — `tests/live/smoke.e2e.test.ts`,仅当 `MBA_LIVE_E2E=1` **且** `ANTHROPIC_API_KEY` 都在时跑一次真 `LLMClient.complete` 验响应形状 + token 计数(mock 唯一测不到的 SDK 漂移),CI/离线默认 skip。typecheck/build 过、无 persona/site 漂移。**测试用 mutation-style workflow 对抗性复核**(每条 mutation 是否会被至少一个断言抓住)。[M/高]
- **F8 quality_check 弱代理收紧 ✅ 已完成(2026-07-11)** —— 堵掉 3 项「计数而非计实质」的假过代理,收紧后 **43/43 仍全过 6/6**,并加负样本自测证明有牙:**① 心智模型 3-7 → ≥6**(SOP §3 明确要求 6 个 `### 模型N`;原来一个只写 3 个模型的偷懒 SKILL 也能过)。收紧暴露唯一低于标准的 `likejia`(5 个模型)——**没有为凑数硬编**(那正是本项目反对的 count-gaming),而是从其 research 补了一个**真有据、且与既有 5 个不同**的第 6 模型「中国运营 know-how 的不对称迁移(出海优先)」(李可佳原话「直播、社群、投流等打法,中国团队上手更快」——逐字在 references/research,firewall 通过),使 43/43 达 6 模型。**② 表达DNA:全文计词 → section 内去重 facet**(原来把「句式」写 3 遍即过、且不限区段;改为在表达DNA section 内数**不同** facet 类型 ≥3)。**③ 内在张力:计关键词次数 → ≥2 条不同「非 H2 标题」行**(原来同一句里写两遍「矛盾」即过;改为数含张力标记的独立行,排除只命名区段的 `## 内在张力` H2 标题、保留 `### 张力N` 子标题与正文行——headless 式逐套验证 0 误伤)。**④ `quality_check.py --selftest`**:合成假样本(3 模型 / 单 facet 重复 / 同行堆词)断言被拦、合规样本断言通过,接 `panel-validation.yml` 硬 gate(有人把阈值调松即红)。likejia 改动重生成 personas/site 无漂移。**诚实重定后两项**:`--quick --no-judges` 前门 dogfood 需真跑一次(研究+合成 sub-agent)产出**新发布 artifact**,属 dogfood-run(与 F3 同级),非「便宜收尾」,单列;`--dry-run` **该 flag 在 skill / MCP / 脚本中均不存在**(全仓 grep 仅 `--quick` 有定义),不存在的模式无从 golden-test——若要做需先设计 `--dry-run`(打印解析后的 panel/评委/阶段计划而不执行),属功能新增而非测试,留作独立小项。[S/中]
- **F9 `--dry-run` 计划解析器 + golden 测试 ✅ 已完成(2026-07-11)** —— 兑现 F8 留的独立小项:新增 `scripts/resolve_plan.py` —— 把 SKILL Phase 0 的路由/自检落成**确定性、可测、离线**的脚本,`/mba <brand> --dry-run` 直接调它,**跑前预览、不花一分钱**:解析 panel(严格 `--panel > --industry > 品牌绑定 > default` 优先级,并说明如何解析)、评委名单 + perspective 可用性、自动 flag(无 `WUYING_API_KEY` → `--quick`、评委全缺 → `--no-judges`、部分缺 → judges_incomplete)、self-conflict 冲突评委 + 建议 `--panel-drop`(复用 `check_self_conflict` 关联表)、会跑哪些阶段(FRESH/EVOLUTION/PANEL-MERGE)与大致 sub-agent 规模;panel 缺失 / industry 死映射 → 退出码 2 提前 ABORT。中文品牌名经 `reports-meta.yaml` brand_cn/brand_en 映射到英文 slug 以正确识别 EVOLUTION 基线(美团→meituan)。**golden 测试** `resolve_plan.py --selftest`(16 条断言:优先级/自动 flag/self-conflict/`--no-judges` 跳阶段/`--focus`/死映射 ABORT/panel-merge/中文基线)接 `panel-validation.yml` 硬 gate。`--dry-run` 写进 SKILL.md(命令列表 + Parameters + 触发模式),无 persona/site 漂移。[S/中]

### 优先级 P0 — 立即可执行，不依赖外部解锁

#### P0-A：深化 vc-en 英文评委 ✅ 已完成（2026-07-07）

**结果**：vc-en 5 位全部 seed→full（paulg #47；naval/pmarca/pthiel/rhoffman #48）。
用"CCR Full 出口 + curl 抓一手全文 + 工作流并行建 dossier + 独立防伪(逐字比对语料)"打法。
按引用计一手占比 90–93%。pthiel=Masters CS183 笔记(semi-first-party)、rhoffman AI 偏斜均如实标注。

- [x] paulg — paulgraham.com 28 essay（#47）
- [x] naval — nav.al「How to Get Rich」+ happiness（#48）
- [x] pmarca — pmarchive.com Guide + a16z manifestos（#48）
- [x] pthiel — CS183(Masters 笔记) + Cato essay（#48）
- [x] rhoffman — reidhoffman.org（AI 期,偏斜已注）（#48）

#### P0-A2：深化 luxury-en 中能过门槛的评委（预抓已做,**非 5/5**）

**现实**(2026-07-07 预抓探明):luxury-en 5 位**不是**都能达 80% 一手——多数是设计师访谈(二手)。
按门槛只做能达标的:
- [ ] **`cucinelli`** ✅ 一手强:investor.brunellocucinelli.com「人文资本主义与人的可持续性」报告 PDF(~3.9 万英文词)+ 官网哲学页 + 主席信。**可做真·full**。
- [ ] `arnault` ⚠️ 边际:LVMH 致股东信(lvmh.com/static/letter-to-shareholders-*,单篇短)+ 股东会 transcript;需多篇凑够 30 条一手,勉强。
- [ ] `awintour` / `tomford` / `burton` ⛔ 多为访谈(二手),难过 80%——**保持 seed**,在 docs/10 注明。

**卡点**:深化工作流(subagent)需等 session limit 重置(10:20am UTC);Cucinelli/Arnault 语料现已 curl 预抓在 scratchpad。
**参考 SOP**:`docs/10-deepening-perspectives.md`;模板 `paulg-perspective`。

#### P0-A3：中文评委首批(严守 80% 一手)— ✅ 已完成(2026-07-07)

**结果**：首批 3 位中文评委 `huangzheng`(黄峥,cross-border)、`yuminhong`(俞敏洪,edu-cn)、
`yangjianhui`(阳萌,cross-border / consumer-cn)全部在主循环手工深化到 full——分别由公众号名篇+致股东信合集、
三篇公开演讲全文、安克官网两篇对谈实录蒸馏,均中文去空格+全半角规范化逐字校验,`check_structure`+`quality_check` 6/6,
按引用计一手占比 93–95%。`yangjianhui` 对谈有清晰 speaker 标签(阳萌 vs 杨轩/张鹏),按 speaker 只引本人回答。
**方针兑现**:3 位均过 80% 一手门槛;达不到(源被挡/仅二手)的中文评委保持 seed 并在 docs/10 注明。

#### P0-B：实现 `--dry-run` 标志 ✅ 已完成（2026-06-25）

**目标**：`/mba 小米 --dry-run` 打印 PRD + 面板选择 + 维度计划，不触发真实搜索  
**实现位置**：`metric-brand-auditor/SKILL.md` Phase 0 §0.5 + 参数列表

- [x] SKILL.md 增加 `--dry-run` 参数解析
- [x] Phase 0 新增 §0.5 dry-run exit（原 §0.5 Write panel.yaml 顺延为 §0.6）
- [x] docs/05-usage.md §3.6 补充 `--dry-run` 完整示例

---

### 优先级 P1 — 依赖 Wuying Pro 升级

#### P1-A：批量深化中文评委（25 人）

**触发条件**：Wuying 升级到 Pro/Ultra，`GetLink` 可用  
**执行顺序建议**（按面板使用频率排序）：

1. consumer-cn 5 人（使用频率高，国内品牌大量需求）
2. vc-cn 3 人（投资/创业类品牌需要）
3. ai-app-cn 3 人（AI 产品审计核心面板）
4. cross-border 4 人（出海品牌需求）
5. edu-cn 3 人（教育类）

**每人标准工作量**：约 6 个研究文件（`01-06.md`）+ `quotes.md` 更新  
**验收标准**：`scripts/perspective-tools/quality_check.py` 通过（80% 一手来源）

- [ ] 升级 Wuying 套餐
- [ ] 跑 smoke test 确认 `GetLink` 可用
- [ ] 按顺序深化 25 人

#### P1-B：`--panel-merge` 跨面板对比报告 ✅ 已完成（2026-06-25）

**目标**：支持将两次不同面板的审计结果合并到同一报告的对比章节  
**场景**：同一品牌用 default + vc-en 两套视角对比，形成"内行 vs 外行"差异热力图  
**实现**：SKILL.md v0.2.38；Phase 5M 4步流程；docs/05-usage.md §3.7 用例

- [x] 设计跨面板对比数据结构（Phase 0.3 guard + Phase 0.4 bypass）
- [x] SKILL.md Phase 5M 增加 panel-merge 逻辑（5M.1-5M.4 完整流程）
- [x] HTML 报告模板增加跨面板 diff 热力图组件（面板选择器 toggle + delta 列）

---

### 优先级 P2 — 质量与基础设施

#### P2-A：集成测试 Workflow ✅ 已完成（2026-06-25）

**实现**：基于已发布报告的结构校验（比运行真实流水线更稳定、更快）

- [x] `scripts/validate_report.py`：7 条规则校验 report.md（标题/ScoreMatrix 5镜头/Dissent/Verdict/Legal/Sources）
- [x] `scripts/validate_html_report.py`：7 条规则校验 report.html（canvas/Mermaid/热力图/Verdict/Legal/Sources）
- [x] `tests/fixtures/mock_report.md` + `mock_report.html`：最小合法 fixture
- [x] `.github/workflows/report-validation.yml`：PR/push to main 自动运行

#### P2-B：扩充公开报告（各面板至少 1 份）

**目标**：10 个面板各有 1 份公开样本报告  
**理由**：当前仅 2 份（default + auto），其他 8 个面板无演示  
**选定品牌**：奇安信·Kimi·好未来·Anthropic·元气森林·美团·DJI·爱马仕（各面板 1 份）

- [x] 选定 8 个品牌（每面板 1 个）
- [x] 建档：`published/reports/*/panel.yaml` × 8 + `site/reports-meta.yaml` 8 条 pending 条目
- [x] 运行完整审计（10 份报告全部产出，2026-06-26 ~ 06-28）
- [x] 发布到 `published/reports/`（10 个品牌 report.html 齐全）
- [x] 更新 `site/published-reports.txt`（10 个 slug 全部列入白名单）

**✅ P2-B 全部完成**：10 面板各 1 份公开报告，Hermès 创 MBA 三项史上最高（Identity 9.6 / Origin 9.0 / 总分 8.64）。

---

### 优先级 P3 — 未来形态

#### P3-A：MCP Server 封装 ✅ 完成（2026-06-30）

**包**：`packages/mcp-server/` · **npm**：`mba-mcp-server@0.1.0`  
**工具**：`propose_audit` · `confirm_audit` · `get_status` · `fetch_report` · `list_audits` · `add_judge`  
**内置评委**：傅盛 / Jobs / 李可佳 / 吴俊东 / 张一鸣  
**测试**：22 tests passing · TypeScript zero errors

- [x] 确认 MCP Server 框架选型（`@modelcontextprotocol/sdk` + TypeScript + stdio）
- [x] 实现 6 个核心工具 + Phase 2-5 完整 LLM 编排
- [x] 文档 + 示例调用 + site/agents.html 同步

#### P3-B：报告订阅 / 品牌演化追踪

**目标**：用户订阅某品牌，当品牌有重大新闻时自动触发 EVOLUTION 模式重新审计  
**设计文档**：`docs/12-evolution-tracking.md`（2026-06-30）  
**场景**：品牌发布新产品、高管变动、负面事件后自动更新报告  
**新增 MCP 工具**：`subscribe_brand` · `trigger_evolution` · `list_subscriptions` · `get_delta_report` · `unsubscribe_brand`

- [x] 设计触发机制（keyword / news RSS / cron / webhook）
- [x] P3-B-1：`subscribe_brand` + `trigger_evolution` + `list_subscriptions` + `unsubscribe_brand` + CronScheduler（2026-06-30，commit 61fb801，34 tests）
- [x] P3-B-2：delta 报告生成（`get_delta_report` + `scores.json` 结构化打分 + per-lens 均值差 + LLM 变化叙述，2026-07-02，47 tests）
- [x] P3-B-5（成本优化）：EVOLUTION 增量维度重跑 —— 变化探针只重跑变了的维度，成本 ~$3 → ~$0.3-0.6/次（省 80%+），2026-07-02，52 tests
- [x] P3-B-4a：notify 推送出站（webhook POST + Resend email + mcp-push），审计完成自动算 delta 并推送，best-effort 容错，2026-07-02，60 tests
- [x] P3-B-4b：webhook **接收端**（`mba-webhook-receiver`）—— `POST /webhooks/trigger` 外部事件转 EVOLUTION 重审，可选 Bearer 鉴权，2026-07-05，85 tests
- [ ] P3-B-3：keyword / news 触发器（**阻断**：Wuying Pro GetLink；可改 RSS/新闻 API 绕过）

---

## 进度日志

> **记录格式**：每次完成一项开发动作后，在此追加一条记录，包括日期、完成事项、commit hash、备注。

---

### 2026-06-25

**事项**：整理开发路线图，创建本文档  
**完成内容**：
- 分析全量代码库（43 评委、10 面板、5阶段流水线、完整文档集）
- 整理当前状态快照（v0.2.36）
- 制定 P0-P3 四级优先级路线图
- 识别关键阻断项（Wuying 免费版限制）

**关键发现**：
- 最高杠杆单点：升级 Wuying 套餐，可解锁 25 位评委深化
- 不依赖 Wuying 的立即可执行项：vc-en 英文评委深化 + `--dry-run` 实现
- 测试覆盖是当前最大技术债（无集成测试）

**commit**：`4d41917` · branch `claude/sharp-turing-496l8b`

---

### 2026-06-25（续）

**事项**：实现 `--dry-run` 标志（v0.2.36 → v0.2.37）  
**完成内容**：
- `metric-brand-auditor/SKILL.md`：
  - 版本号 bump 0.2.36 → 0.2.37
  - 参数列表新增 `--dry-run` 说明
  - Phase 0 新增 §0.5 dry-run exit，原 §0.5 顺延为 §0.6
  - 输出格式：品牌、模式、面板评委状态（✓/✗）、Wuying leg、维度列表、输出路径、生效 flags
- `docs/05-usage.md`：参数表增行，新增 §3.6 dry-run 完整示例
- `site/roadmap.html`：P0-B 三个子任务标为完成，版本快照更新为 v0.2.37，追加进度日志

**同步发现**：WebFetch paulgraham.com 返回 HTTP 403，沙箱阻断仍有效。P0-A（vc-en 评委深化）暂挂起。

**commit**：待推送（与 P2-A 合并提交）

---

### 2026-06-25（续二）

**事项**：集成测试 Workflow 建立（P2-A）  
**完成内容**：
- `scripts/validate_report.py`：报告 Markdown 结构校验器（7 条规则）
- `scripts/validate_html_report.py`：HTML 报告组件校验器（7 条规则）
- `tests/fixtures/mock_report.md` + `mock_report.html`：最小合法 mock fixture
- `.github/workflows/report-validation.yml`：CI workflow（PR + push to main）
- 本地测试：2 份 HTML ✓、1 份 Markdown ✓、2 份 mock fixture ✓

**commit**：待推送

---

### 2026-06-25（续三）

**事项**：实现 `--panel-merge` 跨面板对比（P1-B，v0.2.37 → v0.2.38）  
**完成内容**：
- `metric-brand-auditor/SKILL.md` v0.2.38：
  - 参数列表新增 `--panel-merge` 描述
  - Phase 0.3：FRESH 品牌（无先前 report.md）触发 `--panel-merge` 时 ABORT
  - Phase 0.4：`--panel-merge` bypass clause（跳过面板相同检测）；STOP 条件追加 "AND `--panel-merge` was NOT passed"
  - Phase 5M（新增完整章节）：
    - 5M.1 读取旧版 score.json / report.md 提取分值
    - 5M.2 用新面板正常跑 N-Judge（复用 Phase 4）
    - 5M.3 生成 Panel Comparison 报告节（side-by-side delta 表 + 共识/分歧/fingerprint + cross-panel verdict）
    - 5M.4 HTML 模板扩展（面板选择器 toggle + 5 镜头 delta 热力图列）
- `docs/05-usage.md`：
  - 参数表新增 `--panel-merge` 行
  - §3.7 新增"跨面板对比审计"两步示例（Step 1 首次审计 + Step 2 panel-merge）

**commit**：待推送

---

### 2026-06-25（续四）

**事项**：P2-B 报告扩充基础设施（8 品牌建档）  
**完成内容**：
- 选定 8 个品牌，覆盖全部 8 个待补面板：
  - 奇安信（security-cn-global）、Kimi（ai-app-cn）、好未来（edu-cn）、Anthropic（vc-en）
  - 元气森林（consumer-cn）、美团（vc-cn）、DJI（cross-border）、爱马仕（luxury-en）
- `published/reports/{slug}/panel.yaml` × 8（status: pending，锁定面板 + mba_version: 0.2.38）
- `site/reports-meta.yaml`：追加 8 条 pending 条目（含 run_cmd、panel、ticker 等字段）

**待完成**：在 Claude Code 会话中逐一运行真实审计 → 生成 report.md/html → 更新 published-reports.txt → 移除 pending status

**commit**：待推送

---

---

### 2026-06-30

**事项**：P3-A MCP Server v0.1.0 全量完成 + P3-B 设计文档  
**完成内容**：
- PR-01~03：pnpm workspace 架构、TypeScript 8 阶段状态机、FilesystemStore 原子写入、6 工具框架
- PR-04：Phase 2-5 LLM 完整编排（llm/client.ts 重试逻辑、llm/prompts.ts 全套 prompt、四个 orchestrator、runner.ts 非阻塞链式执行 + cost guard）；22 tests passing，TypeScript zero errors
- PR-05 文件：scripts/add-shebang.js，README.md 状态更新，site/api/install.json 新增 MCP server 条目
- P3-B 设计文档 docs/12-evolution-tracking.md：4 种触发器（keyword/news/cron/webhook）、增量维度重跑方案、5 个新 MCP 工具设计、存储结构扩展
- roadmap.html + agents.html + docs/11-roadmap.md 同步更新

**commit**：069c5c4（PR-04）· c18c465（文档）· 待推送（PR-05 + P3-B）

---

### 2026-07-02

**事项**：P3-B-1 订阅+触发落地 + P3-B-2 delta 报告  
**完成内容**：
- **P3-B-1**（commit 61fb801）：4 个新 MCP 工具（`subscribe_brand` / `trigger_evolution` / `list_subscriptions` / `unsubscribe_brand`）+ `SubscriptionStore` JSON 持久化 + `CronScheduler`（setInterval 轮询到期订阅，fire-and-forget 触发演化）；cadence guard（min_interval_days + max_per_month）；34 tests
- **P3-B-2**（本次）：`get_delta_report` 工具 —— 新增 `src/orchestrator/scores.ts`（从 judge review 解析结构化打分，英文 lens 名作锚点，中英文都能解析）；Phase 4 生成时持久化 `scores.json`；delta 计算 per-lens 均值差 + LLM 变化叙述；旧 audit 无 scores.json 时从 reviews/ 重建；`FilesystemStore.listFiles` 辅助方法；47 tests passing
- MCP Server 现共 **11 个工具**（6 核心 + 4 订阅 + 1 delta）
- 同步修正 docs/11-roadmap.md 中 P2-B / P3-B-1 的 stale 勾选状态

**commit**：a185b9c（P3-B-2）

---

### 2026-07-02（续）

**事项**：EVOLUTION 增量维度重跑（成本优化）  
**完成内容**：
- `src/orchestrator/phase-2-evolution.ts`（`runPhase2Evolution`）：演化审计时先用廉价"变化探针"（256 tokens）逐维判断 CHANGED/UNCHANGED，只重跑变了的维度，UNCHANGED 直接复用上次 `_raw/dimension_N_slug.md`
- `llm/prompts.ts`：`changeProbeSystemPrompt` / `changeProbeUserPrompt`；触发事件通过 `options.evolution_context` 喂给探针
- `runner.ts`：`mode === 'evolution' && previous_audit_id` 时自动切到增量路径，否则全量研究
- `trigger-evolution.ts`：把 `event_type + event_summary + source_url` 组装成 `evolution_context` 写入 audit options
- 保守回退：探针无法解析 → 默认 CHANGED；无基线维度文件 → 全量研究
- 透明度：写 `_raw/evolution_probes.md` 逐维记录
- **成本**：~$3/次 → ~$0.3-0.6/次（省 80%+）
- 测试：52 tests passing（新增 5），TypeScript zero errors
- docs/12-evolution-tracking.md §5 标记已实现

**commit**：4931e1e

---

### 2026-07-02（续二）

**事项**：P3-B-4a notify 推送出站  
**完成内容**：
- `src/notify/webhook.ts`：`sendWebhook` —— fetch POST JSON，10s 超时，网络错误捕获进结果不抛出
- `src/notify/email.ts`：`sendEmail` —— Resend API（需 `MBA_RESEND_API_KEY` + `MBA_NOTIFY_FROM`），未配置静默返回
- `src/notify/dispatch.ts`：`dispatchNotifications` —— 逐个 target 独立投递（webhook/email/mcp-push），单个失败不影响其他
- `runner.ts`：新增可选 `onComplete(finalState)` 钩子，'done' 后 best-effort 调用（try/catch 包裹）
- `trigger-evolution.ts`：构造 onComplete —— 有基线时算 delta（getDeltaReport）→ dispatchNotifications；无基线时推送简单摘要
- README + docs/12 §7.5 补通知说明和环境变量
- 测试：60 tests passing（新增 8，mock global fetch + stubEnv），TypeScript zero errors

**闭环打通**：品牌变化 → trigger_evolution → 增量重审 → 算 delta → webhook/email 主动通知

**commit**：9fef872

---

### 2026-07-02（续三）

**事项**：MCP 端到端集成测试  
**完成内容**：
- `tests/integration/server.e2e.test.ts`：用真实 MCP `Client` + `InMemoryTransport` 驱动 `createServer()`，覆盖前 60 个单元测试没触及的协议层（工具注册、zod schema 接线、请求/响应）
- 7 个 e2e 用例：11 工具全部注册校验；propose_audit 产出 PRD；list_audits + get_status 往返；confirm_audit 无 key → MISSING_API_KEY；subscribe → list → unsubscribe 往返；add_judge validate_only；未知 audit → AUDIT_NOT_FOUND
- 测试用临时 store dir + stubEnv（无 API key，不起 scheduler、不发真实 LLM 调用），确定性、无网络
- 测试：67 tests passing（新增 7），TypeScript zero errors

**commit**：33ba200

---

### 2026-07-02（续四）

**事项**：npm 发布准备（拿到 token 即可一键 publish）  
**完成内容**：
- 验证 `pnpm build` 产出干净：全量 `.js` + `.d.ts`，`dist/index.js` 带 shebang + 可执行位，`node dist/index.js` 能起 stdio server
- `npm pack --dry-run`：34.5 kB / 65 文件，仅含 dist/ + README + LICENSE + package.json（`files` 白名单生效，无源码/测试泄漏）
- 新增 `LICENSE`（MIT，© 2026 zhanglunet，随包发布）
- package.json 补发布质量字段：`homepage` / `repository`（含 directory）/ `bugs` / `publishConfig.access=public`
- 新增 `prepublishOnly` 守卫：`typecheck && test && build`（67 tests 全绿才允许 publish，杜绝发布坏包）
- README 加 Publishing 小节（登录 + publish + 版本 bump 步骤）
- **唯一剩余阻断**：npm token + 出站网络（此环境无）；本地一切就绪

**commit**：待推送

### 2026-07-06

**事项**：npm 首发 + 面板/演化/CI 增强 + `resume_audit`（v0.4.0 → v0.4.1）
**完成内容**：
- **发布 `mba-mcp-server@0.1.0` 到 npm**（`npx -y mba-mcp-server@latest` 即可用，无需 clone）。踩过三关：`ENEEDAUTH`（补 `NPM_TOKEN`）→ `E403`（Classic 令牌换 Granular Access Token 以绕过账号 2FA）→ Node 20 弃用告警（CI 升 Node 22）
- **`list_panels` + `get_brand_trend`**（11 → 13 工具）：面板发现 + 品牌跨 N 次审计评分轨迹
- **`resume_audit`**（13 → 14 工具）：续跑卡住/失败的审计，复用 audit_id 与配置，已完成阶段从磁盘复用产物（`_raw/dimension_*.md` / `synthesis.md` / `reviews/*.md`）、只重跑未完成阶段；接上了此前 dormant 的 `interrupted`/resume 脚手架
- **mcp-ci.yml**：MCP 包的 typecheck + 测试 + build 现在每个 PR 都跑（此前只有 Python 报告校验器在跑），外加 generated 数据同步校验
- **文档/网站**：README（npm 徽章 + `npx` 一行安装）、CHANGELOG、site 首页、v0.4.1 GitHub Release 全部同步
- 测试：99 → **113 tests**（resume 新增 14）

**关键判断**：代码侧无阻断建设已收尾。剩余高杠杆项全部需外部资源解锁（Wuying Pro → 中文评委 + 自主新闻触发器；出站网络 → vc-en 英文评委，实测 paulgraham/Google News RSS 仍 403）

**commit**：见 PR #41（list_panels/get_brand_trend）· #42（Node 22）· #43（v0.4.1 docs）· 本次（resume_audit）

### 2026-07-07

**事项**：实时联网研究 + 断点续跑，打 v0.4.2（v0.4.1 → v0.4.2）
**完成内容**：
- **`resume_audit`**（PR #44，13 → 14 工具）：续跑卡住/失败的审计，复用 audit_id 与配置，已完成阶段从磁盘复用产物、只重跑未完成阶段
- **实时联网研究**（PR #45）：`MBA_WEB_SEARCH=1` 让 Phase 2 用 Anthropic **服务端 web_search** 工具带真实来源 URL 研究，写入 `_raw/`；搜索在 Anthropic 侧发生、**不需要沙箱出网**，锁死出站策略的环境也能用。仅研究阶段联网。`MBA_WEB_SEARCH_MAX_USES` 控成本
- 测试：113 → **121 tests**
- v0.4.2 GitHub Release + README/site/CHANGELOG 同步

**关键结论（出站网络）**：实测沙箱出站是**组织级 egress allowlist**（网关 403，只放包管理源），代理 README 明令禁止绕行。给 MCP server 真实数据的最优解是 **web_search**（零 egress 改动、最安全），已落地。仅剩 **Wuying leg**（中文登录墙源，需 Pro）和**全量出站**（几乎无非它不可的场景）两条，均需你解锁资源

**commit**：PR #44（resume_audit）· #45（web_search）

### 2026-07-12

**事项**：Brand Watch(品牌舆情监控)M1 启动 —— PRD 落地为 W 系列开发计划,W1/W2 完成、W3 首批
**完成内容**：
- **docs/15**(PR #95):需求分析 PRD —— 9 监控维度(招投标 W3 深潜:信号分类学 + 数据源 + 落地示例)、事件模型与 P0-P3 分级、舆情→EVOLUTION 触发规则、13 品牌适用性矩阵、反捏造边界(舆情只建议不改分)
- **W1 数据层 + 硬 gate**：`watch/matrix.yaml`(适用性矩阵单一真源,机器强制与发布白名单对齐)· `watch/<slug>/events.yaml` schema(quote_type 增补 + URL 自证日期原则)· `scripts/watch-tools/validate_watch.py`(静态硬 gate + 12 组 --selftest)· 接入 panel-validation CI
- **W2 源验证**：PRD 数据源清单逐源真 curl —— 政采网/公共资源/联通/巨潮/SAM.gov ✅;**b2b.10086.cn 需 OPENSSL_CONF 遗留 TLS 重协商 workaround**(已留档);电信阳光采购/国网 ECP 疑似 JS 壳待深挖
- **W3 试点首批**：亚信 6 / 奇安信 3 / 垣信 6 共 15 条可溯源事件。亮点:亚信 **P0 =被中国移动子公司禁入采购三年**(PRD 黑名单分类学首个真实实例);垣信 2026 组网 238 颗 = v1 审计未覆盖的新信号(watch「两版之间的眼睛」价值实证)。M1 验收(≥10/品牌)缺口已诚实记账
- 踩坑:YAML 1.1 把 on/off 解析成布尔 —— 校验器归一化,坑记 docs/16 §2.4
**关键判断**：先用招投标等硬信号跑通「发现→溯源→入库→校验」闭环,软信号(W2 社交)后置;下一步 W4(--watch 进 SKILL + EVOLUTION 消费事件流,注意坑 #2 连带再生成)
**commit**：本次 PR(docs/16 是过程文档,做一项记一项)

<!-- 在此追加后续进度记录，格式参考上方 -->
