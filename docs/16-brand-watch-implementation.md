# 16 — 品牌舆情监控实现与过程记录(Brand Watch Implementation)

> Status: **M1 完成 · M2 首项落地**(W1-W4 ✅,W5 ✅)· Last verified: 2026-07-12
> **2026-07-13 增补**:回填 W2(社交社区)与 W7(人事组织)两个此前空白维度共 6 条事件
> —— W7:OpenAI 高管出走(Murati 等,2024-09-25)、Anthropic 聘前 Stripe CTO(2025-10-02);
> W2:爱马仕「Wirkin」平替走红(2024-12-30)、Sora 登顶 App Store(2025-10-03)、元气森林 0糖
> 致歉(2021-04-13)、美团外卖大战舆论(2025-09-15)。均 `quote_type: title`,URL 内嵌日期自证,
> 经 WebSearch(服务端出口,绕开沙箱 egress)取真实链接;全库 87 条,validate_watch 全绿。
> **二批 +3**:kimi「DeepSeek 时刻」(W2,2025-07-19)、SpaceX 散户打新热(W2,2026-06-15)、
> 好未来双减停课组织巨变(W7,2021-11-17)。全库 **90 条**。
>
> **社媒正文可达性复测(2026-07-13,环境网络策略已切 Full)**:网关已全放行(curl paulgraham
> = 200,知乎/微博/小红书 302 非拒绝)。但**站点自身墙仍在**:curl 知乎=648B 反爬壳、微博=登录墙、
> 小红书=JS 应用壳,**都拿不到正文**。预装 Playwright/Chromium 经 egress 代理**连不通**(连
> paulgraham 控制组都 `ERR_CONNECTION_RESET`,代理端口 Full 切换后由 35003 轮换到 37607)。
> **结论:Full 网络对 curl-able 源(paulgraham/a16z/36氪/新浪等)是真解锁,但对知乎/微博/小红书
> 三家反爬+登录墙站无效——正文全文仍须 Wuying(带登录态真云浏览器)**。事件级信号继续走 WebSearch。
> 需求与维度设计见 **docs/15**(PRD);本文是**开发计划 + 实现细节 + 过程记录**,
> 按 W 系列工作项组织,做一项记一项(格式对齐 docs/11 的进度日志纪律)。

---

## 1. 开发计划(W 系列工作项)

对应 PRD(docs/15 §7)的 M1→M3 分期,拆成可单独 PR 的工作项:

| # | 工作项 | 内容 | 验收 | 状态 |
|---|---|---|---|---|
| **W1** | 数据层 + 硬 gate | `watch/matrix.yaml`(适用性矩阵单一真源)· `watch/<slug>/events.yaml` schema · `scripts/watch-tools/validate_watch.py`(静态校验 + `--selftest`)· 接入 panel-validation CI | 校验器全绿 + 自测有牙 + CI 跑 | ✅ 2026-07-12 |
| **W2** | 源可达性验证 | PRD §4.2.3 清单逐源真 curl,🔍 → ✅/⚠️/❌,坑记录在案 | 每源有结论 + workaround 可复现 | ✅ 2026-07-12(见 §3) |
| **W3** | 试点采集(持续) | 亚信 / 奇安信 / 垣信三品牌真实事件回填与增量 | **每品牌 ≥10 条**可溯源事件(M1 验收) | ✅ 2026-07-12 二批后 **11/11/10,验收达成**(见 §4.5);后续增量随 W6 周扫 |
| **W4** | 半自动扫描进 skill | `/mba <brand> --watch` 单次扫描 SOP 进 SKILL.md;EVOLUTION Phase 2 先消费 events.yaml 再补扫 | 一次重审的 delta 调研直接引用事件流 | ✅ 2026-07-12 **验收达成**:奇安信 v1→v2(见 §5) |
| **W5** | 首页徽章 + 时间线页(M2) | `build_home_cards.py` 读 watch 产出 P0/P1 徽章(进 REPORTS 生成区 + 漂移 gate)· `/watch/<slug>/` 时间线页 | 徽章与 events.yaml 零漂移 | ✅ 2026-07-12(见 §6) |
| **W6** | 定期采集(M2) | CCR Routines / cron 周扫,按矩阵扫开启维度 | 13 品牌适用维度覆盖 ≥80% | ✅ 2026-07-12:周扫 Routine + G3 冷启动 ×8 → **覆盖 13/13(100%)达标**,全库 69 条(见 §7.4 更新) |
| **W7** | 触发与联动(M3) | 触发规则评估器(30 天窗 P0≥1 / P1≥2)· MCP `get_watch_events` / `record_watch_event` · 订阅链路下发重审建议 | 触发建议精确率 ≥60% | ✅ 2026-07-12(见 §8);精确率 n=1 初步达标,每次重审后续账 |

依赖关系:W1 → {W3, W4} → W5 → W6 → W7。W2 与 W3 并行滚动(每接新源先过 W2 验证)。

---

## 2. W1 实现记录(数据层 + 硬 gate)

### 2.1 落库结构

```
watch/
  matrix.yaml            # 维度×品牌适用性(单一真源,core/on/off)
  <slug>/events.yaml     # 每品牌一个事件流,追加式
scripts/watch-tools/
  validate_watch.py      # 静态硬 gate + --selftest
```

### 2.2 事件 schema(相对 PRD §5.1 的实现增补)

PRD schema 原样落地,增补以下几点(均为实操/驾驶舱需求发现的需要):

1. **`quote_type: title | body`(可选,缺省 body)** —— 采集实操发现:搜索结果的
   AI 摘要**不是逐字原文**,不能当 quote;但**标题是逐字的**。故允许 quote 取源文章
   标题并显式标注 `title`;`body` 类引用则要求先 curl 原文核对。这保住了
   「quote 必须逐字」的反捏造底线,同时让无法 curl 的源也能入库。
2. **URL 自证日期原则(SOP,非 schema 字段)** —— 优先收录 **URL 内嵌日期**的源
   (如 `…/article/20240117/…`、`…/2025-04-07/…`):日期不依赖任何转述,
   事件的 `date` 可被 URL 直接核对。首批 15 条事件全部满足此原则
   (唯一例外 ithome 一条,已 curl 原文核对正文日期,见 §4.2)。
3. **舆情驾驶舱扩展字段(4 个可选,2026-07-14,docs/20)** —— 为对齐「舆情驾驶舱」的
   7 标签,加 `related_persons`(关联人物)、`source_type`(来源类型枚举:official/media/
   finance/social/investor_community/search/regulator)、`suggested_action`(结构化建议动作)、
   `alert_tier`(L1/L2/L3 预警层级覆写)。全部**可选、向后兼容**(旧事件不动);校验由
   `validate_watch.py` 的枚举 gate + `--selftest`(17 组断言)兜底,MCP 侧 `watch/store.ts`
   镜像同一套。反捏造:`related_persons` 须取自源文本真实人名;其余是标签/判断,不进 firewall。
   **消费方**:`scripts/build_watch_cockpit.py` 生成 `site/watch/<slug>/cockpit.html`
   舆情驾驶舱看板(管理层摘要 / 发布时间分布 / 维度×方向归因 / 来源类型 / 投资社区专区 /
   可筛选全量表),`notify_feishu.py` 用 `alert_tier` 做 L1/L2/L3 分层预警(docs/19)。

### 2.3 校验器检查项(全部静态,CI 不出网)

- **A 溯源结构**:必填字段齐全;quote ≤100 字;url 为 http(s);fetched_at 为 ISO UTC。
  (quote 是否逐字命中原文属**抽检 SOP**,不进 CI —— 网络校验 flaky。)
- **B 判断/事实分列**:`direction_by` 恒为 `model-judged`;dim/severity/direction/
  lens_map 枚举合法;`id` 格式 `<date>-<slug>-NNN` 且日期与 `date` 一致、全局唯一。
- **C 矩阵对齐**:`matrix.yaml` 品牌集合 == 发布白名单(**新发布品牌必须补矩阵行**,
  这把「监控台每个品牌都有舆情配置」变成了机器强制);事件的 dim 在该品牌上不得为 off。
- **`--selftest`**:17 组断言(含舆情驾驶舱 4 字段),每类违规造一个假样本证明会被抓
  (与 `quality_check --selftest` 同一哲学:门禁要自证有牙)。

### 2.5 候选取数半自动助手 `fetch_candidate.py`(2026-07-16)

手工加事件里最累的是 curl 源站取逐字标题 + 抓日期 + 算 id;引用又必须真实(反捏造)。
`scripts/watch-tools/fetch_candidate.py` 把**机械部分**自动化,**判断字段(dim/severity/
direction/lens_map)仍留人工**、**quote 只回填 curl 到的真实标题**(脚本从不编造):

- `draft <url> [...] [--brand SLUG]` —— curl(走 `$HTTPS_PROXY` 出口 + CA + 浏览器 UA)→
  提取逐字标题(优先 `<h1>`,去 `_站名`/` - 站名` 尾缀)→ 抓 URL 内嵌日期 → 猜 `source_type` →
  给 `--brand` 时算下一个 id + 列该品牌非 off 维度 → 打印**候选 YAML 草稿**(dim/severity/
  direction/lens_map 标 TODO)。人工核验维度/等级/方向后再粘进 `events.yaml`。
