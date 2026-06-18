# Panels —— 字段参考 / 怎么写一个新 panel

5 镜头是固定的尺子,**坐在尺子后面打分的人是可换的**。本目录下每个 yaml 都是一份"评委名单",
SKILL.md Phase 0 router 会按四层优先级选其中一份用。

> 上层概念(为什么要做 panel / 跨品牌调用规则 / 与 perspective skill 的关系)在仓库根
> `README.md §4`。本文件只解释**字段级**细节 —— 怎么写、什么字段、resolver 会怎么找它。

---

## 1. 一个最小可用的 panel

```yaml
name: solo
display_name: Solo Judge
description: 速读用,只放一位评委
judges:
  - slug: fusheng
```

只有 `name` 和 `judges[*].slug` 是必填。其它字段都可省略,resolver 会用默认值兜底
(display_name 回退到 slug、language 回退到 `zh`、portrait 走 emoji/monogram、weight 默认 `1.0`)。

---

## 2. 字段参考

### Top-level

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | ✓ | panel 标识符,必须与文件名(去 `.yaml`)一致。`--panel <name>` 引用的就是这个 |
| `display_name` | string | – | 人类可读名,用于报告头部 / `/mba panels` 列表。缺省时显示 `name` |
| `description` | string | – | 一两句话说明这个 panel 适合什么场景。`/mba panels` 显示这个 |
| `judges` | list | ✓ | 评委列表,至少 1 位。3 / 5 / 7 位都合法,不强制 5 位 |

### `judges[*]`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `slug` | string | ✓ | 必须能在 `${PERSPECTIVES_PATH}` 任一目录下找到 `<slug>-perspective/SKILL.md`,否则该评委 `MISSING`、panel 自动降级为 N-of-M |
| `display_name_cn` | string | – | 中文显示名。缺省时 = `slug` |
| `display_name_en` | string | – | 英文显示名。缺省时 = `slug` |
| `language` | enum: `zh` / `en` | – | 该评委在 `reviews/<slug>.md` 里用哪种语言落笔。缺省 `zh` |
| `portrait` | string | – | 头像文件名(相对 `${IMAGES_DIR}`)。缺省走 emoji / monogram 兜底 |
| `weight` | float | – | Phase 5 算 mean 的权重。缺省 `1.0`。雷达图 / 异议热力图按 raw score 画,不被权重污染 |

> `slug` 一定要跟 perspective skill 的目录名前缀严格对齐:`fusheng-perspective/` ⇒
> slug 写 `fusheng`,**不要**写 `fusheng-perspective`、`Fusheng`、`fu-sheng`。

---

## 3. 加一个新评委 —— 端到端 6 步

> 假设要加 `pmarca`(Marc Andreessen)。

```text
1. 复制视角 skill 模板
   cp -r ../../perspectives/fusheng-perspective ../../perspectives/pmarca-perspective

2. 改 ../../perspectives/pmarca-perspective/SKILL.md frontmatter
   - name: pmarca-perspective
   - description: Marc Andreessen / a16z 创始合伙人 ...
   - 显式触发 / 不要激活 / anti-fabrication 段全部改完

3. 跑 6 路并行调研填 references/research/01-06.md
   /research Marc Andreessen --persona-mode
   (01 身份卡 / 02 表达 DNA / 03 心智模型 / 04 决策启发式 /
    05 反共识立场 / 06 anti-fabrication 边界)

4. (可选)放一张插画头像到 ../../assets/judges/pmarca.jpg
   严禁真人照片,插画 / 卡通 / monogram 都行

5. 单独跑一次确认 perspective 自己可用
   /pmarca-perspective 帮我看一眼龙虾这个事

6. 注册进 panel —— 在某个 yaml 的 judges: 下面追加:
     - slug: pmarca
       display_name_cn: 安德森
       display_name_en: Marc Andreessen
       language: en
       portrait: pmarca.jpg
```

第 3 步是大头 —— "像不像"靠的是 80% 一手访谈/文章/播客 transcript 的高密度调研,
不是 frontmatter 里的几句口令。

---

## 4. 写一个新 panel —— 4 步

```text
1. 选一个语义化的 name(同时是文件名)
   tech-cn / vc-en / consumer-cn / solo / china-edu ...

2. 复制 default.yaml 改名
   cp default.yaml tech-cn.yaml

3. 改 name / display_name / description / judges
   - judges 至少 1 位
   - 每位 slug 必须能 resolve 到 sibling perspective skill

4. 验证
   /mba panels show tech-cn        # 打印解析后的 yaml
   /mba <test-brand> --panel tech-cn --quick --no-judges   # 不真打分,只走 Phase 0 把 panel.yaml 写下来
```

