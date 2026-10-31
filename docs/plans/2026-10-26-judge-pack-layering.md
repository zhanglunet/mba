# PRD-233/T1：评委盘点与分维度映射设计

> 依据：trend `adopted/PRD-233-mba-judge-pack-layering.md`（trend issue #1165）；分层规范以 PRD-227（livepowers，技能包分层五件套源头规范）为准，本仓只做适配，不另立口径。
> 范围：T1 只出盘点与映射设计。不改任何 panel 文件、不动代码；分包落地是 T2（#1166），总登记册是 T3（#1167）。
> 借鉴：AgriciDaniel/claude-seo（MIT）的 sub-pack 分层形态，仅借鉴结构，评委与映射均为 mba 自有内容。

## 〇、先说结论

- 盘点口径下 mba 共有 **46 位评委**（去重），其中**专家评委 43 位**、**模拟消费者评委 3 位**；按席位计共 55 个（9 位评委各跨 2 个 panel）。
- PRD 里的“43 评委”与盘点**对得上**：43 就是专家评委数，差额 3 位是 PRD-178 引入的模拟消费者（role: consumer），其结论按既有规则不进专家评分矩阵（对账见 §二）。
- 43 位专家按“第一发力点”归包：品牌 26 / 文案 8 / 视觉 4 / 合规 5。分布不均是评委构成的真实反映（创始人与投资人为主），不硬均分（§四.4）。
- PRD-227 的 T1 规范文档（livepowers #1135）尚未落地：本文登记册字段先按 PRD-227/PRD-233 正文推导的必填最小集设计，**字段名、包命名与版本规则待 227/T1 定版后最终对齐**（对齐清单见 §七）。

## 一、盘点口径与方法

- 数据源：`metric-brand-auditor/panels/*.yaml`，共 11 个 panel 文件，盘点时点为 2026-10-26 main（HEAD `cd619a1f`）。
- 身份口径：**slug 是评委唯一身份**。同一 slug 出现在多个 panel，算同一位评委、多个席位。跨 panel 复用是既有有意设计（panel 模板规范 T1 §二 #2 已明示，如 fusheng 同时在 ai-app-cn 与 default）。
- 不计入项：`industries.yaml` 是行业到 panel 的路由表，不含评委；`_template.yaml.example` 是建 panel 的模板，其示例 slug（first-judge-slug / second-judge-slug）不是真实评委。
- 视角/专长字段来源：panel yaml 本身没有逐评委的专长字段，本文从各 panel 的 `description` 与文件头注中对评委阵容的定位语逐人提炼；更细的视角定义在各评委的 perspective 资料中，T3 登记册落地时逐人回填。
- 三个计数：**席位 55**（11 个 panel 的 judges 条目总数）/ **去重评委 46** / 其中**专家 43 + 消费者 3**。

各 panel 席位：ai-app-cn 5、auto 5、consumer-cn 6、consumer-mixed 3、cross-border 5、default 5、edu-cn 5、luxury-en 5、security-cn-global 6、vc-cn 5、vc-en 5，合计 55。

## 二、与 PRD “43” 的对账

| 口径 | 数量 | 说明 |
|---|---|---|
| PRD-233 所述 | 43 | 专家评委数，与盘点一致 |
| role: consumer 的模拟评委 | +3 | consumer-mixed 的 3 位合成人设（PRD-178/T2，trend #891） |
| 去重评委总数 | 46 | 43 + 3 |
| 跨 panel 复用产生的额外席位 | +9 | 9 位评委各出现在 2 个 panel（见下） |
| 席位总数 | 55 | 46 + 9 |

跨 panel 复用 9 位：zhouhongyi（ai-app-cn、security-cn-global）、fusheng（ai-app-cn、default）、zhuxiaohu（ai-app-cn、vc-cn）、musk（auto、security-cn-global）、leijun（auto、vc-cn）、yangjianhui（consumer-cn、cross-border）、xuxin（consumer-cn、vc-cn）、likejia（default、edu-cn）、wu-jundong（default、edu-cn）。

