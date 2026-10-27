# PRD-177/T5 验收记录：评审结论三态机读 findings（trend #889）

> 验收对象：PRD-177（mba 评审结论三态机读 findings.json）T1–T4 已合并交付。
> 本记录只做验收走查，不改 schema（T1）、适配层/校验器（T2）、消费接线（T3）、
> 契约文档（T4）的任何行为；评分业务公式与四项审计算法零改动。
>
> 验收标准（PRD-177 任务表 T5 行 / issue #889）：
> ① 完整评审样例机读通过校验；② 无密钥。

## 一、验收标准逐条核对

| # | 验收标准 | 证据（可复现命令） | 结果 |
|---|---|---|---|
| 1 | 完整评审样例机读通过校验 | §二：三棵样例树的完整评审样例（三态俱全）逐一过 `validate_findings.py` R-1…R-7，退出码全 0 | ✅ |
| 1a | 真实评委稿适配→校验过 | §三：评委稿（STEP 5 形态）→ `adapt_findings.py` → 与金样例逐字节一致（10 次复跑）→ R-1…R-7 PASS | ✅ |
| 1b | 消费面按契约可读 | §四：对照 `findings-export-contract.md`（T4，#888）「消费面」表三口逐一实读 | ✅ |
| 2 | 无密钥 | §五：R-7 同源 C-3 扫描器对三棵样例树 + 两份 findings 文档 0 命中；密钥只放环境变量 | ✅ |

回归断言已固化为 `tests/quality/test_findings_t5_acceptance.py`
（`.venv/bin/python -m pytest tests/quality/test_findings_t5_acceptance.py -q`），
本文档中的命令输出与断言一一对应，可随时复跑。

## 二、完整评审样例机读通过校验（标准 ①）

完整评审样例 = confirmed / needs_validation / rejected 三态俱全的 findings.json：

```text
$ python3 scripts/validate_findings.py published/reports/example-meta-brand/versions/v1/findings.json --root tests/fixtures/meta-review
结论: PASS published/reports/example-meta-brand/versions/v1/findings.json（findings 4 条，R-1…R-7 全过）
附录: {"tool":"validate_findings","schema":"prd-177-v1",...,"ok":true,"error_count":0,"violations":[]}

$ python3 scripts/validate_findings.py published/reports/example-brand/versions/v1/findings-full.json --root tests/fixtures/findings
结论: PASS published/reports/example-brand/versions/v1/findings-full.json（findings 3 条，R-1…R-7 全过）

$ python3 scripts/validate_findings.py tests/fixtures/consumer-findings/published/reports/example-consumer-brand/versions/v1/findings-full.json --root .
结论: PASS tests/fixtures/consumer-findings/.../findings-full.json（findings 3 条，R-1…R-7 全过）
```

三份样例的三态计数分别为 1/2/1、1/1/1、1/1/1（confirmed/needs_validation/rejected），
`counts` 字段与 `findings[]` 实际计数逐项对账（R-1）。root 口径沿各树 README：
meta/findings 两棵为自包含 mini 树；consumer 树 `--root` 是真实仓库根（其
source_ref 指向真实 `perspectives/` 语料，kind=research，T3 定稿口径）。

## 三、真实评委稿适配 → 校验过（标准 ①a，范例可复现）

评委稿输入：`tests/fixtures/findings/.../reviews/example-judge.md`
（judge-prompt-template STEP 5 形态：Scores 表 / Verdict / Critical gap / Brand action）。

```text
$ python3 scripts/adapt_findings.py published/reports/example-brand/versions/v1/reviews/example-judge.md --root tests/fixtures/findings --panel example > /tmp/adapted.json
== adapt_findings (prd-177-v1) ==
投影: 4 条 findings（全部 needs_validation，confirmed=0 / rejected=0——适配层不判三态升级）
note: Brand action 是建议不是结论（T1 §3.3），不入 findings

$ diff /tmp/adapted.json tests/fixtures/findings/published/reports/example-brand/versions/v1/findings.json && echo BYTE-IDENTICAL
BYTE-IDENTICAL        # 10 次复跑输出一致，且与入库金样例逐字节一致

$ python3 scripts/validate_findings.py published/reports/example-brand/versions/v1/findings.json --root tests/fixtures/findings
结论: PASS ...（findings 4 条，R-1…R-7 全过）    # 契约：退出码 0 才算产出完成
```

适配层纪律复核：产出全 needs_validation（**绝不默认 confirmed**）、每条附
unresolved_fact、Brand action 不入 findings、同一输入逐字节可复现。

## 四、消费面按契约可读（标准 ①b，对照 T4 契约文档逐口走查）

对照 `docs/quality/findings-export-contract.md`「消费面」表：

| 契约登记的消费口 | 实测命令 | 实测结果 |
|---|---|---|
| 元评审（PRD-063） | `python3 scripts/meta_review.py <report.md> --findings <findings.json>` | 附录 F「三态计数（透明化全量）：confirmed 1 · needs_validation 2 · rejected 1，共 4 条」与 counts 对账一致；Top3 分歧点行内回指 `findings 线索：F-alpha-judge-001、F-beta-judge-002`；报告明示「四项审计算法与 A–F 阈值未动」 |
| 工程质量门（PRD-151） | `quality_gate.findings_annex(<金样例>, tests/fixtures/findings)` | 附件行「findings_version=prd-177-v1（识别）· R-1…R-7 校验 PASS · 违规 0 处」；`available/ok/recognized` 全真；只读附件，不计入 13 条 checklist、不改 PASS/FAIL |
| CI 透传（PRD-063 CI） | `python3 scripts/ci_meta_review.py --report <report.md> --findings <findings.json>` | exit 0；「**findings 线索**：…（PRD-177/T3 只读回指…）」行可见，Top3 条目附 finding id |
| 人工 review | 打开 findings.json 阅读 claim + evidence | 每条 `evidence.quote` 在 `source_ref` 指向文件中逐字命中（R-5 反捏造防火墙，三态无一例外） |

读侧纪律抽查：元评审对 counts 改动报「计数对账差异」线索而不静默取子集；
版本不识别（非 prd-177-v1）按「拒读不猜测语义」降级——与契约「消费方契约」
四条一致（回归见 `tests/test_findings_consumers.py`，T3 交付，本 T5 未改动）。

## 五、无密钥（标准 ②）

- R-7（复用 PRD-151 C-3 正则清单与白名单）对三棵样例树全部 findings.json 的
  JSON 字符串值扫描：0 违规（§二/§三的 PASS 已含 R-7）。
- C-3 扫描器对三棵样例树全部文本文件 + `docs/quality/findings-export-contract.md`
  （T4 契约）+ 本验收记录：**0 命中**（无真实主机名、IP、账号、密钥形态；
  示例一律用占位符）。
- 密钥只放环境变量：findings 链路全部工具（适配层/校验器/消费方）无网络 I/O、
  不读凭据，纯本地文件处理。

## 六、结论与登记

- 验收标准两条全部满足：完整评审样例机读通过校验 ✅；无密钥 ✅。
- T1–T4 交付物在验收走查中行为与各自文档一致，未发现需要修复的偏差。
- PRD-177 全线 T1–T5 完成（#885/#886/#887/#888/#889）。

登记：2026-10-26（PRD-177/T5，trend #889）。验收回归：
`tests/quality/test_findings_t5_acceptance.py`。
