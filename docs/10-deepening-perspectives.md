# 10 — 深化 perspective:从 seed tier 到 full tier(研究 SOP + 进度追踪)

本文档把"把一套 perspective 从 **seed tier** 补到 **full tier**"变成一个可追踪、可交接的流程,
并记录 43 套 perspective 当前各自的 tier。

> **为什么需要它**:2026-06 一口气把 7 个 SKELETON panel 全部建成可运行(perspective 15 → 43),
> 新增的 28 套是 **seed tier**——质量够用于打分,但还没补齐 6 路深度调研。本文档是把它们
> 逐一升到 full tier 的作业手册。

## 1. 两个 tier 的定义

| tier | 一套 perspective 包含 | 校验 | 够不够打分 |
|---|---|---|---|
| **seed** | `SKILL.md`(过 5 段结构规范)+ `references/research/quotes.md`(URL 锚定金句库) | `check_structure.py` ✓ | 够(Phase 4 可用) |
| **full** | seed + `references/research/01-06.md`(6 路深度调研) | + 内容质量底线(§3) | 够,且可复盘 / 可 refresh / 抗漂移 |

`check_structure.py` 与 `validate_panels.py` **只要求 seed**(SKILL.md 的 5 个 H2 + 能被 panel resolve)。
full tier 是质量增强,不是 CI 硬门槛——所以深化是"提质"而非"修红"。

## 2. full tier 的 6 路调研文件(命名固定)

`references/research/` 下,命名与 [`07-code-standards.md`](07-code-standards.md) §2 一致:

| 文件 | 内容 | 一手 / 二手 |
|---|---|---|
| `01-writings.md` | 本人写作(文章 / 书 / 致股东信 / 公众号 / 推文) | 一手 |
| `02-conversations.md` | 本人接受或主持的对话(访谈 / 播客 / 演讲 / 听证 transcript) | 一手 |
| `03-expression-dna.md` | 语言风格抽样(句式 / 词汇 / 节奏 / 口头禅,带例句) | 一手 |
| `04-external-views.md` | 外部对 TA 的评价 / 报道 / 复盘 | 二手 |
| `05-decisions.md` | 可追溯的真实决策案例(做了什么 + 结果) | 一手 + 二手 |
| `06-timeline.md` | 关键时间节点 | 一手 + 二手 |

`quotes.md` 已有(seed 阶段产出),深化时把它扩进 01 / 02 / 03。

## 3. 内容质量底线(来自 [`07-code-standards.md`](07-code-standards.md) §9)

每套 full tier 至少:

- ≥ 30 条调研引用,分布在 6 路文件
- ≥ 80% 一手来源占比(本人写作 / 本人接受的访谈 / 本人主持的播客)
- ≥ 5 条决策启发式、≥ 5 个表达样例

**禁止**:把维基百科条目当一手;用 LLM 凭空生成的"风格化引言";已被本人公开否认 / 道歉的内容当正面 DNA。

## 4. 深化一套 perspective 的 SOP(端到端)

```text
Step 1  采集 6 路一手材料
        - 英文人物:本人 essays / 书 / 听证 transcript / 长访谈(需要能读全文,WebFetch 或浏览器)
        - 中文人物:致股东信 / 公众号 / 长访谈 / 播客 —— 强烈建议走 Wuying 云浏览器
          (见 docs/wuying-usage.md):X / 微信公众号 / 知乎 / B 站 / 中文媒体很多对
          无浏览器的抓取返回 403 或反爬,Wuying 才拿得到全文。
        - 每条材料记 URL + 一手/二手标注。
Step 2  写 references/research/01-06.md(按 §2 模板),把 quotes.md 扩进 01/02/03。
Step 3  re-distill SKILL.md —— 用 01-06 的结论回填 Core Mental Models / Decision Heuristics /
        Expression DNA / Sources,确保 SKILL.md 是从研究里"提炼"的,而非反过来。
Step 4  质量校验:
          python3 scripts/perspective-tools/check_structure.py --perspective <slug>
          python3 scripts/perspective-tools/quality_check.py perspectives/<slug>-perspective/SKILL.md
Step 5  (可选)与对照组对跑:/mba <demo-brand> --panel-add <slug> --quick,
        确认深化后该评委更 in-character、引用更扎实、与同 panel 评委有独立观点而非趋同。
Step 6  commit(纯内容增强,不动行为 / CI),走 PR。
```

## 5. ⚠️ 环境前提(为什么不能在受限沙箱里硬做)

full tier 的核心是 **≥80% 一手来源**——必须能**读到一手原文**(不是搜索摘要)。

- 受限执行环境(如 Claude Code on the web 的默认网络策略)下,`WebFetch` 常被目标站
  以 403 挡掉(实测 paulgraham.com / 维基百科 / 受 CF 保护的中文站均 403),`WebSearch`
  只给摘要。**只靠摘要拼 6 路调研 = 二手为主,违反 80% 一手底线**——宁可保持 seed,
  也不要把 seed 包装成"看着像 full"。
- 因此深化作业应在**能读全文的环境**做:本地 + `WebFetch` 放行,中文人物配 **Wuying** 云浏览器。
- 这也正是仓库 `scripts/wuying/` 与 `docs/wuying-usage.md` 存在的原因。

## 6. 进度追踪(43 套 perspective 的 tier)

**FULL(39)**:

早期三套 panel(default / auto / security-cn-global)的评委(15):