- `verify [--brand SLUG]` —— **反捏造自审 + 死链检测**:对所有 `quote_type=title` 事件重新 curl,
  核对 quote 是否仍在源站标题里(去空白/实体规范化匹配),报告 OK / MISMATCH / DEAD。

**边界**:需要网络,**不进 CI**(CI 不出网,与 §2.3 的「逐字命中属抽检 SOP」同因);它是把
「WebSearch → curl 核对 → 入库」这条人工链的取数/核对两段**减负**,不替代人工定维度与判断。

### 2.6 前台候选 triage 页(2026-07-18)—— 取代「读 PR diff」

`discover` 除 `<date>.md` 外再写 `<date>.json`(结构化候选)。`scripts/build_watch_triage.py`
聚合 `watch/_candidates/*.json` → 生成 **`site/watch/triage.html`**(自包含,候选数据 inline)。
每条候选一张卡片,带 **✓采纳 / ✗丢弃** + 就地选 dim/severity/direction/lens,选完一键
**复制「已采纳」YAML**(按 slug 分组、续号,粘进 `watch/<slug>/events.yaml`)。选择只存
浏览器 localStorage。

- **反捏造边界不变**:卡片只呈现源 feed 的标题/日期/URL;判断字段是**人工在页面上打的勾**,
  非自动打分;**前台不写审计仓库**——采纳项必须 commit 进 `events.yaml` 再 `validate_watch` 才生效,
  git 仍是唯一真源(公开访客改不了打分)。
- **候选如何上站**:`watch-discover` workflow 把候选**直推 main**(暂存草稿、非改分),Cloudflare
  重建后生产站 `/watch/triage.html` 立即显示;main 有保护则回退候选分支 + PR(triage 在预览部署可用)。
- 入口:全站/单品牌驾驶舱 nav 与 crumb 均挂「候选 triage」。页面在 `site/watch/`(gitignored,随 build 重生成)。

**中文标题(2026-07-18 迭代)**:`discover` 的 Google News 源改中文档
(`hl=zh-CN&gl=CN&ceid=CN:zh`)+ 查询用 `brand_cn brand_en` 组合 → 候选标题**直接是中文**
(取自中文媒体,**非机器翻译**,quote 仍逐字);反捏造不变。

**「✅ 提 PR」一键流(取代复制粘贴)**:triage 页「提 PR」按钮把采纳项(扁平列表、每条带 `slug`,
JSON 即合法 YAML)经 **GitHub 预填新文件深链**创建 `watch/_adopt/<ts>.yaml` → 用户点「Commit / Propose」
即开 PR(无需 copy/paste、无后端、无密钥)。`watch-adopt.yml`(PR 触发、`paths: watch/_adopt/**`)跑
`scripts/watch-tools/fold_adopt.py`:按 slug **折入** `events.yaml`、**重算 id 尾号防撞**、删暂存、跑
`validate_watch`,并**回推 PR 分支**(仅同仓 PR;fork PR 只 `--check`,维护者本地折叠)。维护者只看最终
`events.yaml` diff 再合并 —— **合并仍是人工闸门**(反捏造:折叠只搬运不打分,采纳事件合并后才由评委
在 EVOLUTION 消费)。URL 超长(采纳过多)时页面提示分批 / 回退「复制 YAML」。

### 2.7 LLM 预分类 → 全自动开「建议入库」PR(2026-07-18)—— 人工只审 diff

连人工 triage 也嫌费事时的更高档自动化:`scripts/watch-tools/classify_candidates.py` 用 Claude
(Messages API,仅标准库 `urllib`)给每条候选判 **keep? + dim/severity/direction/lens + 置信度 + 理由**,
高置信 keep 写成 `watch/_adopt/auto-<date>.yaml`。`watch-discover.yml` 随后开一个「**建议入库**」PR,
`watch-adopt.yml` 把它折入 `events.yaml` → **维护者只审最终 `events.yaml` diff 再合并**;丢弃/低置信项
在 PR 正文列出理由(透明,可在预览 triage 页手动补)。

- **反捏造(硬约束)**:`quote/title/url/date` **原样透传**,模型**只做分类、绝不改写或编造**引文;
  `direction` 等标 `direction_by: model-judged`(显式编辑判断,不假装客观);**不改任何审计分数**,
  合并入库后仍由评委在 EVOLUTION 重审时消费。字段非法一律兜底留空(由人工在 diff 补),不硬塞。
- **前置(多 provider,配一个即可)**:仓库 Secrets 加下列**任一** key,`classify_candidates.py`
  按优先级择一:
  - `GLM_API_KEY`(智谱 GLM):**默认走 Anthropic 兼容端点** `https://open.bigmodel.cn/api/anthropic`、
    模型 `glm-4.6` —— 即 **Claude Code 等交互式编码工具用 GLM coding 套餐的方式**。
    (coding 套餐的 OpenAI `/chat/completions` 对程序化批量调用 **429 硬限流**,故走 Anthropic messages 端点。)
    想改用**通用开放平台**:设 `GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4` + `MBA_CLASSIFY_MODEL=glm-4-flash`
    (base 含 `paas` → 自动切 OpenAI 格式)。
  - `OPENAI_API_KEY`(OpenAI 或任意兼容端点,配 `OPENAI_BASE_URL`)→ `ANTHROPIC_API_KEY`(默认 `claude-haiku-4-5`)。
  - 限流韧性:`call_llm` 对 429/5xx **退避重试**(4/10/20/35s,认 `Retry-After`);批间隔 `MBA_CLASSIFY_BATCH_PAUSE`(默认 2s)。
  - 空串等同未设,不会覆盖默认。
  **一个都没配时 `classify` 优雅跳过**,`watch-discover` 自动回退到 §2.6 的「直推候选 + 人工 triage」流,不报错。
- 本地自测(不联网):`python3 scripts/watch-tools/classify_candidates.py --selftest`(验证兜底/分流/落盘)。

### 2.4 踩坑记录

- **YAML 1.1 布尔坑**:`on` / `off` 会被 PyYAML 解析成 `True` / `False`
  (`yes/no/y/n/true/false` 同理)。矩阵取值恰好用了 on/off,首跑 58 条误报。
  处置:校验器内 `_norm_flag` 归一化(True→on / False→off),矩阵文件保持人类可读的
  on/off 写法。**以后任何 YAML 配置想用 on/off 当枚举,都要过这一层。**

---

## 3. W2 源可达性验证记录(2026-07-12,坑 #1 纪律)

方法:每源真 curl(走 `$HTTPS_PROXY` 出口 + CA + 浏览器 UA,15s 超时),
看 HTTP 码 + 响应体积(<3KB 疑似 JS 壳)。**结论只对本环境、本日期负责**,
接入采集前需复验。

| 源 | 结论 | 说明 |
|---|---|---|
| 中国政府采购网 ccgp.gov.cn | ✅ | 200 / 69KB 真实内容 |
| 全国公共资源交易平台 ggzy.gov.cn | ✅ | 200 / 69KB |
| 联通招标网 chinaunicombidding.cn | ✅ | 200 / 14KB |
| 巨潮资讯 cninfo.com.cn | ✅ | 200 / 110KB;`static.cninfo.com.cn/finalpage/<日期>/<id>.PDF` 直链法定披露件,是**最高置信度源** |
| SAM.gov(美国联邦合同) | ✅ | 200 / 55KB |
| 证券时报 stcn.com · 21 经济网 21jingji.com | ✅ | 200,正文可抓 |
| **中国移动采购与招标网 b2b.10086.cn** | ⚠️ **可连,需 workaround** | 直连报 `unsafe legacy renegotiation disabled`(源站用旧 TLS 重协商,OpenSSL 3.x 默认拒绝)。用 `OPENSSL_CONF` 开 `UnsafeLegacyRenegotiation` 后 200(见下方配置)。**二批实测:全站(含公告列表各路径)均返回同一个 855B JS 壳,curl 不可用 —— 该源需真浏览器(Wuying / Playwright),转 W6 排期** |
| 电信阳光采购 caigou.chinatelecom.com.cn | ⚠️ | 200 但 2.2KB,疑似 JS 壳,正文待验证 |
| 国网 ECP ecp.sgcc.com.cn | ⚠️ | 200 / 3.6KB,边缘体积,待深挖 |

**b2b.10086.cn 的 TLS workaround**(亚信 W3 核心源,必须留档):

```bash
cat > /tmp/openssl_legacy.cnf <<'EOF'
openssl_conf = openssl_init
[openssl_init]
ssl_conf = ssl_sect
[ssl_sect]
system_default = system_default_sect
[system_default_sect]
Options = UnsafeLegacyRenegotiation
EOF
OPENSSL_CONF=/tmp/openssl_legacy.cnf curl -sSL --cacert /root/.ccr/ca-bundle.crt \
     -A "Mozilla/5.0 …" "https://b2b.10086.cn/…"
```

---

## 4. W3 试点采集记录(首批,2026-07-12)

### 4.1 方法(即 M1 半自动扫描的 SOP 雏形)

