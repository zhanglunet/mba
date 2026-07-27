# 29 — Cloudflare 命名隧道 + RSSHub 加固(免费社媒线正式接线)

> **前置**:`docs/27` 的 A/B 两步已跑通(RSSHub 容器起来了、微博路由能出真实条目)。
> 本手册接的是 `docs/27 §C` 的"再换稳定 URL"那一步 —— 把临时 `trycloudflare` 换成
> **永久域名 + 鉴权**,这是把 `rss_feeds` 填进仓库的**前置条件**。
>
> **为什么必须换**:临时隧道 URL **重启即变**、进程停即断,填进 `reports-meta.yaml`
> 只会让每日流水线天天请求死链;而且它**默认无鉴权公网可达**——2026-07-27 实测,
> 一台无关的数据中心机器能直接从该 URL 拉到微博数据。
>
> **本手册的验证状态(诚实标注)**:§1 的 ACCESS_KEY 验证、§4 的公网侧验收、§5 的仓库侧
> 占位符机制,都有对应的门禁/自测在仓库里;**§2 的 Cloudflare 控制台步骤按其当前文档编写,
> 未在本会话实操** —— 控制台文案可能与截图时点略有出入,以页面为准,流程不变。

**全程约 20 分钟。顺序不能换**:先上锁(§1),再暴露到公网(§2),否则中间有一段裸奔窗口。

---

## 0. 开工前的三项检查

```bash
# ① RSSHub 活着
curl -s http://localhost:1200/healthz                      # → ok

# ② cloudflared 已装(没有就 brew install cloudflared)
cloudflared --version

# ③ mbabrand.com 的 DNS 确实托管在 Cloudflare —— 命名隧道靠它自动建 CNAME
dig NS mbabrand.com +short                                 # → 应返回 *.ns.cloudflare.com
```

③ 若不是 Cloudflare 的 NS,命名隧道**建不了自定义域名**(可退回 §附录B 的 CLI 方式并用
Cloudflare 提供的 `*.cfargotunnel.com`,但那个域名不便记且仍需 DNS 侧配置)。

---

## 1. 先给 RSSHub 上锁:ACCESS_KEY

```bash
# 1) 生成一串随机密钥。**记到密码管理器里** —— 第 5 步 GitHub secrets 要填同一串。
KEY=$(openssl rand -hex 24); echo "$KEY"

# 2) 重建容器,带上 ACCESS_KEY(原容器没这个环境变量,只能重建)
docker rm -f rsshub
docker run -d --name rsshub --restart unless-stopped -p 1200:1200 \
  -e ACCESS_KEY="$KEY" \
  diygod/rsshub:chromium-bundled

# 3) 本机验:**不带 key 必须被拒**,带 key 必须出 RSS
curl -s -o /dev/null -w "无 key  → %{http_code}\n" "http://localhost:1200/weibo/user/2803301701"
curl -s -o /dev/null -w "带 key  → %{http_code}\n" "http://localhost:1200/weibo/user/2803301701?key=$KEY"
```

**验收标准**:`无 key` 非 200(401/403 都算对),`带 key` = 200。

