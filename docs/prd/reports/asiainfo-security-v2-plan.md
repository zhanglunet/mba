# 亚信安全品牌报告 v2 满血升级计划

**Report slug:** `asiainfo-security`  
**Current version:** v1, 2026-05-18  
**Target panel:** `security-cn-global`  
**Goal:** 把当前“面板跑通版”升级为接近联想 / 橙仕报告密度的正式发布版。

## 1. 当前 v1 状态

v1 已完成:

- 绑定 `security-cn-global` 6 评委组。
- 生成 `published/reports/asiainfo-security/report.md`。
- 生成 `published/reports/asiainfo-security/report.html`。
- 生成 6 位评委 review。
- 生成 `_raw/synthesis.md`。
- 加入 `site/published-reports.txt` 发布白名单。

v1 的问题:

- 只有压缩 synthesis，没有 7 个维度级 `_raw/dimension_*.md`。
- 评委 review 偏短，没有深度引用公开资料。
- 新增 5 位安全评委仍是 `production-seed v1`，需要继续蒸馏。
- HTML 有热力图、图表、Mermaid，但版式和内容密度不如联想 / 橙仕。
- 没有产品截图、产品图、官网视觉、公告截图等公开视觉材料。
- 竞品横评不足，缺少奇安信、深信服、安恒信息、启明星辰、绿盟科技、CrowdStrike、Palo Alto Networks 等定位参照。

## 2. v2 研究目标

核心问题:

> 亚信安全到底应该被市场理解为“安全公司”、“亚信系数智集团平台”、
> “运营商级 AI XDR 安全运营平台”，还是“控股亚信科技后的安全 + 数智基础设施公司”？

v2 需要回答:

1. 亚信安全网络安全主业的真实产品力和收入地位是什么？
2. 并表亚信科技后，安全品牌是增强还是稀释？
3. “天穹 AI XDR”能否成为唯一主叙事？
4. 亚信安全与奇安信、深信服、安恒、启明星辰、绿盟等相比，差异化在哪里？
5. 面向政企 / 运营商 / 金融 / 能源客户，亚信安全最可信的品类承诺是什么？
6. 6 位评委会在哪些维度产生真正分歧？

## 3. 必补 7 个维度

写入:

```text
published/reports/asiainfo-security/_raw/dimension_1_founder-origin.md
published/reports/asiainfo-security/_raw/dimension_2_product-positioning.md
published/reports/asiainfo-security/_raw/dimension_3_distribution-channels.md
published/reports/asiainfo-security/_raw/dimension_4_community-pr.md
published/reports/asiainfo-security/_raw/dimension_5_visual-verbal-identity.md
published/reports/asiainfo-security/_raw/dimension_6_competitive-landscape.md
published/reports/asiainfo-security/_raw/dimension_7_reception-sentiment.md
```

每个维度至少包含:

- 5-10 条发现。
- 每条发现带 URL。
- 公司自述 vs 第三方观察。
- 矛盾 / 空白。
- confidence 标记。

## 4. 必查来源

一手来源:

- 亚信安全官网：https://www.asiainfo-sec.com/
- 产品中心：https://www.asiainfo-sec.com/product
- 天穹 XDR：https://www.asiainfo-sec.com/product/detail-177.html
- 投资者关系 / 公告：https://www.asiainfo-sec.com/investor/notice
- 2024 年报、2025 年报 / 年度业绩预告。
- 收购亚信科技控股权相关公告。
- 亚信科技官网及公告，用于判断并表后的品牌边界。

产品方向:

- 天穹 AI XDR。
- 终端安全。
- 服务器深度安全防护。
- 云主机安全。
- 身份安全 / IAM / 4A。
- 信舱 / 数据安全 / 大模型安全相关产品。

竞品:

- 奇安信。
- 深信服。
- 安恒信息。
- 启明星辰。
- 绿盟科技。
- 三六零。
- CrowdStrike。
- Palo Alto Networks。
- Trend Micro。
- Microsoft Security。

市场 / 第三方:

- Gartner、IDC、Forrester、赛迪、信通院、FreeBuf、数世咨询、证券研报、上交所公告。
- 财经媒体对并购、业绩、裁员、产品发布、行业格局的报道。

## 5. 评委蒸馏升级

需要继续增强这些评委:

- `zhouhongyi-perspective`
- `zhangmingzheng-perspective`
- `renzhengfei-perspective`
- `jensenhuang-perspective`
- `satyanadella-perspective`

每位评委补:

- 6 路研究文件扩写到更接近 auto panel 质量。
- 至少 8-12 条一手来源锚点。
- 更清楚的 scoring bias。
- 更强的 anti-fabrication 边界。
- 代表句式和“避免像谁”。

优先级:

1. 周鸿祎：安全行业心智和攻防判断。
2. 张明正：企业安全全球化和长期威胁情报。
3. Satya Nadella：微软安全、云、AI、企业信任。
4. Jensen Huang：AI 基础设施和 AI security stack。
5. 任正非：硬科技组织和政企基础设施信任。

## 6. v2 报告结构

v2 `report.md` 应包含:

- Hero summary / TL;DR。
- 评委机制解释。
- MBA 是什么、官网和 GitHub。
- 亚信安全品牌主线判断。
- Score Matrix。
- Judge Dissent Heatmap 的解释。
- 7 维度研究摘要。
- 竞品定位矩阵。
- 产品线 / 业务线拆解。
- 并表亚信科技后的品牌影响。
- 6 评委长版观点。
- Lead's Read。
- 90 天行动建议。
- 法律、商标、知识产权、版权、公开资料和免责声明。
- 完整 citations。
- Versions。

v2 `report.html` 应包含:

- 更接近联想报告的高级排版。
- 品牌主色调：优先使用亚信安全官网蓝色 / 科技蓝。
- 热力图。
- 雷达图。
- 总分柱状图。
- 影响力构造图。
- 竞品定位象限。
- 品牌心智图。
- 产品图片或官网截图，旁边标注公开来源。
- 评委卡片。
- 法律声明区。
- Citations 折叠区。

## 7. 建议执行命令

换机器后先同步代码:

```bash
git pull
```

确认面板:

```bash
python3 scripts/validate_panels.py
```

确认站点构建:

```bash
bash site/build.sh
```

建议启动 v2 时直接说明:

```text
继续 docs/prd/reports/asiainfo-security-v2-plan.md，把亚信安全报告升级成 v2 满血版。
```

## 8. 发布步骤

完成 v2 后:

```bash
bash site/build.sh
git add published/reports/asiainfo-security site/published-reports.txt docs/prd/reports/asiainfo-security-v2-plan.md
git commit -m "publish asiainfo security report"
git push
```

如果要部署网站:

```bash
npx wrangler pages deploy site --project-name mba-92r
```

部署后验证:

```bash
curl -I https://mbabrand.com/reports/asiainfo-security/
```