`fusheng` · `jobs` · `likejia` · `wu-jundong` · `zhang-yiming` · `musk` · `leijun` · `lixiang` ·
`hexiaopeng` · `libin` · `zhouhongyi` · `zhangmingzheng` · `renzhengfei` · `jensenhuang` · `satyanadella`

**vc-en 面板全员 full(2026-07-07 深化,5/5)**:`paulg` · `naval` · `pmarca` · `pthiel` · `rhoffman`
—— **首个整面板从 seed 全部升到 full 的行业 panel**。均由各自一手语料(curl 走已放行出口代理全文抓取)
6 路蒸馏、每条 verbatim 金句逐条比对源站校验,`check_structure` + `quality_check` 6/6 双过。
按引用计一手占比:`paulg` 93% · `naval` 92% · `pmarca` 92% · `pthiel` 90% · `rhoffman` ~90%,均过 §3 的 ≥80% gate。

**luxury-en(2026-07-07 深化):`cucinelli`** —— luxury-en 首位 full(该面板 1/5)。一手 = 公司发布的
《2024 Report on Humanistic Capitalism and Human Sustainability》(布鲁内洛·库奇内利本人 doctrine,
~3.9 万英文词,curl 抓 PDF + pdfminer 抽)+ humanistic 页;22 条 verbatim 逐字校验,`check_structure`
+ `quality_check` 6/6。**provenance 已注**:语料集中于这一份大 doctrine 文档(像 pthiel 的 CS183),
偏 sustainability/fair-profit/dignity;他的经典文学引用(Dostoevsky/Kant/Benedict)只按名归属、不逐字引;
2025 做空争议明确排除。

**luxury-en(2026-07-10 深化,route-A 4 路 scout 验证):`awintour`(Anna Wintour)** —— luxury-en 第二位 full(该面板 2/5)。
**4 路 luxury-en scout(awintour/tomford/burton/arnault)全部判 deepen,推翻上轮"多为访谈=二手"与"arnault marginal"的结论**:
出口代理未挡 vogue.com/burton.com/gq.com/interviewmagazine.com/lvmh Prismic CDN,均可 curl。awintour 一手 =
**其署名 Vogue Editor's Letters + 悼念信**(vogue.com/contributor/anna-wintour 作者页解锁 ~17 篇署名文,~1 万英文词,
**100% 一手 by byline,无说话人标签歧义**);我方独立 firewall 复核 39 条 verbatim(0 漏),6/6。6 模型(超越流行的
timelessness/clarity of purpose·power+attitude/让人更像自己·self-possession 知道自己是谁·backwards and forwards
承前启后·champion the new/community 非精英主义·crisis as catalyst/singular 不可替代)。**⚠️ 两条诚实注记**:①可达一手
**集中在 2020–2021 疫情编者信 + 2022–2025 悼念信**,读来比其"Nuclear Wintour"名声温和;②她最出名的 punchy 金句
("Taste is not democratic"/"indecision"/"forward"/"mass with class")**无法一手校验**,一律标〔reported〕入 04、
**绝不当逐字引**(这是反捏造该守处)。**self-conflict**:她是时尚圈头号 gatekeeper、与 LVMH/Kering/Condé Nast 结构性绑定,
评其治下品牌应 `--panel-drop awintour`。悼念信里 André 的邮件/VGC 嘉宾的话=他人所说,不归到她名下。
`tomford`(GQ 2021 + Interview Mag 干净标签问答)、`arnault`(LVMH 年报董事长致辞 + 致股东信署名)
两位 scout 判 deepen、语料已抓,待逐位深化落地。