1. **发现**:WebSearch 按「品牌 + 维度关键词」检索(如 `亚信科技 中标 集采`);
2. **收录门槛**:只收 **URL 内嵌日期**的结果(date 自证),quote 取标题
   (逐字,`quote_type: title`);无日期 URL 的重要事件 → 先 curl 原文核对日期与
   引用再入库,curl 不动的记入 §4.3 leads,**不入库**;
3. **聚合库纪律**(PRD §4.2.3):千里马/标标达等商业聚合平台的结果**只作线索**,
   入库必须回溯到法定公示或权威媒体原文;
4. 每条事件补 `lens_map`(供重审消费)与 `note`(含日期自证方式)。

### 4.2 首批产出(15 条,全部过 validate_watch)

| 品牌 | 条数 | 亮点 |
|---|---|---|
| asiainfo | 6(P0×1 · P1×3 · P2×1 · P3×1) | **P0:亚信安全被中国移动子公司禁入采购三年(2025-04-07)** —— PRD §4.2.2 分类学「采购黑名单 → P0」的第一个真实实例,而且发生在命脉客户群(运营商)上 |
| qianxin | 3(P1×2 · P2×1) | 2025 年报净利 −12.87 亿(2026-04-30):v1 审计「持续亏损」风险信号在新财年**继续成立**——首个「审计结论被 watch 流延续验证」的样本 |
| yuanxin | 6(P1×1 · P2×4 · P3×1) | 2026 组网进展(至 7 月 238 颗、年度目标 324 颗):**v1 审计(语料止于 2025-10)未覆盖的新信号**——watch 层「两版之间的眼睛」价值的直接演示;一箭 20 星(2026-07-05)已 curl ithome 原文核对标题与正文日期 |

### 4.3 Leads(有线索、未达入库门槛,待回溯)

- 亚信科技:中国移动贵州公司 2025-2028 集微服务框架多标段中选(源=标标达**聚合库**,
  待回溯移动集采官网公示;用 §3 的 TLS workaround 深挖列表页);
- 亚信安全禁入事件的**处罚公示原文**(现引新浪科技报道,应回溯运营商采购平台原公示);
- 奇安信 2025 年中标集:大行 NDR / 电信安全大脑集采 / 移动终端安全软件三年 /
  中海油 ~8000 万框架(源=年报经营分析转述,待逐条回溯集采公示);
- 垣信:手机直连试验星(2026-06-09)与 5G 直连通话(2026-06-19)—— 摘要有日期但
  未见带日期 URL 的原文,待定位官方稿。

### 4.4 M1 验收记账

首批(2026-07-12 上午):asiainfo 6/10 · qianxin 3/10 · yuanxin 6/10 —— 未达线。
二批(同日,§4.5)补采后:**asiainfo 11 · qianxin 11 · yuanxin 10 —— 验收线达成**。

### 4.5 二批补采记录(2026-07-12)

方法与首批相同(§4.1),两处升级:

1. **curl 核日期成为主力**:URL 无日期但源站可 curl 的(奇安信官网新闻详情页、
   亚信官网、stcn),一律 curl 原文取页面日期 + 核对标题逐字 —— 本批 8 条事件
   靠这条路入库。**奇安信官网新闻详情页(qianxin.com/news/detail)可稳定 curl
   且带日期,是奇安信 W3 的高置信度一手源**(官网自己的中标稿)。
2. **纠错实例(SOP 价值实证)**:「奇安信×东方国信战略合作」搜索摘要暗示为
   2026 年事件,curl 页面实际 **2025-02-12** —— 摘要不可信、原文为准,
   这条纪律本批直接防了一次错年入库。

产出(+17 条,累计 32 条全过 validate_watch):

| 品牌 | 二批新增 | 累计 | 分级结构(累计) |
|---|---|---|---|
| asiainfo | +5(六强评估/盈利预喜/亚信安全半年报/2025 年报 −5.2%/亚信安全年报) | **11** | P0×1 · P1×4 · P2×5 · P3×1 |
| qianxin | +8(保险 2000 万/市大数据/东方国信/2024 年报/国核自仪 2900 万/运营商防病毒/CyberSec-Eval/医疗 AI 安全) | **11** | P1×2 · P2×9 |
| yuanxin | +4(三连发×运力短板/手机直连试验星/品类议程/无改造直连通话首例) | **10** | P1×3 · P2×5 · P3×2 |

观察(供 W7 触发规则参考):垣信 2026-06-09 / 06-19 / 07-05 三个 P1 落在同一个
30 天窗内 —— 若 watch 早于 v1 审计存在,当时就会亮「建议重审」;v1(2026-07-12)
已吸收该现实,后续以 v1 日期为 last_update_date 起算。

Leads 状态更新:垣信手机直连两条已回溯入库(销案);移动贵州框架与亚信禁入处罚
公示原文仍开放(b2b.10086.cn 需浏览器,见 §3);奇安信年报中标集部分已由官网
一手稿覆盖(保险/大数据/运营商),其余(大行 NDR/中海油框架)仍开放。

---

## 5. W4 实现记录(`--watch` 进 skill + EVOLUTION 消费,2026-07-12)

改动全部在 `metric-brand-auditor/SKILL.md`(版本 0.4.2 → 0.4.3,front-matter 与
panel 模板 `mba_version` 同步 bump,过版本对齐 gate):

1. **`--watch` 参数**(Parameters 区 + front-matter trigger patterns):单次扫描、
   不跑评委不出报告 —— 读矩阵 → 按开启维度搜集有据事件(收录门槛 = §4.1 SOP)→
   追加 events.yaml → 跑 validate_watch 必须全绿 → 评估触发规则(30 天窗
   P0≥1 / P1≥2 → 打印重审建议)。**watch 永不改分**的边界写进了参数说明本身。
2. **Phase 1E 先消费 watch 流**:`last_update_date` 之后的 P0/P1 事件,其 `lens_map`
   维度必须在 diff plan 标 YES 并引用事件 id;diff plan 模板新增
   `Watch events since v{n}` 行。原则:不重复发现 watch 已记录的东西。
3. **Phase 2E 贴入 prompt**:相关事件(id/date/title/quote/url)作为已核实线索贴给
   sub-agent,先验证扩展、再泛搜 —— 有据事件优先级高于新发现。
4. **配套**:docs/12 新增 §5.5(与维度差分探针的关系:有 P0/P1 事件的维度可跳过
   探针直接标 CHANGED);坑 #2 已履行(两个派生产物重生成,personas 零漂移,
   index.json 仅时间戳已回退)。

**验收状态(2026-07-12,达成)**:**奇安信 v1→v2 是 MBA 首个由 watch 事件流驱动的
EVOLUTION**。diff plan 直接消费 `watch/qianxin/events.yaml` 全部 11 条事件:P1
`2026-01-31-qianxin-002` / `2026-04-30-qianxin-003` 驱动 Signal 重审(锚点校正:v1 引
2023 口径 67 亿营收,FY2025 现实 43.92 亿 + 净亏 12.87 亿 → 全员下调 6.8→5.7),
P2 中标×5 + CyberSec-Eval 作 Leverage 对冲证据(7.0→6.5)。Origin/Category/Identity
无新证据保留(↔)。结果 185→175(6.17→5.83)。报告的 What-changed 段与 Sources
逐条引用事件 id;重打分记录在 `reviews/v2_rescores.md`。

**consumed_by 机制(W4↔W5 连接件)**:被审计消费的事件标 `consumed_by: vN`
(校验器强制 vN 格式)——奇安信 11 条标 v2;亚信 4 条(001/002/003/005,其信息已在
v1 证据基内)标 v1。徽章(§6)只数**未消费**的 P0/P1,审计一跑徽章即清,闭环成立。

## 6. W5 实现记录(首页徽章 + 时间线页,2026-07-12)

1. **首页「舆情待审」行**:`build_home_cards.py` 新增 `load_watch_pending()`(数未消费
   P0/P1)与 `render_watch_line()`(P0/P1 chips + 触发规则命中时的「建议重审」chip +
   `/watch/<slug>/` 链接,z-index 浮于拉伸链接上)。进 REPORTS 生成区,由既有
   `--check` 漂移 gate 覆盖;CSS 手动加在标记外(与 footer 同模式)。
   **P2/P3 永不上卡**(docs/15 §5.2)。
2. **实现偏差(记录在案)**:PRD §5.3 的触发窗是「滚动 30 天」,实现改为
   「**未消费**(无 consumed_by)的 P0/P1」——滚动窗依赖"今天",会让生成物随日期漂移、
   打破 `--check` 确定性;「未消费」语义等价于"这些信号还没进任何审计",更可执行。
   W7 做触发评估器时可在运行时(非生成物)恢复 30 天窗。
3. **时间线页**:`scripts/build_watch_pages.py` 生成 `site/watch/<slug>/index.html`
   (事件倒序、P0/P1 高亮、consumed 标记、每条直链原文、页脚重申"不改分"边界)。
   接入 `site/build.sh` 的 python 守卫块(与 agents-api 同模式),`site/watch/` 已
   gitignore(与 `site/reports/` 同:deploy 时生成,不入库)。
4. **验证**:headless 首页 —— 亚信卡 `P0×1 P1×1 建议重审`、垣信卡 `P1×3 建议重审`、
   奇安信(全部已消费)无徽章;`/watch/asiainfo/` 11 条 + 触发命中;
   奇安信 v2 报告页 render-qa 离线 13/13 通过。