消费者 3 位单列的原因：其 yaml 头注已定死规则——模拟人设、非真实调研，结论不进专家 Score Matrix、与专家分数不换算不平均、报告分开展示。所以 PRD 写 43 时没有把他们算进“评委”并不矛盾。本设计对他们的安排是横切组（§四.3），登记册照常登记（§六）。

## 三、评委全量盘点表（46 位）

按所在 panel 分组；跨 panel 复用的评委在每个 panel 各列一行，视角按该 panel 语境提炼。

### ai-app-cn（AI 应用 / Agent 层）

| slug | 中文名 | 英文名 | 语言 | 视角 / 专长 |
|---|---|---|---|---|
| yangzhilin | 杨植麟 | Yang Zhilin | zh | 大模型创业现役选手，技术品类定义（长上下文） |
| wanghuiwen | 王慧文 | Wang Huiwen | zh | 连续创业者，品类探索与新产品定位 |
| zhouhongyi | 周鸿祎 | Zhou Hongyi | zh | 安全派 + 反共识布道 |
| fusheng | 傅盛 | Fu Sheng | zh | 反共识 Agent 布道者，认知叙事 |
| zhuxiaohu | 朱啸虎 | Zhu Xiaohu | zh | 卷王 VC，实战派投资判断 |

### auto（汽车 / 电动车）

| slug | 中文名 | 英文名 | 语言 | 视角 / 专长 |
|---|---|---|---|---|
| musk | 马斯克 | Elon Musk | en | 创始人 CEO，第一性原理产品与技术叙事 |
| leijun | 雷军 | Lei Jun | zh | 创始人 CEO，营销与用户社区 |
| lixiang | 李想 | Li Xiang | zh | 创始人 CEO，产品定义 |
| hexiaopeng | 何小鹏 | He Xiaopeng | zh | 创始人 CEO，自动驾驶 / 智能化赌注 |
| libin | 李斌 | William Li | zh | 创始人 CEO，用户社区与服务体系 |

### consumer-cn（中文消费品 / 快消）

| slug | 中文名 | 英文名 | 语言 | 视角 / 专长 |
|---|---|---|---|---|
| jiangnanchun | 江南春 | Jiang Nanchun | zh | 媒介杠杆派，心智占领 |
| zhanglan | 张兰 | Zhang Lan | zh | IP 化餐饮品牌，直播表达 |
| luoyonghao | 罗永浩 | Luo Yonghao | zh | 反共识表达，发布会文案 |
| yangjianhui | 阳萌 | Steven Yang | zh | 跨境产品力（Anker） |
| zhongshanshan | 钟睒睒 | Zhong Shanshan | zh | 渠道极致与品类定义 |
| xuxin | 徐新 | Kathy Xu | zh | 消费投资，品牌可投性 |

### consumer-mixed（模拟消费者，role: consumer）

| slug | 中文名 | 英文名 | 语言 | 视角 / 专长 |
|---|---|---|---|---|
| first-glance-shopper | 第一眼顾客（模拟人设） | First-Glance Shopper (simulated) | zh | 直觉快判，第一印象（C1–C5 题组） |
| homework-buyer | 功课型买家（模拟人设） | Homework Buyer (simulated) | zh | 研究验证型决策，购买意愿与价格直觉 |
| brand-skeptic | 品牌怀疑者（模拟人设） | Brand Skeptic (simulated) | zh | 怀疑求证，信任犹豫 |

### cross-border（出海 / 跨境电商）

| slug | 中文名 | 英文名 | 语言 | 视角 / 专长 |
|---|---|---|---|---|
| huangzheng | 黄峥 | Colin Huang | zh | 极致下沉，算法供应链 |
| yangjianhui | 阳萌 | Steven Yang | zh | 静默产品力（Anker） |
| shouzichew | 周受资 | Shou Zi Chew | zh | 全球化代表，监管听证应对 |
| chennian | 陈年 | Chen Nian | zh | 失败者复盘（凡客） |
| zhuangshuai | 庄帅 | Zhuang Shuai | zh | 行业观察者，署名专栏拆解 |

