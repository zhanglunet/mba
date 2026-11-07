# mba 评委包总登记册（REGISTRY）

> PRD-233/T3（trend #1167）落地。机读权威源：[`registry.json`](registry.json)（4 包 + 消费者横切组 / 共 46 位评委）；本文件由其生成——生成命令 `python3 scripts/judge_registry.py --render > REGISTRY.md`，**禁止手改本文件**，两载体不一致即漂移（规范 §7，测试机判）。
>
> 技能包分层规范：skill-pack-layering-spec@1.0.0（livepowers PRD-227/T1 草案）。本登记册为评委归属与检索的单一事实源（规范 §7）；映射数据源为 T1 docs/plans/2026-10-26-judge-pack-layering.md §四.2（映射是数据不是代码）。
>
> 「分层 + 总登记册」组织形态借鉴 AgriciDaniel/claude-seo（MIT License，Copyright (c) Daniel Agrici，https://github.com/AgriciDaniel/claude-seo）：只复用形态，未复用其代码与文本。

检索：`python3 scripts/judge_registry.py <触发词…>`（例：`定位`、`slogan`、`监管`、`消费者`）。

## mba-brand — 先回答「这个品牌是谁、占什么位置」——看定位、心智占领与长期品牌资产的评委组。

version 0.1.0 ｜ spec_version 1.0.0 ｜ 整包召回时机：新品牌定位审计、品类竞争、品牌资产与可投性评估

| 评委 | 触发条件 | 定位（T1 归包理由） | panels |
|---|---|---|---|
| **arnault**（伯纳德·阿尔诺） | "用 Bernard Arnault 视角", "LVMH / Arnault 会怎么看", "star brand lens", "luxury empire perspective". | 品牌组合经营与 Maison 长期价值、desirability | luxury-en |
| **chennian**（陈年） | 「用陈年视角」「凡客会怎么看」「极致单品 / 复盘视角」。 | 凡客式品牌透支的失败复盘 | cross-border |
| **cucinelli**（布鲁内罗·库奇内利） | "用 Brunello Cucinelli 视角", "Cucinelli 会怎么看", "humanistic capitalism lens", "quiet luxury / craftsmanship perspective". | 人文资本主义品牌哲学 | luxury-en |
| **huangzheng**（黄峥） | 「用黄峥视角」「拼多多 / 多多会怎么看」「本分 / 新电商视角」。 | 下沉市场品类与供应链品牌打法 | cross-border |
| **jensenhuang**（黄仁勋） | “用 Jensen Huang 视角”, “黄仁勋怎么看”, “NVIDIA 式平台生态”, “AI 基础设施评委”, “accelerated computing lens”. | 平台生态心智（CUDA）与技术领导品牌 | security-cn-global |
| **jiangnanchun**（江南春） | 「用江南春视角」「分众会怎么看」「抢占心智 / 一词定位 / 饱和攻击视角」。 | 媒介杠杆与心智占领，品牌定位的锚点评委 | consumer-cn |
| **leijun**（雷军） | 心智占领 + 用户社区，品牌与创始人 IP 一体 | 心智占领 + 用户社区，品牌与创始人 IP 一体 | auto、vc-cn |
| **libin**（李斌） | “用户企业”，社区即品牌资产 | “用户企业”，社区即品牌资产 | auto |
| **likejia**（李可佳） | Bot 派“新物种”，以新品类定义教育产品 | Bot 派“新物种”，以新品类定义教育产品 | default、edu-cn |
| **lixiang**（李想） | 产品定义即定位，开创增程品类 | 产品定义即定位，开创增程品类 | auto |
| **musk**（马斯克） | "use Elon Musk's perspective", "what would Musk say", "Musk view", "first-principles take on this", "if Musk were judging this brand", "Tesla/SpaceX founder lens". | 第一性原理重构品类认知，创始人个人品牌 | auto、security-cn-global |
| **pmarca**（马克·安德森） | "用 Marc Andreessen 视角", "pmarca / a16z 会怎么看", "software eats the world lens", "product/market fit lens", "Andreessen perspective". | Software-eats-world 品类创造叙事 | vc-en |
| **pthiel**（彼得·蒂尔） | "用 Peter Thiel 视角", "Thiel / Founders Fund 会怎么看", "zero to one lens", "contrarian monopoly perspective". | 0→1 独占式定位 | vc-en |
| **rhoffman**（里德·霍夫曼） | "用 Reid Hoffman 视角", "Reid / Greylock 会怎么看", "blitzscaling lens", "network effects perspective", "superagency lens". | 网络效应决定品牌扩张上限 | vc-en |
| **salkhan**（萨尔曼·可汗） | "用 Sal Khan 视角", "Khan Academy 会怎么看", "mastery learning lens", "AI tutor / Khanmigo perspective". | 普惠教育品牌使命与信任 | edu-cn |
| **shennanpeng**（沈南鹏） | 「用沈南鹏视角」「红杉中国会怎么看」「做多中国 / 赛手第一 VC 视角」。 | 平台型 LP，看品类机会与品牌可投性 | vc-cn |
| **wanghuiwen**（王慧文） | 「用王慧文视角」「王慧文 / 老王会怎么看」「清华产品课方法论」「规模效应/马太效应视角」。 | 连续创业的品类探索与产品定位判断 | ai-app-cn |
| **wu-jundong**（吴俊东） | Education becoming，教育理念即品牌定位 | Education becoming，教育理念即品牌定位 | default、edu-cn |
| **xuxin**（徐新） | 「用徐新视角」「今日资本会怎么看」「消费品牌 VC / 第一品牌视角」。 | 消费投资“杀手锏”，看品牌可投性与品类冠军相 | consumer-cn、vc-cn |
| **yangjianhui**（阳萌） | 「用阳萌视角」「Anker / 安克会怎么看」「第一性 / 求极致视角」「出海创造者视角」。 | 以产品力立品牌（Anker 静默产品力） | consumer-cn、cross-border |
| **yangzhilin**（杨植麟） | 「用杨植麟视角」「Moonshot / Kimi 会怎么看」「模型层创始人视角」。 | 以长上下文定义大模型品类，技术品类卡位 | ai-app-cn |
| **zhang-yiming**（张一鸣） | 产品全球化与平台品牌势能 | 产品全球化与平台品牌势能 | default |
| **zhangbangxin**（张邦鑫） | 「用张邦鑫视角」「好未来 / 学而思会怎么看」「教育科技公平视角」「教不好等于抢钱」。 | 教育品牌的使命叙事与信任 | edu-cn |
| **zhanglei**（张磊） | 「用张磊视角」「高瓴会怎么看」「长期主义价值投资视角」。 | 长期主义，看品牌护城河 | vc-cn |
| **zhongshanshan**（钟睒睒） | 「用钟睒睒视角」「农夫山泉会怎么看」「产品主义 / 反低价内卷视角」。 | 品类定义（“大自然的搬运工”）与渠道品牌叙事 | consumer-cn |
| **zhuxiaohu**（朱啸虎） | 「用朱啸虎视角」「朱啸虎会怎么看」「VC 应用层视角」「金沙江会投吗」。 | 红海实战派，看品牌变现与模式成立度 | ai-app-cn、vc-cn |

