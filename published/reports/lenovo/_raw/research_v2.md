# v2 补充调研来源清单（克制原则 · 2026-07-12）

按 G4 任务要求，v2 证据以 watch 事件流为主（3 条，见 `watch_consumption_v2.md`），
补充调研保持克制：仅新增 1 份一手来源，全部经本会话 curl（出口代理 + CA）直接取回原文
核验；拿不到原文的不写入报告。

## 新增一手来源

1. **Lenovo Group FY2025/26 Annual Results Announcement**（港交所业绩公告原文 PDF，43 页）
   - URL: https://doc.irasia.com/listco/hk/lenovo/annual/2026/res.pdf
   - 取回方式：curl 直下 PDF（1,007,289 bytes），pdfminer 抽取全文核验
   - 报告引用的关键数字/原文（均在 PDF 内逐字核对）：
     - Revenue US$83,075M（+20%）；Profit attributable to equity holders US$1,912M（+38%）；
       Adjusted profit attributable US$2,049M（+42%）
     - "AI-related revenues increasing 105 percent year-on-year, representing 33 percent
       of Group's total revenue"；Q4 "AI-related revenues were 38 percent of Group's total
       revenue and grew by 84 percent year-on-year"
     - ISG "turned full year profitable"（全年经营利润，Q4 US$202M 创纪录）；
       "a US$21 billion pipeline exiting the year"（AI 服务器储备）
     - SSG Q4 US$2.6B +19%、经营利润率 22.4%、Managed Services + Project & Solutions 占 62%
     - "Lenovo's personal intelligence system Qira was officially released in April 2026"；
       "In China, enhanced capabilities in Tianxi"（Qira/天禧中外双名的出处）
     - "helping customers reduce time to first token, improve token efficiency and
       maximize value per token"（报告「Token 计量表」讨论的官方原文锚点）
     - 末期息 HK33.7 cents（上年 30.5）；Infinidat 收购 2026 年 4 月完成
     - Q4 PC "largest market share lead in 15 years"（份额 24.4% 数字见 watch 001 stcn 原文）

## 复核（非新增）的 watch 事件原文

- stcn（watch 001）/ doit（watch 002）/ 新浪科技（watch 003）三篇均于 2026-07-12 curl
  取回正文核验，quote（标题逐字）与 events.yaml 一致。

## 未采用的检索

- IDC 2026 Q1 PC tracker：尝试一次 idc.com 页面抓取未能定位到对应联想数据的原发布页，
  **未写入报告**（报告中 24.4%/「15 年最大领先优势」明确标注为公司口径，出处 watch 001
  与官方公告）。
- v1 快照 `../versions/v1_2026-05-10.html`：作为基线引用（v1 评委立场、22/50 = 4.40），
  非新增调研。