### default（默认 5 人）

| slug | 中文名 | 英文名 | 语言 | 视角 / 专长 |
|---|---|---|---|---|
| fusheng | 傅盛 | Fu Sheng | zh | 创始人视角（复用 ai-app-cn） |
| jobs | 乔布斯 | Steve Jobs | en | 产品设计视角 |
| likejia | 李可佳 | Ethan Li | zh | Bot 派教育新物种 |
| wu-jundong | 吴俊东 | Frank Wu | zh | 教育 / 全球化视角，Education becoming 思想派 |
| zhang-yiming | 张一鸣 | Zhang Yiming | zh | 字节系产品视角，全球化 |

### edu-cn（中文教育 / 终身学习）

| slug | 中文名 | 英文名 | 语言 | 视角 / 专长 |
|---|---|---|---|---|
| yuminhong | 俞敏洪 | Michael Yu | zh | 失败重生 IP 化，直播表达 |
| zhangbangxin | 张邦鑫 | Zhang Bangxin | zh | 双减后 AI 转身，使命叙事 |
| likejia | 李可佳 | Ethan Li | zh | Bot 派新物种（复用 default） |
| wu-jundong | 吴俊东 | Frank Wu | zh | Education becoming 思想派（复用 default） |
| salkhan | 萨尔曼·可汗 | Sal Khan | en | AI Tutor 鼻祖，普惠教育 |

### luxury-en（奢侈品 / 时尚）

| slug | 中文名 | 英文名 | 语言 | 视角 / 专长 |
|---|---|---|---|---|
| arnault | 伯纳德·阿尔诺 | Bernard Arnault | en | 收购艺术，Maison 长期价值与 desirability |
| awintour | 安娜·温图尔 | Anna Wintour | en | 行业仲裁人 gatekeeper，编辑内容 |
| cucinelli | 布鲁内罗·库奇内利 | Brunello Cucinelli | en | 人文资本主义，慢生活经营 |
| tomford | 汤姆·福特 | Tom Ford | en | 设计师即 CEO，视觉体系 |
| burton | 莎拉·伯顿 | Sarah Burton | en | 设计师传承，工艺美学 |

### security-cn-global（网络安全 / 企业安全 / AI 安全）

| slug | 中文名 | 英文名 | 语言 | 视角 / 专长 |
|---|---|---|---|---|
| zhouhongyi | 周鸿祎 | Zhou Hongyi | zh | 中国安全心智（复用 ai-app-cn） |
| zhangmingzheng | 张明正 | Steve Chang | zh | 亚洲安全全球化 |
| renzhengfei | 任正非 | Ren Zhengfei | zh | 硬科技长期主义，危机与合规 |
| jensenhuang | 黄仁勋 | Jensen Huang | en | AI 基础设施，生态心智 |
| musk | 马斯克 | Elon Musk | en | 第一性原理技术叙事（复用 auto） |
| satyanadella | 萨提亚·纳德拉 | Satya Nadella | en | 企业级云安全平台与信任 |

### vc-cn（中文投资人）

| slug | 中文名 | 英文名 | 语言 | 视角 / 专长 |
|---|---|---|---|---|
| zhuxiaohu | 朱啸虎 | Zhu Xiaohu | zh | 红海实战派（复用 ai-app-cn） |
| zhanglei | 张磊 | Zhang Lei | zh | 长期主义，品牌护城河 |
| xuxin | 徐新 | Kathy Xu | zh | 消费杀手锏（复用 consumer-cn） |
| leijun | 雷军 | Lei Jun | zh | 跨界 operator VC（复用 auto） |
| shennanpeng | 沈南鹏 | Neil Shen | zh | 平台型超级 LP |

