# 06 — 安装与环境

本文档帮你从零把 MBA 跑起来。

## 1. 系统前置

| 项 | 最低 | 备注 |
|---|---|---|
| OS | macOS 12+ / Linux | Windows 走 WSL2 |
| Python | 3.9+ | 用于 scripts/wuying/open.py / scripts/wuying/smoke_test.py |
| Claude Code | 当前版本 | https://docs.claude.com/ |
| Anthropic API key | 任意计费档 | https://console.anthropic.com/ |
| 阿里云无影 API key | 免费 Lite 即可 | https://wuying.aliyun.com/ (可选,跳过则用 --quick) |

## 2. 克隆仓库

```bash
git clone https://github.com/zhanglunet/mba.git ~/mba
cd ~/mba
```

> **路径不再 hardcode**:从 v0.2.14 起,SKILL.md 用运行时符号(`${SKILL_DIR}` / `${REPORTS_DIR}` /
> `${PERSPECTIVES_PATH}` / `${PANELS_DIR}` / `${IMAGES_DIR}`)在 Phase 0 解析一次后复用。`~/mba` 只是
> 推荐的克隆位置和文档示例,放别处也能跑 —— Lead 会以 SKILL.md 自身所在目录为 `${SKILL_DIR}`,并按
> `${SKILL_DIR}/..` → `~/.claude/skills` → `~/skills` 的顺序探测兄弟 perspective skill。可用环境变量
> `MBA_REPORTS_DIR` / `MBA_PANELS_DIR` / `MBA_IMAGES_DIR` 覆盖默认值。

## 3. 配置 .env

```bash
cp .env.example .env
$EDITOR .env
```

填入:

```
WUYING_API_KEY=akm-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
WUYING_IMAGE_ID=browser_latest
```

API key 获取:

1. 登录 https://wuying.aliyun.com/
2. 控制台 → AgentBay → 创建应用(免费 Lite 套餐)
3. 复制应用密钥,粘到 `.env`

`.env` 已在 `.gitignore` 中,不会进版本库。

## 4. 安装 Python 依赖

```bash
pip3 install --user agentbay
```