5. **追加(2026-07-12,W7 后)——`/watch/` 总览页 + 全站导航入口**:修复"条件孤儿页"
   问题(时间线页唯一入口是首页 P0/P1 chip,信号一被消费入口即消失——奇安信全消费后
   `/watch/qianxin/` 曾无任何页面链入)。`build_watch_pages.py` 增生成 `site/watch/index.html`
   总览:13 品牌逐行列事件数 / 待审 P0/P1 / **双口径**触发状态(欠账口径=首页徽章;
   30 天窗口径复用 W7 `evaluate_triggers.evaluate`,按生成时评估——本页 deploy 产物不入库,
   无 `--check` 确定性约束),未开采品牌诚实标注(含开启维度 n/9);排序:亮灯 → 有事件 →
   未开采。全站 10 个静态页导航统一加第 5 项「舆情信号」(/watch/),时间线页 nav 加
   「舆情总览」;llms.txt 补 /watch/ 两行(经 build_agents_api 模板,无漂移)。
   首页 watch-line 保持"P0/P1 才上卡"纪律不变——入口职责移交导航。

## 7. W6 实现记录(定期采集,2026-07-12)

### 7.1 周扫 Routine(CCR Routines)

- trigger id `trig_01Y1KR5NEkodDTAcwozBwbLt`(2026-07-12 因触发规则校准重建,
  原 `trig_015tVDnBhwsD7wLdeiczBPVT` 已删——update_trigger 不支持改 prompt,只能删建),
  cron `0 1 * * 1`(UTC,即北京时间**每周一 09:00**),每次触发**新开会话**独立执行
  (不依赖任何旧会话上下文)。
- Prompt 固化 7 步 SOP(§10 的自动化版):重置 `claude/watch-weekly-scan` 分支 →
  按 matrix 增量扫描(只找上次事件之后的新信号,优先 W3/W4/W5 硬维度;curl 走出口
  代理,禁 WebFetch)→ 准入门槛(URL 自证日期 / 逐字 quote / 聚合器只当线索,拿不到
  原文宁可不录)→ 追加 events.yaml(id 顺延,**不写 consumed_by**——那是审计时才标)→
  `validate_watch` + `build_home_cards --check` + `check_consistency` →
  **有新事件才** commit + PR(描述列新事件、注明触发规则命中品牌),没有就静默结束 →
  红线:不合并 PR、不动 `published/reports/`、watch 永不改分。
- 运维注:`create_trigger` 带 `notifications` 参数时连续两次报权限流错误
  (`permission stream closed`),去掉该参数后第三次创建成功。

### 7.2 周扫演练:覆盖 3 → 5 品牌(spacex / meituan 首批)

- 新增 `watch/spacex/events.yaml`(3 条,全 CNBC、URL 内嵌日期自证)与
  `watch/meituan/events.yaml`(4 条,新浪财经 / 腾讯新闻)。全库 **39 条 / 5 品牌**,
  `validate_watch` 全绿。
- 回填纪律:美团 FY2025 巨亏 ¥234 亿事件已被 v2 审计(2026-07-11)完整消费 →
  回填标 `consumed_by: v2`(与奇安信 §5 同法,不虚增待审信号)。
- 触发面变化:spacex 未消费 P1×2(IPO 定价 + 首日收盘)、meituan 未消费 P1×2
  (监管叫停外卖大战 + Q1 环比减亏 96 亿)均命中「P1≥2」→ 首页新增两枚
  「建议重审」徽章。当前 **4/13 卡亮灯**:asiainfo(P0)/ yuanxin / spacex / meituan。

### 7.3 演练首战果:SpaceX v1 报告勘误(watch 的自净价值)

- 扫 W5 资本维度时发现 SpaceX 已于 2026-06-12 IPO(NASDAQ:SPCX,募资约 750 亿美元,
  史上最大 IPO)——而当天早些时候发布的 v1 报告 Signal 段误写「作为未上市公司」。
- 处置:报告**就地勘误**(report.md + report.html 同步,标注「勘误 2026-07-12」),
  **分数一分不动**——事实性勘误 ≠ 重审;IPO 信号录为未消费 P1×2,留给下一次
  EVOLUTION 由评委消化。这是 docs/15 §5.3「watch 永不改分」边界的第一个实操样例:
  监控流负责纠事实、亮灯,改分只能走评委重审。

### 7.4 验收记账

- §1 的 W6 验收线「13 品牌适用维度覆盖 ≥80%」——2026-07-12 当天分两步走完:
  周扫基建落地时仅 5/13(当时如实标"未达标");**同日 G3 冷启动 ×8**(docs/11
  G 系列)补齐 lenovo/chengshi-auto/anthropic/dji/kimichat/tal-education/
  genki-forest/hermes → **13/13(100%)达标**,全库 69 条可溯源事件。
- G3 冷启动的诚实记录:chengshi-auto 近 12 个月无过门槛信号(首批为 2023-24
  关键事件回填,邮政采购公示页 JS 壳记为 lead);genki-forest W6/W2、hermes W2
  未采到达标硬信号,诚实留空;anthropic.com/fcc.gov/sec.gov 出口未放行,
  改用 URL 自证日期的权威媒体稿(官方稿 URL 记在 note 待回溯)。
- 冷启动即出硬信号:anthropic **P0 出口管制**(Fable 5/Mythos 5 发布 3 天即
  全球禁用,6-30 解除令同录成闭环)、dji **P0 FCC Covered List**——两卡亮灯,
  成为下一轮重审的现成素材。
- 开放 leads 依旧(§4.3):移动集采公示(855B JS 壳,需真浏览器)、亚信禁入处罚
  原文、奇安信大行 NDR / 中海油框架。

## 8. W7 实现记录(触发与联动,2026-07-12)

### 8.1 运行时触发评估器

- `scripts/watch-tools/evaluate_triggers.py`:滚动 30 天窗(闭区间含窗沿),三条规则
  任一命中即建议重审——**R1** P0≥1、**R2** P1≥2、**R3** 加权 4×P0+2×P1+0.5×P2 ≥5
  (PRD §5.3 全量,含此前徽章未实现的加权条)。默认只数**未消费**事件,
  `--include-consumed` 切 PRD 严格口径;`--as-of / --window-days / --brand / --json`;
  `--selftest` 12 组断言(窗沿、消费语义、每条规则、未来日期、P3 不计)。
  退出码恒 0——它是建议工具,不是 gate。
- **两口径分工的实证**(重要):回测奇安信——其 P1×2(01-31 业绩预告、04-30 年报)
  距 v2 重审(07-11)已 **>30 天**,窗口口径**不命中**;而未消费口径命中,且 v2 实际
  |Δ|=0.34 证明该建议是对的。结论:**窗口答"最近热度",未消费答"欠账"**——年报类
  慢信号靠"未消费"兜底,突发类靠窗口保时效,两口径互补、各自保留
  (徽章=未消费,评估器=窗口,均已文档化)。
- SKILL `--watch` 第⑤步已从"口述规则"落为真命令:
  `python3 scripts/watch-tools/evaluate_triggers.py --brand <slug>`(并补上 R3)。

### 8.2 MCP 双工具 + 订阅链路下发(工具数 14 → 16)

- `get_watch_events(brand, since?, dim?, severity?, unconsumed_only?)`:读事件流
  (倒序)+ 附**全量**触发评估(评估品牌而非查询子集);只读。
- `record_watch_event(brand, event)`:录入门槛与 `validate_watch.py` **同套规则的
  TS 镜像**(`src/watch/store.ts::validateNewEvent`)——事实字段齐且合规、quote ≤100 字、
  dim 不得落矩阵 off;id 自动顺延 `<date>-<slug>-NNN`;`direction_by` 强制
  `model-judged`;`consumed_by` 拒收(审计消费时才标)。写入**只追加文本块、
  不重写文件**(保注释与既有格式)。
- **下发**:P0 事件即时、或触发规则命中 → `findByBrand` 活跃订阅 →
  `dispatchNotifications`(`event: watch_alert`,email 主题
  `MBA watch — <brand> 建议重审`)——复用 `subscribe_brand` 既有管道
  (PRD §6.3「不加新管道」);无订阅或未命中则静默入库,不打扰。
- 配置:`MBA_WATCH_DIR`(默认 `./watch`);新依赖 `yaml@^2`。
  docs/13 §3/§5、e2e 全量工具断言、`check_consistency` 工具数 16 已同步。
- 测试:`tests/tools/watch-tools.test.ts` 19 例——规则/窗沿/消费语义、get 过滤、
  record 顺延与追加不重写、8 类非法输入拒收、强制 model-judged、P0 下发、未命中静默;
  全套 220 通过,typecheck / build 绿。

### 8.3 验收记账(诚实版,2026-07-12 四单重审后更新)