不需要"deploy" —— 文件落地就是注册完成,git 一 commit 跨机器都能用。

---

## 5. Resolver 行为 —— Phase 0 怎么选 panel

每次 `/mba <brand>` 走以下顺序解析,**先命中先用**:

```
CLI --panel <name>            (显式 panel)
  > CLI --industry <name>     (行业 hint,查 industries.yaml)
  > reports/<brand-slug>/panel.yaml 里 panel: <name> 字段
  > metric-brand-auditor/panels/default.yaml
```

具体场景见仓库根 `README.md §4.4`。这里只补几条本目录相关的实现细节:

- Resolver 只在 `${PANELS_DIR}` 下找(默认 `${SKILL_DIR}/panels`,可被 `MBA_PANELS_DIR`
  env 覆盖)。不在仓库其它地方 fallback。
- 如果 `--panel <name>` 或 `--industry <name>` 指定的文件不存在,Phase 0 直接 ABORT
  并提示用户 —— **不**静默回退到 default,因为静默回退会让人以为换 panel 成功了。
- `--industry` 是 `--panel` 的便捷别名:实质就是查表 `industries.yaml` 拿 panel 名,
  然后走同一套 resolver / 写同一份 brand 绑定。

### 5.1  行业映射 —— `industries.yaml`

格式极简,一行一个 `<industry-name>: <panel-name>`:

```yaml
auto: auto                  # 汽车 / 主机厂 / 新能源车
ev: auto                    # 电动车别名 → 复用 auto panel
consumer-cn: consumer-cn    # 中文消费品(panel 已建,当前是 skeleton)
consumer: consumer-cn       # alias
# gaming-cn: gaming-cn      # 注释掉 = wishlist,resolver 看不见
```

校验是 **lazy** 的 —— 这个文件是**行业路线图**,可以列还没建 panel 的行业。Phase 0
不会在 /mba 启动时全表扫;只有用户实际跑 `--industry <name>` 时才校验那一行对应的
panel 文件:

| 调用 | 行为 |
|---|---|
| `--industry auto`(已建)| ✓ 解析到 `auto.yaml`,正常往下 |
| `--industry consumer-cn`(skeleton)| ✓ 解析到 `consumer-cn.yaml`,提示 synthesis-only 降级 |
| `--industry foo`(没注册)| ✗ ABORT "industry 'foo' not registered. Known: auto, ev, consumer-cn, ..." |
| `--industry <new>` 映射到缺失 panel | ✗ ABORT "industry mapped to panel '<panel>' but panels/<panel>.yaml doesn't exist — build it first (§3)" |
| 没传 `--industry`,但 industries.yaml 里有未建 panel 的行业 | 完全不影响 —— 不走 industry 路径就不校验 |

加新行业可以走两步法:**先**把映射行写进 industries.yaml(声明意图),**再**按 §3
建对应的 perspective skill + panel yaml。期间用户跑 `--industry <new>` 会拿到清晰报错。

一个 panel 可以被多个 industry 别名共用 —— 上面的 `auto` 和 `ev` 就是这样,
`consumer-cn` 和 `consumer` 也是。简写别名很有用,别滥用(别名 > 3 个就乱了)。

行业名建议:小写短名 / 不要空格 / 不要中文(`auto` / `edu-cn` / `consumer-cn` 是好名字)。

### 5.2  Skeleton panel —— "评委还没建" 状态

panel yaml 顶部加 `status: skeleton` 字段标记"占位 / 预览 panel",作用:

- Phase 0.2 加载到这种 panel 时会打印一行明确提示,告诉用户这套 panel 还没完全毕业
- 区分"用户误删了 perspective skill" 和 "panel 本身就是占位等评委到位"

`auto.yaml` 曾经是全员占位;v0.2.19 之后,5 位汽车评委(马斯克 / 雷军 / 李想 /
何小鹏 / 李斌)的 perspective skill 都已存在,可用于 MBA Phase 4。当前状态是:

- `leijun`:full v1,6/6 路调研已落地。
- `musk` / `lixiang` / `hexiaopeng` / `libin`:production-seed v1,6/6 路调研 +
  `quotes.md` URL-anchor bank 已落地。仍可继续增强 timestamp quote pass 和插画头像。

跑 `/mba byd --industry auto` 会:

1. resolve 到 `auto.yaml`
2. 检测到 auto panel 已是可运行状态
3. Phase 4 调用 5 位汽车评委打分
4. Phase 5 合成报告 + HTML