或用 venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install agentbay
```

## 5. 校验

### 5.1 烟雾测试 wuying API key

```bash
python3 scripts/wuying/smoke_test.py
```

预期输出末尾:

```
[5/5] CDP endpoint: ws://...
cleanup: session deleted via client.delete()
```

> Lite 套餐拿不到 CDP endpoint,会在第 5 步报 "GetLink is an exclusive premium feature for Pro/Ultra"。
> 这不影响 MBA 运行 —— pipeline 自动降级。看到 `SESSION_ID` 创建成功就算 OK。

### 5.2 配置 Claude Code 识别 skill

把仓库加进 Claude Code 的 skill 目录:

**方法 A**(推荐):软链到全局 skills 目录

```bash
mkdir -p ~/.claude/skills
ln -s ~/mba/metric-brand-auditor ~/.claude/skills/mba
ln -s ~/mba/research ~/.claude/skills/research
# 一次性软链全部 15 套 perspective(default + auto + security 三套 panel 的评委)
for d in ~/mba/*-perspective; do
  ln -s "$d" ~/.claude/skills/"$(basename "$d")"
done
```

> 只装 default panel 的话,至少软链 `fusheng / jobs / likejia / wu-jundong / zhang-yiming` 这 5 套;
> 要用 `--industry auto` / `--panel security-cn-global` 就把对应 panel 的评委也链上。缺失的评委
> Phase 4 会标 `MISSING` 并降级为 N-of-M,不会让流水线崩。

**方法 B**:`cd ~/mba` 后在仓库内启动 Claude Code,自动识别同目录下的 `*-perspective/` 和 `metric-brand-auditor/`。

> 如果你的 Claude Code 安装路径里 `~/.claude/skills/` 不存在,可能用的是不同的 skill 加载机制 —— 查 Claude Code 当前版本的官方文档。

### 5.3 烟雾测试 MBA pipeline

```
/mba list
```

应该返回(空仓库):

```
已审计品牌(reports/ 下):
(暂无)
```

### 5.4 跑一份你自己的报告

```
> /mba <你关注的品牌名>
```

走完 Phase 0-5 后,产出 `metric-brand-auditor/reports/<brand-slug>/report.html`。
本机用 `open report.html` 即可看到完整 HTML 报告(雷达图、异议热力图、Mermaid 影响力流程图)。
如果 Mermaid 块显示 "Syntax error",见下文 §6.4。

> ⚠️ **报告隐私:** `metric-brand-auditor/reports/` 已默认在 `.gitignore`,跑完审计的报告**不会**进版本库。
> 如需分享某份特定报告,显式 `git add -f published/reports/<brand>/`(并 review 内容是否合适公开)。

## 6. 故障排除

### 6.1 `/mba` 命令找不到

→ Claude Code 没识别到 skill。检查:

- 软链是否成功:`ls -la ~/.claude/skills/mba` 应指向 `~/mba/metric-brand-auditor`
- 重启 Claude Code(skills 不热加载)
- frontmatter 的 `name` 字段必须是小写 + 连字符,如 `mba` / `fusheng-perspective`

### 6.2 `python3 scripts/wuying/smoke_test.py` 报 ModuleNotFoundError

→ 没装依赖。`pip3 install --user agentbay`,确认在你的 Python path 里。
   `python3 -c "import agentbay"` 应该静默返回 0。

### 6.3 报错 "Permission denied (publickey,password)"

→ SKILL.md 里有些步骤设计为 `ssh <MAC_USER>@<MAC_HOST>`,这是占位符,假定你在另一台机器上跑 Claude Code 通过 SSH 控制本机。

**如果你就是在本机跑**(最常见情况):把那些 ssh 命令理解为本地命令,SKILL.md 里的 `<MAC_USER>@<MAC_HOST>` 可以替换为空(直接本地执行)。

### 6.4 HTML 报告里 Mermaid 显示 "Syntax error"

→ Lead 生成的 Mermaid 字符里有元字符没转义。

**临时方案:**

- 看浏览器控制台的具体报错
- 编辑 `report.md` 里的 Mermaid 块手动修
- 让 Claude Code "重新渲染 reports/<brand>/report.html"

**长期方案:** Phase 5 的 sanity-check 会校验 Mermaid 语法(MCP 化版本会自动跑 headless 检测)。

### 6.5 wuying session 创建后不能 teardown

→ session 累计计费(虽然 Lite 套餐很便宜)。手动清理:

```bash
python3 -c "
from agentbay import AgentBay
from agentbay.session import Session
key = open('.env').read().split('WUYING_API_KEY=')[1].split('\n')[0].strip()
c = AgentBay(api_key=key)
s = Session(c, 's-04xxxxxx')  # 替换你的 session id
c.delete(s)
"
```

或者用 SDK 的 list 方法看当前所有 active session:

```python
from agentbay import AgentBay
c = AgentBay(api_key="akm-...")
print(c.list())  # 注意 SDK 版本不同 list 行为可能不一样
```

### 6.6 Anthropic API 限流

→ Phase 2 / Phase 4 并发 5 个 sub-agent 时如果碰到限流,报告会标注哪个维度/评委失败。

**缓解:**

- 升级到更高 tier(Anthropic 不同消费档位有不同的 RPM/TPM 上限)
- 在 SKILL.md 里临时把每批 sub-agent 数从 5 调到 3

### 6.7 报告生成不出来,卡在 Phase 5

→ Lead 在生成大段 HTML 字符串时偶尔会因 token 上限被切断。**workaround**:

- 重新触发 Phase 5("重新渲染 report.html,基于现有 report.md")
- 或先生成 markdown,过几分钟再单独跑 HTML 渲染

## 7. 升级到新版

```bash
cd ~/mba
git fetch
git pull
```

软链不需要重做。如果新版动了 SKILL.md 的 phase 名(罕见),可能需要重启 Claude Code。

升级到 minor / major 版本前,跑一次 `git status` 确认本地没未提交的改动(免得 merge 冲突)。

## 8. 卸载

```bash
rm -f ~/.claude/skills/mba ~/.claude/skills/research
rm -f ~/.claude/skills/*-perspective    # 清掉全部 15 套 perspective 软链
rm -rf ~/mba
```

注意:`reports/` 下你跑过的所有报告会一起删。要保留的话,先 `cp -r ~/mba/metric-brand-auditor/reports ~/mba-reports-backup/`。

## 9. 多机协作(高级)

如果想团队多人共用同一份 reports/:

1. 把 reports/ 放到团队共享盘 / git submodule
2. SKILL.md 里 `~/mba/metric-brand-auditor/reports/` 改成共享路径
3. 注意 git push 之前 review report 内容(可能含敏感品牌内部信息)

> 团队协作的最佳实践还在演化,RFC 阶段 —— 实际想做请先开 issue 讨论。

## 10. (可选)加入 BotLearn Agent 社区

BotLearn(`https://www.botlearn.ai`)是一个面向 AI agent 的社区,提供入学考试
(benchmark)、技能市场(skillhunt)、agent 社交(post / DM)等功能。本项目
**可选**地把 MBA agent 注册到 BotLearn 跑 benchmark + 浏览社区。

> ⚠️ **重要**:BotLearn SDK 是第三方代码,**不入本仓库版本库**(`.gitignore`
> 已忽略 `skills/botlearn/`)。安装前请自己审计 SDK 内容。本项目对 BotLearn
> 平台不做担保。

### 10.1 安装前提醒(必读)

- BotLearn 的 marketplace 装第三方 skill = **任意代码执行风险**;`archiveUrl`
  来自服务端,无校验、无签名、无审核队列
- 默认 `templates/config.json` **所有权限开关都是 `true`**,与官方 `core/security.md`
  表格里写的"安全默认值"矛盾。**装好后立刻锁权限**(见下文)
- `botlearn.sh scan` 会上传 workspace 根目录所有**全大写 *.md 文件**(50KB
  截断)+ `.claude/settings.json`(redacted)+ 主机指纹。MBA 仓库的 `README.md`
  是其中之一——**README 里的真名 / 团队信息会被上传**
- `botlearn.sh install <skill>` 之前必须**逐个 skill 让 owner 确认**

### 10.2 安装

```bash
cd ~/mba
mkdir -p skills/botlearn
curl -sL https://www.botlearn.ai/sdk/botlearn-sdk.tar.gz | tar -xz -C skills/botlearn
```

验证 SDK 内容(只解压不安装的安全姿势):

```bash
curl -sL https://www.botlearn.ai/sdk/botlearn-sdk.tar.gz -o /tmp/botlearn-sdk.tar.gz
tar -tzf /tmp/botlearn-sdk.tar.gz                    # 看文件列表
shasum -a 256 /tmp/botlearn-sdk.tar.gz               # 记录 hash 做版本追溯
```

### 10.3 注册 + 立即锁权限

```bash
# 用项目化 handle,不暴露真名
bash skills/botlearn/bin/botlearn.sh register "mba-auditor" \
  "MBA = Metric Brand Auditor. Multi-agent brand-influence research + 5-judge review pipeline."
```

注册成功后 SDK 会写 `~/mba/.botlearn/credentials.json`(api_key)和
`config.json`(模板默认权限**全开**)。**立刻覆盖** `config.json` 为锁死版:

```json
{
  "auto_post": false,
  "auto_comment": false,
  "auto_vote": true,
  "auto_dm_approve": false,
  "auto_dm_reply": false,
  "auto_update": false,
  "heartbeat_enabled": true,
  "learning_context_scan": false,
  "learning_retroactive_scan": false,
  "share_project_context_in_posts": false,
  "share_project_context_in_learning": false,
  "auto_benchmark": false,
  "auto_install_solutions": false,
  "auto_report_runs": true,
  "auto_recheck_after_install": false,
  "learning_actionable_install": false,
  "learning_report_to_platform": false,
  "learning_report_privacy": "redacted"
}
```

### 10.4 Claim(必须本人完成)

注册命令最后会打印类似:

```
https://www.botlearn.ai/claim/botlearn_<hex>
```

打开浏览器用 Twitter / Email / Google 登录,把 agent 绑到你的账号——这步
agent 自己做不了,这是好事。

### 10.5 跑入学考试

```bash
bash skills/botlearn/bin/botlearn.sh scan         # 上传环境配置(注意上面的隐私警告)
bash skills/botlearn/bin/botlearn.sh exam-start <config_id>
# 6 道题,scenario / practical 两种,每题答案以文件 + JSON 形式提交
bash skills/botlearn/bin/botlearn.sh exam-submit <session_id>
bash skills/botlearn/bin/botlearn.sh report <session_id> full
```

### 10.6 卸载

```bash
rm -rf ~/mba/skills/botlearn ~/mba/.botlearn
# 同时上 https://www.botlearn.ai 网站把 agent 删除 + 让平台清你的数据
```

> BotLearn 是可选拼图,不影响 MBA 主流水线。本节内容会跟随 BotLearn SDK 演化,
> 用前先 `cat skills/botlearn/SKILL.md` 看一眼当前版本是否还匹配本节描述。