### vc-en（英文 VC / Silicon Valley）

| slug | 中文名 | 英文名 | 语言 | 视角 / 专长 |
|---|---|---|---|---|
| pmarca | 马克·安德森 | Marc Andreessen | en | Software-eats-world 品类叙事 |
| paulg | 保罗·格雷厄姆 | Paul Graham | en | YC first-principles，写作表达 |
| pthiel | 彼得·蒂尔 | Peter Thiel | en | 0-to-1 反竞争，独占式定位 |
| naval | 纳瓦尔 | Naval Ravikant | en | Leverage 与浓缩表达 |
| rhoffman | 里德·霍夫曼 | Reid Hoffman | en | Blitzscaling，网络效应 |

## 四、分维度映射

### 四.1 归包规则

1. **主包唯一**：每位专家评委恰好归入一个主包（品牌 / 文案 / 视觉 / 合规之一），保证“按包组装”时不重不漏。
2. **判定 = 第一发力点**：归包看该评委评审时最具区分度的视角落点——他最先开火、最能拉开分差的那个维度。判定依据优先级：(1) panel yaml 对该评委的定位语（description 与头注）；(2) 评委公开代表作与标志性言论；(3) 所在 panel 的整体定位。
3. **兼项标注**：明显跨维度的评委在主包之外标 0–2 个兼项。兼项不计入主包人数；T4 编排时主包必召回、兼项按议题加召；同一评委在一次评审中只计一次权重，防止双计。
4. **消费者不进四包**：见 §四.3。
5. **不为均分硬塞**：包大小如实反映构成，薄包给扩编建议（§四.4），不挪人凑数。
6. 本映射是设计建议稿：PRD-233 给 T1 的验收标准是“映射评审通过”，评审要调整直接改本节表格即可，不影响 §三 的盘点事实。

### 四.2 映射表（43 位专家）

#### 品牌包（26 位）——看定位、心智与长期品牌资产

| slug | 中文名 | 归包理由 | 兼项 |
|---|---|---|---|
| jiangnanchun | 江南春 | 媒介杠杆与心智占领，品牌定位的锚点评委 | — |
| arnault | 伯纳德·阿尔诺 | 品牌组合经营与 Maison 长期价值、desirability | — |
| zhongshanshan | 钟睒睒 | 品类定义（“大自然的搬运工”）与渠道品牌叙事 | — |
| leijun | 雷军 | 心智占领 + 用户社区，品牌与创始人 IP 一体 | 文案（发布会营销表达） |
| lixiang | 李想 | 产品定义即定位，开创增程品类 | 视觉（产品设计） |
| libin | 李斌 | “用户企业”，社区即品牌资产 | 文案（社区沟通） |
| xuxin | 徐新 | 消费投资“杀手锏”，看品牌可投性与品类冠军相 | — |
| huangzheng | 黄峥 | 下沉市场品类与供应链品牌打法 | — |
| yangjianhui | 阳萌 | 以产品力立品牌（Anker 静默产品力） | 视觉（工业设计与产品体验） |
| chennian | 陈年 | 凡客式品牌透支的失败复盘 | 合规（品牌危机与透支风险） |
| zhuxiaohu | 朱啸虎 | 红海实战派，看品牌变现与模式成立度 | — |
| zhanglei | 张磊 | 长期主义，看品牌护城河 | — |
| shennanpeng | 沈南鹏 | 平台型 LP，看品类机会与品牌可投性 | — |
| wanghuiwen | 王慧文 | 连续创业的品类探索与产品定位判断 | — |
| yangzhilin | 杨植麟 | 以长上下文定义大模型品类，技术品类卡位 | — |
| zhang-yiming | 张一鸣 | 产品全球化与平台品牌势能 | — |
| zhangbangxin | 张邦鑫 | 教育品牌的使命叙事与信任 | 合规（政策敏感行业的品牌存续） |
| salkhan | 萨尔曼·可汗 | 普惠教育品牌使命与信任 | — |
| likejia | 李可佳 | Bot 派“新物种”，以新品类定义教育产品 | — |
| wu-jundong | 吴俊东 | Education becoming，教育理念即品牌定位 | — |
| cucinelli | 布鲁内罗·库奇内利 | 人文资本主义品牌哲学 | 合规（伦理经营叙事的真实性） |
| jensenhuang | 黄仁勋 | 平台生态心智（CUDA）与技术领导品牌 | 文案（主题演讲叙事） |
| musk | 马斯克 | 第一性原理重构品类认知，创始人个人品牌 | 视觉（产品造型语言） |
| pmarca | 马克·安德森 | Software-eats-world 品类创造叙事 | 文案（manifesto 式表达） |
| pthiel | 彼得·蒂尔 | 0→1 独占式定位 | 合规（政治与监管敏感，panel 已注明可 drop） |
| rhoffman | 里德·霍夫曼 | 网络效应决定品牌扩张上限 | — |