评评委自己的公司或强关联产品时,使用对应 `--panel-drop`。例如评小米 /
Redmi / Xiaomi Auto / SU7:

```bash
/mba xiaomi --industry auto --quick --panel-drop leijun
```

如果保留 conflicted judge,他的输出只能当 founder self-check,不能当中立横评。

这是有意设计的"渐进可用":其它 skeleton panel 即使评委没到位,合成报告本身也有价值。
等评委填齐后,删掉 `status: skeleton` 字段,这个 panel 就自动从 skeleton 升级到正式状态。

### 5.3  Self-conflict judges —— 品牌与评委有关联时怎么处理

有些行业 panel 会包含"行业创始人 / CEO"视角。这个视角在评别的品牌时有价值,但评
自己公司或强关联产品时会有利益冲突。规则:

- 如果品牌与某个 judge 强关联,优先在本次运行使用 `--panel-drop <slug>`。
- 如果用户明确要保留该 judge,该 judge 只能作为"创始人自检"输出,不能给中立横评分。
- Lead 合成报告必须显式标注 conflict,不要把该分数混进平均分。
- 这种规则先写在 panel 文档和 perspective skill 里;未来可升级为 resolver runtime check。

当前已知规则:

| Panel | Judge | Strongly associated brands | Default action |
|---|---|---|---|
| `auto` | `musk` | Tesla / SpaceX / X / Twitter / xAI / Neuralink / Starlink / The Boring Company | use `--panel-drop musk`; if kept, self-check only |
| `auto` | `leijun` | Xiaomi / Redmi / Xiaomi Auto / 小米 / 小米汽车 / SU7 | use `--panel-drop leijun`; if kept, self-check only |
| `auto` | `lixiang` | Li Auto / 理想汽车 / 理想 / 车和家 / 汽车之家 | use `--panel-drop lixiang`; if kept, self-check only |
| `auto` | `hexiaopeng` | XPeng / 小鹏 / 小鹏汽车 / MONA / UC / UC 浏览器 | use `--panel-drop hexiaopeng`; if kept, self-check only |
| `auto` | `libin` | NIO / 蔚来 / Onvo / 乐道 / Firefly / 萤火虫 / 易车网 | use `--panel-drop libin`; if kept, self-check only |
| `security-cn-global` | `zhouhongyi` | 360 / 奇虎 360 / 三六零 / 360 安全 / 奇富科技 | use `--panel-drop zhouhongyi`; if kept, self-check only |
| `security-cn-global` | `zhangmingzheng` | Trend Micro / 趋势科技 | use `--panel-drop zhangmingzheng`; if kept, self-check only |
| `security-cn-global` | `renzhengfei` | Huawei / 华为 / 华为云 / 鸿蒙 / 昇腾 / 鲲鹏 / 海思 | use `--panel-drop renzhengfei`; if kept, self-check only |
| `security-cn-global` | `jensenhuang` | NVIDIA / CUDA / GeForce / DGX / Omniverse | use `--panel-drop jensenhuang`; if kept, self-check only |
| `security-cn-global` | `satyanadella` | Microsoft / Azure / Microsoft Security / Defender / Sentinel / GitHub / LinkedIn / Copilot | use `--panel-drop satyanadella`; if kept, self-check only |
| `ai-app-cn` | `yangzhilin` | 月之暗面 / Moonshot AI / Kimi | use `--panel-drop yangzhilin`; if kept, self-check only |
| `ai-app-cn` | `wanghuiwen` | 美团 / Meituan / 光年之外 / Light Years Beyond | use `--panel-drop wanghuiwen`; if kept, self-check only |
| `ai-app-cn` | `zhuxiaohu` | 金沙江创投 / GSR Ventures 被投组合 | use `--panel-drop zhuxiaohu`; if kept, self-check only |
| `ai-app-cn` | `fusheng` | 猎豹移动 / Cheetah / OpenClaw / 猎户星空 | use `--panel-drop fusheng`; if kept, self-check only |
| `ai-app-cn` | `zhouhongyi` | 360 / 奇虎 360 / 纳米 AI | use `--panel-drop zhouhongyi`; if kept, self-check only |
| `edu-cn` | `yuminhong` | 新东方 / New Oriental / 东方甄选 / 新东方在线 | use `--panel-drop yuminhong`; if kept, self-check only |
| `edu-cn` | `zhangbangxin` | 好未来 / TAL / 学而思 / 学而思网校 | use `--panel-drop zhangbangxin`; if kept, self-check only |
| `edu-cn` | `salkhan` | Khan Academy / Khanmigo / Schoolhouse.world | use `--panel-drop salkhan`; if kept, self-check only |
| `edu-cn` | `likejia` | BotLearn / Aibrary | use `--panel-drop likejia`; if kept, self-check only |
| `edu-cn` | `wu-jundong` | Aibrary / TAL 系 | use `--panel-drop wu-jundong`; if kept, self-check only |
| `vc-en` | `pmarca` | a16z / Andreessen Horowitz 被投组合 | use `--panel-drop pmarca`; if kept, self-check only |
| `vc-en` | `paulg` | Y Combinator / YC 被投(Airbnb / Dropbox / Stripe …) | use `--panel-drop paulg`; if kept, self-check only |
| `vc-en` | `pthiel` | Founders Fund / Palantir / PayPal 系被投 | use `--panel-drop pthiel`; if kept, self-check only |
| `vc-en` | `naval` | AngelList / 其天使被投组合 | use `--panel-drop naval`; if kept, self-check only |
| `vc-en` | `rhoffman` | Greylock / LinkedIn / Microsoft / 其被投组合 | use `--panel-drop rhoffman`; if kept, self-check only |
| `vc-cn` | `zhuxiaohu` | 金沙江创投 / GSR Ventures 被投组合 | use `--panel-drop zhuxiaohu`; if kept, self-check only |
| `vc-cn` | `zhanglei` | 高瓴 / Hillhouse 被投组合 | use `--panel-drop zhanglei`; if kept, self-check only |
| `vc-cn` | `xuxin` | 今日资本被投组合(京东 / 网易 …) | use `--panel-drop xuxin`; if kept, self-check only |
| `vc-cn` | `leijun` | 小米 / 顺为资本被投组合 | use `--panel-drop leijun`; if kept, self-check only |
| `vc-cn` | `shennanpeng` | 红杉中国 / Sequoia China 被投组合(携程 / 如家 …) | use `--panel-drop shennanpeng`; if kept, self-check only |
| `consumer-cn` | `jiangnanchun` | 分众传媒 / 其重要广告客户 | use `--panel-drop jiangnanchun`; if kept, self-check only |
| `consumer-cn` | `zhongshanshan` | 农夫山泉 / 养生堂 | use `--panel-drop zhongshanshan`; if kept, self-check only |
| `consumer-cn` | `luoyonghao` | 锤子科技 / 交个朋友 | use `--panel-drop luoyonghao`; if kept, self-check only |
| `consumer-cn` | `yangjianhui` | 安克创新 / Anker(eufy / soundcore / Nebula);判 = 阳萌 | use `--panel-drop yangjianhui`; if kept, self-check only |
| `consumer-cn` | `zhanglan` | 俏江南 / 麻六记 | use `--panel-drop zhanglan`; if kept, self-check only |
| `cross-border` | `huangzheng` | 拼多多 / Pinduoduo / Temu / 多多买菜 | use `--panel-drop huangzheng`; if kept, self-check only |
| `cross-border` | `shouzichew` | TikTok / 字节跳动 / 小米(曾任职) | use `--panel-drop shouzichew`; if kept, self-check only |
| `cross-border` | `yangjianhui` | 安克创新 / Anker(阳萌) | use `--panel-drop yangjianhui`; if kept, self-check only |
| `cross-border` | `chennian` | 凡客诚品 | use `--panel-drop chennian`; if kept, self-check only |
| `cross-border` | `zhuangshuai` | 百联咨询的咨询客户(分析师,利益相对轻) | use `--panel-drop zhuangshuai`(可酌情); if kept, self-check only |
| `luxury-en` | `arnault` | LVMH 旗下任何 maison(Dior / LV / Tiffany / Bulgari …) | use `--panel-drop arnault`; if kept, self-check only |
| `luxury-en` | `cucinelli` | Brunello Cucinelli(品牌) | use `--panel-drop cucinelli`; if kept, self-check only |
| `luxury-en` | `awintour` | Vogue / Condé Nast / Met Gala / 其公开力捧的品牌 | use `--panel-drop awintour`; if kept, self-check only |
| `luxury-en` | `tomford` | Tom Ford(品牌)/ Gucci(其任职过) | use `--panel-drop tomford`; if kept, self-check only |
| `luxury-en` | `burton` | Givenchy / Alexander McQueen | use `--panel-drop burton`; if kept, self-check only |

