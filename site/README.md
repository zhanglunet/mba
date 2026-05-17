# site/ — mbabrand.com 发布渠道

这个目录是 **mbabrand.com** 的源。Cloudflare Pages 拉这个仓库,跑 `site/build.sh`,把 `site/` 当成站点根。

---

## 目录结构

```
site/
├── index.html              首页(静态,无依赖)
├── build.sh                构建脚本 —— Cloudflare Pages build command 调它
├── published-reports.txt   发布白名单(默认空)
├── reports/                build.sh 自动生成,**不要手动改**
│   └── <brand-slug>/index.html
└── README.md               本文件
```

---

## 工作流

### 发布一份新报告

1. 跑出报告:`/mba <brand>` —— 本地生成 `metric-brand-auditor/reports/<brand>/report.html`
2. 把 brand-slug 加进白名单:`echo "<brand>" >> site/published-reports.txt`
3. Review 报告内容,确认可公开后复制到 `published/reports/<brand>/`
4. 发布源需要显式 add:
   ```bash
   mkdir -p published/reports/<brand>
   cp -R metric-brand-auditor/reports/<brand>/* published/reports/<brand>/
   git add -f published/reports/<brand>/
   git add site/published-reports.txt
   git commit -m "publish: <brand>"
   git push
   ```
5. Cloudflare Pages 检测到 push 自动触发 build,30 秒~2 分钟内 `https://mbabrand.com/reports/<brand>/` 上线。

### 取消发布

1. 编辑 `site/published-reports.txt` 删掉那行(或 `# ` 注释)
2. `git push` —— 下次 build 不会再生 `site/reports/<brand>/`,该 URL 会变 404

### 改首页

直接编辑 `site/index.html`,push 即生效。

---

## 一次性:Cloudflare Pages 控制台操作清单

> 本仓库的所有文件已就绪,下面这些动作只能在 Cloudflare 控制台手动点。
> 全程不会要你贴任何凭据给我。

### 第 1 步:创建 Pages 项目

1. 登录 https://dash.cloudflare.com
2. 左侧栏 **Workers & Pages** → 顶部 tab **Pages** → **Create a project** → **Connect to Git**
3. 授权 GitHub(只授权 `zhanglunet/mba` 这一个仓库就够了)
4. 选 `zhanglunet/mba` → **Begin setup**

### 第 2 步:Build 设置

| 字段 | 值 |
|---|---|
| Project name | `mba`(决定默认域名 `mba.pages.dev`,可改) |
| Production branch | `main` |
| Framework preset | `None` |
| Build command | `bash site/build.sh` |
| Build output directory | `site` |
| Root directory (advanced) | (留空) |
| Environment variables | (无需) |

→ **Save and Deploy**

第一次 build 大约 30 秒~1 分钟。完成后访问 `https://mba.pages.dev` 应该看到首页。

### 第 3 步:绑自定义域

进入刚创建的项目 → **Custom domains** tab → **Set up a custom domain**

绑两个,各跑一次:

1. `mbabrand.com` → Cloudflare 会自动检测到这个域名已经在你的 Cloudflare 账号下,提示 "Activate domain" → 点确认
2. 再点 **Set up a custom domain** → 填 `www.mbabrand.com` → 同样确认

绑定时 Cloudflare 会自动写两条 DNS 记录:
- `mbabrand.com` 的 CNAME(用 CNAME flattening)指向 `mba.pages.dev`
- `www.mbabrand.com` 的 CNAME 指向 `mba.pages.dev`

> ⚠️ 如果你之前在 DNS 里手动加过 `mbabrand.com` 的 A / AAAA / CNAME 记录,Cloudflare 会提示冲突。这种情况:DNS 控制台先把那些旧记录删掉,再回 Pages 点 Activate。

### 第 4 步:验证

- 等 1~2 分钟(SSL 证书签发时间)
- 浏览器访问 `https://mbabrand.com` 和 `https://www.mbabrand.com` 应都能看到首页
- `curl -I https://mbabrand.com` 应返回 `200` + `cf-ray` 头

### 第 5 步(可选):www → 主域 301

默认两个域都直接服务首页(同一份内容,SEO 不利)。要做规范化:

1. Cloudflare dashboard → **Rules** → **Redirect Rules** → **Create rule**
2. When incoming requests match: `Hostname equals www.mbabrand.com`
3. Then: **Dynamic** → `concat("https://mbabrand.com", http.request.uri.path)` · Status 301
4. Save

---

## 常见问题

**Q: 首页改了为什么没更新?**
Cloudflare Pages 默认 cache,push 后等 1~2 分钟。还不行就 dashboard → 项目 → **Deployments** → 看最新 build 是否成功。

**Q: 报告里的图片 404?**
build.sh 只搬 `published/reports/<brand>/` 下深度 ≤2 的图片。如果你的报告引用了更深路径或外部图,要么改报告里的路径,要么扩展 build.sh。

**Q: 想删掉整个 site,改用其他方案?**
Cloudflare Pages 控制台 → 项目 → **Settings** → **Delete project**。DNS 记录手动删。

**Q: 我能加 Google Analytics / Plausible 吗?**
直接编辑 `site/index.html`,在 `</head>` 前插脚本即可。建议 Plausible(无 cookie,合规简单)。
