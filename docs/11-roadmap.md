# MBA 开发路线图与进度日志

> **文档定位**：本文件同时承担两个职责——  
> 1. **路线图**：记录下一步开发计划，优先级和理由  
> 2. **进度日志**：每次开发动作在此追加记录，形成可查历史

---

## 当前状态快照（2026-07-16）

| 维度 | 状态 | 备注 |
|------|------|------|
| 版本 | **v0.5.0** | 关系宇宙:创始人维度 + 创始人晚餐(品牌×品牌合作推演)+ 产业维度 + 七家科技巨头入库(22 品牌,含首次真实 --panel-drop)+ 全站巡检;v0.4.5 舆情驾驶舱;v0.4.4 知识星图 + 飞书群推送;v0.4.3 Brand Watch 全链路(W1-W7) |
| 5阶段流水线 | ✅ 生产就绪 | Phase 0-5 + Phase 5M（panel-merge）稳定 |
| 评委面板数量 | ✅ 10/10 全部可运行 | default / auto / security-cn-global / ai-app-cn / edu-cn / vc-en / vc-cn / consumer-cn / cross-border / luxury-en |
| 评委全档进度 | ✅ **42/43 全档** | 1 人仍在 seed（`zhanglan` 已严格核算诚实留 seed）；权威名单见 `docs/10 §6`（本表曾长期滞后，勿再手抄 slug） |
| mbabrand.com | ✅ 上线 | Cloudflare Pages |
| 公开报告 | ✅ **23 品牌** | 15 品牌有 EVOLUTION 多版本(22 份历史快照);**NVIDIA 8.88 现居审计史最高**;本轮新增七家科技巨头(Apple/Google/微软/亚马逊/华为/NVIDIA/DeepSeek)+ Tesla(2026-07-16),含 **3 个真实 `--panel-drop`**(微软/华为/特斯拉) |
| CI/CD | ✅ 全绿 | 面板校验 + 报告结构校验（硬/建议分级）+ 站点构建 |
| 集成测试 | ✅ 已建立 | report-validation.yml + MCP e2e（真实 MCP 协议层） |
| --dry-run / --panel-merge | ✅ 已实现 | Phase 0 §0.5 / Phase 5M |
| MCP Server 形态 | ✅ 已发布 npm | packages/mcp-server/ · **16 工具**(含舆情 `get_watch_events`/`record_watch_event`)· **10 面板 / 43 评委** · webhook 接收端 · `resume_audit` 续跑 · **实时联网研究**(`MBA_WEB_SEARCH`) · 224 tests · `npx -y mba-mcp-server@latest` |
| 演化追踪 | ✅ 完成 | 订阅 + cron + trigger_evolution + delta 报告 + 增量重跑 + webhook/email 通知 |
| 知识星图 | ✅ 上线 | 全维度星图 `/starmap.html`(82 实体/184 边)+ 每品牌私有星图 `/starmap/<slug>.html`(15 张,评分矩阵+舆情+版本) |
| 飞书群推送 | ✅ 上线 | 合并到 main 涉及 `watch/**`/`reports-meta.yaml` → 自动推 P0/P1 事件/建议重审/评分变动 到飞书群(`notify-feishu.yml`,`docs/19`) |

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

### 站点与运维增量(2026-07-12~14)