#### 文案包（8 位）——看表达、叙事与内容

| slug | 中文名 | 归包理由 | 兼项 |
|---|---|---|---|
| luoyonghao | 罗永浩 | 发布会文案与表达风格，文案包锚点评委 | — |
| zhanglan | 张兰 | 直播话术与餐饮 IP 表达 | — |
| yuminhong | 俞敏洪 | 以直播表达完成品牌重生 | 品牌（IP 化品牌资产） |
| fusheng | 傅盛 | 布道式认知叙事 | 品牌（品类教育即品牌建设） |
| awintour | 安娜·温图尔 | 编辑仲裁，Editor's Letters 定义内容品味 | 视觉（时尚视觉品味） |
| paulg | 保罗·格雷厄姆 | 写作即思考，essay 式清晰表达 | — |
| naval | 纳瓦尔 | 浓缩表达与媒体杠杆 | — |
| zhuangshuai | 庄帅 | 署名专栏拆解，行业叙事写作 | — |

#### 视觉包（4 位）——看设计、美学与视觉识别

| slug | 中文名 | 归包理由 | 兼项 |
|---|---|---|---|
| jobs | 乔布斯 | 产品设计美学，视觉包锚点评委 | 品牌（产品—品牌三位一体） |
| tomford | 汤姆·福特 | 时装视觉体系，设计师即 CEO | — |
| burton | 莎拉·伯顿 | 时装设计传承与工艺美学 | — |
| hexiaopeng | 何小鹏 | 智能汽车造型与座舱体验 | 品牌（智能化品类定位） |

#### 合规包（5 位）——看风险、安全与监管信任

| slug | 中文名 | 归包理由 | 兼项 |
|---|---|---|---|
| zhouhongyi | 周鸿祎 | 中国安全心智，合规包锚点评委 | — |
| zhangmingzheng | 张明正 | 安全产业全球化，企业信任 | — |
| renzhengfei | 任正非 | 危机管理与合规体系，长期风险 | — |
| satyanadella | 萨提亚·纳德拉 | 企业级平台信任与治理 | 品牌（企业平台生态） |
| shouzichew | 周受资 | 监管听证应对一线经验，全球化合规 | — |

### 四.3 跨维度评委与消费者横切组的处理

- **有兼项的评委共 17 位**：leijun、lixiang、libin、yangjianhui、chennian、zhangbangxin、cucinelli、jensenhuang、musk、pmarca、pthiel（品牌包 11 位），yuminhong、fusheng、awintour（文案包 3 位），jobs、hexiaopeng（视觉包 2 位），satyanadella（合规包 1 位）。处理建议统一为“主包 + 兼项标注”：登记册用 `secondary_packs` 字段承载（§六）；编排（T4）按主包必召回、兼项按议题加召；若主包与兼项包结论冲突，以主包口径呈现、兼项意见附注，不并列计权。
- **消费者横切组（3 位，不进四包）**：first-glance-shopper、homework-buyer、brand-skeptic。理由：(1) 他们的题组 C1–C5（第一印象 / 购买意愿 / 价格直觉 / 信任犹豫 / 表达欲）天然横切四个维度，硬塞任一包都会丢信息；(2) PRD-178 已定其结论与专家分开展示、不进专家 Score Matrix，分包不应推翻这条既有口径。建议形态：登记册中单列 `consumer` 横切组，评审编排时作为受众侧校验与四包并行调用。