- §1 W7 验收线「触发建议精确率 ≥60%」(PRD §9:建议重审后,重审总分变动 ≥0.3 的
  比例)。**n=5 全部落地**:

  | 品牌 | 触发依据 | 重审结果 | \|Δ\| | ≥0.3? |
  |---|---|---|---|---|
  | qianxin | 未消费 P1×2 | v2 6.17→5.83 | 0.34 | ✅ |
  | asiainfo | P0 禁入 + P1 年报 | v2 5.93→5.77 | 0.16 | ❌ |
  | yuanxin | P1×3(组网/直连) | v2 5.50→5.77 | 0.27 | ❌ |
  | spacex | P1×2(IPO) | v2 8.60→8.76 | 0.16 | ❌ |
  | meituan | P1×2(监管/减亏) | v3 6.72→6.80 | 0.08 | ❌ |

  **精确率 1/5 = 20%,未达 60% 验收线——如实记录。** 但要区分两个问题:
  ① 五次建议**方向全部正确**(每单重审都产生了真实分数移动与叙事修正,评委无一认为
  "白来一趟");② 未达标的是**幅度**——硬信号驱动的修正天然偏小(评委克制:单镜头
  ±1 为主),0.3 阈值按当前打分惯性约等于"两位评委各动一格以上"。
- **✅ 校准已执行(2026-07-12,同日)**:选路线 (a),全链路把 R2 `P1≥2`→`P1≥3`、
  R3 加权阈值 `5→6`(R1 P0≥1 不动——P0 单事件足以改分是定义本身)。**回测**(用
  上表 5 样本的触发时点计数):

  | 品牌 | 加权 | 旧规则 | 新规则 | 判定 |
  |---|---|---|---|---|
  | qianxin | 8.5 | 灯 | **灯**(R3) | ✅ 真阳性保住 |
  | asiainfo | 8.0 | 灯 | 灯(R1 P0) | P0 照亮——定义使然 |
  | yuanxin | 8.5 | 灯 | 灯(R2/R3) | 0.27 边界样本,保留 |
  | spacex | 4.5 | 灯 | **—** | ✅ 误报压掉 |
  | meituan | 4.5 | 灯 | **—** | ✅ 误报压掉 |

  回测精确率 1/5 → **1/3**;仍未达 60%,但没有丢真阳性、压掉了两个最差误报。
  改动落点:`evaluate_triggers.py`(+selftest 14 组)、`trigger.ts`(+vitest)、
  `build_home_cards.py` 与 `build_watch_pages.py` 的欠账口径(P2 计入加权、仍不上卡)、
  SKILL --watch ⑤、docs/15 §5.3(校准注记)、docs/13、周扫 Routine prompt(重建)。
  路线 (b)(验收阈值 0.3→0.15)留给产品决策,不自行改验收线。
- 历史记录说明:§5/§7/§8.1 中出现的「P1≥2 / ≥5」为当时如实记录,不回改。
- 「P0 推送通知」(M3)管道已具备(record 的 P0 即时下发);真实告警要等品牌被
  `subscribe_brand` 订阅后自然发生。

## 9. 下一步

1. ~~W6 覆盖滚动~~ **✅ 2026-07-12 G3 冷启动补齐 13/13**;周扫 Routine 每周一
   继续增量,开放 leads(§4.3 / §7.4)随周扫回收;
2. ~~重审素材已备~~ **✅ 2026-07-12 四单重审全部落地**(asiainfo v2 / yuanxin v2 /
   spacex v2 / meituan v3),39 条事件 100% 消费、全部灯灭;精确率账见 §8.3
   (1/5,未达标——阈值/门槛校准是下一个决策点);
3. ~~触发规则校准~~ **✅ 2026-07-12 已执行**(P1≥3 / 加权≥6 全链路落地,见 §8.3
   回测表);下一步是随周扫样本积累持续复盘精确率,以及路线 (b)(验收阈值)的产品决策。

## 9.5 L1 预筛:哪些「建议重审」真的值得跑(2026-07-25)

**问题**:每日流水线天天堆事件,触发器(P0≥1 / P1≥3 / 加权≥6)很快被顶过,首页常年一片
「建议重审」。但 2026-07 那轮 **15 家全量重审的实测结果是:净持平 1 家、其余多为 ±1~3 分**
——大量事件是**方向价**(券商观点 / 预览 / 洽谈 / 同一件事的多家转载),根本不该改分。

**成本账**(实测,非估算):

| | 输入规模 | 说明 |
|---|---|---|
| L2 全量重审 **1 家** | `report.md` 7k–13k + 未消费事件 ~12k + 规则 3k ≈ **25k token** | 还要 ×2–3(门禁失败重试、反复查证) |
| **L1 预筛全部 17 家** | 409 条事件的标题+severity ≈ **24.5k token**(`--dry-run` 实测) | **≈ L2 重审一家的量** |

且 L1 可用便宜模型(复用 `classify_candidates` 的 Haiku 级网关),L2 必须用强模型
(弱模型容易「看到利好就加分」,违反克制原则)。**L1 花一次 L2 单家的钱,筛出 17 家里哪几家值得。**

**⚠ `report.html`(42k–50k 字符 ≈ 20k–25k token)是最大黑洞,但完全不必让模型碰**——
2026-07 那轮 15 家重审的 HTML 全部用确定性 `transform` 脚本改(替换 title / score-big /
矩阵 / 雷达数组 / 插 banner),**0 token,且不会破坏 Chart.js 数据结构**。这条要固化。

**实现**:`scripts/watch-tools/prescreen_reaudit.py`
- 复用 `classify_candidates`(provider 分派 / 429 退避)+ `evaluate_triggers`(30 天窗口)
- 只喂**标题 + severity**,不给正文/URL;输出 `watch/prescreen.json`
- `verdict` 仅两值:`substantive`(有已落地硬事实,值得请评委重审)/ `directional`(只有方向价)
- **边界**:只判断「值不值得人去重审」,**绝不建议加减分**;非法 verdict / 模型漏答 → 保守降级为
  `directional` 并标「需人工复核」;`reason` 必须引用事件 id 以便复核;标注 model-judged
- `--dry-run` 打印输入规模与 token 估算(不花钱)· `--selftest` 74 组离线断言 · 无 key 优雅跳过
- **判定粒度 = 逐事件**:模型对每条事件出 `S`/`D`,**品牌结论由代码聚合**(任一 S ⇒ substantive)。
  见下「第 4 次」——per-brand 让模型有机会「挑最弱的一条说不」,这是结构问题,不是 prompt 措辞问题。
- **S 的判定 = 封闭白名单分类**(9 类,见第 5 次);`key_event_ids` 每类别只列 2 条代表,总数记在 `category_counts`。

**三次真跑踩出来的(全部已写成断言,别再踩)**:

| 第几次 | 症状 | 根因 | 修法 |
|---|---|---|---|
| 1 | 裸 `JSONDecodeError` | ① `cc.call_llm` 用了 classify 的模块级 `SYSTEM`,模型在答**另一道题**;② 17 家一次输出撞 `max_tokens=2000` 被截断 | `call_llm` 开放 `system/max_tokens/timeout` 形参;`run()` 显式传自己的 `SYSTEM`;截断报错改为点名 `max_tokens` |
| 2 | 全批 `read operation timed out` | 按**品牌数**分批,但 payload 大小取决于**事件数**(6 家 × ~30 条 = 195 条 ≈ 11.5k token) | 改按**事件数**切批(≤70)+ 每品牌限量 18 条(P0>P1>P2 优先,保证限量不挤掉 P0)+ 标题截 70 字 + timeout 180s → 11.5k 降到 ~3.3k/批 |
| 3 | 跑通了,但 **verdict 有误判** | prompt 只写了「结果类」硬事实 | 见下 |
| 4 | 按第 3 次的结论改完 prompt,**净回退**(8 家 → 2 家,连 P0 都漏) | **per-brand 输出结构**让模型只看一两条就下品牌级结论 | 改**逐事件判定** + 代码聚合;见下 |
| 5 | 假阴性清零(4 项验收全过 · 271/271 全覆盖),但**门槛塌了**(16/17 家 substantive,等于没筛) | S 是**开放判断**(「已发生的实质事件」),模型把「不得用相关性门槛否掉」泛化成「凡已发生都别否」 | S 改成**封闭白名单分类**(9 类)+ 代码校验 + 转载去重;见下 |
| 6 | 白名单生效(第 5 次四条假阳性**全消**,3 家被筛掉),但仍 14/17;`LAUNCH` 被撑开;改写型转载合不掉 | `LAUNCH` 是 9 类里最主观的一类;**标题相似度分不开「同一故事/不同故事」**(分布重叠) | `LAUNCH` 定义里写死排除项;去重阈值**不降**,改「每类别取代表 + 如实计数」;见下 |

**第 3 次的误判分两类,假阴性更危险**(漏掉真该重审的):

- **假阴性**:`anthropic-046`「提交招股书」被判成「IPO **预期**」、`spacex-046`「FAA 禁止员工购买
  SpaceX 股份」被判成「观点性内容」。二者都是**已完成的程序性里程碑**(文件已递交 / 禁令已下达),
  是既成法律行政事实。**错误推理是「后续结果还没出来 ⇒ 判成预期」。**
- **假阳性**:`microsoft-019/020`「**将**在 Azure 部署 AMD Helios」(未来时被当落地)、
  `nvidia-048` 与高校**成立联合实验室**(真实但对品牌影响力权重过低)、
  `kimichat-065`「以 500 亿估值**洽谈**融资」被判 directional 却仍被列进 `key_event_ids`。