## mba-copy — 看品牌怎么说——名字、话术、发布会与内容表达能否把定位说清、说动人。

version 0.1.0 ｜ spec_version 1.0.0 ｜ 整包召回时机：命名与 slogan 评审、发布会与直播话术、创始人 IP 表达

| 评委 | 触发条件 | 定位（T1 归包理由） | panels |
|---|---|---|---|
| **awintour**（安娜·温图尔） | "用 Anna Wintour 视角", "Vogue / Wintour 会怎么看", "taste gatekeeper lens", "fashion editor perspective". | 编辑仲裁，Editor's Letters 定义内容品味 | luxury-en |
| **fusheng**（傅盛） | 布道式认知叙事 | 布道式认知叙事 | ai-app-cn、default |
| **luoyonghao**（罗永浩） | 「用罗永浩视角」「老罗会怎么看」「天生骄傲 / 创始人 IP 视角」。 | 发布会文案与表达风格，文案包锚点评委 | consumer-cn |
| **naval**（纳瓦尔） | "用 Naval 视角", "Naval Ravikant 会怎么看", "leverage & specific knowledge lens", "Naval perspective". | 浓缩表达与媒体杠杆 | vc-en |
| **paulg**（保罗·格雷厄姆） | "用 Paul Graham 视角", "pg / YC 会怎么看", "make something people want lens", "Paul Graham perspective". | 写作即思考，essay 式清晰表达 | vc-en |
| **yuminhong**（俞敏洪） | 「用俞敏洪视角」「老俞会怎么看」「新东方 / 东方甄选视角」「教培转型怎么看」。 | 以直播表达完成品牌重生 | edu-cn |
| **zhanglan**（张兰） | 「用张兰视角」「麻六记会怎么看」「话题营销 / 餐饮直播视角」。 | 直播话术与餐饮 IP 表达 | consumer-cn |
| **zhuangshuai**（庄帅） | 「用庄帅视角」「零售电商分析师怎么看」「商业模式 / 供应链拆解视角」「货场人视角」。 | 署名专栏拆解，行业叙事写作 | cross-border |