> ⚠️ **如果"无 key"也返回 200,说明这一版的鉴权参数名不是 `key`** —— RSSHub 的 Access Control
> 历史上有 `key`(明文)与 `code`(签名)两种形式,版本间变过。**别硬猜**:去
> [docs.rsshub.app](https://docs.rsshub.app) 的 Access Control 一节查当前参数名,
> 然后把上面第 3 步重跑一遍。**以这条 curl 的返回码为准,不以本手册为准。**

`/healthz` 通常不受鉴权保护(它是探活端点),返回 200 是正常的,不代表锁没生效 ——
判断依据只看**数据路由**那一条。

---

## 2. 建命名隧道(Cloudflare 控制台,推荐)

1. 打开 **Cloudflare Dashboard** → 左侧 **Zero Trust**(首次进会让你选一个免费 plan,选 Free)。
2. **Networks → Tunnels → Create a tunnel**。
3. 连接器类型选 **Cloudflared** → 隧道名填 `mba-rsshub` → **Save tunnel**。
4. 页面会给出一段安装命令,里面有一长串 **token**(`eyJ...`)。
   **把 token 复制下来存好** —— 它等同于隧道的钥匙。
   > ⚠️ **不要直接跑它给的 `cloudflared service install <token>`** —— 那条命令在 macOS 上要写
   > `/Library/LaunchDaemons`,**需要 sudo**(你装 Docker Desktop 时正是卡在这)。
   > 改用下面这条,不需要 sudo:
   ```bash
   cloudflared tunnel run --protocol http2 --token <粘贴你的 token>
   ```
   > 若报 `flag provided but not defined: -protocol`,把它挪到 `run` 前面:
   > `cloudflared tunnel --protocol http2 run --token <token>`(两种写法在不同版本上都出现过)。
   > `--protocol http2` 的必要性见 `docs/27 §C`:默认 QUIC(UDP 7844)在很多网络被阻断。
5. 控制台的隧道状态变成 **HEALTHY** 后,进 **Public Hostname → Add a public hostname**:
   - **Subdomain**:`rsshub`
   - **Domain**:`mbabrand.com`
   - **Path**:留空
   - **Type**:`HTTP`   **URL**:`localhost:1200`
   - **Save hostname**
6. Cloudflare 会自动在 DNS 里建一条指向 `<隧道UUID>.cfargotunnel.com` 的 CNAME,**你不用手工加**。

到这里 `https://rsshub.mbabrand.com` 就通了,且**重启不变**。

---

## 3. 免 sudo 的开机自启(macOS LaunchAgent)

第 2 步那条命令跑在前台,关终端就停。用**用户级 LaunchAgent**(`~/Library/`,不需要 sudo)常驻:

```bash
mkdir -p ~/Library/LaunchAgents
cat > ~/Library/LaunchAgents/com.mba.cloudflared.plist <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.mba.cloudflared</string>
  <key>ProgramArguments</key>
  <array>
    <string>__CLOUDFLARED__</string>
    <string>tunnel</string>
    <string>run</string>
    <string>--protocol</string><string>http2</string>
    <string>--token</string><string>__TOKEN__</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/cloudflared.log</string>
  <key>StandardErrorPath</key><string>/tmp/cloudflared.err</string>
</dict>
</plist>
PLIST

# 填进真实路径与 token(token 含密钥,plist 权限收紧到只有自己能读)
sed -i '' "s|__CLOUDFLARED__|$(which cloudflared)|" ~/Library/LaunchAgents/com.mba.cloudflared.plist
sed -i '' "s|__TOKEN__|<粘贴你的 token>|"           ~/Library/LaunchAgents/com.mba.cloudflared.plist
chmod 600 ~/Library/LaunchAgents/com.mba.cloudflared.plist

# 加载(现代写法;老系统用 launchctl load -w <plist>)
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.mba.cloudflared.plist
launchctl list | grep cloudflared          # 出现一行即已托管
```

**机器必须在北京时间 10:17 醒着**(每日 discover 的时刻)。macOS 睡眠会断隧道 ——
在**系统设置 → 电池/节能 → 接通电源时防止自动进入睡眠**打开即可(这项不需要命令行、不需要 sudo)。
笔记本合盖仍会睡,长期跑建议插电常开或换台常驻机器。

停止/重载:

```bash
launchctl bootout gui/$(id -u)/com.mba.cloudflared          # 停
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.mba.cloudflared.plist   # 起
tail -20 /tmp/cloudflared.err                                # 看日志
```

---

## 4. 公网侧验收(**这一步不做等于没验证**)

本机 curl 通 **≠** GitHub Actions 通:云上走的是公网这一侧。
**用手机流量或另一台机器测** —— 家里 WiFi 可能命中本地 DNS/回环,测不出真实路径。

```bash
curl -s -o /dev/null -w "healthz     → %{http_code}\n" https://rsshub.mbabrand.com/healthz
curl -s -o /dev/null -w "无 key      → %{http_code}\n" "https://rsshub.mbabrand.com/weibo/user/2803301701"
curl -s "https://rsshub.mbabrand.com/weibo/user/2803301701?key=<你的KEY>" | head -40
```

**三条同时满足才算过**:`healthz` 200 · `无 key` 非 200 · `带 key` 出含 `<item>` 的真实微博 RSS。

(2026-07-27 用临时隧道做过同样的三段验收,数据侧结论:200 / ~30KB / 10 条真实条目,
再过本仓库 `parse_feed` → 10 条、日期全部归一 ISO。命名隧道只是把 URL 换稳定并加了锁,
数据链路不变。)

---

## 5. 把密钥交给 GitHub —— **绝不进仓库**

**本仓库是公开仓库**。RSSHub 的 key 必须跟在 URL 上,所以密钥**不能**直接写进
`site/reports-meta.yaml`,否则等于公开发布。机制:**meta 里只存占位符,真值放 Actions secrets。**

1. GitHub → 仓库 **Settings → Secrets and variables → Actions → New repository secret**
   - **Name**:`RSSHUB_KEY`
   - **Secret**:§1 生成的那串
2. 然后(这步交给我做,或你自己提 PR)在 meta 里写**占位符**:

```yaml
  - slug: meituan
    ...
    rss_feeds:
      - https://rsshub.mbabrand.com/weibo/user/<美团官微uid>?key=${RSSHUB_KEY}
```

3. 仓库侧已经有两道保险:
   - **门禁**:`check_consistency` 第 16 格「RSS 源无明文密钥」—— 只要 `key/code/token/auth`
     类参数的值不是 `${大写变量名}` 占位符,**CI 直接红**。
   - **哨兵**:变量没配时 discover **跳过该源并明确喊「环境变量未设置」**,而不是拿空 key 去请求。
     (带空 key 请求会 403,看起来像"路由挂了" —— 那会把配置错误伪装成源站故障,排错追错方向。)
   - 日志与候选 md 里打印的**永远是占位符模板串**,展开后的真 URL 不落任何可见处。

---

## 6. 找官微 uid(每个品牌一次)

浏览器打开该品牌**官方微博主页**,地址栏形如 `weibo.com/u/1746173800`,`u/` 后面的数字就是 uid。
**别抄别处给的 uid,自己从主页地址栏确认** —— 抄错了等于监控了别人家。

**先只配 1~2 个品牌,观察一周**:看候选里 `source_type: social` 的条目质量,OK 再扩。
每品牌候选总量不变 —— 社区源共用 **≤1/4 名额**,且**桶内自备 RSS 优先于知乎泛查询**
(2026-07-27 修的静默挤压:同桶排在后面时,知乎召回量大的品牌会把微博条目全数挤掉,
而且**哨兵不会响** —— 源确实抓到了,只是没进候选)。下游成本不涨。

---

## 7. 排错表

| 现象 | 多半是 | 怎么办 |
|---|---|---|
| 隧道起不来 / 时断时续 | 默认 QUIC(UDP 7844)被阻断 | 加 `--protocol http2` |
| 公网访问 502 / 1033 | RSSHub 容器没起 | `docker ps`;`docker start rsshub` |
| 带 key 也 403 | 容器里的 `ACCESS_KEY` 与 URL 里的不一致 | `docker exec rsshub env \| grep ACCESS_KEY` 对一下 |
| 无 key 也 200 | 这版鉴权参数名不是 `key` | 查 docs.rsshub.app 的 Access Control,以实测返回码为准 |
| 微博路由返回空 | 出口 IP 被访客系统拦 / 路由变更 | 换家庭宽带;必要时加 `-e WEIBO_COOKIE=...` |
| 微博路由直接报错 | 镜像用了 `latest` | 必须 `diygod/rsshub:chromium-bundled`(新版路由走 Playwright) |
| 候选里出现「环境变量未设置」 | GitHub secret `RSSHUB_KEY` 没配或名字写错 | 回 §5 第 1 步 |
| 候选里出现「自备 RSS 0 条」 | 路由失效 / cookie 过期 / 隧道断了 | 按本表从上往下排 |
| 隧道进程没了 | LaunchAgent 没加载或机器睡了 | `launchctl list \| grep cloudflared`;看 `/tmp/cloudflared.err` |

**换密钥**:改容器 `-e ACCESS_KEY=` 重建 **+** 改 GitHub secret,**两边必须同时改**,
中间会有一小段候选拿不到数据(哨兵会喊,不会静默)。

**升级 RSSHub**:`docker pull diygod/rsshub:chromium-bundled && docker rm -f rsshub && <重跑 §1 第 2 步>`。

---

## 8. 安全边界(签收后再开工)

1. **隧道 = 把家里的服务放到公网**。`ACCESS_KEY` 是唯一一道门,不配等于开放代理 ——
   别人能用你的 IP 和带宽去请求微博,**风控算在你头上**。
2. **token 与 key 都是秘密**:LaunchAgent 的 plist 里是明文(已 `chmod 600`),
   shell history 里也可能有。别贴群里、别截图带出去。
3. **平台条款不变**:自动化抓取违反微博/小红书 ToS;配 cookie 的账号可能被风控。
   建议微博公开主页**尽量不配 cookie**;小红书如配 cookie,用小号。风险由你拍板。
4. **更强的鉴权目前上不了**:Cloudflare Access 的服务令牌要在请求里带
   `CF-Access-Client-Id` / `CF-Access-Client-Secret` 头,而当前 `fetch_candidate` 只发普通
   GET、不带自定义头 —— 要上得先改仓库侧。**先用 `ACCESS_KEY`,够用**。
   可选的零成本加固:在 Cloudflare 给 `rsshub.mbabrand.com` 加一条 WAF 速率限制规则。
5. **反捏造不变**:进库的只有 feed 里逐字的标题/日期/链接;dim/severity 由分类环节判;
   **审计分数从不自动变,合并 PR = 人工闸门**。

---

## 附录 A — 一页速查

```bash
KEY=$(openssl rand -hex 24)                        # 记到密码管理器
docker rm -f rsshub && docker run -d --name rsshub --restart unless-stopped \
  -p 1200:1200 -e ACCESS_KEY="$KEY" diygod/rsshub:chromium-bundled
curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:1200/weibo/user/2803301701"          # 非 200
curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:1200/weibo/user/2803301701?key=$KEY" # 200
# → 控制台建隧道拿 token → cloudflared tunnel run --protocol http2 --token <token>
# → Public Hostname: rsshub.mbabrand.com → http://localhost:1200
# → LaunchAgent 常驻 → 手机流量做公网侧三段验收 → GitHub secret RSSHUB_KEY → meta 填占位符
```

## 附录 B — CLI 方式建隧道(不用控制台,配置落成文件)

偏好把配置放本地文件、纳入版本管理的话走这条;功能等价。

```bash
cloudflared tunnel login                            # 浏览器授权,选 mbabrand.com
cloudflared tunnel create mba-rsshub                # 生成 ~/.cloudflared/<UUID>.json 凭据
cloudflared tunnel route dns mba-rsshub rsshub.mbabrand.com   # 自动建 CNAME

cat > ~/.cloudflared/config.yml <<'YML'
tunnel: mba-rsshub
credentials-file: /Users/<你的用户名>/.cloudflared/<UUID>.json
protocol: http2
ingress:
  - hostname: rsshub.mbabrand.com
    service: http://localhost:1200
  - service: http_status:404
YML

cloudflared tunnel run mba-rsshub
```

常驻同 §3,只是 `ProgramArguments` 换成 `tunnel run mba-rsshub`(不带 token)。
**`~/.cloudflared/` 整个目录都是凭据,别提交进任何仓库。**