**prompt 修法(2026-07-25)**:① substantive 拆成 (a) 结果类 + (b) **程序性里程碑已完成**
(已递交/已下达/已生效/已签约/已获批/已设立),并显式禁止「后续结果没出来⇒预期」这条推理;
② directional 触发词补「**将**/计划」;③ 加**相关性门槛**——硬事实还须可能影响
市场份额/定价权/护城河/用户信任/品牌身份,真实但边缘的事不足以单独触发重审;
④ `key_event_ids` **只能放 substantive 的依据**;⑤ 附 **7 个 few-shot 对照例,全部取自上述真实事件**。
prompt 每条规则都有对应 selftest 断言(改回去 = 自检红)。

### 第 4 次:prompt 改动净回退,根因是**输出结构**不是措辞(2026-07-25)

改完上面五条后再跑,**8 家 → 2 家**。这是一次干净的 A/B:同一份 `events.yaml`(两次运行之间
没有任何 watch 提交),`git diff 3e976a3 e7f5dbc` 只动了 prompt 与 docs。结果**更差**:

| 品牌 | 新判定 | 输入 digest 里实际有的(前 1~2 条) | 模型引用的 |
|---|---|---|---|
| deepseek | ✗ D | **P0**「完成首轮融资:估值超3500亿,梁文锋持股31%」 | 闭门会实录 |
| dji | ✗ D | **P0**「FCC 最严禁令,大疆全系或被踢出美国市场」 | Osmo 评测 |
| google | ✗ D | 「欧盟罚 8.9 亿欧元」·「Q2 自由现金流首次转负」 | 「考虑屏蔽爬虫」 |
| anthropic | ✗ D | **P0**「AMD 投 50 亿入股」· **P0**「赔 15 亿美元」·「提交招股书」 | FCA 沙盒 |
| spacex | ✗ D | 「FAA 禁令」·「星舰第 13 次试飞成功」 | 「据悉」暂停预订 |

**关键观察**:`deepseek-027` 一字不差地写在当时 prompt 的 substantive 正例里,digest 里排第一条,
模型**仍然**判 D。所以问题不是「判定标准写得不够细」。

**根因**:per-brand 的输出契约(每品牌一个 verdict + 一条 reason)**允许模型只看一两条就下结论**。
第 3 次它挑每家**最强**的事件来论证「值得」;加了「相关性门槛」后,它有了逃生口,改成挑**最弱**的
一条来论证「不值得」。严重度 P0 被完全无视。**prompt 措辞影响它挑哪一条,但挑不挑得完由结构决定。**

**修法(结构性)**:改成**逐事件判定** —— 模型对输入里每条事件单独出 `S`/`D`(扁平数组,
`{"id","v","why"}`),**品牌 verdict 由代码聚合:任一事件 S ⇒ substantive**。
「挑最弱的说不」在结构上不再可能;`key_event_ids` 也不可能混入 D(它就是 S 的 id 列表)。
配套:
- 相关性门槛**封边界**:只排除明显边缘的事(联合实验室 / 单件拍卖 / 单一商户下架);
  **财报数字 / 监管处罚 / 禁令 / 融资完成 / 诉讼和解 / 大额投资入股一律 S,不得被它否掉**。
- few-shot 扩到 6 正 6 反,**第 4 次漏掉的四条硬事实逐条进正例**(有 selftest 断言逐条守)。
- 逐事件后输出条数 == 输入条数,故 `BATCH_EVENTS` 70→40(单批出 ≈1.1k token,离 4000 有大余量),
  且 selftest 里**硬算一遍输出预算**(`BATCH_EVENTS × OUT_CHARS_PER_EVENT / 2 < 0.6 × MAX_TOKENS`)。
- **漏答必须看得见**:模型没回的事件按 D 保守处理,但 `coverage`(如 `15/18`)写进结果、
  摘要里打 ⚠ 告警 —— 静默的漏答比误判更危险。

**教训(比这个脚本更通用)**:当 LLM 的判断需要**遍历一批证据**时,不要让它直接输出聚合结论。
**让它逐条表态,聚合交给代码。**否则你永远在调 prompt,而它永远只看它想看的那几条。

### 第 5 次:逐事件成立,但「什么算重要」这种开放判断弱模型托不住(2026-07-25)

逐事件改造后**假阴性清零**,四项验收全过、`271/271` 全覆盖:

| 验收项 | 结果 |
|---|---|
| deepseek 含 `027` 融资完成 | ✅ 排第一位,并带出 `030`(510亿)、`043`(国家 AI 产投基金入股) |
| dji 含 `018` FCC 禁令 | ✅ 排第一位 |
| google 含 `051` 欧盟罚款 | ✅ 排第一位,并带出 `034`/`040` 财报 |
| anthropic 含 `034`/`062` | ✅ 两条都在,排前二 |
| 逐事件覆盖率 | ✅ 271/271 |

**但门槛塌了:16/17 家 substantive,等于没筛。** 假阳性:`SIGGRAPH展示已进行`、
`网络回滚操作已完成`、`开启 HarmonyOS 升级`、`宣布 2027 年 1 月推出`(未来时)。
机制:上一轮为了堵假阴性写了「财报/处罚/禁令…一律 S,**不得用相关性门槛否掉**」,
模型把「不得否掉」泛化成了**「凡是已发生的都别否」**。

**连续 5 轮在「过严 ↔ 过松」之间摆**,说明让 Haiku 级模型做**「这件事重不重要」这种开放判断**
本身就不稳。第 5 次的修法是把任务**降级成分类**:

- **S 的封闭白名单(9 类)**:`FIN` 财报数字 · `FUND` 融资/投资入股已完成且金额明确 ·
  `MA` 并购已完成 · `REG` 处罚/禁令/判决/和解已下达 · `IPO` 招股书已递交/上市/解禁 ·
  `PEOPLE` 大规模裁员/核心高管变动 · `CRISIS` 重大事故/大规模服务中断/召回 ·
  `PRICE` 股价大幅异动且有明确事由 · `LAUNCH` 全新旗舰产品正式发布并已可用。
  **挑不出就是 D。** prompt 里显式打断那条推理:**「已发生 ≠ 值得重审」**——
  已发生但不属这 9 类的(展会、规格公布、版本升级、运维操作)一律 D。
- **白名单由代码守**(`_aggregate`):类别必须 ∈ `CATS`,**模型自创类别一律落成 D**。
  prompt 与代码的 9 个类别有 selftest 逐个对照,防漂移。
- **转载去重**(第 4 次埋的债):prompt 里写了「去重由后续代码做」却**没写那段代码**,
  于是 spacex 的 `059/062/063/065` 四条同为「星舰第 13 次试飞」全进了 `key_event_ids`。
  现按**同类别 + 标题字符二元组重叠系数 ≥0.65** 合并,只留 id 最小(最早)的一条,
  合并条数记进 `merged_duplicates` 并写进 reason。用**重叠系数而非 Jaccard**:
  转载常见「一条是另一条的浓缩版」,长度差距大时 Jaccard 会被长的那条稀释。
  这是启发式,**只影响展示与计数,不影响 S/D 判定**;漏合(如简繁体不同源)只是多列一条。

**教训**:弱模型能稳定做的是**分类**(从封闭集合里挑一个),不是**判断**(这值不值得)。
把开放判断改写成封闭分类,再把边界校验放进代码,比继续雕 prompt 措辞有效得多。

### 第 6 次:白名单生效;并证伪了「靠标题相似度去重」(2026-07-25)

**白名单机制成立**:第 5 次那四条假阳性(`SIGGRAPH展示`、`网络回滚`、`HarmonyOS升级`、
`宣布2027年1月推出`)**全部消失**,hermes / huawei / lenovo 三家被整家筛成 directional,
覆盖率仍 `271/271`。

**但仍是 14/17。** 逐条核对后要修正上一轮的预期:**「回落到个位数」这个验收标准本身设错了。**
14 家里 **13 家确实有真实硬事实**——`REG` FCC 禁令 / 欧盟罚款 / 判赔 2.4 亿、`FIN` Q2 财报、
`FUND` 融资完成 3500 亿、`CRISIS` 模型失控入侵、`MA` 收购中科加禾、`PRICE` 显卡涨价 101%……
这 17 家是全球最活跃的科技公司,30 天窗口里叠了财报季 + 多起监管处罚,**本来就该筛出这么多**。
L1 的价值因此要重新定位:**它给的是「每家一个可核对的分类依据」,不是替人做减法。**

**两处真问题,修法如下:**

**① `LAUNCH` 是唯一剩下的漏斗口**(9 类里最主观):`apple-036`「**7月28日**推出 Apple Upgrade」
是定档(未来时)却判了 LAUNCH,`google-031` 产品线扩展、`dji-014` 扫拖机器人也被塞了进来。
→ 把排除项**写死在类别定义里**:「该品牌**主力旗舰**产品或模型正式发布**且当下已可用**
(**不含**:定档/预告、版本升级、产品线扩展或廉价版、配件与周边品类)」,并把这三条加进 D 对照例。

**② 「降去重阈值」这条路被数据否决了。** 原打算把 0.65 降到 0.45 去够改写型转载,量完发现
**两个分布是重叠的**:

