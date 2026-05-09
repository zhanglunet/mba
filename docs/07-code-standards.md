# 07 — 代码与文档规范

本文档给贡献者用。约定 SKILL.md 怎么写、命名怎么取、Python 脚本怎么风格、commit 怎么写。

## 1. SKILL.md 写作规范

### 1.1 必须的 frontmatter

```yaml
---
name: <slug>             # 小写 + 连字符,与 / 命令对应
description: |           # 多行,Claude 用此判断激活
  一句中文 + 一句英文短摘要
  IF user asks "..." THEN ...
  NOT WHEN: ...
  Trigger patterns: ...
---
```

`description` 必须包含 IF / THEN / NOT WHEN 三条 —— 这是 Claude Code 判断激活与否的关键提示。

### 1.2 章节顺序

```
# 标题
> 一句话副标题

## What you orchestrate (or What this does)
## Parameters
## Output layout
## Phase 0 — Router (FIRST STEP, ALWAYS)
## Phase 1F — ...
## Phase 2F — ...
...
## EVOLUTION MODE
...
```

每个 Phase:

- `## Phase X — 名称`(半角短横线 + 全角空格)
- `### Output` 写哪个文件
- `### GATE` 标记停顿点
- 给 sub-agent 的 prompt 必须用 ``` 块包

### 1.3 路径约定

- 引用文件用 `~/mba/<path>`(假定用户克隆到 `~/mba`)
- 相对路径(在同一 skill 内)用 `references/<file>` / `reports/<brand>/`
- **不要用 `/Users/john/...` 这样的绝对路径**(除占位符 `<MAC_USER>` / `<MAC_HOST>`)

### 1.4 触发规则纪律

- 显式触发列出至少 3 个用户原话变体
- 路由 / 排他("不要激活")条款必须有,防误触发
- 与兄弟 skill 重叠时,显式说"X 走我,Y 走兄弟"

## 2. Perspective skill 必备章节

每个 `*-perspective/SKILL.md` 必须有这 4 个章节:

1. **frontmatter** + 触发规则
2. **核心心智模型 / 决策启发式**(≥ 5 条编号项)
3. **表达 DNA**(怎么说话,带样例,展示 ≥ 3 句"这就是 TA 会说的话")
4. **Anti-fabrication 红线** —— 必须出现以下任一关键词:
   - "不要激活"
   - "不可编造"
   - "anti-fabrication"
   - "留白"

`references/research/` 下的 6 路调研文件命名固定:

```
01-writings.md
02-conversations.md
03-expression-dna.md
04-external-views.md
05-decisions.md
06-timeline.md
```

> 命名固定是为了未来 add_judge 的 schema 校验能批量校验。

## 3. 命名规范

### 3.1 brand-slug

`<brand-slug>` 必须:

- 全小写
- 只用 ASCII 字母 / 数字 / 连字符
- ≥ 3 字符
- 不带后缀(`.com` / `-skill` 之类)

例:

- `openclaw` ✓
- `OpenClaw` ✗(大写)
- `字节豆包` ✗(非 ASCII)→ 用 `bytedance-doubao`
- `aibrary-2026` ✓(可带年份/季度版本)

### 3.2 dimension-slug

dimension 文件名 `dimension_<n>_<slug>.md`:

- `<n>` 是 1-7
- `<slug>` 与 `dimensions.md` 的 H2 标题对应,小写连字符:

| n | slug |
|---|---|
| 1 | `founder-narrative` |
| 2 | `product-positioning` |
| 3 | `distribution-channels` |
| 4 | `community-pr` |
| 5 | `visual-verbal-identity` |
| 6 | `competitive-landscape` |
| 7 | `reception-sentiment` |

### 3.3 judge-name

5 内置评委 slug 固定:

- `fusheng`
- `jobs`
- `likejia`
- `wu-jundong`
- `zhang-yiming`

自定义评委(MCP 化后):`^[a-z][a-z0-9-]{1,30}$`,不要和内置同名。

### 3.4 audit-id(MCP 化后)

格式:`<brand-slug>-<yyyymmdd>-<HHMM>`。例:`openclaw-20260509-2030`。

## 4. Python 脚本风格

`wuying_open.py` / `test_wuying.py` 当前是参考实现。新增脚本应:

### 4.1 .env 加载

不依赖第三方库,用项目内的 `load_env()` 模式:

```python
from pathlib import Path