**luxury-en(2026-07-10 深化,route-A 干净标签访谈):`burton` = Sarah Burton(纪梵希创意总监)** —— luxury-en 第三位 full(该面板 3/5)。
**⚠️ 身份纠错:`burton` slot 是 Sarah Burton(麦昆/纪梵希创意总监),不是单板滑雪创始人 Jake Burton Carpenter**——
我在 4 路 scout 时把 slug 误当 Jake 去抓了(Jake 语料虽好但人错),经用户确认后改回深化 Sarah 本人。一手 =
其 **3 篇干净说话人标签访谈,只取本人的答**(WWD Womenswear Designer of the Year 专访 by Miles Socha + AnOther 纪梵希首秀专访
+ WWD《Givenchy's Sarah Burton》),排除记者提问 → **100% 一手 by count**;我方 firewall 复核 39 条 verbatim(0 漏),6/6。
**seed 的招牌句现全部一手证实**(此前标〔reported〕):"atelier 是 heart and soul / to go forward you have to go back to the beginning"(AnOther)、
"comes alive in the fitting"、"a form of armor"、"go back to the DNA of the house"(WWD)——seed 方向对,full 补上真 provenance。
6 模型(atelier=heart and soul/回到起点·comes alive in the fitting/在身上而非草图·how the woman feels=armor 但仍是她自己·
look-by-look couture mindset·create out of nothing/"it was never 'no'"·steward the DNA 但为今天的女性设计)。**⚠️ 注记**:
①语料集中在 2024–2025 纪梵希转场期 + 麦昆回忆;②她描述 Lee McQueen / Hubert de Givenchy 的话是"论他们",**不当她本人的信条**;
③**self-conflict**:她是 LVMH 旗下纪梵希创意总监,身处被审计的奢侈品体系内,评其治下品牌应 `--panel-drop burton`。
剩余 luxury-en 两位 `tomford`/`arnault`(scout 已判 deepen、语料已抓)做完 = luxury-en 5/5。

**cross-border(2026-07-07 深化):`huangzheng`(黄峥)** —— cross-border 首位 full(该面板 1/5)。一手 =
黄峥 **9 篇公众号原创文(2016–2018)+ 拼多多致股东信**(**原公众号已删**,据「投资研究」整理合集 PDF,
pdfminer 抽;主循环手工深化)。**只引原创文+致股东信,合集里的采访实录属二手不逐字引**;段永平承袭如实标注;
2021 黄峥淡出后决策非本人主张(cutoff 边界)。19 条 verbatim 逐字校验(中文去空格),`check_structure`+`quality_check` 6/6。

**edu-cn(2026-07-07 深化):`yuminhong`(俞敏洪)** —— edu-cn 首位 full(该面板 1/3)。一手 = 俞敏洪
**三篇公开演讲全文**(2016 创业家讲课 / 2023「人生四件最重要的事」/ 2025「韧性的力量」,转载于
muhn.edu.cn / 新浪财经 / 腾讯新闻;主循环手工深化)。**演讲全文 transcript=一手,记者转述/摘要=二手不逐字引**;
引用他人的诗文/典故(罗曼·罗兰、陆游、孔孟)已标注非本人原创;2016「个人英雄主义/组织变革」锁定当年语境;
主播去留/舆情/未公开财务明确排除。6 路合计 55+ 条 verbatim 逐字校验(中文去空格+全半角规范化),
按引用计一手占比 ≈95%,`check_structure`+`quality_check` 6/6。

**cross-border / consumer-cn(2026-07-07 深化):`yangjianhui`(阳萌 / Anker)** —— 一手 = 安克官网
anker.com.cn **两篇对谈实录**(anker_71 与杨轩 / anker_72 与张鹏,均 2024,发表于公司自有官网=一手发声;
主循环手工深化)。**按 speaker 只逐字引「阳萌：」的回答**,提问者(杨轩/张鹏)与承袭他人(任正非"价值分配"、
科林斯"先人后事"、赵东平)的话分开标注;narrated 文章(anker_65/70/75/78 记者叙述框架)不逐字引;
AI/存算一体/机器人属前瞻判断非事实。35 条 verbatim 逐字校验(中文去空格+全半角规范化),
按引用计一手占比 ≈93%,`check_structure`+`quality_check` 6/6。**至此首批中文评委(黄峥/俞敏洪/阳萌)全部 full。**

**consumer-cn(2026-07-07 深化):`luoyonghao`(罗永浩)** —— 一手 = 2014「一个理想主义者的创业故事」
第四场**演讲全文实录**(网易科技,~3 万中文字,curl 抓)+ 2021 搜狐独家专访里他本人的直接引语。
**演讲=一手独白全部逐字引;采访只引其本人原话**,记者旁白与他人(如黄贺)的话分开;引用他人的书/歌词/评价
(格拉德威尔《异类》、崔健、刘瑜)标注非原创。6 大主题(天生骄傲不作弊/理想主义营销/直面认错/能做出来≠能量产/
理想主义vs商业能力/创始人IP)。29+ 条 verbatim 逐字校验(去空格+全半角规范化)。**provenance 同 cucinelli/pthiel:
语料集中于这一场 2014 演讲**,偏「锤子危机+理想主义」语域,已注明锁定年份。按引用计一手占比 ≈95%,6/6。
旧 seed 里"每一个生命来到这世界都注定要改变世界"等**网络误传句已移除**(非本人原话)。

**cross-border(2026-07-07 深化):`shouzichew`(周受资 / TikTok)** —— 一手 = 其 **2023-03-23 美国众议院
能源与商业委员会书面证词全文**(docs.house.gov PDF,~3.1 万字符,他署名的准备陈述,pdfminer 抽)。
英文,firewall 用空白 + 引号/破折号 glyph 规范化;28+ 条 verbatim 逐字校验。6 大主题(使命/产品哲学
"发现之窗·创作之布·连接之桥"/创作者小企业经济/信任靠行动赢得/安全优先于短期变现/Project Texas 本地化)。
**provenance 格外谨慎**:这是**敌意听证语境下的辩护性准备陈述**,独立性/数据安全类是其 **stated commitments 非事实**,
SKILL/research 全程标注不作既成事实;听证会 flash transcript 有转写错误**不逐字引**,只用书面证词;锁定 2023。
按引用计一手占比 ≈96%,`check_structure`+`quality_check` 6/6。

**consumer-cn(2026-07-07 深化):`jiangnanchun`(江南春 / 分众)** —— 一手 = 其**两场公开演讲第一人称实录**
(2017 湖畔大学「与其追随主流,不如自成主流」/ 2017 高榕资本 CEO 年会「饱和攻击」,36氪+前瞻 curl)。
6 大主题(反着走/抢占心智一词定位/信任状/时间窗口先入为主/饱和攻击/道就是人心)。30+ 条 verbatim 逐字校验
(去空格+全半角+引号『』→"规范化)。**provenance 两处关键**:①其定位/信任状理论**承袭特劳特(Trout/Ries)**,
全程标注非原创;②他是**分众创始人**,框架偏向"品牌广告/饱和攻击/电梯媒体"(=自己的生意),SKILL 加了 self-conflict
与"高估品牌广告"的张力警示;编者(笔记侠)插注不逐字引。按引用计一手占比 ≈92%,6/6。是**品牌审计判官里契合度最高的之一**。

**edu-cn(2026-07-07 深化):`salkhan`(Sal Khan / Khan Academy)** —— 英文,一手 = 其**两场官方 TED transcript**
(2011「Let's use video to reinvent education」+ 2023「How AI could save (not destroy) education」),
**从 TED 页面内嵌 transcript JSON(cues)抽取,是权威逐字版**(坑#1 说的"TED 正文被 JS 截断"指可见 DOM;
内嵌 JSON 仍是完整原文)。6 模型(免费普惠/自定进度翻转课堂/掌握学习无 Swiss-cheese/技术人性化课堂/2 sigma 问题→机会/
带护栏的 AI 家教)。29 条 verbatim 逐字校验(英文空白+引号 glyph 规范化)。**provenance**:2 场演讲、其中 2023 是
**Khanmigo 产品 demo(自利营销,非独立证据)**,已加 self-conflict 与"demo 好看≠有效果证据"的张力;"2 sigma"归 Benjamin Bloom;
两本书不在语料;锁定 2011/2023。按引用计一手占比 ≈95%,6/6。

**vc-cn(2026-07-07 深化,route-A 验证):`xuxin`(徐新 / 今日资本)** —— 一手 = 其**第一人称实录**:前瞻大咖
(源"投资人说")的自述长文 + 格隆汇访谈里她的回答(**只逐字引「徐新：」的答,主持人问不引**)。**关键:这是用
"curl 抓演讲实录聚合站(前瞻/36kr/混沌)"这条免费路做成的——`xuxin` 原被标"多二手",实际前瞻大咖是第一人称
逐字自述(我=100/徐新=8)。** 6 模型(第一品牌/心智占领·打造品牌四大要义·赌赛道+狼性企业家·三段论 winner-pattern·
时间的复利长期持有·成长性投资)。32 条 verbatim 逐字校验(去空格+全半角规范化)。**provenance**:承袭巴菲特(复利)/
马斯克(第一性原理)/黄峥(Costco+Disney)已标注;她夸的公司是自己 portfolio(self-conflict);**她如实承认错过字节/
拼多多=框架认知边界**(已入张力)。按引用计一手占比 ≈92%,6/6。**方法论沉淀见文末"免费取数路径"注。**

**vc-cn(2026-07-07 深化,route-A 验证):`zhanglei`(张磊 / 高瓴)** —— 一手 = 其**第一人称实录**:2017 人大毕业
演讲全文(k.sina 镜像)+《价值》自序「这是一条长期主义之路」(张磊本人所写,格隆汇)+ 2021 中国发展高层论坛低碳
演讲实录(36kr)。**关键:`zhanglei` 原被标"《价值》= 版权书不可逐字引",但其演讲实录 + 自序是第一人称逐字,curl
直接 200 拿全文——route-A 再下一城。** 6 模型(长期主义/做时间的朋友·价值创造是唯一标准/正和游戏·弱水三千但取一瓢·
与伟大格局观的创业者同行·动态护城河·第一性原理+人文/哑铃理论)。42 条 verbatim 逐字校验(去空格+全半角规范化,
0 漏)。**provenance**:三个投资哲学(守正用奇/弱水三千/桃李不言)+ 朱元璋战略 + 弗罗斯特诗 + 第一性原理均为古典/
承袭,已标注;"弱水三千"他在演讲归《论语》,通行考据实为《红楼梦》——按他的说法标注并注明差异;他夸的公司多为
高瓴 portfolio(self-conflict);规模/回报数字均为自述(需核验)。3 张力(只取一瓢 vs 广布局·做时间的朋友 vs
择时减持·价值观叙事 vs 收益导向基金本质)。按引用计一手占比 ≈90%,6/6。

**vc-cn(2026-07-07 深化,route-A 验证):`shennanpeng`(沈南鹏 / 红杉中国)** —— 一手 = 其**第一人称实录**:两场
带干净说话人标签的问答——陆家嘴《何问西东》(何振红访,约 2020)+ 秦朔访(2016),**只逐字引「沈南鹏：」的答,
主持人/记者的问不引**(同徐新格隆汇做法)。answer-only 语料 ~11.3 万字符/11299 CJK。6 模型(赛手第一/反"只投赛道"误区·
看公司三点标准·长期主义=抵御诱惑+理智诚实+反人性·创业者背后的创业者/司机旁看地图·优秀创业者共通性·做多中国+全站式平台)。
43 条 verbatim 逐字校验(0 漏)。**关键 seed 纠偏**:旧 seed 的「资本可能无情…社会责任」「专注成专家」**未在一手逐字命中**,
且他原话弱化"成专家"、强调"做出理智成功的选择"——已纠正(见 quotes/02/04)。**provenance**:"创业者背后的创业者"=红杉
1972 定位(标注);夸的公司几乎全是 portfolio 或自己创办(self-conflict);字节=看走眼后九个月补投、京东=欠仓(如实)。
3 张力(赛手第一 vs 好赛道/做多中国·聪明的钱不砸钱 vs 红杉规模化广撒网·尊重规则/赢家通吃 vs 反垄断监管)。
**且与同面板徐新"只赌赛道不赌赛手"直接对立——面板内部有意见分歧,是有意义的对照。** 按引用计一手占比 ≈92%,6/6。

**vc-cn(2026-07-07 深化,route-A 验证)—— `zhuxiaohu`(朱啸虎 / 金沙江):vc-cn 收官,面板 5/5 全 full!** 一手 =
其 **2025 第一人称实录**:中关村论坛演讲实录《生成式 AI:应用为王》(腾讯,monologue)+ 新浪《未竟之约》张小珺访谈
(**只引「朱啸虎：」的答,张小珺问不引**,470 处干净标签)。语料 18253 CJK。6 模型(泡沫与死亡谷反向指标·应用为王反 AGI 叙事·
商业化/单位经济优先·错开共识 15 度·离开大厂三条马路/纯工具难守·快决策+控规模)。46 条 verbatim 逐字校验(0 漏)。
**锁年 2025**:seed 的"5 年后没有独立大模型公司"(2024 另一访谈)、"批量退出人形机器人"(投中网二手)**未在本 2025 语料
逐字命中**,不作逐字引、不代拟其对"退出人形机器人"争议的表态。**provenance**:眼球经济/Dark Fiber/猥琐发育/遥遥领先/老登=
网络黑话/行业术语,LeCun/Ilya/Sam Altman 观点=转述他人,均标注;举例公司(饿了么/滴滴/小红书/Lovart/Liblib…)多为
portfolio(self-conflict)。3 张力(反向指标 vs 自己 AI 乐观·算得清账才投 vs 系统性错过范式·十分钟决策 vs 深度/运气)。
按引用计一手占比 ≈90%,6/6。**至此 vc-cn 5/5:xuxin/zhanglei/shennanpeng/zhuxiaohu route-A 深化 + leijun 复用 auto——
继 vc-en 之后第二个整面板 full,首个整面板 full 的中文行业 panel。**

**ai-app-cn(2026-07-07 深化,route-A 验证):`yangzhilin`(杨植麟 / 月之暗面 Moonshot):ai-app-cn → 4/5。** 一手 =
其 **2024-02 第一人称实录**:《潜望》张小珺对话 +「海外独角兽」(拾象)对话两场长访谈(**只引「杨植麟：」的答,提问方
《潜望》/海外独角兽不引**;正文在 window.DATA JSON,注意大写 `<P>` 标签 + 排除提问方标签防污染)。清洗后语料 15327 CJK。
6 模型(第一性原理/去雕花·无损压缩=智能/long-context·长期主义反 PMF 短视·成立的非共识/技术理想主义·AGI=科学+工程+商业/登月·
智能是核心增量)。44 条 verbatim 逐字校验(0 漏)。**⚠️ 强锁年 2024-02**:月之暗面/Kimi 早期、大模型高潮期;此后格局与 Kimi/
月之暗面本身剧变,SKILL/quotes/04 全程标注"勿当永恒立场";seed 的"Be Simple Be Naive"未在本语料逐字命中,不作逐字引(精神由
"去雕花"承载)。**provenance**:scaling law/next-token-prediction/Transformer/MoE=领域术语,OpenAI 理想主义/字节商业化/Ilya/
降维打击=承袭他人,均标注;long-context/Kimi 为自家路线(self-conflict)。3 张力(长期主义 vs 商业化生存·领先叙事 vs 追赶 OpenAI·
精简组织 vs 百亿美元豪赌)。**与同面板朱啸虎"应用为王/商业化优先"正面对立——ai-app-cn 面板核心张力。** 按引用计一手占比 ≈90%,6/6。

**ai-app-cn(2026-07-07 深化,route-A 验证)—— `wanghuiwen`(王慧文 / 美团):ai-app-cn 收官,面板 5/5 全 full!** 一手分两级
(**provenance 分层,类比 pthiel**):纯一手 = 2017 源码码会演讲全文《"农村包围城市"是个误解》+ 2020 清华「不设限的人生」演讲
全文(蓝洞商业,"以下为王慧文演讲全文"之后);**semi-一手 = 混沌《高手如何做决策》= 笔记侠整理自 2020 清华产品课现场实录**
(非逐字口吻,类比 Blake Masters 的 CS183,每条标注"整理稿")。6 模型(体量决定成败·规模效应=商业世界的万有引力·马太效应=
进化论/后发优势·管理是反规模效应/人越少越好·做正确的事 vs 做容易的事/边算账·不设限/找规律)。**按引用计:纯一手 21 条、
semi-一手 16 条、二手 0 条**——纯一手占多数,semi 全程标注(纯一手占比高于 pthiel)。**关键 provenance 判断**:王慧文最著名的
战略框架(体量/规模效应/马太效应)只存在于笔记侠整理稿,故按 pthiel 先例作 semi-一手引用而非纯一手;36kr 正文其实在原始 HTML
`<p>` 标签(非 JSON content 字段)。**provenance**:马太效应=社会学 Merton、规模效应/网络效应=经济学、小沃森/Facebook-MySpace=
商业史、知止不殆=道德经,均标注;案例几乎全是美团/校内网(自己创办,self-conflict)。3 张力(人越少越好 vs 美团十万铁军·
"做正确的事"是幸存者复盘·框架 vs 创新的不连续)。**红线:健康/私人/2023 光年之外退隐一律留白**(锁年 2017/2020)。6/6。
**至此 ai-app-cn 5/5:杨植麟/王慧文/朱啸虎 route-A 深化 + 周鸿祎/傅盛 复用 default——继 vc-en、vc-cn 之后第三个整面板 full。**

**consumer-cn(2026-07-07 深化,route-A 验证):`zhongshanshan`(钟睒睒 / 农夫山泉):consumer-cn → 4/5。** 一手 =
其 **2024-2025 第一人称实录**:2024-08 央视《对话》陈伟鸿专访(**只引「钟睒睒：」的答,主持人及其他现场发言人=经销商/县长/书记
一律排除防污染**)+ 2025-01 养生堂年会演讲全文(monologue)。清洗后语料 ~1.3 万 CJK。6 模型(产品主义/慢就是快·反低价内卷/往上卷
=价格是产品的生命·差异化逆共识·首富的可执行利他主义/助农·独行做长期/战略性亏损/制度传承·研究型企业/互联网是过眼烟云)。
42 条 verbatim 逐字校验(0 漏)。**⚠️ 强锁年 2024-2025**:罕见密集发声、正值"绿瓶水/农夫山泉有点甜/美国籍二代接班"网络风暴,
**大量自述带辩护性/道德高地(24000 瓶水/停产纯净水/股权/接班),SKILL/quotes/02/04 全程标注"须审视,不作定论"**。
**provenance**:马斯克/李冰父子/塞万提斯"理想的疯子"/梅特卡夫效应/善欲人见(朱子治家格言)/黄仁勋=承袭/引用他人,均标注;
案例几乎全是农夫山泉/养生堂(self-conflict);身家/利润/捐赠/亩数=自述需核验。3 张力(反低价 vs 自己高毛利首富·利他叙事 vs
争议自辩·慢/研究型 vs 幸存者复盘+强主观宏大叙事)。按引用计一手占比 ≈90%,6/6。

**cross-border(2026-07-10 深化,route-A 验证):`zhuangshuai`(庄帅 / 百联咨询):cross-border 收官,面板 5/5 全 full!**
一手 = 庄帅**署名专栏 / 个人博客原文**:2020-05 腾讯云开发者社区《直播电商"人、货、场"的解读和趋势预测》(signature 稿)+
新浪博客 5 篇署名评论(万达 O2O 倒退 2013-12 / 易迅+顺丰 2013-12 / 双11 优购 2013-11 / 1号店生鲜之战 2013-09 / 美业 O2O 2015-07),
清洗后 ~1.3 万 CJK。**与创始人型判官不同:其逐字几乎全是本人书写的署名文章,不依赖记者转述——无需 semi 分层,按引用计一手占比 100%。**
40+ 条 verbatim 逐字校验(0 漏)。6 模型(人货场→货场人=直播电商反向逻辑,货第一/场第二/人=社交属性·平台无纯粹=内容电商化+电商内容化·
人设=主播核心资产·全网爆款→人群爆款=个性化推荐·先拆盈利模式/单位经济=反"有规模自然盈利"忽悠·殊途同归=大佬做电商底盘归地产+金融)。
**⚠️ signature「货场人」框架强锁 2020(直播电商红利期)**:头部主播/平台监管/"内卷"整治其后都在变,SKILL/quotes/04/05 全程标注不顺延;
2013–2015 案例为当年时点,被点评公司(易迅并入京东、优购转型、多数 O2O 出清)**带后见之明看**。**provenance**:卡思数据/抖音价格带/直播频率=
引第三方或自述,标"需 live 核验";评论对象多为别人的公司(旁观者)。3 张力(冷静拆解 vs 过度还原/低估非线性·signature 锁 2020 时代性·
旁观者后见之明"拆得清楚≠做得成")。**self-conflict**:百联咨询有付费客户,评其咨询客户按分析自检、可 `--panel-drop zhuangshuai`。6/6。
**至此 cross-border 5/5:黄峥/阳萌/周受资/陈年/庄帅 全 full——继 vc-en、vc-cn、ai-app-cn 之后第四个整面板 full。**

> **12 位剩余 seed 的 route-A 可达性并行侦察(2026-07-07,12 路 scout,curl+firewall):`deepen` 11 · `marginal` 1(arnault)· `keep-seed` 0。**
> 结论坐实"访谈=二手"的标签几乎全下早了——张小珺《晚点/潜望/未竟之约》、央视《对话》、Interview Mag、CNN transcript
> 都是带干净说话人标签、可 curl、可逐字校验的一手。各判官已验证源见下"剩余判官侦察结果";除 arnault(财报电话会实录全 403、
> 量薄)外,`yangzhilin`/`wanghuiwen`/`zhongshanshan`/`zhanglan`/`chennian`/`zhuangshuai`/`zhangbangxin`/`awintour`/
> `tomford`/`burton` 均判 deepen(其中 zhanglan、zhangbangxin 偏紧)。
>
> **⚠️ 张兰 keep-seed 判定(2026-07-07,严格取数核算,守 §3 的 80% 硬门槛):** 严格取全可 curl 一手后核算,张兰**不达标,留 seed**。
> 唯一实质干净一手是澎湃《时代面孔》深访(带干净「张兰：」标签,但仅 23 段 / ~2114 CJK / ~15 条可引);新浪睿见两篇极薄
> (634 / 337 CJK,多为记者叙述体、直引仅 3-4 短句);楚天都市报图订会为记者转述;自传《我的九条命》= 版权书不可逐字引;
> 她最本真的**直播 / 短视频口语无文字实录**(money.163=403、lady.163=403、foodtalks=JS 墙、csdn=521)。
> **凑不齐 ≥30 条逐字、真实纯一手 <80%**——按用户"能达标才做、达不到诚实留 seed"原则**留 seed**(这是本会话唯一严格核算后主动留 seed 的判官,反捏造纪律该守处)。
> 未来若出现张兰**长篇第一人称演讲/访谈实录**(非直播口语、非记者转述),可再评估。

> 各判官取数要点(深化时沿用):
> - `paulg` — 28 篇 paulgraham.com essay(2001–2024)。
> - `naval` — nav.al「How to Get Rich」系列 + happiness essays(2018–2021);**这些是他自网发布的播客转录,非手写文章**,已全程标注,Nivi 的提问与 Naval 的话区分开,借用观点(四种运气→Andreessen 等)标注来源。
> - `pmarca` — pmarchive.com「Pmarca Guide to Startups」(2007)+ a16z「It's Time to Build」(2020)/「Techno-Optimist Manifesto」(2023);两套语域相差十年,已按年份锁定不混用。「Why Software Is Eating the World」(2011 WSJ)不在语料,只按名归属不逐字引。
> - `pthiel` — **语料是 Blake Masters 记录的 Thiel 斯坦福 CS183 课堂笔记(2012,semi-first-party),每条都标「Masters' notes of Thiel's lecture」**,唯一纯一手是 Cato「The Education of a Libertarian」(2009);《Zero to One》与「Competition is for losers」只按名归属、明确标注不逐字引;政治内容排除。
> - `rhoffman` — **可读一手语料偏 2023–2025 AI 期**(reidhoffman.org essays/speeches);经典 canon(Blitzscaling / Start-up of You / Masters of Scale / 网络效应)源站不可读,只按名归属不逐字引,偏斜已在 01/04/SKILL 如实标注;seed 里未经核实的两条 maxim 已移除。

> 注:`quality_check` 内建的「一手占比」字段是 SKILL Sources 段的**标签词粗代理**(阈值 50%),读数 62–67%;§3 gate 以上面按引用计的真实占比为准。

**seed → 待深化(4)**——行业 panel 评委(43 = 39 full + 4 seed;下表按面板列主要中文/待评估者,luxury-en 剩余 2 位另见 docs/11):

| 首次所属 panel | seed 评委(slug) | 取数难度 |
|---|---|---|
| ai-app-cn | ✅ **5/5 全 full** | `yangzhilin`/`wanghuiwen`/`zhuxiaohu` route-A 深化 + `zhouhongyi`/`fusheng` 复用 default——**整面板收官** |
| edu-cn | `zhangbangxin` | 侦察判 deepen(≈82%,偏紧):中欧校友刊访谈实录+致员工信引文;部分官方源 403 需拼 |
| vc-cn | ✅ **5/5 全 full** | `xuxin`/`zhanglei`/`shennanpeng`/`zhuxiaohu` route-A 深化 + `leijun` 复用 auto——**整面板收官** |
| consumer-cn | `zhanglan`(**严格核算后留 seed**) | ✅ `zhongshanshan` 已 full → **consumer-cn 4/5**;张兰**经严格取数核算不达标,诚实留 seed**(见下"张兰 keep-seed 判定") |
| cross-border | ✅ **5/5 全 full** | `huangzheng`/`yangjianhui`/`shouzichew`/`chennian`/`zhuangshuai` 全 full——**整面板收官**(庄帅=署名专栏 self-writing,一手 100%) |

> **状态(2026-07-10 更新)——剩余 4 位;luxury-en 4 路 scout 证明其中 4 位全部可 route-A deepen(arnault 反转上轮 marginal);awintour + Sarah Burton 已 full → luxury-en 3/5。**
> 本会话已把 **24 位**做到 full:paulg/naval/pmarca/pthiel/rhoffman + cucinelli + 黄峥/俞敏洪/阳萌/罗永浩/
> 周受资/江南春/Sal Khan + **徐新 + 张磊 + 沈南鹏 + 朱啸虎(收官 vc-cn)+ 杨植麟 + 王慧文(收官 ai-app-cn)+ 钟睒睒(consumer-cn→4/5)+ 陈年 + 庄帅(收官 cross-border 5/5)+ Anna Wintour + Sarah Burton(luxury-en→3/5;均 route-A 验证)**。
> **⚠️ 教训:`xuxin` 一度被标"多二手",实际前瞻大咖有第一人称逐字自述 —— 说明"访谈=二手"的标签下早了,
> 剩余判官应先用 route-A 重扫再判。** 目前仍卡住的:
> - `zhangbangxin`(张邦鑫)**已侦察**:芥末堆(2013 记者特写)、CEIBS 校友刊均为**记者转述**,非逐字实录;
>   多知网 / jyb.cn **403 挡**;名句全为媒体转述,无法逐字校验 → 暂留 seed。
> - `wanghuiwen`(王慧文)清华产品课**只有旁听者整理笔记**(非逐字),firewall 做不可靠 → seed。
> - `yangzhilin`/`zhuxiaohu`/`chennian`/`zhuangshuai`——**均已 route-A 重扫并 full**(印证不该下早"二手"结论);
>   `zhongshanshan`(钟睒睒)已 full(2024 央视《对话》+2025 养生堂年会);`zhanglan`(张兰)以直播/访谈为主,**经严格核算不达标,留 seed(见上"张兰 keep-seed 判定")**。
> - `zhanglei`(张磊)**已 full**(2026-07-07):《价值》版权书虽不可逐字引,但**人大演讲 + 自序 + 高层论坛演讲**是
>   第一人称逐字,route-A curl 直接拿全文——印证"演讲实录 > 版权书"这条免费路。
> - `shennanpeng`(沈南鹏)**已 full**(2026-07-07):原以为"多二手",实测陆家嘴《何问西东》+ 秦朔访是**带干净说话人
>   标签的问答**,只引「沈南鹏：」的答即得干净一手(同徐新格隆汇做法)——再证"访谈=二手"标签常常下早了。
>
> **免费取数路径(route-A / B,2026-07-07 实测):**
> - **route-A(curl 聚合站,已验证首选,零依赖):** `t.qianzhan.com/daka/…`(前瞻大咖)、`36kr.com`、混沌 等站的
>   **演讲实录是第一人称逐字**,curl(浏览器 UA + `--cacert`)直接 200 拿全文。江南春、徐新都靠这条做成 full。
>   访谈类要**按 speaker 切分,只引本人回答**(主持人问不引)。**大多数中文判官用这条就够,不必上浏览器。**
> - **B站字幕 API:** `api.bilibili.com`(view + 字幕接口)curl 可达,给真实 bvid 拿字幕 JSON = 逐字口述(同 TED cues 招)。
> - **网页内嵌 JSON:** JS 反爬站(知乎/TED/36氪)正文常藏在 `__NEXT_DATA__`/`initialState`,curl HTML 后 grep 内嵌 JSON 可绕反爬。
> - **微信公众号永久链:** 部分可 curl(很多会跳"环境异常"验证页,看运气)。**Wayback**(`archive.org/wayback/available`)抓删除/被挡页存档。
> - **route-B(Playwright + Chromium,本环境已装但受限):** `playwright@1.56.1` + `/opt/pw-browsers/chromium` 都在,
>   确认走了出口代理(指死端口报 `ERR_PROXY_CONNECTION_FAILED`);但走 MITM 代理时 CONNECT 隧道 TLS **一律
>   `ERR_CONNECTION_RESET`**——已 `apt` 装 `certutil`、以 `CT,C,C` 把 `/root/.ccr/agent-proxy-ca.crt` 导入 `~/.pki/nssdb`、
>   试过 `--ignore-certificate-errors`/`--test-type`/`--disable-http2`/`headless=new` 全无效。**判断:该 MITM 代理 + headless
>   Chromium 握手不兼容(curl 能吃 `--cacert`、Chromium 吃不进),属环境层限制,脚本绕不过,需代理侧(管理员)修。
>   登录墙站(微博/部分知乎)暂抓不了 —— 但 route-A 已覆盖大多数判官。**
> **解封路径**:①Wuying Pro/Ultra 抓中文反爬站(微信公众号/知乎/B站);②找到某位的**逐字演讲实录 / 致股东信 / 本人博客**
> curl-可达源(如黄峥的合集 PDF、周受资的国会证词模式);③luxury-en 剩余四位见 docs/11。**在此之前,硬凑 = 破坏立身之本,不做。**

> 建议优先级:~~vc-en 5 位~~ ✅ **已全部 full(2026-07-07)** → 下一批 `salkhan` / `shouzichew` /
> `huangzheng`(有英文 / PDF 一手,可 curl)→ 其余中文人物(配 Wuying)。

> **状态更新(2026-07-07)——英文腿全通,中文腿仍挂起。**
> - ✅ **Full 出口访问已开**:CCR 环境 Network access 设为 **Full** 后,**`curl`(带浏览器 UA,走
>   `$HTTPS_PROXY` 出口代理 + `--cacert /root/.ccr/ca-bundle.crt`)可 200 抓任意源站全文**
>   (nav.al / a16z.com / pmarchive.com / blakemasters.com / cato-unbound.org / reidhoffman.org …)。
>   vc-en 5 位即用此法一次性深化到 full(见 §6 FULL 列)。**深化英文人物用 `curl`,不要用 `WebFetch`**
>   (后者走 Anthropic 服务端出口、绕不开源站 UA 封锁)。验证放行:`curl -sS "$HTTPS_PROXY/__agentproxy/status"`。
> - ⛔ **中文腿仍挂起**:Wuying tenant `1685405689137018` 仍在免费档,`GetLink` 报 400
>   (Pro/Ultra 限定);中文一手(微信公众号 / 知乎 / B 站 / CF 保护中文站)未通。ai-app-cn /
>   vc-cn / consumer-cn / cross-border 的中文人物仍需 Wuying 解封或把对应中文源站加进
>   allowlist 后用 curl 抓。

## 7. 本会话已处理的数据修正(深化时请沿用)

- `yangjianhui`(slug 沿用历史命名):真实人物是 **阳萌(Steven Yang,Anker)**,旧标"杨建辉"系误标,
  已在 panel / roster 更正为"阳萌"。
- `shouzichew`(周受资,TikTok):替换原 `zhangyong-shein`(SHEIN 许仰天)——后者旧标"张勇"
  且**几乎无一手资料**,无法在不违反 anti-fabrication 的前提下建立。

---

> 维护:每深化完一套,把它从 §6 的 seed 表移到 FULL 列。当 28 套全部上 full,本文档可归档。