### 四.4 包规模与不均衡说明

品牌 26 / 文案 8 / 视觉 4 / 合规 5。原因如实写明：mba 评委主体是创始人与投资人，其第一发力点天然聚集在品牌战略层；专职设计背景者只有 luxury-en 的设计师与 jobs 等少数；安全与监管背景者集中在 security panel。

处理建议：(1) T2 落地时四包结构与人数照此不均分布，不做人为平衡；(2) 扩编方向：后续新增评委优先补视觉（平面 / 品牌设计从业者）与合规（法务 / 监管背景），在登记册维护说明中写明；(3) 视觉包人数少但区分度高（设计师视角无可替代），组装评审时建议整包召回。

## 五、四个 sub-pack 设计（T2 落地输入）

包标识为过渡期临时名（正式命名规则待 PRD-227/T1 定版，见 §七）。

| 临时标识 | 一句话定位 | 主包人数 | 典型召回场景 |
|---|---|---|---|
| brand（品牌包） | 先回答“这个品牌是谁、占什么位置”——看定位、心智占领与长期品牌资产的评委组。 | 26 | 新品牌定位审计、品类竞争、品牌资产与可投性评估 |
| copy（文案包） | 看品牌怎么说——名字、话术、发布会与内容表达能否把定位说清、说动人。 | 8 | 命名与 slogan 评审、发布会与直播话术、创始人 IP 表达 |
| visual（视觉包） | 看品牌长什么样——产品与视觉识别是否配得上定位，第一眼是否成立。 | 4 | 产品设计与包装评审、视觉识别系统、高端 / 时尚品牌审计 |
| compliance（合规包） | 看品牌经不经得起查——安全、监管、危机与信任治理视角下的品牌成色。 | 5 | 政企与安全行业品牌、监管敏感行业、出海合规与危机议题 |
| consumer（横切组，非 sub-pack） | 受众侧的一面镜子——第一印象、购买意愿、价格直觉、信任犹豫与表达欲。 | 3 | 与任一 sub-pack 并行，给专家结论加消费者校验 |

## 六、总登记册字段设计（T3 落地输入）

对齐声明：PRD-227 的 T1 规范文档（livepowers #1135）尚未落地，本节“227 必填”为依据 PRD-227 / PRD-233 正文（总登记册 = 检索 / 触发条件 / 验收例，每包一句话定位，命名与版本规则归规范）推导的**最小集**；字段名与口径待 227/T1 定版后逐项对齐，若冲突以 227 为准回改本节。

### 六.1 评委条目

| 字段 | 类别 | 说明 |
|---|---|---|
| judge_id | 227 必填 | 唯一检索键，取评委 slug（如 `jiangnanchun`） |
| name_cn / name_en | 227 必填 | 双语名，检索键 |
| pack | 227 必填 | 主包标识（brand / copy / visual / compliance；消费者填 consumer 横切组） |
| positioning | 227 必填 | 一句话定位：该评委的视角一句话（例：“媒介杠杆与心智占领”） |
| search_keys | 227 必填 | 检索键集合：slug、双语名、所在 panel 名、维度名、专长词 |
| trigger | 227 必填 | 触发条件：何种品牌类型 / 审计议题 / 行业应召回该评委 |
| acceptance_example | 227 必填 | 验收例：一个典型审计场景，期望召回包含该评委 |
| source_panels | mba 扩展 | 所在 panel 列表（席位来源，跨 panel 复用者多值） |
| secondary_packs | mba 扩展 | 兼项包（§四.3），无兼项留空 |
| language | mba 扩展 | zh / en（取 panel yaml 的 language 字段） |
| role | mba 扩展 | expert / consumer |
| conflicts | mba 扩展 | 自冲突规则：审到自家品牌时的 drop 约定（来源：auto、security-cn-global 的 panel 头注 self-conflict rule 与 `metric-brand-auditor/self-conflict.yaml`） |
| weight_default | mba 扩展 | panel 内默认权重（现行均为 1.0） |
| perspective_ref | mba 扩展 | perspective 资料路径（`perspectives/<slug>-perspective/` 形式占位） |

