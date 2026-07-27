# 27 — 本机自托管 RSSHub 操作手册(免费社媒线 ②)

> **对应计划**:`docs/16 §9.9` 三步走的第 ② 步(用户侧验证)。第 ① 步(仓库侧 `rss_feeds`
> 管道)已在 PR #214 落地 —— 你只要按本手册把 RSSHub 跑起来、把 URL 填进
> `site/reports-meta.yaml`,**当天流水线就开始吃微博信号,仓库侧零改动**。
> **前提**:本机装了 Docker(macOS/Windows 用 Docker Desktop,Linux 用 docker engine)。
> **为什么走这条路**:见 §9.9 —— 零运维的免费方案(公共实例 / 无登录 API)已全部实测排除,
> 免费可行的路 = 把计算挪到你自己的机器(家庭宽带 IP 通常能过微博访客系统)。

---

## A. 起服务(1 分钟)

```bash
docker run -d --name rsshub --restart unless-stopped -p 1200:1200 diygod/rsshub
# 验证服务活着:
curl -s http://localhost:1200/healthz        # → ok
```

`--restart unless-stopped`:开机/Docker 重启后自动拉起,免得哪天悄悄停了。

## B. 验微博路由(核心验收)

1. **找官微 uid**:浏览器打开该品牌的微博主页,地址栏形如 `weibo.com/u/1746173800`,
   `u/` 后面的数字就是 uid。**别抄别处给的 uid,自己从主页地址栏确认** —— 抄错了
   等于监控了别人家。
2. 验路由:

```bash
curl -s "http://localhost:1200/weibo/user/<uid>" | head -40
```

**验收标准**:输出是 RSS(`<rss …><item><title>…真实微博内容…`)。
出 `<item>` 且标题是该官微的真实微博 → **② 通过,进 C**。

排错:
- 返回错误/空 → 大概率你的出口 IP 也被访客系统拦(公司网/代理常见),换家庭宽带试;
  仍不行可在容器加 `-e WEIBO_COOKIE='<你登录微博后的 cookie>'`(浏览器 DevTools →
  Network → 任一 weibo.com 请求 → Request Headers → cookie 整串复制)。
- 小红书(可选,**必须**配 cookie):路由与所需环境变量以
  [docs.rsshub.app](https://docs.rsshub.app) 对应路由页为准(小红书路由历史上变过几次,
  别按老文章配);cookie 同样从 DevTools 复制,过期后哨兵会喊(见 E)。

## C. 让 GitHub 每日 workflow 够得到你本机(二选一)

每日发现跑在 GitHub 云上(02:17 UTC = **北京 10:17**),`localhost` 它够不着。

### 方案 a:Cloudflare Tunnel(推荐 —— 你已有 Cloudflare 账号,mbabrand.com 就在上面)

**先快速试通**(临时 URL,重启就变,只用来验证):

```bash
# macOS: brew install cloudflared   |   其它平台: developers.cloudflare.com/cloudflared 下载
cloudflared tunnel --url http://localhost:1200
# 输出一个 https://<随机>.trycloudflare.com —— 在手机流量(非家里 WiFi)下打开
# https://<随机>.trycloudflare.com/weibo/user/<uid> 能出 RSS 即通。
```

**再换稳定 URL**(正式用):Cloudflare 控制台 → **Zero Trust → Networks → Tunnels →
Create a tunnel**,照页面给的一行命令在本机安装 connector,把 Public Hostname 配成
`rsshub.mbabrand.com → http://localhost:1200`。免费档,URL 永久稳定。

**加一道钥匙(强烈建议)**:隧道 URL 是公网可达的,别人扫到就能白嫖你的 RSSHub 且用你的
IP/cookie 去请求微博。给容器加 `-e ACCESS_KEY='<随便一串长随机字符>'`(重建容器:
`docker rm -f rsshub` 后带上该参数重跑 A 的命令),之后所有请求带 `?key=<那串字符>`
(具体参数形式以 docs.rsshub.app 的 Access Control 一节为准)。

### 方案 b:不穿透,本地 cron 推候选(更私密,多点运维)

本机 clone 仓库 + 装 python3,crontab 加一行(北京每天 09:30,赶在云端 10:17 之前):

```
30 9 * * *  cd ~/mba && git pull -q && python3 scripts/watch-tools/fetch_candidate.py discover --days 2 --out watch/_candidates/$(date +\%F)-local.md && git add watch/_candidates && git commit -qm "chore(watch): 本地社媒候选 $(date +\%F)" && git push -q
```

候选走既有 triage/建议入库流程,**合并仍是人工闸门**。缺点:多一台要维护的"生产机"。

## D. 把 URL 填进 reports-meta(打通最后一步)

`site/reports-meta.yaml` 里,给要监控的品牌加 `rss_feeds`(字符串或列表都行):

```yaml
  - slug: meituan
    ...
    news_page: https://about.meituan.com/news
    rss_feeds:
      - https://rsshub.mbabrand.com/weibo/user/<美团官微uid>?key=<你的ACCESS_KEY>
```

提交 PR 合并后,**次日 10:17(北京)的自动发现就带微博信号**:候选标
`source_type: social`,与知乎共用「社区 ≤1/4 名额」,每品牌总量不变、下游成本不涨。
先只配 1~2 个品牌观察一周,质量 OK 再扩。

## E. 维护:哨兵会替你盯着

- **失效是静默的**(路由挂 / cookie 过期都只是"不再有条目"),所以 discover 对
  「配了 `rss_feeds` 却抓到 0 条」会在**运行日志(stderr)与当日候选 md** 里双告警:
  `⚠️ 自备 RSS 0 条:<slug> <- <url>(路由可能失效或 cookie 过期)`。
  在每日 watch-discover 的 Actions 日志里能直接看到。
- 本机要在**每天北京 10:17 在线**;睡着/关机则当天该源走哨兵告警,其他源不受影响。
- 升级 RSSHub:`docker pull diygod/rsshub && docker rm -f rsshub && <重跑 A 的命令>`。

## F. 风险与边界(签收后再开工)

1. **平台条款**:自动化抓取违反微博/小红书 ToS;配 cookie 的账号可能被风控。
   建议:**微博公开主页尽量不配 cookie**;小红书如配 cookie,用小号。风险由你拍板。
2. **反捏造不变**:进库的只有 feed 里逐字的标题/日期/链接;dim/severity 由分类环节判;
   **审计分数从不自动变,合并 PR = 人工闸门**。
3. **隧道安全**:务必配 `ACCESS_KEY`;URL 别公开发。
4. 「家庭 IP 能过访客系统」是机制推断 + RSSHub 社区经验 —— **B 步就是拿你的真实网络验证它**,
   不通就如实回报,按 §9.9 ③b 决策 Playwright 备选。
