# CLAUDE.md — MBA(Metric Brand Auditor)项目笔记

> 给未来每个 Claude 会话:**先读这份再动手**。本文件只记高频、易踩坑、非显然的东西;
> 细节一律指向 `docs/`,不在这里重复。

## 这是什么

MBA = 把品牌影响力拆成**可打分 / 可比较 / 可复盘**的事。一套 Claude Code skill:多位
"人物评委"(perspective)按 7 维度 × 5 镜头对品牌独立打分,Lead 合成版本化报告(雷达图 +
异议热力图 + 影响力构造图 + 90 天建议)。`/mba <brand>` 一行触发,EVOLUTION 模式追踪同一
品牌随时间演化。

- **核心 skill**:`metric-brand-auditor/SKILL.md`
- **评委**:`perspectives/<slug>-perspective/`(43 套),每套 = `SKILL.md` + `references/`
- **面板**:`metric-brand-auditor/panels/*.yaml`(把评委组合成 panel;`industries.yaml` 做映射)
- **MCP server**:`packages/mcp-server`(`mba-mcp-server`,把 panel/评委打包成工具)
- **站点 / API**:`site/` + `site/api/*.json`(**生成物**,见坑 #2)
- **已发布报告**:`published/reports/`

## 文档索引(别重复造轮子)

`docs/01-prd` … `docs/13-mcp-quickstart`。最常用:
- `docs/07-code-standards.md` — 代码 / 内容规范
- **`docs/10-deepening-perspectives.md`** — perspective 深化 SOP(seed→full),含 43 套 tier 追踪表
- `docs/03-architecture.md` / `docs/04-pipeline.md` — 架构与 5 阶段流程
- `docs/12-evolution-tracking.md` · `docs/13-mcp-quickstart.md` · `docs/wuying-usage.md`

---

## ⚠️ 三条最费时间的坑(先看这里)

### 坑 1 — 读一手原文:用 `curl` 走出口代理,**不要用 `WebFetch`**

- `WebFetch` 走 Anthropic 服务端出口,很多源站(`paulgraham.com` 等)对其 UA 回 **403**。
  深化取一手时**不要依赖 WebFetch**。
- 正确姿势(走本会话 `$HTTPS_PROXY` 出口代理 + CA):
  ```bash
  curl -sSL --cacert /root/.ccr/ca-bundle.crt \
       -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36" \
       "<url>"
  ```
- **前提**:CCR 环境 Network access 要放行目标域名(默认 **Trusted** 只放包仓库/GitHub)。
  设为 **Full**(一键放行)或 **Custom** 加白名单;改完**大概率要新开会话**才生效。
- 验证放行是否生效:`curl -sS "$HTTPS_PROXY/__agentproxy/status"` 看 `recentRelayFailures`;
  `connect_rejected`=该域名被出口策略挡住(不是源站的错)。
- 中文站:知乎 / 百度百科 / 微博 / 澎湃常反爬或 JS 登录墙(curl 拿不到正文);
  **36氪 / 新浪财经 / 腾讯新闻 / 企业官网(如 anker.com.cn)/ 公众号文章(部分)** 可 curl。
- PDF:`pip install pdfminer.six`;若报 `_cffi_backend` / cryptography panic,先 `pip install --upgrade cffi`。

### 坑 2 — 改了**任何** `SKILL.md` → 必须重生成两个派生产物,否则 CI 必红

SKILL 的 front-matter `description:` 与 `## Core Mental Models` 标题会被生成器读取:
```bash
python3 scripts/build_agents_api.py                       # → site/api/*.json
python3 packages/mcp-server/scripts/generate-personas.py  # → packages/mcp-server/src/llm/{personas,panels}.generated.ts
```
CI 漂移检查:`panel-validation.yml` 跑 `build_agents_api.py --check`;`mcp-ci.yml` 跑
`generate-personas.py` 后 `git diff --quiet`。忘了重生成 = **validate-panels / mcp-ci `test` 失败**。
(注:`site/api/index.json` 的 `generated_at` 时间戳每次会变,但 `--check` 会忽略它,不算漂移。)

### 坑 3 — 反捏造是本项目立身之本(anti-fabrication)

- 引号内的引用**必须是源站/语料里逐字存在的原话**。写入前 `grep -F` 验证;
  **中文按去空格匹配**(CJK 无词间空格,把引用和语料都 `re.sub(r'\s+','')` 后再比)。
- **✅ 现已机器强制(2026-07-10)**:`scripts/perspective-tools/firewall_check.py` 校验每套 SKILL
  「心智模型 / 关键引用」区的 `>` 逐字引用**必须**在本套 `references/research/*.md` 语料里规范化后逐字存在,
  已接入 `panel-validation.yml` **硬 gate**(引一句 research 里没有的话 = CI 红)。本地先跑:
  `python3 scripts/perspective-tools/firewall_check.py`(可带单套路径)。**这把"反捏造"从人工纪律升级成门禁,
  但它只保证 SKILL⊆research;research 本身对不对(引用是否真是那人说的)仍靠 provenance 标注 + 人工 `grep -F` 源站。**
- **禁止**:LLM 凭空生成的"风格化引言";把维基当一手;把已被本人公开否认/道歉的内容当正面 DNA。
- **provenance 要如实标**:
  - 半一手(如 Thiel 的 CS183 = Blake Masters 记录的讲课笔记)→ 标"Masters' notes of Thiel's lecture"。
  - 二手(记者访谈)→ 只引其中本人的直接引语并标注,或不逐字引。
  - 原文已删的合集(如黄峥公众号名篇)→ 标"原文已删,据 X 整理合集";关键引用与另一来源交叉核对。
  - 对谈里**主持人/记者的话**要与**本人的话**分开,不能混引。
- **`quality_check.py` 的"一手来源占比"是 SKILL `## Sources` 段的标签词粗代理(阈值 50%),
  不是 SOP §3 的 ≥80% gate。** 真实一手占比按**引用计数**算(如 paulg 93%、vc-en 各 ~90%);
  §3 的 80% 门槛以引用计数为准,并在 Sources 段写明真实数字。

---

## perspective 深化 SOP(seed → full)

完整流程见 `docs/10`。要点:
- **seed** = `SKILL.md`(过 `check_structure`)+ `references/research/quotes.md`;
  **full** = seed + `references/research/01-06.md`(6 路一手调研)。
- 6 路文件命名固定:`01-writings` / `02-conversations` / `03-expression-dna` /
  `04-external-views`(唯一二手路)/ `05-decisions` / `06-timeline`。
- 质量底线(§3):≥30 条一手引用、≥80% 一手(按引用计)、≥5 决策启发式、≥5 表达样例。
- SKILL 从 research **回填重蒸馏**:6 个 `### 模型N`(各带已验证引用 + 日期 + research 锚点 +
  明确**局限/盲区/anti-application**)、≥2 条**张力/Tension**、表达DNA(含 ≥3 个:句式/词汇/
  语气/节奏/幽默/引用/口头禅)、诚实边界 ≥3、Anti-Fabrication 红线、Self-Conflict Rule、Sources。
- **参照模板**:英文人物看 `paulg-perspective`;中文人物看 `renzhengfei-perspective`。
- 时代性观点**锁定年份**(如"founder mode"=2024),别把晚期观点安到早期口吻上。
- 收尾更新 `docs/10 §6`:把 slug 从 seed 表移到 FULL 列。

## 提交前必跑(本地跑 = CI 镜像)

```bash
python3 scripts/perspective-tools/check_structure.py                 # 全部 43 套结构必须 OK
python3 scripts/perspective-tools/firewall_check.py                  # 反捏造硬 gate:SKILL 引用全部逐字命中 research(坑 #3)
python3 scripts/perspective-tools/quality_check.py <path/to/SKILL.md># 必须 6/6(CI 只对本 PR 改动的 SKILL 阻断)
python3 scripts/validate_panels.py                                   # panel 能解析
python3 scripts/build_agents_api.py --check                          # site/api 无漂移(坑 #2)
python3 packages/mcp-server/scripts/generate-personas.py             # 再 git diff --quiet 确认无漂移
```
动了 `packages/mcp-server/` 另跑:`pnpm --filter mba-mcp-server typecheck && ... test && ... build`。

## 环境 & 约定

- monorepo:**pnpm workspace**(Node ≥20,pnpm ≥9)。深化取数的临时文件放 scratchpad,**别进仓库**。
- Wuying 云浏览器(`scripts/wuying/`、`docs/wuying-usage.md`)本为抓中文站;截至 2026-07 免费档
  `GetLink` 报 400,多数情况**"Full 出口 + curl"更省事**。
- **Git / PR**:conventional commit;合并走 **squash**(每个 PR 落成一个 `(#NN)` 提交)。
  只在用户明确要求时开 PR。若 designated 分支的 PR 已合并 → 把分支从最新 `main` 重置再做新活
  (旧提交都是已合并历史,`--force-with-lease` 推送 OK)。
