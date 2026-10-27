# PRD-178/T5 验收记录：消费者视角评委（双视角对照）（trend #894）

> 验收对象：PRD-178（mba 消费者视角评委）T1–T4 已合并交付。本记录只做验收走查，
> 不改消费者评委 skill（T2）、三态对齐适配层（T3）、对比报告模板（T4）的任何
> 行为；不与专家 5 镜头换算、不平均，不改评分业务逻辑。
>
> 验收标准（PRD-178 任务表 T5 行 / issue #894）：
> ① 双视角报告演示；② 无人真 PII；③ 无密钥。

## 一、验收标准逐条核对

| # | 验收标准 | 证据（可复现命令/断言） | 结果 |
|---|---|---|---|
| 1 | 双视角报告演示 | §三：`docs/quality/comparison-report-t5-demo.md` 按模板（T4，#893）填写，对照表 9 行逐行机检「只抄自两侧 findings.json」 | ✅ |
| 1a | 含假岗位样例被标 needs_validation | §二：假岗位样例（开场白声称「持证采购顾问 / 替公司买过三次」，无任何可核对证据）走满 C1–C5，适配层投影 5 条全 needs_validation、confirmed=0 | ✅ |
| 2 | 无人真 PII | §四：样例树 + 演示报告 + 验收记录的邮箱/手机号形态扫描 0 命中；答卷与报告自述「模拟人设（合成角色），非真实消费者」 | ✅ |
| 3 | 无密钥 | §四：R-7 同源 C-3 扫描器对样例树 + 演示报告 + 验收记录 0 命中 | ✅ |
| 1b | 对照报告可读 | §三：模板四节结构齐（报告头/对照表/差异解读/纪律复核）+ 诚实盒置顶 + 纪律复核全勾 | ✅ |

回归断言已固化为 `tests/quality/test_consumer_t5_acceptance.py`
（`.venv/bin/python -m pytest tests/quality/test_consumer_t5_acceptance.py -q`）。

## 二、假岗位样例走 C1–C5 题组 → 一律 needs_validation（标准 ①a）

样例树 `tests/fixtures/consumer-fake-position/`（自包含 mini 仓库树，全占位）：
假岗位消费者 `fake-title-buyer`（模拟人设开场白声称头衔与采购经历，样例内
**不可验证声明**，无任何可核对证据）+ 专家 `expert-judge`（STEP 5 形态）。

```text
$ python3 scripts/adapt_consumer_findings.py published/reports/example-dual-brand/versions/v1/reviews/fake-title-buyer.md --root tests/fixtures/consumer-fake-position --panel example-dual-consumer -o .../findings-consumer.json
投影: 5 条 findings（全部 needs_validation，confirmed=0 / rejected=0——适配层不判三态升级；C2 只投影 ≤5 低分）
note: 「One-liner verdict」/「Would I share it?」为总结性表态，C1–C5 已覆盖，不入 findings

$ python3 scripts/validate_findings.py published/reports/example-dual-brand/versions/v1/findings-consumer.json --root tests/fixtures/consumer-fake-position
结论: PASS ...（findings 5 条，R-1…R-7 全过）
```

- lens 集合恰为 {c1, c2, c3, c4, c5}（题组走满；题号 Cn ↔ lens cn 咬合）；
  C2=4（低分 ≤5）按 T1 §六.1 只投影低分主因。
- 全部 findings：status=needs_validation、单条 kind=review 逐字引用
  （缺可验证证据的形态）、unresolved_fact 载明「未满足 confirmed 进入条件」。
- **机器门不认岗位背书**：答卷中的头衔/经历声明没有换来任何 confirmed
  （confirmed=0 / rejected=0）——适配层不判三态升级，升级留待评委复核。
- 专家侧 findings-expert.json（adapt_findings.py 投影 5 条）同样全 needs_validation
  且过 R-1…R-7；两侧重生成 2 次与入库文件逐字节一致（范例可复现）。

## 三、双视角报告演示 + 对照报告可读（标准 ①/①b）

`docs/quality/comparison-report-t5-demo.md`：同一虚构品牌 example-dual-brand 的
专家侧（findings-expert.json，3 镜头行 + 2 跨口径行）× 消费者侧
（findings-consumer.json，C1–C5 五行）并排对照。

- 对照表 9 行逐行机检：每行 (域, lens, claim, 状态, evidence 摘录) 都能在对应侧
  findings 中逐字命中（T4 模板纪律 1「对照表数据只准抄自两侧 findings.json」）。
- 差异解读（人工撰写节）：一致处（专家 signal 与消费者 c2/c4 同向指向「缺可核对
  证据」）、分叉处（identity 与 c1，两域无共同量纲只描述不裁决）、盲区（两侧全部
  needs_validation，如实标注不补位）。
- 诚实盒置顶：模拟人设（假岗位样例），非真实市场调研，不代表任何真实人群统计；
  纪律复核四项全勾；未做跨域换算（C2 的 0–10 自评分未与专家镜头分数平均或相减）。

## 四、无人真 PII + 无密钥（标准 ②③）

- C-3 扫描器（PRD-151 正则清单，R-7 同源）对样例树全部文本 + 演示报告 + 本验收
  记录：**0 命中**（无真实主机名、IP、账号、密钥形态）。
- 邮箱 / 大陆手机号形态正则扫描同范围：**0 命中**（无真人 PII；人设不携带
  人口学标签——年龄/性别/地域未写入人设卡，T1 §七.2 多样性纪律沿用）。
- 诚实标签在位：答卷开场白自述「我是合成角色，非真实消费者」，报告诚实盒置顶；
  密钥只放环境变量（样例链路全部工具无网络 I/O、不读凭据）。

## 五、结论与登记

- 验收标准三条全部满足：双视角报告演示 ✅；无人真 PII ✅；无密钥 ✅。
- 任务书附加验收点：含假岗位样例被标 needs_validation ✅；对照报告可读 ✅。
- T1–T4 交付物在验收走查中行为与各自文档一致，未发现需要修复的偏差。
- PRD-178 全线 T1–T5 完成（#890/#891/#892/#893/#894）。

登记：2026-10-26（PRD-178/T5，trend #894）。验收回归：
`tests/quality/test_consumer_t5_acceptance.py`。