def load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env

env = load_env(Path.home() / "mba" / ".env")
```

理由:零依赖、跨 macOS/Linux、跟仓库其他脚本一致。

### 4.2 异常处理

只 catch 真正能恢复的异常,其他向上抛。**不要** `except Exception: pass`。

```python
try:
    client.delete(session)
    print("cleanup: session deleted")
except Exception as e:
    print(f"cleanup failed: {e!r}", file=sys.stderr)
```

### 4.3 不打印 secrets

Anthropic key / wuying key 即使在 debug 输出里也不能完整打印。

> 当前 `wuying_open.py` 在 teardown 命令里把 api_key 内联进了 print —— **新代码不要这么做**(已知 issue,修在 v0.3 backlog)。

### 4.4 单文件优先

工具脚本如非必要不引入 third-party 框架。Python 标准库 + `agentbay` 已经够用。

## 5. Markdown 风格

- 表格不用 HTML,用 GFM
- 代码块必须标语言:` ```bash` / ` ```python` / ` ```yaml`
- 列表层级 ≤ 3
- 长链接放链接文本,例:`[36氪](https://36kr.com/p/xxx)` 不要裸 URL
- 多语言混排:中文用全角标点,英文术语保留半角
- 标题层级跳跃只在确实有意义时(`#` → `##` → `###`,不要跳到 `####`)

## 6. Commit message

格式(已用过的):

```
<type>: <一句话主题>

- 具体改动 1
- 具体改动 2
- ...

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

`<type>` 限定:

- `feat` — 新功能
- `fix` — bug 修复
- `docs` — 只改文档
- `chore` — 构建 / 发版 / 杂项
- `refactor` — 不改行为的重构

主题用中文 OK(README 是中文为主),subject ≤ 72 字符。

## 7. 版本与发布

- 用 SemVer:`vMAJOR.MINOR.PATCH`
- 文档更新 = patch(`v0.2.x`)
- 新 skill / 新评委 = minor(`v0.3.0`)
- SKILL.md 不向后兼容的改动 = major(慎重,目前还没到 1.0)
- 每个 minor+ 版本配套 GitHub Release,release notes 列出所有 commit summary

## 8. 文档维护原则

文档分两类:

- **行为描述类**(`03-architecture.md` / `04-pipeline.md` / `08-extending.md`)—— 必须跟 SKILL.md 同步,改 SKILL.md 必更新文档
- **意图 / 设计类**(`01-prd.md` / `02-product-design.md` / `07-code-standards.md` / `mcp-server-design.md`)—— 设计稳定,只在大版本变时更新

每个 docs/ 文件顶部理想有 `Status:` 和 `Last verified:` 元信息(`mcp-server-design.md` 已示例)。本批次新文档暂时省略,待 v0.3 补上。

## 9. 评委(perspective)的内容质量底线

每位评委最少需要:

- ≥ 30 条调研引用(分布在 6 路 research 文件)
- ≥ 80% 一手来源占比(本人写作 / 本人接受的访谈 / 本人主持的播客)
- 至少 5 条决策启发式
- 至少 5 个表达样例(展示 in-character 是什么样)

**禁止**:

- 把维基百科条目复制粘贴当 research 来源
- 用 ChatGPT / Claude 凭空生成的"风格化引言"
- 已被本人公开否认或道歉的内容,作为正面 DNA 引用

## 10. PR / Issue 模板(建议)

PR description 至少含:

- 做了什么(one-liner)
- 为什么(链接到 issue / discussion)
- 对存量影响(是否动了 SKILL.md / 是否改了产物路径)
- 测试方式(跑了哪个 demo brand)

Issue 报 bug 至少含:

- 复现步骤
- 期望 vs 实际
- 相关 phase / sub-agent / 评委
- log / 报告片段(脱敏后)
