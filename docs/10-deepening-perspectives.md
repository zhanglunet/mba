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

**FULL(20)**:

早期三套 panel(default / auto / security-cn-global)的评委(15):

`fusheng` · `jobs` · `likejia` · `wu-jundong` · `zhang-yiming` · `musk` · `leijun` · `lixiang` ·
`hexiaopeng` · `libin` · `zhouhongyi` · `zhangmingzheng` · `renzhengfei` · `jensenhuang` · `satyanadella`

**vc-en 面板全员 full(2026-07-07 深化,5/5)**:`paulg` · `naval` · `pmarca` · `pthiel` · `rhoffman`
—— **首个整面板从 seed 全部升到 full 的行业 panel**。均由各自一手语料(curl 走已放行出口代理全文抓取)
6 路蒸馏、每条 verbatim 金句逐条比对源站校验,`check_structure` + `quality_check` 6/6 双过。
按引用计一手占比:`paulg` 93% · `naval` 92% · `pmarca` 92% · `pthiel` 90% · `rhoffman` ~90%,均过 §3 的 ≥80% gate。

> 各判官取数要点(深化时沿用):
> - `paulg` — 28 篇 paulgraham.com essay(2001–2024)。
> - `naval` — nav.al「How to Get Rich」系列 + happiness essays(2018–2021);**这些是他自网发布的播客转录,非手写文章**,已全程标注,Nivi 的提问与 Naval 的话区分开,借用观点(四种运气→Andreessen 等)标注来源。
> - `pmarca` — pmarchive.com「Pmarca Guide to Startups」(2007)+ a16z「It's Time to Build」(2020)/「Techno-Optimist Manifesto」(2023);两套语域相差十年,已按年份锁定不混用。「Why Software Is Eating the World」(2011 WSJ)不在语料,只按名归属不逐字引。
> - `pthiel` — **语料是 Blake Masters 记录的 Thiel 斯坦福 CS183 课堂笔记(2012,semi-first-party),每条都标「Masters' notes of Thiel's lecture」**,唯一纯一手是 Cato「The Education of a Libertarian」(2009);《Zero to One》与「Competition is for losers」只按名归属、明确标注不逐字引;政治内容排除。
> - `rhoffman` — **可读一手语料偏 2023–2025 AI 期**(reidhoffman.org essays/speeches);经典 canon(Blitzscaling / Start-up of You / Masters of Scale / 网络效应)源站不可读,只按名归属不逐字引,偏斜已在 01/04/SKILL 如实标注;seed 里未经核实的两条 maxim 已移除。

> 注:`quality_check` 内建的「一手占比」字段是 SKILL Sources 段的**标签词粗代理**(阈值 50%),读数 62–67%;§3 gate 以上面按引用计的真实占比为准。

**seed → 待深化(23)**——2026-06 新建的行业 panel 评委:

| 首次所属 panel | seed 评委(slug) | 取数难度 |
|---|---|---|
| ai-app-cn | `yangzhilin` `wanghuiwen` `zhuxiaohu` | 中文一手,建议 Wuying |
| edu-cn | `yuminhong` `zhangbangxin` `salkhan` | 俞/张中文(Wuying);Sal Khan 英文(可 WebFetch) |
| vc-cn | `zhanglei` `xuxin` `shennanpeng` | 中文一手,建议 Wuying |
| consumer-cn | `jiangnanchun` `zhongshanshan` `luoyonghao` `yangjianhui` `zhanglan` | 中文一手,建议 Wuying |
| cross-border | `huangzheng` `shouzichew` `chennian` `zhuangshuai` | 黄峥致股东信/周受资听证(英文 PDF,可 WebFetch);陈年/庄帅中文 |

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
