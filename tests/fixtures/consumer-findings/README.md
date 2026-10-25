# tests/fixtures/consumer-findings —— PRD-178/T3 消费者输出对齐三态 findings 样例树

本目录是消费者评委输出对齐 PRD-177 三态 findings（PRD-178/T3，trend #892）的
**自包含样例树**：所有内容为占位示例，不指向任何真实品牌、人物、主机、IP、
账号或密钥。与 `tests/fixtures/findings/`（PRD-177/T2 树）、
`tests/fixtures/meta-review/`（PRD-177/T3 树）相互独立。

与那两棵 mini 仓库树不同：本树的 `--root` 是**真实仓库根**——panel 取真实
`metric-brand-auditor/panels/consumer-mixed.yaml`（PRD-178/T2 交付），scenario
引用真实 `perspectives/<slug>-perspective/references/scenario.md`（PRD-178/T2
交付），以证明消费者评委与 T2 交付物「咬合」。

结构：

    published/reports/example-consumer-brand/versions/v1/
    ├── report.md                          report_ref 指向物 + 诚实盒（rejected 引用锚，占位）
    ├── reviews/first-glance-shopper.md    消费者答卷（judge-prompt-template STEP 5 consumer 形态）
    ├── reviews/homework-buyer.md
    ├── reviews/brand-skeptic.md
    ├── findings.json                      适配层产出（scripts/adapt_consumer_findings.py 生成，
    │                                      全 needs_validation；C2=7 高分行按规则跳过）
    └── findings-full.json                 手工三态样例（confirmed / needs_validation / rejected 各一）

## 答卷行 → findings 对齐规则（T3 定稿口径，T1 §六.1 落地）

| 答卷行 | lens | 投影规则（adapt_consumer_findings.py） | 三态默认 |
|---|---|---|---|
| C1 第一印象 | c1 | 定性结论：claim=Key phrase，quote=Why 原文 | needs_validation |
| C2 购买意愿 | c2 | **仅低分（答案 0–10 中 ≤5）投影主因**；>5 无复核事项，跳过记 note | needs_validation |
| C3 价格直觉 | c3 | 贵了 / 值了 / 说不清 定性结论 | needs_validation |
| C4 信任与犹豫 | c4 | 逐条犹豫点（含推荐给家人与否） | needs_validation |
| C5 表达欲 | c5 | 会 / 不会 + 消费者口吻一句 | needs_validation |
| One-liner verdict / Would I share it? | — | 不入 findings（C1–C5 已覆盖，避免重复计数），记 note | — |

- 题号 Cn ↔ lens `cn` 严格咬合（PRD-177/T1 §2.2 预留枚举）；题号不在 C1–C5 的行
  lens 落 null（跨口径），不猜枚举。
- 适配层**绝不默认 confirmed**（PRD-177/T2 同款纪律）；confirmed / rejected 由评委
  或下一轮复核判定，样例见 `findings-full.json`。
- evidence kind 沿 PRD-177 schema 现有枚举：`review` = 答卷落笔原文；`research` =
  该人设 `scenario.md`（perspectives 语料）。PRD-178/T1 §四.3 预告的「kind 增
  scenario 候选」在 T3 定稿为 **research（perspectives 语料）**，不新增枚举值
  （口径不膨胀；`validate_findings.py` 属 PRD-177/T2 域，T3 不改其枚举）。
- 消费者结论是「模拟消费者视角信号」，不代表市场调研；不与专家 5 镜头换算、
  不平均、不进专家 Score Matrix（T1 §三纪律）。

用法：

    python3 scripts/adapt_consumer_findings.py \
      tests/fixtures/consumer-findings/published/reports/example-consumer-brand/versions/v1/reviews/first-glance-shopper.md \
      tests/fixtures/consumer-findings/published/reports/example-consumer-brand/versions/v1/reviews/homework-buyer.md \
      tests/fixtures/consumer-findings/published/reports/example-consumer-brand/versions/v1/reviews/brand-skeptic.md \
      --root . -o tests/fixtures/consumer-findings/published/reports/example-consumer-brand/versions/v1/findings.json

全量 R-1…R-7 校验（`scripts/validate_findings.py --root .`，属 PRD-177/T2 #295，
合入后可用）：

    python3 scripts/validate_findings.py \
      tests/fixtures/consumer-findings/published/reports/example-consumer-brand/versions/v1/findings.json --root .

回归测试：`tests/test_consumer_findings_alignment.py`（pytest 会断言 findings.json
与适配层重生成结果逐字节一致——改 reviews 样例后必须重跑适配层同步本文件）。
