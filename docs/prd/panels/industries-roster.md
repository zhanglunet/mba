# Industries Roster — 按行业推荐评委名单

**Status:** 候选菜单,等用户勾选
**Created:** 2026-05-17
**用法:** 在 §2 选择栏里把 `[ ]` 改成 `[x]` 表示"这套先建",剩下的留空。
       改完保存,直接 commit;后续 `/research` 阶段会按勾选清单跑。

---

## 1. 评估口径

每个 panel 标三个维度:

| 维度 | 1★ | 5★ |
|---|---|---|
| **源密度** | 评委公开材料(演讲 / 访谈 / 微博 / 书籍 transcript)极少 | 第一人称材料海量,可以撑起 6 路并行调研 |
| **构建难度** | 模板能直接套,3-5 天 / 人 | 政治敏感 / 已故 / 静默 / 跨语种,7-10 天 / 人 |
| **与 default 复用** | 0 = 全部要新建 perspective skill;N = 有 N 位可复用现有 skill |

候选评委后面标 ⚠ = 有特殊风险(沉默 / 政治敏感 / 在押 / 已故),
建之前 anti-fabrication 边界段要重写得更严。

---

## 2. 选择栏(在这里勾选 ☑ / ☐)

8 套全部已勾选(2026-05-17,通过"先按照这个吧"接受);骨架 panel.yaml 都已落到
`./` 同级,industries.yaml 映射已登记。下一步是按 §5 流程逐位建 perspective skill。

| 骨架已建 | Panel | 评委(5 人) | 源密度 | 难度 | 复用 |
|---|---|---|---|---|---|
| ☑ | `auto` | 马斯克 / 雷军 / 李想 / 何小鹏 / 李斌 | ★★★★ | ★★★ | 0 |
| ☑ | `consumer-cn` | 江南春 / 张兰 / 罗永浩 / 杨建辉 / 钟睒睒 ⚠ | ★★★★ | ★★ | 0 |
| ☑ | `ai-app-cn` | 杨植麟 / 王慧文 / 周鸿祎 / 傅盛(复用) / 朱啸虎 | ★★★★ | ★★★ | 1 |
| ☑ | `vc-cn` | 朱啸虎 / 张磊 / 徐新 / 雷军(顺为) / 沈南鹏 ⚠ | ★★★ | ★★★ | 0 |
| ☑ | `vc-en` | Marc Andreessen / Paul Graham / Peter Thiel ⚠ / Naval Ravikant / Reid Hoffman | ★★★★★ | ★★ | 0 |
| ☑ | `edu-cn` | 俞敏洪 / 张邦鑫 / 李可佳(复用) / 吴俊东(复用) / Sal Khan | ★★★ | ★★ | 2 |
| ✅ | `cross-border` | 黄峥 / 阳萌 / 周受资 / 陈年 / 庄帅 | ★★★ | ★★★★ | 5 |
| ☑ | `luxury-en` | Bernard Arnault / Anna Wintour / Brunello Cucinelli / Tom Ford / Sarah Burton | ★★★ | ★★★ | 0 |

**其它候选(暂不推荐):** gaming-cn(选手极沉默)/ f&b-cn(可作为 consumer-cn 子集)/
biotech(政治敏感 + 源差)/ real-estate(行业敏感)。

---

## 3. 每套 panel 详细评委名单 + 一句话理由

### 3.1 `auto` — 汽车/电动车 ✅ 已草

| slug | 评委 | 一句话理由 |
|---|---|---|
| musk | 马斯克 | 全英文 + 工业 + 太空 + 政治杠杆,差异度最高 |
| leijun | 雷军 | 工程师 + 营销天才 + 价值观主义者三轴清晰,推荐先建 |
| lixiang | 李想 | 微博 6800+ 条 / 增程派 / 用户社区 |
| hexiaopeng | 何小鹏 | 智驾派 / 出海 / 工程派 |
| libin | 李斌 | 高端服务 / 换电体系 / 资本紧绷 |

