# tests/fixtures/consumer-fake-position —— PRD-178/T5 假岗位消费者样例 + 双视角对照演示树

本目录是 PRD-178/T5（trend #894）的**自包含样例仓库树**：构造「假岗位」消费者
样例（模拟人设开场白声称头衔与采购经历，但无任何可核对证据），走满 C1–C5 题组，
验收「适配层一律标 needs_validation（缺可验证证据），机器门不认岗位背书」；
并为双视角对照报告演示（`docs/quality/comparison-report-t5-demo.md`）提供同一
虚构品牌的专家/消费者两侧 findings。所有内容为占位示例，不指向任何真实品牌、
人物、主机、IP、账号、密钥或真实 PII。

结构（mini 仓库树，`--root` 指到本目录即可让校验器/适配层把它当仓库根）：

    metric-brand-auditor/panels/
    ├── example-dual-expert.yaml      专家侧样例 panel（R-4 归属核对用）
    └── example-dual-consumer.yaml    消费者侧样例 panel（fake-title-buyer，role: consumer）
    published/reports/example-dual-brand/versions/v1/
    ├── report.md                     report_ref 指向物 + 诚实盒（占位）
    ├── reviews/expert-judge.md       专家评委稿（judge-prompt-template STEP 5 形态）
    ├── reviews/fake-title-buyer.md   假岗位消费者答卷（C1–C5 题组全走）
    ├── findings-expert.json          专家侧投影（scripts/adapt_findings.py 生成，全 needs_validation）
    └── findings-consumer.json        消费者侧投影（scripts/adapt_consumer_findings.py 生成，全 needs_validation）

两个 findings 文件名带侧别后缀（`-expert` / `-consumer`）：双视角对照要求两侧
指向**同一虚构品牌**，schema 对文件名无要求；真实评审轮单侧产物仍按契约命名为
`findings.json`。

用法：

    python3 scripts/adapt_findings.py \
      published/reports/example-dual-brand/versions/v1/reviews/expert-judge.md \
      --root tests/fixtures/consumer-fake-position --panel example-dual-expert \
      -o published/reports/example-dual-brand/versions/v1/findings-expert.json
    python3 scripts/adapt_consumer_findings.py \
      published/reports/example-dual-brand/versions/v1/reviews/fake-title-buyer.md \
      --root tests/fixtures/consumer-fake-position --panel example-dual-consumer \
      -o published/reports/example-dual-brand/versions/v1/findings-consumer.json
    python3 scripts/validate_findings.py \
      published/reports/example-dual-brand/versions/v1/findings-consumer.json \
      --root tests/fixtures/consumer-fake-position

验收要点（tests/quality/test_consumer_t5_acceptance.py 断言）：

- 假岗位样例走满 C1–C5（lens 集合 = {c1, c2, c3, c4, c5}；C2=4 为低分被投影）；
- 两侧 findings 全部 needs_validation、confirmed=0 / rejected=0，每条 evidence
  均为单条 kind=review 逐字引用（缺可验证证据的形态）；头衔/经历声明没有换来
  任何 confirmed——适配层不判三态升级，机器门不认岗位背书；
- 两侧 findings 均过 R-1…R-7（退出码 0）；
- 对照报告 `docs/quality/comparison-report-t5-demo.md` 对照表逐行抄自本树两侧
  findings（模板纪律 1，由验收测试机检），诚实盒与「不换算、不平均」纪律在位；
- 全树无真实 PII / 密钥（C-3 扫描 0 命中 + PII 形态扫描 0 命中）。

回归测试：`tests/quality/test_consumer_t5_acceptance.py`（pytest 会断言两侧
findings.json 与适配层重生成结果逐字节一致——改 reviews 样例后必须重跑适配层
同步本文件）。
