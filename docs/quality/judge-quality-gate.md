# 评委工程质量门禁使用说明（PRD-151）

> 相关：zhanglunet/trend #755–#759（T1 草案 / T2 脚本 / T3 元评审挂钩 / T4 全绿范例 / T5 验收入库）。
> 设计文档：[docs/plans/2026-10-23-judge-quality-gate.md](../plans/2026-10-23-judge-quality-gate.md)。
> 脚本：[scripts/perspective-tools/quality_gate.py](../../scripts/perspective-tools/quality_gate.py)（纯标准库，
> 只调用 A 组既有命令、不改它们的业务逻辑）。
> 本说明由 PRD-151/T5 入库（issue #759）。

## 一、这是什么

把散在 6 个既有脚本里的评委质量信号收拢成**单评委一页视图**：13 条 checklist
（P0 六条机检 + P1 七条），结论形如 `PASS 13/13 · warn m · exempt k`。

- **P0（A-1..A-6）**：结构 spec、内容质量 6/6、反捏造防火墙、self-conflict、
  panel 引用完整、派生产物同步。任一 fail ⇒ 结论 FAIL，**P0 不设豁免**。
- **P1（B-1..B-4 / C-1..C-3）**：六路语料齐全、quotes 锚定率 ≥90%、可复制调用示例、
  Boundary 研究截止、description 触发短语、tier 追踪表如实、占位符纪律。
  过渡期 warn-only，可按 §四登记豁免。

## 二、怎么跑

前提：仓库根，Python 3.10+，环境可 `import yaml` 且能跑 `python -m pytest`
（CI 与本地惯例：`pip install pyyaml pytest`；本仓 `.venv` 已含）。

```bash
# 1) 单评委：13 条全跑并产出报告（slug 或含 SKILL.md 的目录路径）
python3 scripts/perspective-tools/quality_gate.py --judge satyanadella
python3 scripts/perspective-tools/quality_gate.py --judge tests/quality/fixtures/fake-judge  # 金负样本

# 2) 抽样：确定性抽 5 套（slug 字典序排序后取 slugs[(5*轮次+i) mod N]，i=0..4；
#    不用时间、不用随机，同轮次可复现；换轮次即换下一批）
python3 scripts/perspective-tools/quality_gate.py --sample 0

# 3) 自测回归：金正样例零误报 + 金负样本必拦 + 连跑 10 次 sha256 逐字节一致
python3 scripts/perspective-tools/quality_gate.py --selftest
```

退出码：`0` = 报告产出且结论 PASS；`1` = 结论 FAIL（任一 P0 fail；报告照常产出）；
`2` = 用法/IO 错误。

报告纪律：结论行 → 条目表 → 缺口表 → 豁免（显式列出，不静默）→ 机器可读 JSON 行。
报告不含时间戳/耗时/绝对路径，同仓库状态下逐字节可复现。**T2 起只报告不阻断**
（P1 转 hard gate 另立议题）。

## 三、契约 JSONL（元评审只读消费）

`--json-out FILE` 把同一份契约 JSON 行**追加**写入 FILE（JSONL，一评委一行）：

```bash
python3 scripts/perspective-tools/quality_gate.py --judge satyanadella \
    --json-out /tmp/gate-results.jsonl
```

- 契约（T1 §四.2）：`gate_version` / `judge_slug` / `items[{id,level,status}]` /
  `pass_count` / `warn_count` / `exempt_count`；`status` 四值枚举
  `pass|warn|fail|exempt`，`level` 固定 `P0|P1`。
- 追加语义：多评委逐次 `--judge` 累积到同一文件；**同一评委多行时以最后一行为准**
  （消费方去重规则）。FAIL 结论同样写。
- `--selftest` 不支持 `--json-out`（回归验收走 stdout）。
- 消费方：[scripts/ci_gate_status.py](../../scripts/ci_gate_status.py)（PRD-151/T3）
  对门禁**只读不解释**——不重跑条目、不改判定，只按契约字段渲染 PR 摘要；
  `.github/workflows/panel-validation.yml` 的 meta-review job 在 PR 改动
  `perspectives/**` 时自动调用（只报告，不设合并门禁）。

## 四、豁免台账（docs/quality/exemptions.yaml）

P1 条目的缺口在过渡期可登记豁免；台账集中单文件，便于 diff review。

```yaml
- slug: <judge-slug>          # 一位评委
  item_id: B-2                # 只允许 P1 条目（B-1..B-4 / C-1..C-3）
  reason: <一句话，必填>
  expires: 2026-12-31         # 必填，按日期判断，过期自动失效
  issue: zhanglunet/trend#755 # 追踪链接
```

规则（T1 §五）：

1. **P0 不设豁免**——它们今天已全绿，退步即回归。
2. 每位评委同时有效豁免 **≤3 条**。
3. 改豁免文件的 PR 必须**人工 review**（人工闸门）。
4. 报告中豁免条目显式列出并计入 `exempt_count`（状态 `exempt`），**不静默**；
   已机检 pass 的条目无需豁免。
5. 当前登记：0 条（台账文件由 T5 建立，仅含用法注释）。

## 五、报告归档（docs/quality/judges/）

需要留档的门禁报告按 `docs/quality/judges/<slug>-<YYYY-MM-DD>.md` 命名归档
（纯加法目录，T1 §四.5）；元评审复核线索联动会优先取「本次运行的契约 JSONL」，
其次按文件名日期取该评委最新归档的结论行与过门日期。

范例（PRD-151/T4 全绿样例，T5 归档）：
[judges/satyanadella-2026-10-25.md](judges/satyanadella-2026-10-25.md)
——一条命令即可复核：`--judge satyanadella` 应得 `PASS 13/13 · warn 0 · exempt 0`。
归档是日期快照（A-5 全局 pytest 计数、C-2 评委总数会随仓库演进变化），
复核对照「结论行 + 机器可读 JSON 行」即可，不必逐字节比对。

## 六、密钥纪律（C-3）

SKILL.md 与 `references/research/*.md` 不得出现真实内部主机名、IP、账号、密钥；
示例一律占位符。白名单占位形态（不报）：`<API_KEY>`、`<TOKEN>`、`${ENV_VAR}`、
`akm-xxx`、`sk-ant-...`、`example.com`、`example.internal`、`127.0.0.1`、`localhost`。
命中类别：凭据赋值 / 内网网段 / 密钥前缀 / 私钥块（P1 warn-only，报告给出
文件:行号与建议动作）。本目录（docs/quality/）与门禁文档同样受
`tests/quality/test_t5_acceptance.py` 的 0 命中断言约束。

## 七、金样例与自测

- 金正样例 `satyanadella`：期望 13/13 全绿（T4 范例，见 §五归档）。
- 金负样本 `tests/quality/fixtures/fake-judge/`（合成，不入 perspectives/）：
  内置 3 模型 / DNA 同 facet / 伪造 blockquote / 合成密钥形态，期望 A-2 / A-3 必拦
  （fail）、C-3 必拦（warn）。
- `--selftest` 断言上述期望 + 连跑 10 次报告 sha256 逐字节一致；
  pytest 包装见 [tests/quality/test_quality_gate.py](../../tests/quality/test_quality_gate.py)、
  [tests/quality/test_t5_acceptance.py](../../tests/quality/test_t5_acceptance.py)。

T5 验收记录：[t5-acceptance-2026-10-25.md](t5-acceptance-2026-10-25.md)。