详见 `auto-judges.md` 这份 PRD。

---

### 3.2 `consumer-cn` — 消费品/快消

| slug | 评委 | 一句话理由 |
|---|---|---|
| jiangnanchun | 江南春(分众)| 媒介杠杆 + 品类教育第一人,讲品牌教科书 |
| zhanglan | 张兰(麻六记)| 短视频时代 IP 化典范,失败-翻身-翻身的强叙事 |
| luoyonghao | 罗永浩(锤子→直播→AR)| 一次失败一次重生,反共识表达 DNA 极强 |
| yangjianhui | 阳萌 / Steven Yang(Anker;slug 沿用历史命名,旧标"杨建辉"系误标)| 跨境产品力 + 工程师式静默优秀,反"营销天花板" |
| zhongshanshan | 钟睒睒(农夫山泉)⚠ | 极致渠道 + 价值标签,但**几乎不公开发言** |

**替补建议:** 钟睒睒源太少,可替换为周成建(美邦)或喜茶聂云宸或卫龙刘卫平。

---

### 3.3 `ai-app-cn` — AI 应用/Agent 层

| slug | 评委 | 一句话理由 |
|---|---|---|
| yangzhilin | 杨植麟(月之暗面/Kimi)| 大模型创业现役选手,Token 经济视角 |
| wanghuiwen | 王慧文(光年之外)| **失败者**复盘视角,稀缺 |
| zhouhongyi | 周鸿祎(360→AI)| 安全 + 反共识商业化,跟傅盛对话最有戏 |
| fusheng | 傅盛(复用 default)| 反共识 + Agent 派 |
| zhuxiaohu | 朱啸虎(金沙江)| VC 对 AI 应用的"卷"派,跟杨植麟正面冲突 |

**潜在替换:** 朱啸虎是 VC 不是 operator,可替换为杨振(LiblibAI)或李一舟(争议)
或孔令博(智谱)。

---

### 3.4 `vc-cn` — 中文投资人

| slug | 评委 | 一句话理由 |
|---|---|---|
| zhuxiaohu | 朱啸虎(金沙江)| 红海实战派 / 卷王哲学 |
| zhanglei | 张磊(高瓴)| 长期主义 + 把企业当宗教 |
| xuxin | 徐新(今日资本)| 消费洞察 + "杀手锏"派 |
| leijun | 雷军(顺为,如 auto 已建则复用)| 跨界 VC + operator,跟纯财务投资者对照 |
| shennanpeng | 沈南鹏(红杉)⚠ | 平台型超级 LP,**几乎不公开发言** |

**替补建议:** 沈南鹏源极少,可替换为李丰(峰瑞)或王嘉廉(华兴)或熊俊(蓝湖资本)。

---

### 3.5 `vc-en` — 英文 VC

| slug | 评委 | 一句话理由 |
|---|---|---|
| pmarca | Marc Andreessen | "软件吃世界",反共识写手 |
| paulg | Paul Graham | YC / first principles essay 量大 |
| pthiel | Peter Thiel ⚠ | 0→1 / 反竞争论;**政治敏感** |
| naval | Naval Ravikant | Leverage / wealth without luck 框架完整 |
| rhoffman | Reid Hoffman(LinkedIn/Greylock)| 网络效应 + Blitzscaling |

**潜在替换:** Peter Thiel 政治敏感,部分用户场景不合适,可替换为 Bill Gurley(Benchmark)
或 Vinod Khosla(Khosla Ventures)。

---

### 3.6 `edu-cn` — 教育/终身学习

| slug | 评委 | 一句话理由 |
|---|---|---|
| yuminhong | 俞敏洪(新东方→东方甄选)| 失败重生 + IP 化教科书 |
| zhangbangxin | 张邦鑫(TAL→AI)| 双减后的 AI 教育转身 |
| likejia | 李可佳(复用 default)| Bot 派 / 新物种 |
| wu-jundong | 吴俊东(复用 default)| Education becoming / inner core |
| salkhan | Sal Khan(Khan Academy)| AI Tutor 鼻祖,英文视角 |