## mba-visual — 看品牌长什么样——产品与视觉识别是否配得上定位，第一眼是否成立。

version 0.1.0 ｜ spec_version 1.0.0 ｜ 整包召回时机：产品设计与包装评审、视觉识别系统、高端 / 时尚品牌审计

| 评委 | 触发条件 | 定位（T1 归包理由） | panels |
|---|---|---|---|
| **burton**（莎拉·伯顿） | "用 Sarah Burton 视角", "McQueen / Givenchy 会怎么看", "atelier / craftsmanship lens", "creative-director-as-steward perspective". | 时装设计传承与工艺美学 | luxury-en |
| **hexiaopeng**（何小鹏） | 智能汽车造型与座舱体验 | 智能汽车造型与座舱体验 | auto |
| **jobs**（乔布斯） | 产品设计美学，视觉包锚点评委 | 产品设计美学，视觉包锚点评委 | default |
| **tomford**（汤姆·福特） | "用 Tom Ford 视角", "Tom Ford 会怎么看", "glamour / branding lens", "creative director perspective". | 时装视觉体系，设计师即 CEO | luxury-en |

## mba-compliance — 看品牌经不经得起查——安全、监管、危机与信任治理视角下的品牌成色。

version 0.1.0 ｜ spec_version 1.0.0 ｜ 整包召回时机：政企与安全行业品牌、监管敏感行业、出海合规与危机议题

| 评委 | 触发条件 | 定位（T1 归包理由） | panels |
|---|---|---|---|
| **renzhengfei**（任正非） | “用任正非视角”, “华为式长期主义”, “硬科技组织怎么看”, “政企基础设施品牌”, “Ren Zhengfei perspective”. | 危机管理与合规体系，长期风险 | security-cn-global |
| **satyanadella**（萨提亚·纳德拉） | “用 Satya Nadella 视角”, “微软 CEO 怎么看”, “企业级云安全平台”, “Microsoft Security lens”, “Nadella perspective”. | 企业级平台信任与治理 | security-cn-global |
| **shouzichew**（周受资） | 「用周受资视角」「TikTok 会怎么看」「全球平台 / 出海信任 / 地缘合规视角」。 | 监管听证应对一线经验，全球化合规 | cross-border |
| **zhangmingzheng**（张明正） | “用张明正视角”, “Trend Micro 创办人怎么看”, “亚洲安全全球化”, “企业安全品牌长期信任”, “Steve Chang perspective”. | 安全产业全球化，企业信任 | security-cn-global |
| **zhouhongyi**（周鸿祎） | “用周鸿祎视角”, “红衣教主怎么看”, “360 安全视角”, “中国网络安全心智评委”, “攻防实战判断这个品牌”. | 中国安全心智，合规包锚点评委 | ai-app-cn、security-cn-global |

## mba-consumer（横切组，非 sub-pack） — 受众侧的一面镜子——第一印象、购买意愿、价格直觉、信任犹豫与表达欲。

version — ｜ spec_version — ｜ 整包召回时机：与任一 sub-pack 并行，给专家结论加消费者校验（C1–C5 题组）

| 评委 | 触发条件 | 定位（T1 归包理由） | panels |
|---|---|---|---|
| **first-glance-shopper**（第一眼顾客（模拟人设）） | “用普通消费者视角看”、“第一印象怎么样”、“会不会买”、 “消费者第一眼”、“购买意愿”。 | 受众侧的一面镜子——第一印象、购买意愿、价格直觉、信任犹豫与表达欲。 | consumer-mixed |
| **homework-buyer**（功课型买家（模拟人设）） | “用普通消费者视角看”、“买前做功课的人怎么看”、“宣传点能信吗”、 “购买意愿”、“会不会推荐给家人”。 | 受众侧的一面镜子——第一印象、购买意愿、价格直觉、信任犹豫与表达欲。 | consumer-mixed |
| **brand-skeptic**（品牌怀疑者（模拟人设）） | “用普通消费者视角看”、“多疑的消费者怎么看”、“这牌子可信吗”、 “翻车记录”、“购买意愿”。 | 受众侧的一面镜子——第一印象、购买意愿、价格直觉、信任犹豫与表达欲。 | consumer-mixed |

版本政策：全库 lockstep 0.1.0（规范 §6.3 允许的本地政策；包内评委增删或定位变更至少升 MINOR）
