# 24 · 全站功能巡检与修复(Site Functional QA)

> **Status:** v1(2026-07-16)。一次系统性的全站点击/执行/验证 + 修复 + 复测记录。
> **触发:** 用户「对网站的所有功能点击、执行、验证,改正那些不起作用的功能,过程中做好测试和文档记录」。

## 方法(可复现)

```bash
# 1) 本地构建出完整站点(founders/collabs/watch/starmap/reports 均为构建产物)
bash site/build.sh

# 2) 起本地静态服务器(site/ 作为根,绝对路径 href="/..." 才能解析)
cd site && python3 -m http.server 8199 &

# 3) Playwright 广度优先爬全站:枚举所有内链 → 逐页访问 → 记录 HTTP 状态 + JS 错误
#    再对全部发现的链接做响应状态检查抓 404(脚本见 scratchpad,非仓库常驻)
# 4) 交互功能单独驱动测试:排序/产业筛选/晚餐 CTA/组合器/动态页(judge/panorama/starmap/cockpit)
```

**覆盖面(本次):爬取 177 个页面、188 条唯一链接。** 含首页、22 份报告 + 历史版本快照、22 创始人页、
40+ 评委页(`judge.html?slug=`)、22 品牌星图、舆情时间线 + 驾驶舱、组合器 + 2 场晚餐、以及所有顶层页。

### 环境假阳性(必须排除,否则误报)

报告页 `<head>` 里的 `Chart.js` 走 `cdn.jsdelivr.net`。**沙箱/CI 出口不可达该 CDN 时,阻塞的
`<script src>` 会拖住 `domcontentloaded`,爬虫按超时记为 `[0]`**——这是**测试环境假阳性,不是线上缺陷**
(直连 `curl` 这些报告页均 200;线上 Cloudflare CDN 可达;`render-qa` 用 `--offline-libs` 已权威验证图表渲染)。
判定死链以**响应状态(fetch/response.status)**为准,不以 `domcontentloaded` 超时为准。

## 发现与修复(4 个真实缺陷)

| # | 缺陷 | 根因 | 修复 |
|---|---|---|---|
| 1 | `roadmap.html` 链到 `/docs/12-evolution-tracking.md` → **404** | 该页其余 doc 链接都用完整 GitHub URL,这一处漏写成裸站内路径(站点不发布裸 `.md`) | 改成 `https://github.com/zhanglunet/mba/blob/main/docs/12-evolution-tracking.md`(与兄弟链接一致) |
| 2 | `chengshi-auto` 报告 v1 版本链 → `versions/v1_2026-05-17.md` **404** | `build.sh` 只发布 `versions/*.html`;而 v1 根本没有 HTML 快照(仅 md/docx/pdf 源文件) | v1 链改为指向 GitHub 源文件 `.../versions/v1_2026-05-17.md`(标注「源文件」) |
| 3 | 历史快照断图:`lenovo` v1 / `chengshi-auto` v5·v6 引用 `_assets/*.jpg`(评委头像 / 车型实拍)**404** | `_assets/` 实际发布在报告根 `/reports/<slug>/_assets/`,但快照在 `versions/` 目录下,相对路径 `_assets/` 解析成 `versions/_assets/`(不存在) | `build.sh` 发布版本快照时,把 `<slug>/_assets/` 一并镜像到 `<slug>/versions/_assets/`,匹配快照的相对路径 |
| 4 | `chengshi-auto` v2 快照(redirect stub)跳转 `../report.html` **404** | build 部署时 `report.html` 被拷成 `index.html`;stub 的 `meta refresh` 目标 `../report.html` 在部署后不存在 | 改跳 `../`(部署后的目录 URL,自动服务 index.html) |

### 复测(全部 200 / 0 真实 JS 错误)

- Fix 3:`/reports/lenovo/versions/_assets/fusheng.jpg`、`/reports/chengshi-auto/versions/_assets/chengshi01-cabin.jpg` → **200**;lenovo v1 / chengshi v5·v6 快照 **0 console 404**。
- Fix 4:v2 stub → 最终 URL `/reports/chengshi-auto/`,响应追踪 **0 个 4xx**。
- Fix 1/2:裸 `.md` 死链已消除(改为外链 GitHub)。

## 交互功能测试(11/11 通过)

| 功能 | 页面 | 结果 |
|---|---|---|
| 排序(评分降序) | `index.html` | ✅ 首卡 = 最高分,严格降序 |
| 产业筛选(AI / 全部复位) | `index.html` | ✅ 点 AI 只显 ai 卡;全部复位 22 张 |
| 晚餐亮点 CTA 可达 | `index.html` | ✅ 200 |
| 组合器「开饭」(已建对) | `collabs/` | ✅ 显示并跳该场晚餐页 |
| 组合器「点单」(未建对) | `collabs/` | ✅ 显示并生成预填 GitHub issue |
| 组合器同人提示 | `collabs/` | ✅ 「请选两位不同的创始人」 |
| 评委页动态渲染 | `judge.html?slug=` | ✅ 读 `/api/judges.json`,正确渲染(如「保罗·格雷厄姆」「任正非」) |
| 评委页裸 URL 兜底 | `judge.html` | ✅ 优雅兜底「没有指定评委,回评委全景挑一位」(非 bug) |
| 评委全景 | `panorama.html` | ✅ 加载 0 JS 错误 |
| 知识星图 | `starmap.html` | ✅ svg/canvas 渲染,搜索框在位,0 JS 错误 |
| 全站舆情驾驶舱 | `watch/cockpit.html` | ✅ 加载 0 JS 错误 |

## 结论

全站 4 个真实缺陷(2 处死链 + 版本快照断图 + 1 处 redirect 目标错)已全部修复并复测通过;11 项交互功能全部工作正常;
其余「超时」项经响应状态复核为 CDN 环境假阳性,非线上缺陷。

**后续可选(本期未做):** 把「构建 → 起服务器 → 爬 404」做成一个轻量 CI link-check job,防止死链回归(需在 CI 里跑本地 server + Playwright,较重,留后续)。
