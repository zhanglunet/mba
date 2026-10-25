# tests/fixtures/findings —— PRD-177/T2 findings.json 校验样例树

本目录是 findings.json 三态机读链路（PRD-177/T2，trend #886）的**自包含样例仓库树**：
所有内容为占位示例，不指向任何真实品牌、人物、主机、IP、账号或密钥。

结构（mini 仓库树，`--root` 指到本目录即可让校验器/适配层把它当仓库根）：

    metric-brand-auditor/panels/example.yaml        样例 panel（judge_slug 归属核对用）
    published/reports/example-brand/versions/v1/
    ├── report.md                                   report_ref 指向物（占位）
    ├── _raw/synthesis.md                           synthesis 逐字引用锚（占位）
    ├── reviews/example-judge.md                    样例评委落笔（judge-prompt-template STEP 5 形态）
    ├── findings.json                               适配层产出（scripts/adapt_findings.py 生成，全 needs_validation）
    └── findings-full.json                          手工三态样例（confirmed / needs_validation / rejected 各一）

用法：

    python3 scripts/adapt_findings.py \
      published/reports/example-brand/versions/v1/reviews/example-judge.md \
      --root tests/fixtures/findings --panel example
    python3 scripts/validate_findings.py \
      published/reports/example-brand/versions/v1/findings.json --root tests/fixtures/findings

回归测试：`tests/test_validate_findings.py` / `tests/test_adapt_findings.py`
（pytest 会断言 findings.json 与适配层重生成结果逐字节一致——改 reviews 样例后
必须重跑适配层同步本文件）。