### 六.2 sub-pack 条目

| 字段 | 类别 | 说明 |
|---|---|---|
| pack_id | 227 必填 | 包标识（正式命名待 227 定版） |
| positioning | 227 必填 | 一句话定位（§五已给四包文案） |
| member_count | 227 必填 | 主包人数 |
| search_keys | 227 必填 | 维度名与同义词（如 品牌 / 定位 / 心智） |
| trigger | 227 必填 | 何种审计任务整包召回 |
| acceptance_example | 227 必填 | 一个典型任务，期望组装出该包 |
| member_slugs | mba 扩展 | 主包成员 slug 列表（T2 落地时生成） |
| pack_kind | mba 扩展 | sub-pack / cross-cutting（消费者横切组标 cross-cutting） |

### 六.3 登记册条目示例（结构示意，非真实落地数据）

```yaml
- judge_id: jiangnanchun
  name_cn: <例：江南春>
  name_en: Jiang Nanchun
  pack: brand
  positioning: 媒介杠杆与心智占领
  search_keys: [jiangnanchun, 品牌定位, 心智, 媒介, consumer-cn]
  trigger: 消费品牌定位审计 / 需要判断心智占领与媒介打法时
  acceptance_example: 审计一个新消费品牌，期望品牌包召回包含 jiangnanchun
  source_panels: [consumer-cn]
  secondary_packs: []
  language: zh
  role: expert
  conflicts: []
  weight_default: 1.0
  perspective_ref: perspectives/jiangnanchun-perspective/
```

## 七、命名与版本规则（引用 PRD-227，不自创）

- sub-pack 命名格式、登记册字段名、版本号规则一律以 PRD-227/T1 规范文档（livepowers #1135）定版为准，本文不另立口径。本文中的 `brand / copy / visual / compliance / consumer` 只是过渡期行文标识，不是正式 pack id。
- T2 开工前置动作——227 对齐检查（逐项与定版规范核对，有差异回改本文与 T2 输入）：
  1. 登记册必填字段集与字段名（§六）；
  2. sub-pack 命名格式（§五临时标识是否合规）；
  3. 登记册与 sub-pack 的版本号规则；
  4. 兼项（多包归属）在规范层是否有标准表达——若有，回收本文的 `secondary_packs` 扩展字段，改用规范口径。
- 版本引用方式：T2 / T3 的落地文档须标注所依据的规范版本（如“PRD-227 规范 vX.Y”，版本号以定版文档为准）；规范升版时，本仓跟随更新标注并复查 §六 字段。

## 八、T1 验收自查

| 验收项（PRD-233 T1） | 状态 |
|---|---|
| 43 评委归包完整 | 品牌 26 + 文案 8 + 视觉 4 + 合规 5 = 43，主包无重无漏 |
| 全量盘点 | 46 位去重评委全列（含 3 位消费者的横切安排），与 PRD 的 43 已对账（§二） |
| 四包一句话定位 | §五，T2 可直接引用 |
| 总登记册字段 | §六，标注 227 必填与 mba 扩展，待 227/T1 定版对齐 |
| 命名与版本 | §七，引用 PRD-227，不自创 |
| 只开 PR 不合并、不改 panel 与代码 | 本 PR 仅新增本文档一个文件 |
