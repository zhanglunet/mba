# 16 — 品牌舆情监控实现与过程记录(Brand Watch Implementation)

> Status: **M1 进行中**(W1/W2 已落地,W3 起未动)· Last verified: 2026-07-12
> 需求与维度设计见 **docs/15**(PRD);本文是**开发计划 + 实现细节 + 过程记录**,
> 按 W 系列工作项组织,做一项记一项(格式对齐 docs/11 的进度日志纪律)。

---

## 1. 开发计划(W 系列工作项)

对应 PRD(docs/15 §7)的 M1→M3 分期,拆成可单独 PR 的工作项:

| # | 工作项 | 内容 | 验收 | 状态 |
|---|---|---|---|---|
| **W1** | 数据层 + 硬 gate | `watch/matrix.yaml`(适用性矩阵单一真源)· `watch/<slug>/events.yaml` schema · `scripts/watch-tools/validate_watch.py`(静态校验 + `--selftest`)· 接入 panel-validation CI | 校验器全绿 + 自测有牙 + CI 跑 | ✅ 2026-07-12 |
| **W2** | 源可达性验证 | PRD §4.2.3 清单逐源真 curl,🔍 → ✅/⚠️/❌,坑记录在案 | 每源有结论 + workaround 可复现 | ✅ 2026-07-12(见 §3) |
| **W3** | 试点采集(持续) | 亚信 / 奇安信 / 垣信三品牌真实事件回填与增量 | **每品牌 ≥10 条**可溯源事件(M1 验收) | 🟡 首批 15 条(6/3/6),缺口见 §4.4 |
| **W4** | 半自动扫描进 skill | `/mba <brand> --watch` 单次扫描 SOP 进 SKILL.md;EVOLUTION Phase 2 先消费 events.yaml 再补扫 | 一次重审的 delta 调研直接引用事件流 | ⬜(注意坑 #2:SKILL.md 改动连带重生成) |
| **W5** | 首页徽章 + 时间线页(M2) | `build_home_cards.py` 读 watch 产出 P0/P1 徽章(进 REPORTS 生成区 + 漂移 gate)· `/watch/<slug>/` 时间线页 | 徽章与 events.yaml 零漂移 | ⬜ |
| **W6** | 定期采集(M2) | CCR Routines / cron 周扫,按矩阵扫开启维度 | 13 品牌适用维度覆盖 ≥80% | ⬜ |
| **W7** | 触发与联动(M3) | 触发规则评估器(30 天窗 P0≥1 / P1≥2)· MCP `get_watch_events` / `record_watch_event` · 订阅链路下发重审建议 | 触发建议精确率 ≥60% | ⬜ |

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
| **中国移动采购与招标网 b2b.10086.cn** | ⚠️ **可连,需 workaround** | 直连报 `unsafe legacy renegotiation disabled`(源站用旧 TLS 重协商,OpenSSL 3.x 默认拒绝)。用 `OPENSSL_CONF` 开 `UnsafeLegacyRenegotiation` 后 200(见下方配置)。首页为 855B 壳,公告列表页待深挖 |
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

### 4.4 M1 验收缺口(诚实记账)

验收线 **每品牌 ≥10 条**:当前 asiainfo 6/10 · qianxin 3/10 · yuanxin 6/10。
缺口主要在 W3 一手公示(需按 §3 workaround 深挖运营商集采列表页)与 W4/W7 维度。
W3 工作项持续滚动,不阻塞 W4 起步。

---

## 5. 下一步(按 §1 顺序)

1. **W3 滚动**:用 b2b.10086.cn workaround 深挖亚信集采公示;回溯 §4.3 全部 leads;
2. **W4**:`--watch` SOP 进 SKILL.md(⚠️ 坑 #2:连带 `build_agents_api.py` +
   `generate-personas.py` 重生成)+ EVOLUTION Phase 2 消费 events.yaml;
3. **W5**:徽章生成进 `build_home_cards.py`(P3 永不上卡,P0/P1 计数 + 30 天窗;
   沿用 REPORTS 生成区 + `--check` 漂移 gate 模式)。

## 6. 单次扫描操作 SOP(M1 人肉/半自动版)

```
1. 选品牌,读 watch/matrix.yaml 确认开启维度
2. 按维度关键词 WebSearch(W3:品牌+中标/集采/禁入;W4:品牌+处罚/问询;W5:品牌+年报/预告)
3. 过收录门槛(§4.1):URL 日期自证 / curl 核对;聚合库只作线索
4. 追加事件到 watch/<slug>/events.yaml(id 顺序号递增;fetched_at 用当下 UTC)
5. python3 scripts/watch-tools/validate_watch.py   # 必须全绿
6. 重大事件(P0/P1)顺手评估触发规则(30 天窗 P0≥1 / P1≥2 → 值得建议重审)
```