示例:

```text
/mba xiaomi --industry auto --quick --panel-drop leijun
/mba tesla --industry auto --quick --panel-drop musk
/mba li-auto --industry auto --quick --panel-drop lixiang
/mba xpeng --industry auto --quick --panel-drop hexiaopeng
/mba nio --industry auto --quick --panel-drop libin
/mba 360 --industry security-cn-global --quick --panel-drop zhouhongyi
/mba trend-micro --industry security-cn-global --quick --panel-drop zhangmingzheng
/mba microsoft-security --industry security-cn-global --quick --panel-drop satyanadella
/mba kimi --industry ai-app-cn --quick --panel-drop yangzhilin
/mba meituan --industry ai-app-cn --quick --panel-drop wanghuiwen
/mba new-oriental --industry edu-cn --quick --panel-drop yuminhong
/mba tal --industry edu-cn --quick --panel-drop zhangbangxin
/mba stripe --industry vc-en --quick --panel-drop paulg
/mba jd --industry vc-cn --quick --panel-drop xuxin
/mba nongfu-spring --industry consumer-cn --quick --panel-drop zhongshanshan
/mba temu --industry cross-border --quick --panel-drop huangzheng
/mba dior --industry luxury-en --quick --panel-drop arnault
```

---

## 6. 校验规则 —— Phase 0 拒绝加载的 panel

