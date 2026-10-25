# tests/fixtures/meta-review —— PRD-177/T3 findings 消费方样例树

本目录是元评审（`scripts/meta_review.py --findings`，PRD-063 消费侧）与
findings 校验器联测用的**自包含样例仓库树**（trend #887）：所有内容为占位示例，
不指向任何真实品牌、人物、主机、IP、账号或密钥。

结构（mini 仓库树，`--root` 指到本目录即可让校验器把它当仓库根）：

    metric-brand-auditor/panels/example-meta.yaml       样例 panel（R-4 judge_slug 归属核对用）
    published/reports/example-meta-brand/versions/v1/
    ├── report.md                                       带 Score Matrix 的占位报告（审计输入）
    ├── reviews/alpha-judge.md                          confirmed 依据链的 review 逐字引用锚
    └── findings.json                                   三态样例（confirmed 1 / needs_validation 2 / rejected 1）

用法：

    python3 scripts/meta_review.py \
      tests/fixtures/meta-review/published/reports/example-meta-brand/versions/v1/report.md \
      --findings tests/fixtures/meta-review/published/reports/example-meta-brand/versions/v1/findings.json
    python3 scripts/validate_findings.py \
      tests/fixtures/meta-review/published/reports/example-meta-brand/versions/v1/findings.json \
      --root tests/fixtures/meta-review

与 `tests/fixtures/findings/`（PRD-177/T2 适配层/校验器金样例树）相互独立，
两棵树各自自包含，互不引用。回归测试：`tests/test_findings_consumers.py`。