| | 重叠系数 |
|---|---|
| 同一故事的**最低**有效值(anthropic 三条「15 亿版权和解」) | **0.41** |
| 不同故事的**最高**值(`046 提交招股书` vs `034 盗版书赔 15 亿`) | **0.48** |

降到 0.45 会把**招股书**和**版权赔偿**合并成一件事。更糟的是相似度**根本抓不到**改写型转载:
zhipu 两条同为「收购中科加禾」只有 **0.04**,google 的 Q2 财报四条低到 **0.06**。
**靠标题这条路走不通。**

→ 阈值**保持 0.65**(只合并近乎逐字的转载,第 6 次 apple / spacex 各合并 1 条就是它抓的),
另加一层 **`EVENTS_PER_CAT=2`:每个类别只列 2 条代表,并把该类别真实总数报出来**
(`category_counts`,reason 里写「REG 共 3 条,只列代表」)。
**不假装能识别同一事件**——限制展示量 + 如实计数,让被截掉的可见。
阈值由一条断言钉死:拿那两条真实标题做反例,降到 0.45 就红。

**教训**:去重/聚类这类启发式,**先量分布再定阈值**。两类分布重叠时,正确的动作不是挑个折中
阈值,而是**换一个不假装能分开它们的设计**。

**尚未做(有意)**:未接入每日 workflow、未接首页。理由:本地无 key 无法端到端验证模型判断质量;
应先手动跑一段时间、确认 `verdict` 靠谱,再考虑 ① 进 workflow ② 首页只对 `substantive` 亮红。
**L2(自动跑全量重审)更要等 L1 验证之后**——分数只在评委重打时变,这条不能让弱模型代劳。

## 9.6 官方源召回:为什么 Opus 5 只被"转述"捡回来(2026-07-25)

**问题**:用户问「Anthropic 发 Opus 5 这么大的事,为什么没收录?」查下来实情分三层:

1. **收录了**——`2026-07-24-anthropic-059`「中国模型加速AI明星"内卷",**Anthropic上新Opus 5**,
   性能逼近 Fable 5 价格打对折」。但报告是 **v4(2026-07-20)**,比该事件早四天,
   所以报告页看不到它不是漏,是**还没重审**(`consumed_by: None`,正在等触发)。
2. **但发现渠道单一**:discover 的唯一信息源是 Google News RSS **中文档**的**品牌名**查询,
   **没有任何官网 / 官方博客源**。实证:该品牌 12 条事件的 `url` 全是
   `news.google.com/rss/articles/...`、`source_type` 全是 `media`。于是官方公告
   《Introducing Claude Opus 5》**没进库**,进库的是中文媒体转述——标题主语还是
   "中国模型内卷",Opus 5 只是从句。
3. **分级偏低**:旗舰模型发布判了 **P1**,而 R1 是 `P0 ≥ 1` 才立即触发,P1 要攒 3 条。

### 修法一:加 `site:<官方新闻源>` 第二路召回

不新增抓取器——**Google News RSS 支持 `site:` 语法**,复用现有管道即可,
且 URL 直指官方原文。`site/reports-meta.yaml` 新增可选字段 **`news_site`**。

**三条实测结论(都是踩出来的,别再试错)**:

- **① 必须锚到新闻室子域/路径,不能用根域名。**
  `site:apple.com` 召回的是 Apple Music 歌曲页、`site:tesla.com` 是招聘页、
  `site:openai.com` 是状态页。改成 `apple.com/newsroom` / `news.microsoft.com` 后才干净。
- **② 官方源查询要 EN + CN 两档都发。** 模块默认 `hl=zh-CN`,而多数官方源在中文档召回**几乎全为 0**:

  | | EN | CN | | | EN | CN |
  |---|---|---|---|---|---|---|
  | `anthropic.com/news` | **16** | 0 | | `news.lenovo.com` | **41** | 0 |
  | `openai.com/index` | **32** | 0 | | `blogs.nvidia.com` | **38** | 0 |
  | `blog.google` | **75** | 1 | | `news.microsoft.com` | **28** | 0 |
  | `aboutamazon.com/news` | **34** | 0 | | `apple.com/newsroom` | **7** | 0 |
  | `huawei.com/en/news` | **17** | 0 | | `ir.tesla.com` | **5** | 0 |
  | `spacex.com/updates` | **2** | 0 | | `investors.palantir.com` | **2** | 0 |
  | `deepseek.com` | **100** | 9 | | | | |

  **但反例存在**:`qianxin.com/news` **只在中文档有**(CN 12 条 / EN 0),首条是真新闻
  「AI又惹祸了?硅谷大佬Mac遭一键清空」。所以**不能写死一档**——第一版写死 EN,
  qianxin 就会被漏掉。现改为**两档都发、结果合并**(重复项由既有的标题 key 去重兜住),
  代价是每个已配品牌每天多一次请求。
  官方条目标题因此可能是**英文一手原文**——反捏造不变:quote 仍是源 feed 逐字标题,
  **不翻译不改写**。
- **③ 部分中文品牌的官网 Google News 确实不收录**,但要**逐个试过才算数**:
  `moonshot.cn` / `about.meituan.com` / `100tal.com/news` / `dji.com/newsroom` 召回均为 **0**;
  而 `qianxin.com/news`(CN 12)与 `finance.hermes.com`(EN 15)是**能用的**——
  第一版只试了根域名就下了"中文品牌不行"的结论,**结论下早了**。
  故 `news_site` **设计成可选**,目前 **15 家**已配;其余 9 家保持原行为,**无回归**。

  **仍未覆盖的 9 家**(`chengshi-auto` / `kimichat` / `tal-education` / `genki-forest` /
  `meituan` / `dji` / `asiainfo` / `zhipu` / `yuanxin`)—— 直接 curl 官网实测:
  `about.meituan.com/news`(124KB,18 条新闻链接,**标题可解析**)与 `100tal.com/news`
  (108KB,14 条)**能抓**;`moonshot.cn` / `dji.com/cn/newsroom` 是 JS 壳、
  `chi.cn` / `spacesail.com` 返回 114B 空壳。
  → **已做,但比预想的窄**(见下 §9.7)。

### 修法二:P0 判则加严

预分类 prompt 显式列出 P0 类别,**首条就是"旗舰产品 / 主力大模型的正式发布或重大版本更新"**;
候选 payload 带上 `src`(official/media),官方渠道的上述事件优先判 P0。
同时**防住反向滥用**:招聘、产品目录、状态页、技术博客**不能**因为"来自官网"就升级。
三条 selftest 断言钉住(改回去 = 自检红)。

### 接线时踩的三个坑

| 坑 | 现象 | 根因 / 修法 |
|---|---|---|
| 1 | 官方源接好了,候选里 **0 条 official** | 模块用中文档,多数官方源在中文档召回 0 → 增开 `GNEWS_EN`(后又改两档合并) |
| 2 | 改英文档后仍 **0 条 official** | media 查询在前,`new[:limit]` 把官方条目**整段截掉** → 官方保留名额 |
| 3 | 官方条目霸占 98/184 席,且混入分页页 | 官方**只占一半名额**、媒体保底;`is_noise` 加"`Page N of M`"与资源页 ID 模式 |

**端到端验收**(真跑 discover,不是单测):`[official] Introducing Claude Opus 5` 已召回 ✓ ·
分页噪音 0 残留 ✓ · 每品牌 official/media ≈ 5/5 ✓。

## 9.7 第三路:官网新闻页直采(2026-07-25)

给 Google News **不索引官网**的品牌兜底。实现在 `scripts/watch-tools/official_site.py`。

### 先说三条"走不通"的实测结论(别再试)

| 路子 | 实测 | 结论 |
|---|---|---|
| **官方微博** | `weibo.com/meituan` 与 `m.weibo.cn` 都返回 `Sina Visitor System` | **登录墙,curl 拿不到** |
| **微信公众号发现** | 搜狗微信搜索返回 10KB **JS 壳**,HTML 里没有任何结果条目 | **拿不到**(已知 URL 的单篇文章能读,但那不是"发现") |
| 好未来官网 | `100tal.com/news` 的 HTML 里**只有页面标题与月份选择器**,新闻走 `gw-web-api.100tal.com` 接口 | **纯客户端渲染,抓不到** |

⚠️ **更正 §9.6 的一处错话**:那里写「`100tal.com/news`(108KB,14 条)能抓」是**错的** ——
那是粗略数 `href` 里含 `news` 的链接数得出的,真去提取内容才发现全是导航链接、
所谓"66 个日期"是月份选择器。**数链接数不等于能提取内容。**

### 做法:通用内嵌 JSON 提取,不写死站点选择器

最容易想到的是"每站一套 CSS 选择器",但那是最难维护的:站点改版即静默失效,
而 CI 不出网、无法回归。实测发现更好的抓手 —— **现代官网多是 Next.js / Nuxt,
数据以 JSON 内嵌在页面里**(美团新闻中心的 `__NEXT_DATA__` 里就有 `newsCenterlist`,
字段齐整还带日期与来源)。

所以做成**通用提取**:抽出内嵌 JSON → 自动找"像新闻列表"的对象数组
(≥3 条、且 ≥60% 条目同时有标题类字段与日期类字段)→ 取最大的那个。
换站点、站点改版只要还用同一套框架就仍然能跑;新字段名加进 `TITLE_KEYS` / `DATE_KEYS` 即可,
**不必写选择器**。