下面任一条命中,Phase 0 拒绝该 panel,要求修复:

| 规则 | 失败时的报错 |
|---|---|
| `name` 缺失或与文件名不一致 | `panel name "<x>" doesn't match filename <file>.yaml — rename one of them` |
| `judges` 为空或缺失 | `panel "<name>" has no judges — a panel needs ≥ 1 entry` |
| 任一 `judges[*].slug` 在 `${PERSPECTIVES_PATH}` 下找不到 sibling skill | `judge "<slug>" not found — looked in: <paths>. Drop from panel or install the perspective skill first.` 默认行为是降级为 N-of-M 并打 `judges_incomplete` flag;若全员 MISSING 则强制 `--no-judges` |
| `language` 不是 `zh` / `en` | `judge "<slug>" language="<x>" — only zh/en supported` |
| `weight` 不是正数 | `judge "<slug>" weight must be > 0` |

`portrait` 缺失或文件不存在**不**是失败 —— 回落到 emoji/monogram。

---

## 7. 不要踩的 4 条

写 / 改 panel 时这几条不能踩,踩了会破坏跨版本可读性:

1. **不要直接改已经在用的 panel 的 `judges:`**(尤其 default)—— 旧品牌的
   `reports/<brand>/panel.yaml` 记的是 panel 名,evolution 重跑时会读到新名单,
   导致 v{n+1} 跟 v{n} 不可比。要换评委时 → 起一个新 panel 名。
2. **不要把同一个 `slug` 列两次** —— 静默 dedupe 会让人意外少打一份分。
3. **不要给 `language` 写 `bi` / `auto` / `mixed`** —— Phase 4 的 sub-agent 需要一个明确的
   落笔语言,混合语会让 Lead 合成时挑哪种作为引用都不对。
4. **不要让 panel 里全是同一类视角**(比如 5 个全是 VC、5 个全是产品经理)——
   panel 的价值在"异议的几何分布",同质 panel 让 σ 永远低于阈值、Phase 5 出不来戏剧张力。
   /mba 不会校验这个,但 Phase 5 的 dissent 热力图会一眼看出来。

---

## 8. 自带 panel 一览

跑 `/mba panels` 看当前目录下所有 panel 和它们的 judge 列表 + 用过的次数。

最低限度本目录会有:

- `default.yaml` —— 5 人混合 panel,/mba 的兜底
- `auto.yaml` —— 汽车 / EV panel,可运行
- `security-cn-global.yaml` —— 网络安全 / 企业安全 / AI 安全 panel,可运行
- `ai-app-cn.yaml` —— AI 应用 / Agent 层 panel,可运行(v1 production-seed)
- `edu-cn.yaml` —— 中文教育 / 终身学习 panel,可运行(v1 production-seed)
- `vc-en.yaml` —— 英文 VC panel,可运行(v1 production-seed)
- `vc-cn.yaml` —— 中文 VC panel,可运行(v1 production-seed)
- `consumer-cn.yaml` —— 中文消费品 / 快消 panel,可运行(v1 production-seed)
- `cross-border.yaml` —— 出海 / 跨境电商 panel,可运行(v1 production-seed)
- `luxury-en.yaml` —— 奢侈品 / 时尚 panel,可运行(v1 production-seed)—— 至此 **10/10 panel 全部可运行**
- `industries.yaml` —— 行业 → panel 映射表,被 `--industry` flag 查询(本身不是 panel,
  也不会被 `--panel` 解析到)