**复用 2 位**(likejia + wu-jundong)使本 panel 工程量从 5 份降到 3 份。

---

### 3.7 `cross-border` — 出海/跨境电商

| slug | 评委 | 一句话理由 |
|---|---|---|
| huangzheng | 黄峥(Pinduoduo / Temu)⚠ | 极致下沉 + 算法供应链,**2021 后沉默** |
| yangjianhui | 阳萌(Anker,与 consumer-cn 复用)| 静默优秀 |
| shouzichew | 周受资(Shou Zi Chew,TikTok / 字节;替换原 SHEIN 许仰天——其几乎无一手资料)| 全球化出海 + 数据主权与信任 + 地缘合规 |
| chennian | 陈年(凡客)| **失败者**视角,稀缺 |
| zhuangshuai | 庄帅(零售电商研究)| 行业观察者,弥补创始人沉默 |

**注意:** 这套 panel 沉默选手占 2/5,真正能挖出第一人称材料的只有杨建辉 + 陈年 + 庄帅。
要么接受"低密度 panel"(评分会偏 withheld),要么把黄峥 / 张勇换成更 vocal 的人
(比如李宁的非凡中国 CEO 钱炜 / 致欧家居 / 跨境通)。

---

### 3.8 `luxury-en` — 奢侈品/时尚

| slug | 评委 | 一句话理由 |
|---|---|---|
| arnault | Bernard Arnault(LVMH)| 收购艺术家 + 工艺信仰 |
| awintour | Anna Wintour(Vogue)| gatekeeper / 行业仲裁人 |
| cucinelli | Brunello Cucinelli | 慢生活 + 人文主义经营 |
| tomford | Tom Ford | 设计师同时是 CEO 的代表 |
| burton | Sarah Burton(McQueen)| 设计师传承视角(替代已故 Lagerfeld) |

---

## 4. 选型说明

- **复用 slug 省事**:`edu-cn` 里复用 likejia / wu-jundong,`ai-app-cn` 复用 fusheng,
  `cross-border` / `consumer-cn` 共享杨建辉,`vc-cn` / `auto` 共享雷军。复用越多,
  整体 perspective skill 数量越少
- **沉默选手要谨慎**:蔡浩宇等源密度差;SHEIN 许仰天因几乎无一手资料,已用周受资替换。
  (钟睒睒 / 沈南鹏 / 黄峥 经核验有足够公开一手材料,已建成 v1)。原注:
  即使名头响,做 perspective 实际是用第三人称报道倒推他们怎么想 —— 跟
  anti-fabrication 边界冲突,建议替换或缓建
- **失败者视角稀缺且珍贵**:王慧文 / 陈年 / 罗永浩判分维度跟成功者不同,每个 panel
  留 1 位失败者会让异议热力图更好看
- **政治敏感人选**:Peter Thiel / 黄峥这类标了 ⚠,建之前 anti-fab 段要写更严
- **女性占比偏低**:候选名单基本是男性,因为高源密度 + 在赛道顶层的女性创始人偏少
  (Anna Wintour / 张兰 / 徐新 / Sarah Burton 这几位算)。如果用户能补充,优先采纳。

---

## 5. 下一步(用户拍板后跑)

1. 用户在 §2 表里勾选要建的 panel
2. 用户在 §3.x 里把不喜欢的评委划掉 / 换成自己想要的人(可以用 strikethrough 标记)
3. commit + push 这份修改后的 roster
4. 我读这份 roster 启动:
   - 第一阶段:写所有勾选 panel 的 panel.yaml 骨架(全部 `status: skeleton`)
     + 在 industries.yaml 里登记映射
   - 第二阶段:按 PRD 推荐的 Path A,每次单跑一位评委的 perspective skill
     (先建雷军、再 voicepriority 排第二的评委、依此类推)
5. 每位 perspective skill 建完都 dogfood + commit;勾掉 panel 里对应 slug 的
   `status: skeleton` 标记
