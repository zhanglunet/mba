# 18 — 中文社媒正文:免费方案调研 + 本机抓取脚本

> Status: **2026-07-13** · 定位:Brand Watch 的 W2(社交社区)要拿**知乎/微博/小红书正文全文**时,
> 无影(付费)之外的**免费替代**调研结论 + 一份本机可跑的 Playwright 脚本。
> 相关:docs/15(PRD §4.1 W2)、docs/16(可达性验证)。

---

## 1. 问题:事件级信号够用,正文全文才是缺口

- **事件级信号**(某话题在知乎/微博火了 + 真实链接 + 标题):**WebSearch 就够**,已在跑
  (本会话 W2 事件即如此取得,见 `watch/*/events.yaml`)。
- **正文全文**(某条知乎回答/微博原文的大段逐字引用):这才是 W2 的缺口,需要**登录态 + 能过反爬的真浏览器**。

## 2. 关键结论:Full 网络解锁了一半,China IP 是真墙(2026-07-13 实测)

环境网络策略切到 **Full** 后实测:

| 层 | 结果 |
|---|---|
| 出口网关(egress gateway) | ✅ 全放行:`curl paulgraham.com` = 200;知乎/微博/小红书 = 302(站点自身跳转,非网关拒绝) |
| curl 取正文 | ❌ 知乎 = 648B 反爬壳 · 微博 = 登录墙 · 小红书 = JS 应用壳 —— **都拿不到正文** |
| 沙箱内预装 Playwright 经出口代理 | ❌ 连不通(控制组 paulgraham 亦 `ERR_CONNECTION_RESET`) |

**结论**:Full 对 **curl-able 源**(paulgraham/a16z/36氪/新浪…)是真解锁;但对知乎/微博/小红书这三家
**反爬 + 登录墙**站无效。

## 3. 免费替代品调研(无影 = 阿里云无影,付费)

| 类别 | 免费选项 | 说明 |
|---|---|---|
| 指纹/防关联浏览器(桌面) | **GoLogin**(永久免费 3 环境)· **AdsPower**(免费档)· **Dolphin Anty**(免费计划) | Cookie 隔离持久化 = 登录态;反指纹强,**桌面 GUI,在你自己机器跑** |
| 开源 / 免费云浏览器 API | **Steel.dev**(开源自托管全免费)· **Browserless**(开源 + 云免费档)· **Browserbase**(云免费档 1h) | 可编程,可从服务端调;但机房在美/欧 |
| 纯开源库 | **Playwright + `storageState`**(全免费) | 原生支持"登录一次、保存 session、复用"——**登录态这件事根本不用付费工具** |

### ⚠️ 但免费工具都补不上的三件事(无影的真正壁垒)
1. **真实账号 + 过验证**:手机短信 2FA + 滑块/点选验证码,手动、按账号来,换什么工具都一样。
2. **China IP** ⭐:知乎/微博/小红书**重度封禁境外/机房 IP**。无影跑在阿里云**中国机房**才过得去;
   境外免费云浏览器(Steel/Browserless/Browserbase 都是美/欧机房)即使登录也大概率被验证码/封。
   **免费云浏览器补不上"中国 IP"这一环 —— 这才是无影不可替代的地方。**
3. **ToS / 封号风险**:用登录账号抓取违反三家 ToS,账号有被限/封风险(合规成本,非工具成本)。

**一句话**:最省钱的路是**在你自己的中国机器上**用 GoLogin 免费版 / 纯 Playwright + storageState,
而不是找一个"能从服务端自动跑的免费云浏览器"(那个基本不存在)。

## 4. 本机抓取脚本

`scripts/social-fetch/zhihu_fetch.mjs` —— Playwright + storageState,知乎公开页正文抓取。**在你自己机器 + 中国网络跑**。

```bash
npm init -y && npm i playwright && npx playwright install chromium

node scripts/social-fetch/zhihu_fetch.mjs login          # 首次:弹浏览器,手动登录一次,存 session
node scripts/social-fetch/zhihu_fetch.mjs <知乎URL>      # 之后:复用 session 抓正文(标题 + 正文 + quote 候选)
```

会话过期(几周~几月)就重跑 `login` 刷新。微博/小红书同理,换选择器即可(登录墙更硬,小红书大量内容 App-only)。

## 5. 红线(不可动)
- **在你自己机器 / 中国网络跑,用你自己的账号,低频,尊重 robots/ToS** —— 这不是绕过风控的工具,是"手动登录后读页"。
- 抓到的正文写进 Brand Watch 时,仍守**反捏造**:只存 **≤100 字逐字引用 + URL + 抓取时间戳**,
  `direction` 恒 `model-judged`,**只建议不改分**(与所有 watch 事件同一条纪律,见 docs/15 §5.3、§6)。
- 达不到"可溯源"的信号,**宁可不入库**——与"张兰诚实留 seed"同一条纪律。

> 线上版:[mbabrand.com/social-fetch.html](https://mbabrand.com/social-fetch.html)