- **G-daily 每日工作日报 + cron 自动落库 ✅ 已完成(2026-07-14,PR #132)** —— `scripts/new_daily.py`:每天盘点「前一天合并到 main 的提交 / PR」,数据源是 git(可验证、不靠人工回忆,反捏造)。`new [date]`(默认昨天,按 Asia/Shanghai 归日,CI 在 UTC 跑也不错位)从提交按 conventional-commit 类型分组生成 `docs/daily/<date>.md` + PR 链接,无提交则跳过、不落空文件;`week [date]` 把某周日报合成周报草稿喂给 `new_weekly.py`;`index` 重建索引。兼容本仓库自用类型(design/research/publish→发布)。**自动化**:`.github/workflows/daily-report.yml` cron 01:00 UTC(=09:00 北京)盘点前一天、直接 commit 到 main(`[skip ci]`,append-only 文档),`workflow_dispatch` 手动可指定日期,无变化不提交。seed 三天(07-12/13/14)。**注意**:该 PR 因**新增 workflow 文件**被 GitHub 安全策略 withhold 了 PR/push 的 Actions(修改已有 workflow 不受影响),故以本地验证(`py_compile` / yaml 可解析 / `check_consistency` / 3 天日报 + 周报合成)替代;新 cron 首次运行需在 Actions 页点一次「Approve and run」。
- **G-cockpit Brand Watch → 舆情驾驶舱 ✅ 已完成(2026-07-14,v0.4.5,PR #128/#129/#130)** —— 按 `docs/20`(舆情驾驶舱需求 × MBA 能力映射,源自某企业「舆情驾驶舱」需求脱敏归纳)把 Brand Watch 顺势扩展覆盖驾驶舱需求,三阶段:**① 事件 schema 补 4 可选字段**(`related_persons`/`source_type`/`suggested_action`/`alert_tier`,对齐 7 标签;`validate_watch` 12→17 断言、MCP `store.ts` 镜像 +4 tests);**② 飞书 L1/L2/L3 分层预警**(P0/建议重审→L3、P1→L2、评分变动→L1;各层可配独立 webhook 分流,同 webhook 合并成一张卡,`alert_tier` 可覆写);**③ 每品牌舆情驾驶舱看板** `scripts/build_watch_cockpit.py` → `/watch/<slug>/cockpit.html`(管理层摘要 / 发布时间分布 / 维度×方向归因 / 来源类型 / 投资社区专区 / 可筛选全量表,零依赖静态 SVG,15 张 headless 0 JS 错误;入口:时间线页 + 首页卡片)。**守界不做**(docs/20 ⚠️ 共同缺口):自动化反爬 / 私域内网 / 小时级实时 / 处置工单——属外部数据源或 CRM 域。端到端贯通:asiainfo 驾驶舱「来源=财经 2 / 关联人物 田溯宁」正是 Phase 1 标注的事件。
- **G-site1 品牌监控全维度知识星图 ✅ 已完成(2026-07-13,PR #121)** —— `mbabrand.com/starmap.html`:参考 zhanglunet/shanghai 的知识星图,用**零依赖纯 SVG 星座图**把品牌监控体系可视化 —— **5 镜头 × 9 监控维度 × 15 品牌 × 10 面板 × 43 评委,82 实体 / 184 条真实关系边**(维度→镜头、品牌→面板、品牌→监控维度 core/weak、面板→评委),关系全部来自 `watch/matrix.yaml` + `panels/*.yaml` + `reports-meta.yaml`(`scripts/build_starmap.py` 生成)。可搜索/类型筛选/点击聚焦/缩放平移/详情面板。首页 banner + 全站导航「知识星图」入口。
- **G-site2 每品牌私有知识星图 ✅ 已完成(2026-07-13,PR #122)** —— `mbabrand.com/starmap/<slug>.html`(15 张,`scripts/build_brand_starmap.py`,`site/starmap/` gitignore、部署时随 watch 页重生成):以单品牌为圆心的 ego 图,画出全局图没有的三样自有真实数据 —— **内环 5 镜头(按评委均分)+ 中环评委(细线=每位评委对每个镜头的逐格打分,report.md 评分矩阵 5×N 条真实边)+ 外环舆情事件流(P0-P3 定大小、正/负向定颜色,连到其 lens_map 影响的镜头)**,版本演化进详情面板。矩阵解析兼容中英文标题 + delta 单元格(`5→6`取当前值)。下钻入口:全局星图点品牌节点 + 首页每张卡片「品牌私有星图 →」。
- **G-ops1 品牌监控/舆情信号 → 飞书群推送 ✅ 已完成(2026-07-13,PR #123/#124)** —— 合并 PR 到 main 时,若改动 `watch/**` 或 `site/reports-meta.yaml`,GitHub Action(`.github/workflows/notify-feishu.yml`)diff 出变化、拼一张飞书交互卡片 POST 到自定义机器人 webhook 进群。**推送门槛与首页卡片「建议重审」同口径**(避免刷屏):① 新增 **P0/P1** 事件(P2/P3 不单独刷群)② 品牌**新命中**触发规则(base 未命中、head 命中;复用 `evaluate_triggers.py` 单一真源)③ **评分变动**(score_normalized,含首审)。`scripts/notify_feishu.py`:`base..head` diff + 三类检测 + 卡片(含可选 HMAC-SHA256 签名)+ `--dry-run` 预览 + `--test` 连通性卡片(`workflow_dispatch` 手动触发)。内容**全部取自仓库文件**(事件标题/引用/URL、真实评分),反捏造。secrets:`FEISHU_WEBHOOK`(必需)/ `FEISHU_SIGN_SECRET`(可选),未配则跳过。**已端到端验证**:手动 Run workflow → 群里收到测试卡片。配置与格式见 `docs/19`。

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
- [x] **`cucinelli`** ✅ 一手强:investor.brunellocucinelli.com「人文资本主义与人的可持续性」报告 PDF(~3.9 万英文词)+ 官网哲学页 + 主席信。**可做真·full**。
- [x] `arnault` ⚠️ 边际:LVMH 致股东信(lvmh.com/static/letter-to-shareholders-*,单篇短)+ 股东会 transcript;需多篇凑够 30 条一手,勉强。
- [x] `awintour` / `tomford` / `burton` ⛔ 当时预判难过 80%——**实际 2026-07-10 三人均经 route-A 补足一手并升 full**(#66-68),luxury-en 5/5 收官(docs/14)。上两行也已完成。

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

- [x] ~~升级 Wuying 套餐~~ **未升级——路线被 route-A(curl 出口代理直取一手)取代**
- [x] ~~跑 smoke test~~ 免费档 GetLink 400 留档(docs/wuying-usage);Wuying 降级为可选增强
- [x] 按顺序深化 25 人 → **2026-07-10 已全部完成(route-A),42/43 全档,仅 zhanglan 诚实留 seed**(docs/14)

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

### 2026-07-12 · 全仓盘点 → G 系列 backlog(第四轮工程清账)

四路并行盘点(MCP/CI · scripts+site · docs · 数据层)结论:代码本体干净(全仓 0 条真 TODO、SKILL 引用零断链、10 面板零浪费、已采事件 100% 消费);欠账集中在发布状态 / 门面数字 / 审计留痕 / 监控覆盖。

| # | 工作项 | 内容 | 状态 |
|---|---|---|---|
| **G1** | 发布与门面清账 | npm bump 0.1.0→**0.2.0** 并发布(16 工具上 npm);根 README / docs/README / docs/11 快照 / site(docs·roadmap·handoff)全部落后数字修复;README 静态报告表改指针(无门禁的静态表必漂);CHANGELOG v0.4.3 阈值文字校正;`evaluate_triggers --selftest` 进 CI;check_consistency 增 panorama 评委数门禁;归档 migrate_legacy_report_panels.py;docs/05 补 `--watch` | ✅ 2026-07-12(npm 0.2.0 发布待 PR 合并后触发 workflow)|
| **G2** | 审计留痕补齐 | asiainfo/spacex/yuanxin 补 `reviews/<judge>.md` 逐评委文件(v1+v2 整合,诚实标注"事后整合、AI 模拟")+ `_raw/` 补 watch 消费记录与缺口说明(**不伪造从未存在的原始调研**) | ✅ 2026-07-12:三品牌 19 份留痕,引语 100% 逐字核验,缺口如实标注 |
| **G3** | watch 冷启动 ×8 | lenovo/chengshi-auto/anthropic/dji/kimichat/tal-education/genki-forest/hermes 各采首批可溯源事件 → W6 覆盖 5/13→13/13 | ✅ 2026-07-12:8 品牌 30 条首批事件,覆盖 13/13,W6 验收达标;anthropic/dji 各一条 P0 |
| **G4** | 遗留报告重审 | lenovo(50 分制,2026-05-10)→ v2、chengshi-auto(50 分制 0.2.20,v6)→ v7,升 0.4.3 现行分制,消费 G3 新事件 | ✅ 2026-07-12:lenovo v2 119/250(4.76)· chengshi v7 151/250(6.04);PDF 重生成 |

**决策项(待产品拍板,不在 G 系列内)**:① 触发建议精确率验收线 0.3 vs 0.15(docs/16 §8.3);② `keyword`/`news` 触发器去留(schema 收但调度器不执行的静默位——砍 enum 或接 RSS,即 P3-B-3);③ PDF 管线复活 or 声明按需(11 份报告无 PDF);④ webhook receiver 是否补 `POST /webhooks/watch-event` 录信号入口;⑤ zhanglan 留 seed 维持(等一手语料)。

### 2026-07-16

**事项**:创始人维度(Founder Dimension)v1 上线 —— 给 MBA 增加一个「品牌创始人」维度
**完成内容**:
- **数据层** `founders/<slug>.yaml`:创始人履历(每条里程碑带 provenance)+ 从人物角度看创始人↔品牌关系(按 5 镜头,标注为分析)。首批 4 位「创始人即评委」:spacex·musk / meituan·王慧文(联合创始人,主创始人王兴无 perspective 如实标注)/ tal-education·张邦鑫 / kimichat·杨植麟,复用其 perspective `references/research/06-timeline.md` 一手调研
- **独立创始人页** `scripts/build_founder_pages.py` → `site/founders/<slug>.html`(house style·零依赖) + 索引页;接入 `site/build.sh`(gitignore)。从首页卡片 / 品牌星图 / 舆情驾驶舱 / watch 时间线页加「创始人 →」入口(仅有数据的品牌)
- **硬 gate** `scripts/founder-tools/validate_founders.py`(schema + brand 对齐白名单 + 履历带 provenance + 镜头合法 + perspective 真实 + 10 组 `--selftest`)接入 `panel-validation.yml`;`check_consistency.py` 增第 8 格「创始人维度」
- **反捏造**:履历只用真实 provenance、关系文字标注为分析不冒充原话、逐字引语须命中评委 research 语料、cutoff 外(如王慧文 2023 健康退隐 / 张邦鑫 2021 双减后 / 杨植麟 2024 之后)诚实留白;**只作调研输入,不改评分**。Playwright 自检 4 页 0 JS 错误
- **文档**:`docs/21-founder-dimension.md`(schema/SOP/反捏造约定/开发计划存档)+ docs 索引 + roadmap 网页存档
**明确不做**:首批只 4 位;其余 11 品牌留后续(需 `curl` 取一手履历再落库);不改已发布报告 HTML;不做创始人自动传记生成
**commit**:本次 PR

### 2026-07-16(续)

**事项**:创始人晚餐(品牌×品牌合作推演)v1 上线 —— 把两位创始人放一桌,假想推演合作
**完成内容**:
- **数据层** `collabs/<a>--<b>.yaml`:两位创始人按 5 镜头逐"道菜"聊合作(每道两 turn + 合作点)+ 假想合作备忘 + **诚实盒 tensions** + sources;首场 = **田溯宁(亚信)× 唐杰(智谱)**「骨干网遇见基座模型:两代科技基础设施建设者」。同批补 `founders/asiainfo.yaml`(田溯宁,curl 一手:前瞻网/21世纪/搜狐诺亚精选)
- **生成器** `build_collab_dinners.py` → `site/collabs/<a>--<b>.html` + **组合器索引**(选两位创始人→有则开饭/无则待推演);复用 founder house-style;**disclaimer 横幅硬编码**。接入 build.sh、gitignore
- **硬 gate** `validate_collabs.py`(brands 恰 2 且都有创始人档案 · 文件名规范序 · lens 合法 · who∈brands · takeaways/**tensions 非空** · 12 组 selftest)接入 `panel-validation.yml`;`check_consistency` 增第 9 格
- **反捏造**:发言为 AI 演绎公开立场(与 MBA「人物评委」同机制)、paraphrase 不冒充逐字原话、锁年留白、合作点标「假想」、**诚实盒强制列合作张力**、不谎称真实合作;只作调研启发不改评分。Playwright 自检晚餐页(5 道菜/10 气泡)+ 组合器 0 JS 错误
- **入口**:创始人页「🍽️ 与 X 共进晚餐」、首页 nav/intro、创始人索引;**文档** docs/22 + docs 索引 + CLAUDE.md + roadmap 存档
**明确不做**:首批只样板场次(田溯宁×唐杰);不做 LLM-at-build 生成对话(全人手精编);不谎称真实合作
**commit**:本次 PR

### 2026-07-16(续二)

**事项**:两个新品牌完整入库(DeepSeek + NVIDIA)+ 产业维度
**完成内容**:
- **DeepSeek 入库**(PR #144):ai-app-cn 5 评委完整审计 200/250·8.00 + 创始人梁文锋(curl 一手);Origin 8.6 领跑、Leverage 7.0 最弱(芯片禁运+开源护城河悖论);分歧沿"技术理想主义值多少钱"断层线。修 index.json 报告计数 + 采纳 Codex 建议修首页驾驶舱死链
- **NVIDIA 入库**(PR #145):vc-en 5 评委完整审计 **222/250·8.88(MBA 最高)** + 创始人黄仁勋(复用 jensenhuang perspective);Leverage 9.6(CUDA 护城河)、Category 9.4(发明 GPU 品类)领跑;唯一分歧 Signal 8.2(蒂尔"垄断能否穿越浪潮" vs 安德森"平台非周期")。黄仁勋是评委但不在 vc-en panel,无自冲突
- **产业维度**(本 PR):17 品牌分 6 大类(AI/消费/硬科技·航天/智能制造·硬件/企业服务·安全/教育);`reports-meta.yaml` 的 `industry` 字段单一真源;首页每卡产业标签 + 产业筛选条(计数,复用排序条交互);`check_consistency` 加第 10 格。docs/23 存档。反捏造:审计评分标 AI 模拟、事实带来源/需核验;产业仅作分组标签不改分
**MBA 现覆盖**:17 品牌 + 17 位创始人 + 6 产业
**commit**:PR #144 · #145 · #146

### 2026-07-16(续三)

**事项**:创始人晚餐「亮点」嵌入首页
**触发**:用户「`collabs/` 创始人晚餐这个对话有亮点,可以嵌入到首页里来」
**完成内容**:
- 首页(`site/index.html`,品牌网格后、接入区前)新增**「创始人晚餐 · 亮点」块**:精选那场晚餐的一段亮点往返对话(两个气泡)+ 合作点 + AI-演绎 disclaimer + 「看完整晚餐 / 组合更多创始人」双入口。首场亮点 = 田溯宁×唐杰的 leverage 镜头(「你的渠道,我的模型」)
- **单一真源仍是 `collabs/*.yaml`**:`build_collab_dinners.py` 生成 `<!-- DINNER:START/END -->` 块(机制同 `build_home_cards` 的 REPORTS 块),`--check-home` 守漂移;`collabs/asiainfo--zhipu.yaml` 加可选 `featured`/`home_highlight`,`validate_collabs.py` 认这两字段(featured=bool、home_highlight 须为本场存在的 lens)+ selftest 16 组
- `check_consistency` 加**第 11 格「晚餐亮点对齐」**;docs/22 补首页块说明 + 开发计划存档
- 反捏造:say 为 AI 演绎公开立场(非逐字原话)、disclaimer 在位、只作调研启发不改评分;QA:首页 0 JS 错误、产业筛选/排序 JS 与亮点块共存不冲突
**MBA 现覆盖**:17 品牌 + 17 位创始人 + 6 产业 + 1 场创始人晚餐(首页亮点)
**commit**:本 PR

### 2026-07-16(续四)

**事项**:第二场创始人晚餐 —— 梁文锋 × 黄仁勋「芯片与模型」+ 首页亮点轮换到此场
**触发**:用户「黄仁勋 × 梁文锋 那场晚餐,做上」
**完成内容**:
- `collabs/deepseek--nvidia.yaml`:5 镜头假想对谈。核心张力 = **芯片与模型**——梁文锋用开源 + 高效重定义竞争(V2「AI 界拼多多」、R1 开源权重),黄仁勋以 **Jevons 之辩**回应(模型越省、部署越广,推理总算力反而爆炸,高效放大而非缩小市场)。leverage 镜头点破「你的护城河(先进芯片)恰是我的结构性约束」
- **诚实盒(反炒作)**给足:地缘/出口管制使实质合作现实中高度敏感、DeepSeek 高效曾被解读为利空英伟达(2025-01 大跌)= 结构性利益冲突、身份南辕北辙、数字待核验——如实说明二者更像"叙事对手"而非天然盟友
- **首页亮点轮换**:新场设 `featured: true`、asiainfo--zhipu 设 `featured: false`,首页「亮点」块自动切到 marquee 的 `deepseek--nvidia` 的 category 镜头
- 反捏造:梁文锋非评委,发言为 curl 一手(京报网/21 世纪经济报道/新浪财经/暗涌 Waves)的 AI 演绎转述,不冒充逐字原话;黄仁勋用其评委 jensenhuang 表达 DNA;引号内「AI 界拼多多」为公开报道外部标签
- QA:`validate_collabs`(2 场合规)+ `check_consistency`(11 格)+ 首页 0 JS 错误 + 晚餐页 5 道菜/10 气泡/disclaimer/诚实盒俱在
**MBA 现覆盖**:17 品牌 + 17 位创始人 + 6 产业 + **2 场创始人晚餐**(首页亮点 = 芯片与模型)
**commit**:本 PR

### 2026-07-16(续五)

**事项**:新增受监控品牌 Apple + 创始人史蒂夫·乔布斯(完整审计入库)
**触发**:用户「增加 apple、google 两家公司和其创始人」(先 Apple 跑通再 Google)
**完成内容**:
- **Apple 完整审计**(vc-en 5 评委):安德森 42 · 格雷厄姆 45 · 蒂尔 45 · 纳瓦尔 46 · 霍夫曼 43 = **221/250 · 8.84(MBA 第二高**,仅次 NVIDIA 8.88)。**Identity 9.6 拿下 MBA 迄今身份维度最高分**(极简设计/Think Different/Jony Ive 美学/乔布斯"美是产品本质");与 NVIDIA 峰值在 Leverage 不同,Apple 峰值在 Identity。唯一实质分歧在 Signal(7.8):纳瓦尔"品牌是穿越周期的杠杆"9 vs 安德森/蒂尔"AI 落后动摇创新 durability"7
- **创始人乔布斯**:复用评委 jobs 的 06-timeline(车库创业 1976→被逐出 1985→归来 1997 传奇弧线 + 连续品类创造);status 已故;乔布斯是评委但 vc-en 不含其本人,无 --panel-drop
- **产业归类**:智能制造·硬件(与联想/橙市汽车同列,用户选定)
- **全套耦合**:report.md(10 段 + 数字自洽 Score Matrix)+ 手写 report.html(内联 Chart.js 雷达 + 均值条)+ panel.yaml + reports-meta + published-reports.txt + watch/matrix + founders/apple.yaml
- 反捏造:评委评分/对话为 AI in-character 模拟(disclaimer),Apple 事实取自 jobs 06-timeline 锚点;数字需 live 核验
- QA:validate_report/check_report_integrity/validate_html_report 全过 · render-qa canvas=2 离线 · check_consistency 11 格 · 首页 0 JS 错误(18 品牌,智能制造·硬件筛选→3)· founders 18 对齐白名单
**MBA 现覆盖**:**18 品牌** + 18 位创始人 + 6 产业 + 2 场创始人晚餐
**commit**:本 PR(Google 下一 PR)

### 2026-07-16(续六)

**事项**:新增受监控品牌 Google + 创始人拉里·佩奇(完整审计入库)
**触发**:用户「增加 apple、google 两家公司和其创始人」(Apple 已合并,本 PR 做 Google)
**完成内容**:
- **Google 完整审计**(vc-en 5 评委):安德森 40 · 格雷厄姆 42 · 蒂尔 43 · 纳瓦尔 44 · 霍夫曼 42 = **211/250 · 8.44**(vc-en 高分梯队,在 NVIDIA/Apple/SpaceX 之后)。**Category 9.2 领跑**(定义现代搜索 + 搜索广告商业模式 + 2017 发明 Transformer);蒂尔把 Google 当"创造性垄断"范式给满分 10。与 Apple/NVIDIA 在 Signal 上"高分歧"不同,Google 的 **Signal(7.6)是 5 评委一致谨慎**:2024 搜索反垄断败诉 + "发明了 Transformer 却被 OpenAI 的 ChatGPT 抢先"的创新者窘境
- **创始人拉里·佩奇**:curl 一手(Google 官方 our-story:1995 斯坦福、BackRub、使命逐字、1998 Bechtolsheim 10 万支票、Wojcicki 车库 + Ten things + Alphabet 2015 创始人信);status 已离任(2019 卸任 Alphabet CEO,仍为联合创始人/董事/控股股东);非评委无自冲突
- **产业归类**:人工智能(用户默认)
- **全套耦合**:report.md(10 段 + 数字自洽)+ 手写 report.html(内联 Chart.js)+ panel.yaml + reports-meta + published-reports.txt + watch/matrix + founders/google.yaml + api 重生成 19 reports
- 反捏造:评委评分/对话为 AI in-character 模拟(disclaimer),Google 起源事实取自官方 our-story(使命句逐字),数字/反垄断进展需 live 核验
- QA:report/integrity/html 全过 · render-qa canvas=2 离线 · check_consistency 11 格 · 首页 0 JS 错误(19 品牌,人工智能筛选→7)· founders/watch 各 19 对齐
**MBA 现覆盖**:**19 品牌** + 19 位创始人 + 6 产业 + 2 场创始人晚餐(Apple/Google 两家科技巨头入库完成)
**commit**:本 PR

### 2026-07-16(续七)

**事项**:新增受监控品牌 Microsoft + 创始人比尔·盖茨(完整审计入库)· **首个真实触发 --panel-drop 的发布报告**
**触发**:用户「增加微软和亚马逊两个公司和创始人」(先微软再亚马逊)
**完成内容**:
- **Microsoft 完整审计**(vc-en,**--panel-drop rhoffman**):安德森 44 · 格雷厄姆 42 · 蒂尔 42 · 纳瓦尔 45 = **173/200 · 8.65**(vc-en 高分梯队)。**Leverage 9.5 领跑**(Windows/Office + Azure + GitHub + OpenAI 股权——不同于 NVIDIA 单点 CUDA,微软胜在"多元+纵深")。唯一分歧在 Signal(8.25):蒂尔"AI 领先借自 OpenAI"7 vs 安德森/纳瓦尔"分发已把 AI 变自有杠杆"9
- **首次真实用 --panel-drop**:里德·霍夫曼(rhoffman)创办 LinkedIn(2016 售予微软)并曾任微软董事 → 在 `self-conflict.yaml` 给 rhoffman.orgs 补 Microsoft/微软/领英,审微软时 drop,4 评委打分、满分 200。`check_self_conflict --brand Microsoft --panel vc-en` 正确命中
- **创始人比尔·盖茨**:curl 一手(微软官方 facts:1975 founded/1981 incorporates/Windows 95/2014 Nadella CEO/当代使命逐字 + 盖茨哈佛 2007 演讲);status 已离任(2020 离开董事会);非评委(注:现任 CEO 纳德拉是评委 satyanadella,但不在 vc-en)。产业归类:企业服务·安全
- **全套耦合**:report.md(10 段 + 数字自洽 /200)+ 手写 report.html(4 评委 + drop 卡)+ panel.yaml(drop: [rhoffman])+ reports-meta + published-reports.txt + watch/matrix + founders/microsoft.yaml + api 重生成 20 reports
- 反捏造:评委评分/对话 AI in-character 模拟(disclaimer),微软事实取自官方 facts(使命句逐字),数字需 live 核验
- QA:report/integrity(/200 自洽)/html 全过 · render-qa canvas=2 离线 · check_self_conflict + check_consistency 11 格 · 首页 0 JS 错误(20 品牌,企业服务·安全→3)· founders/watch 各 20 对齐
**MBA 现覆盖**:**20 品牌** + 20 位创始人 + 6 产业 + 2 场创始人晚餐
**commit**:本 PR(亚马逊下一 PR)

### 2026-07-16(续八)

**事项**:新增受监控品牌 Amazon + 创始人杰夫·贝索斯(完整审计入库)
**触发**:用户「增加微软和亚马逊两个公司和创始人」(微软已合并,本 PR 做亚马逊)
**完成内容**:
- **Amazon 完整审计**(vc-en 5 评委,贝索斯非评委无自冲突):安德森 43 · 格雷厄姆 44 · 蒂尔 43 · 纳瓦尔 45 · 霍夫曼 43 = **218/250 · 8.72**(vc-en 高分梯队,在 SpaceX 8.76 之后、微软 8.65 之前)。**Leverage 9.4 领跑**——被写进商学院教材的"飞轮"+ AWS + Prime + 物流,是商业史最深的运营型护城河。唯一分歧在 Signal(8.0):蒂尔"护城河深到触发 FTC 反垄断 + AI 追赶者"7 vs 纳瓦尔"飞轮复利穿越周期"9
- **三种护城河对照成型**:NVIDIA=CUDA 软件锁定 · 微软=多元产品捆绑 · 亚马逊=规模+运营飞轮(均 Leverage 峰值,但质地不同)
- **创始人杰夫·贝索斯**:curl 一手(亚马逊官方 About Us:使命/创业;贝索斯 2016 致股东信 "Day 1 / Day 2 is stasis..." 逐字);status 已离任(2021 卸 CEO 任执行董事长);非评委。产业归类:企业服务·安全
- **全套耦合**:report.md(10 段 + 数字自洽)+ 手写 report.html(内联 Chart.js)+ panel.yaml + reports-meta + published-reports.txt + watch/matrix + founders/amazon.yaml + api 重生成 21 reports
- 反捏造:评委评分/对话 AI in-character 模拟(disclaimer),亚马逊事实取自官方 + 贝索斯致股东信(Day 1 逐字),数字/FTC 进展需 live 核验
- QA:report/integrity/html 全过 · render-qa canvas=2 离线 · check_consistency 11 格 · 首页 0 JS 错误(21 品牌,企业服务·安全→4)· founders/watch 各 21 对齐
**MBA 现覆盖**:**21 品牌** + 21 位创始人 + 6 产业 + 2 场创始人晚餐(本轮 Apple/Google/微软/亚马逊 四家科技巨头入库完成)
**commit**:本 PR

### 2026-07-16(续九)

**事项**:新增受监控品牌 Huawei + 创始人任正非(完整审计入库)· 第二个 --panel-drop(创始人自冲突)
**触发**:用户「增加华为公司」
**完成内容**:
- **Huawei 完整审计**(security-cn-global,**--panel-drop renzhengfei**):周鸿祎 45 · 张明正 40 · 黄仁勋 44 · 马斯克 45 · 纳德拉 38 = **212/250 · 8.48**(高分梯队,Google 8.44 之上、微软 8.65 之下)。**Origin 9.0 领跑**(43 岁 2.1 万元创业 + 农村包围城市 + 抗住美国封锁,MBA 最强创业-生存叙事之一);Identity 8.8(狼性/备胎/自立)。**分歧沿东西方最清晰**:周鸿祎(国家队)与马斯克(工程崇拜)并列 45,纳德拉(西方信任视角)38 全卷最低;唯一实质分歧在 Signal(8.0):马斯克/周鸿祎"Mate 60 突破是韧性证明"9 vs 纳德拉/张明正"先进制程天花板仍在"7
- **面板 security-cn-global**(奇安信/亚信同款政企安全面板);任正非是创始人评委(renzhengfei),按面板 self-conflict 规则(明列 Huawei→drop renzhengfei)剔除,5 评委打分。**第二个真实 --panel-drop 报告**(继微软 drop 霍夫曼)
- **创始人任正非**:复用评委 renzhengfei 的 06-timeline(1944 贵州山区 / 1974 基建工程兵 / 1987 创业 / 1993 农村包围城市 / 2019 实体清单+备胎 / 2023 Mate 60);status 现任(轮值董事长制,持股约 1%)。产业归类:企业服务·安全
- **全套耦合**:report.md(10 段 + 数字自洽)+ 手写 report.html(5 评委 + drop 卡 + 东西方分歧)+ panel.yaml(drop: [renzhengfei])+ reports-meta + published-reports.txt + watch/matrix(W5 资本市场 off:未上市)+ founders/huawei.yaml + api 重生成 22 reports
- 反捏造:评委评分/对话 AI in-character 模拟(disclaimer),华为事实取自 renzhengfei 06-timeline 锚点,数字/制程/鸿蒙规模需 live 核验
- QA:report/integrity/html 全过 · render-qa canvas=2 离线 · check_self_conflict(命中并 drop)+ check_consistency 11 格 · 首页 0 JS 错误(22 品牌,企业服务·安全→5)· founders/watch 各 22 对齐
**MBA 现覆盖**:**22 品牌**(首个中国科技巨头本轮入库)+ 22 位创始人 + 6 产业 + 2 场创始人晚餐
**commit**:本 PR

### 2026-07-16(续十)

**事项**:全站功能巡检 —— 点击/执行/验证所有功能,修复不起作用的,做测试与文档记录
**触发**:用户「对网站的所有功能点击、执行、验证,改正那些不起作用的功能,过程中做好测试和文档记录」
**方法**:`build.sh` 构建完整站点 → 本地 server → Playwright 广度优先爬 **177 页 / 188 链接** 查 404 + JS 错误 → 交互功能单独驱动测试
**修复 4 个真实缺陷**(复测全过):
1. `roadmap.html` 死链 `/docs/12-evolution-tracking.md`(裸站内路径,漏写)→ 改 GitHub URL(与兄弟链接一致)
2. `chengshi-auto` v1 版本链 `versions/v1_2026-05-17.md`(v1 无 HTML 快照,build 只发 .html → 404)→ 改指 GitHub 源文件
3. 历史快照断图:`lenovo` v1 / `chengshi-auto` v5·v6 引用 `_assets/*.jpg`,相对 `versions/` 解析成 `versions/_assets/`(不存在)→ **`build.sh` 把 `_assets/` 镜像到 `versions/_assets/`**
4. `chengshi-auto` v2 redirect stub 跳 `../report.html`(部署后 report.html 变 index.html → 404)→ 改跳 `../`
**排除环境假阳性**:报告页 `<head>` 的 Chart.js CDN 在沙箱不可达 → `domcontentloaded` 超时记为 `[0]`,经响应状态/直连 curl 复核均 **200**,非线上缺陷(render-qa `--offline-libs` 权威验证图表)
**交互测试 11/11**:排序 / 产业筛选 / 晚餐 CTA / 组合器(开饭+点单+同人提示)/ 评委页动态渲染 + 裸 URL 兜底 / panorama / starmap / watch cockpit 全部正常
**文档**:docs/24-site-qa.md(方法 + 发现 + 修复 + 复测)+ docs 索引
**commit**:本 PR

### 2026-07-16(续十一)

**事项**:新增受监控品牌 Tesla + 创始人埃隆·马斯克(完整审计入库)· **第 3 个真实 --panel-drop**
**触发**:全仓盘点后的下一步计划(用户四选:加新品牌 + 加创始人晚餐 + 决策项 + 文档保鲜)
**完成内容**:
- **Tesla 完整审计**(auto 面板,**--panel-drop musk**):雷军 45 · 李想 40 · 何小鹏 45 · 李斌 40 = **170/200 · 8.50**(高分梯队,微软 8.65 之下、华为 8.48 之上)。**Category 9.5 拿下 MBA 迄今品类维度最高分**——特斯拉没发明电动车,却第一个把它做成"人们真正想要"的高端欲望品,开创了四位打分者都身处其中的品类。叙事亮点 = "**四位中国新势力创始人给他们共同的祖师爷特斯拉打分**",分歧沿"祖师爷 vs 挑战者":雷军/何小鹏(最直接沿特斯拉打法)并列 45,李想/李斌(增程务实、换电社区,刻意分道)40。唯一强分歧在 Signal(7.5,**Δ3 全卷最大**)——何小鹏"数据飞轮是硬护城河"9 vs 李想"FSD 过度承诺、价格战暴露软件护城河未兑现"6
- **第 3 个真实 --panel-drop**:马斯克(musk)是特斯拉领投人/CEO 且为 MBA 评委,`self-conflict.yaml` 里 musk.orgs 已含 Tesla → 审特斯拉时 drop,4 位中国新势力创始人打分、满分 200。`check_self_conflict --brand Tesla --panel auto` 正确命中(继微软 drop 霍夫曼、华为 drop 任正非)
- **创始人马斯克**:复用评委 musk 的 06-timeline(2003 Eberhard/Tarpenning 创立 → 2004 领投 → 2008 任 CEO + 濒临倒闭 → 2012 Model S → 2017 制造地狱 → 2022 X → FSD)。**起源归属如实标注**:特斯拉非马斯克一人独创,2009 和解确立联合创始人身份;status 现任。产业归类:智能制造·硬件(与 apple/lenovo/chengshi-auto 同列)
- **全套耦合**:report.md(10 段 + 数字自洽 /200)+ 手写 report.html(4 评委 + drop 卡,Category 9.5 设为最强紫、Signal 7.5 最弱橙 + Δ3 核心分歧)+ panel.yaml(drop: [musk])+ reports-meta + published-reports.txt + watch/matrix(W5 core:TSLA 上市)+ founders/tesla.yaml + api 重生成 23 reports
- 反捏造:评委评分/对话 AI in-character 模拟(disclaimer),特斯拉事实取自 musk 06-timeline 锚点,交付/份额/FSD 进展需 live 核验
- QA:report/integrity(/200 自洽)/html 全过 · render-qa canvas=2 离线(bodyH=6057)· check_self_conflict(命中并 drop)+ check_consistency 11 格 · 首页 0 JS 错误(23 品牌,智能制造·硬件筛选→4)· founders/watch 各 23 对齐
**MBA 现覆盖**:**23 品牌** + 23 位创始人 + 6 产业 + 2 场创始人晚餐
**commit**:本 PR

<!-- 在此追加后续进度记录，格式参考上方 -->