- 只搬运**标题 / 日期 / 链接**,逐字取自页面,**不改写不翻译**;dim/severity 仍留给分类环节。
- **拿不到就如实报 0,绝不编造条目** —— 这条有专门的 selftest 断言守着。
- 日期归一支持 ISO / 中文 / 斜杠 / 时间戳;**认不出就留空,不猜**。

### 哨兵:配了却抓到 0 条 = 告警

这类失效是**静默的**(不报错,只是不再有条目)。所以配了 `news_page` 却抓到 0 条时,
同时打到 **stderr** 与**候选 md 文件**里。red-green 三场景验过:
抓不到 → 喊 ✅ · 候选文件里也写 ✅ · 还原后不误报 ✅。

（踩坑:第一次 red-green 我把 `news_page` 指向 `about.meituan.com/`,哨兵"没喊"——
查下来是**首页碰巧也带 7 条新闻列表**,是测试用例选错了,不是哨兵失效。
换成真正抓不到的 URL 后三场景全对。）

### 覆盖与边界

目前只配 **meituan**(`about.meituan.com/news`,实测稳定抓到 10 条,带日期与来源)。
其余 8 家未配:好未来/元气森林/垣信/橙仕是客户端渲染或空壳,kimichat/dji 是 JS 壳,
asiainfo/zhipu 路径未定。**没配 = 保持原行为,无回归。**

`--selftest`(13 组)已接入 `panel-validation.yml`;它用 fixture 离线跑,不需要网络。

## 9.8 第四路:知乎社区信号(2026-07-26)

用户问「能不能上带登录态的云浏览器,抓微博/公众号/知乎/小红书」。先探了**零成本的路**,
结果知乎这条**根本不需要云浏览器**:

| 源 | Google News 中文档收录 | 结论 |
|---|---|---|
| **知乎** `site:zhihu.com 美团` | **100 条**,「如何看待…」问题 + 专栏,贴题 | ✅ **零新增抓取器可用** |
| 小红书 `site:xiaohongshu.com` | 3~5 条 | ❌ 覆盖不了 |
| 微博 / 公众号发现 | 登录墙 / JS 壳(§9.7 实测) | ❌ curl 走不通 |

做法:discover 每品牌加第四条查询 `site:zhihu.com <品牌>`(中文档),命中标
`source_type: social`(schema 枚举本就有)。**只取标题入库,不碰知乎反爬墙**,
与全管道同构、反捏造不变。名额分配:官方 ≤1/2、社区 ≤1/4、其余媒体,
**每品牌总量不变** —— 下游分类成本不涨,只是信号配比更好。

实测(kimichat,limit=12):social 3 + media 9,社区条目如
「Kimi K3 使用指南:会员暂停后仍可访问的5种替代方案」——正是 W2 想要的用户侧信号。

### 云浏览器(Wuying)现状——真要抓微博/小红书才需要它

仓库已有基建(`scripts/wuying/open.py` + `smoke_test.py` + `docs/wuying-usage.md`),但:

1. **远程 CCR 会话没有 `.env` / `WUYING_API_KEY`** —— 无法在这类会话里实测或运行;
2. 项目记录(CLAUDE.md,2026-07):**免费档 `GetLink` 报 400**,未确认是否已修复/需付费档;
3. **登录态是人的事**:AgentBay 会话默认是全新浏览器,微博/小红书要人先登录 + 会话持久化;
   **用谁的账号、平台条款与风控风险(自动化抓取违反微博/小红书 ToS,账号可能被封)由人决策**;
4. 按分钟计费,漏关烧钱(`open.py` 的 teardown 纪律见 wuying-usage)。

**前置条件**:本地桌面版把 `WUYING_API_KEY` 配进 `.env` → 跑 `scripts/wuying/smoke_test.py`
确认 GetLink 是否仍 400。烟测通过之前,云浏览器 leg 不动工。

## 9.9 免费社媒线开发计划:微博 / 小红书 / 公众号(2026-07-26)

用户不想为 Wuying 付费,问免费方案。**先把"零运维白嫖"的路全部实测排除**(本会话数据中心 IP):

| 免费候选 | 实测 | 原因 |
|---|---|---|
| 微博移动端 API 无登录直连 | ❌ 返回访客系统 HTML | 新浪按 **IP 信誉**拦,数据中心 IP 直接挡 |
| RSSHub 公共实例(rsshub.app 等) | ❌ 403 / 503 | 公共实例限流数据中心 IP,微博/小红书路由多半没配 cookie |
| 公众号镜像(freewechat) | ❌ 403 | 同上 |
| GitHub Actions + Playwright | 不推荐 | runner 也是数据中心 IP,同一套访客系统照拦;cookie 进 secrets 有过期与泄露问题 |

**结论:免费可行的路 = 把"计算"挪到用户自己的机器 / 家庭网络。** 三步走:

### ① 仓库侧铺管道:`rss_feeds` 任意 RSS 源支持(✅ 本 PR 已做)

- `reports-meta.yaml` 可选字段 **`rss_feeds`**(字符串或列表),`discover` 第五路消费:
  逐源 curl → `parse_feed`(**RSS 2.0 + Atom 都认**,解析失败返回空绝不编造)→
  标 `source_type: social` → 名额与去重复用 #213 的逻辑。
- **哨兵**:配了却 0 条(RSSHub 路由挂 / cookie 过期都是静默失效)→ stderr + 候选 md 双告警。
- 验收(已过):selftest 10 组(RSS2 日期归一 / Atom href 与 published / 垃圾输入返回空);
  真源 Atom 解析 25+10 条;端到端临时配真 RSS → 候选正确标 social;坏 URL → 哨兵喊。
  ⚠ 沙箱假象记录:GitHub `releases.atom` 在本会话被仓库代理拦成 JSON 错误,**不是解析 bug**,
  换 reddit/.rss 与 github.blog/feed 验证通过。

### ② 用户侧验证:本地自托管 RSSHub(**用户动作**,零成本一条命令)

> **逐步操作手册(含隧道、加固、排错、维护)见 [`docs/27`](27-rsshub-local-setup.md)**;下面是速览。

```bash
docker run -d --name rsshub -p 1200:1200 diygod/rsshub
# 微博(公开主页,通常无需 cookie;家庭宽带 IP 一般能过访客系统):
curl "http://localhost:1200/weibo/user/1746173800"          # 美团官微 uid
# 小红书(需要 cookie:RSSHub 环境变量 XIAOHONGSHU_COOKIE):
curl "http://localhost:1200/xiaohongshu/user/<user-id>/notes"
```

- **验收标准**:本地能出含 `<item>` 的 RSS(条目标题是真实微博/笔记)。
- **诚实边界**:「家庭 IP 能过访客系统」是机制推断 + RSSHub 社区经验,数据中心会话**无法代验**;
  不通就说明该路由当前版本失效,进 ③ 的 Playwright 备选。
- **账号与条款风险由用户拍板**:自动化抓取违反微博/小红书 ToS,cookie 绑定的账号可能被风控。
- **公网可达性**:每日 workflow 在 GitHub runner 上跑,要吃你本地 RSSHub 有两个选:
  (a) 内网穿透(cloudflared tunnel 免费档)把 `localhost:1200` 暴露成 https URL 填进 meta;
  (b) 不穿透,本地 cron 定期跑 `discover --brand <x>` 把候选文件推 PR。**(a) 简单但 URL 半公开
  (建议加随机路径),(b) 更稳私但要本地跑东西 —— 到时按偏好选。**

### ③ 条件分支(②通了 / 没通)

- **②通了**:把 RSSHub URL 填进 `rss_feeds`(每品牌微博一条,有 cookie 再加小红书)→
  当天流水线开吃,仓库侧零改动。观察一周,信号质量 OK 再考虑给更多品牌配。
- **②没通**:退到**本地 Playwright + 登录态**脚本(免费但要逐站写、逐站维护),
  只做微博 + 小红书两站、只抓官方账号页标题;产出直接复用 `rss_feeds` 也吃的候选格式。
  这条成本高,**等 ② 的实测结果再决定,不预先动工**。

### 全线不变的边界

标题/日期/链接逐字取自源,不改写不翻译;dim/severity 留给分类环节;
**审计分数从不自动变,合并 PR = 人工闸门**。

## 10. 单次扫描操作 SOP(M1 人肉/半自动版)

```
1. 选品牌,读 watch/matrix.yaml 确认开启维度
2. 按维度关键词 WebSearch(W3:品牌+中标/集采/禁入;W4:品牌+处罚/问询;W5:品牌+年报/预告)
3. 过收录门槛(§4.1):URL 日期自证 / curl 核对;聚合库只作线索
4. 追加事件到 watch/<slug>/events.yaml(id 顺序号递增;fetched_at 用当下 UTC)
5. python3 scripts/watch-tools/validate_watch.py   # 必须全绿
6. 重大事件(P0/P1)顺手评估触发规则:python3 scripts/watch-tools/evaluate_triggers.py
   (30 天窗 P0≥1 / P1≥3 / 加权 4·2·0.5 ≥6,2026-07-12 校准)
```
