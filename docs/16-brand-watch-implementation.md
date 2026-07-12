# 16 — 品牌舆情监控实现与过程记录(Brand Watch Implementation)

> Status: **M1 完成 · M2 首项落地**(W1-W4 ✅,W5 ✅)· Last verified: 2026-07-12
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
| **W6** | 定期采集(M2) | CCR Routines / cron 周扫,按矩阵扫开启维度 | 13 品牌适用维度覆盖 ≥80% | 🟡 2026-07-12 基建落地:周扫 Routine 已建 + 演练扩覆盖 3→5 品牌(见 §7);**覆盖率 5/13 未达标**,靠周扫滚动逼近 |
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

### 2.2 事件 schema(相对 PRD §5.1 的两处实现增补)

PRD schema 原样落地,增补两点(均为实操中发现的需要):

1. **`quote_type: title | body`(可选,缺省 body)** —— 采集实操发现:搜索结果的
   AI 摘要**不是逐字原文**,不能当 quote;但**标题是逐字的**。故允许 quote 取源文章
   标题并显式标注 `title`;`body` 类引用则要求先 curl 原文核对。这保住了
   「quote 必须逐字」的反捏造底线,同时让无法 curl 的源也能入库。
2. **URL 自证日期原则(SOP,非 schema 字段)** —— 优先收录 **URL 内嵌日期**的源
   (如 `…/article/20240117/…`、`…/2025-04-07/…`):日期不依赖任何转述,
   事件的 `date` 可被 URL 直接核对。首批 15 条事件全部满足此原则
   (唯一例外 ithome 一条,已 curl 原文核对正文日期,见 §4.2)。

### 2.3 校验器检查项(全部静态,CI 不出网)

- **A 溯源结构**:必填字段齐全;quote ≤100 字;url 为 http(s);fetched_at 为 ISO UTC。
  (quote 是否逐字命中原文属**抽检 SOP**,不进 CI —— 网络校验 flaky。)
- **B 判断/事实分列**:`direction_by` 恒为 `model-judged`;dim/severity/direction/
  lens_map 枚举合法;`id` 格式 `<date>-<slug>-NNN` 且日期与 `date` 一致、全局唯一。
- **C 矩阵对齐**:`matrix.yaml` 品牌集合 == 发布白名单(**新发布品牌必须补矩阵行**,
  这把「监控台每个品牌都有舆情配置」变成了机器强制);事件的 dim 在该品牌上不得为 off。
- **`--selftest`**:12 组断言,每类违规造一个假样本证明会被抓(与
  `quality_check --selftest` 同一哲学:门禁要自证有牙)。

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

- trigger id `trig_015tVDnBhwsD7wLdeiczBPVT`,cron `0 1 * * 1`(UTC,即北京时间
  **每周一 09:00**),每次触发**新开会话**独立执行(不依赖任何旧会话上下文)。
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

### 7.4 验收记账(诚实版)

- §1 的 W6 验收线是「13 品牌适用维度覆盖 ≥80%」——当前仅 **5/13 品牌**有事件流,
  **未达标**。本次落地的是"定期"本身(Routine + SOP 固化 + 演练跑通),覆盖率
  靠周扫逐轮逼近,自下轮起在本节记账。
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
- **校准结论(留给后续)**:两条路二选一或并行——(a)调紧触发门槛(如 P1≥2 升为
  P1≥3 或引入加权≥6),减少小幅重审;(b)与产品共识把验收阈值降到 0.15(与"评委
  克制"惯性匹配)。**在数据面前先认账,再调参;不反向把分数做大来凑阈值**(那是
  反捏造红线的镜像违例)。
- 「P0 推送通知」(M3)管道已具备(record 的 P0 即时下发);真实告警要等品牌被
  `subscribe_brand` 订阅后自然发生。

## 9. 下一步

1. **W6 覆盖滚动**:周扫 Routine 每周一自动跑;逐步把余下 8 品牌纳入事件流,
   顺带回收 §4.3 / §7.4 的开放 leads;
2. ~~重审素材已备~~ **✅ 2026-07-12 四单重审全部落地**(asiainfo v2 / yuanxin v2 /
   spacex v2 / meituan v3),39 条事件 100% 消费、全部灯灭;精确率账见 §8.3
   (1/5,未达标——阈值/门槛校准是下一个决策点);
3. **触发规则校准**(§8.3 结论):在积累更多样本前,优先考虑把 P1≥2 调为 P1≥3
   或加权阈值 5→6,减少小幅重审的误报。

## 10. 单次扫描操作 SOP(M1 人肉/半自动版)

```
1. 选品牌,读 watch/matrix.yaml 确认开启维度
2. 按维度关键词 WebSearch(W3:品牌+中标/集采/禁入;W4:品牌+处罚/问询;W5:品牌+年报/预告)
3. 过收录门槛(§4.1):URL 日期自证 / curl 核对;聚合库只作线索
4. 追加事件到 watch/<slug>/events.yaml(id 顺序号递增;fetched_at 用当下 UTC)
5. python3 scripts/watch-tools/validate_watch.py   # 必须全绿
6. 重大事件(P0/P1)顺手评估触发规则(30 天窗 P0≥1 / P1≥2 → 值得建议重审)
```
