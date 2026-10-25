# PRD-151/T5 验收记录（2026-10-25）

> trend issue：zhanglunet/trend#759（PRD-151/T5）。前置：T1 #755（PR #286）、
> T2 #756（PR #287）、T3 #757（PR #288）、T4 #758（PR #290）均已合入 main。
> 验收标准（PRD 任务表 T5 行）：**门禁文档入库；范例可复现；无密钥**。
> 环境：仓库 main @ 57e5605，分支 trend/prd-151-t5-judge-quality-gate，
> Python 3.14.4（.venv，pyyaml 6.0.3 / pytest 9.1.1）。

## 一、验收标准逐条结果

### 1. 门禁文档入库 — 通过

| 文件 | 内容 |
|---|---|
| `docs/quality/judge-quality-gate.md` | 完整使用说明：怎么跑单评委（`--judge`）/ 抽样（`--sample` 确定性公式与轮次用法）/ 自测（`--selftest`）；契约 JSONL（`--json-out` 字段、追加语义、同 slug 取末行、元评审只读消费 `ci_gate_status.py`）；豁免台账用法（字段、P1-only、≤3 条、人工 review、不静默）；报告归档约定；密钥纪律（C-3 白名单占位形态） |
| `docs/quality/exemptions.yaml` | 豁免台账建立（含规则与登记模板注释，当前 0 条；注释形态不参与脚本解析，`load_exemptions()` 仍返回空） |
| `docs/quality/judges/satyanadella-2026-10-25.md` | T4 全绿范例报告归档（`--judge satyanadella` stdout 原样，见 §2） |
| `scripts/perspective-tools/README.md` | 补 T5 指针行，指向上述使用说明与验收记录 |

### 2. 范例可复现 — 通过

**(a) selftest 断言引用（入库测试，随每次 CI 跑）**

- `tests/quality/test_quality_gate.py::test_golden_positive_satyanadella`：
  P0 六条全 pass + 13/13 全绿（pass_count=13, warn=0, exempt=0）。
- `tests/quality/test_quality_gate.py::test_golden_negative_fixture`：
  金负样本 A-2/A-3 fail、C-3 warn，结论 FAIL，退出码 1。
- `scripts/perspective-tools/quality_gate.py --selftest`（T2/T4 交付内建）：
  金正连跑 10 次 sha256 逐字节一致。

**(b) T5 独立复跑记录（2026-10-25，main 基线 57e5605）**

`--selftest` 原样输出（exit 0，28.7s user）：

```
PRD-151/T2 quality_gate 自测（金样例回归 + 确定性验收，F8 先例）
================================================================
  ✅ 金正样例 satyanadella 结论 PASS  结论 PASS · PASS 13/13 · warn 0 · exempt 0
  ✅ 金正样例 P0 六条全 pass  A-1..A-6 = ['pass', 'pass', 'pass', 'pass', 'pass', 'pass']
  ✅ 金正样例 C-3 机检 0 命中  C-3 = pass
  ✅ 金负样本 fake-judge 结论 FAIL  结论 FAIL
  ✅ 金负样本 A-2 必拦  A-2 = fail
  ✅ 金负样本 A-3 必拦  A-3 = fail
  ✅ 金负样本 C-3 必拦  C-3 = warn
  ✅ 确定性 10 次复跑 sha256 一致  sha256=493ef2fb20d88eed…（1 种）
================================================================
✅ 自测通过：门禁对金正样例零误报、对合成负样本有牙、报告逐字节可复现。
```

另做 selftest 之外的独立复核：`--judge satyanadella` 单独连跑 3 次，
stdout sha256 三次一致：

```
4ecc5828ed9decbe10d6d314e5104323570767b45fff7caeb97fdfda21b43add
4ecc5828ed9decbe10d6d314e5104323570767b45fff7caeb97fdfda21b43add
4ecc5828ed9decbe10d6d314e5104323570767b45fff7caeb97fdfda21b43add
```

**(c) 金负样本必拦复核**（`--judge tests/quality/fixtures/fake-judge`，exit 1）：

```
结论: FAIL · PASS 4/13 · warn 7 · exempt 0
  A-2 内容质量 6/6  FAIL  quality_check 4/6 (exit 1)
  A-3 反捏造防火墙  FAIL  firewall 1 quotes checked · 1 FAIL (exit 1)
  C-3 占位符纪律（机检）  WARN  正则清单初版命中 4 处（凭据赋值 / 密钥前缀 / 内网网段 / 私钥块，均为 fixture 内置合成串）
```

**(d) 归档与复跑一致性落为硬测试**：
`tests/quality/test_t5_acceptance.py::test_archived_golden_report_reproducible`
断言归档报告结论行 `PASS 13/13 · warn 0 · exempt 0` 且契约 JSON 行 13 条状态与
三计数 == 现场复跑结果（比对话语见 usage 文档 §五：归档是日期快照，A-5 全局
pytest 计数 / C-2 评委总数会随仓库演进，故比对结论与契约字段、不逐字节比对全文）。

### 3. 无密钥 — 通过

- 硬测试 `tests/quality/test_t5_acceptance.py::test_gate_docs_no_secrets`：
  用门禁自带 C-3 扫描器（四类：凭据赋值 / 内网网段 / 密钥前缀 / 私钥块，白名单
  占位形态不报）扫 `docs/quality/**`（使用说明、豁免台账、归档报告、本记录）与
  `scripts/perspective-tools/README.md`，断言 0 命中。
- 金正样例 C-3 本身 0 命中（见 §2 复跑输出）；金负样本的命中全部来自 fixture
  内置合成串（`SYNTHETIC*` 形态），用于证明扫描器有牙。
- 本批入库文档中的示例一律占位符（`<API_KEY>` / `example.com` 等）。

## 二、测试命令与结果（原样）

| 命令（仓库根，.venv/bin/python） | 结果 |
|---|---|
| `.venv/bin/python scripts/perspective-tools/quality_gate.py --selftest` | exit 0，全 ✅（见 §2(b)） |
| `.venv/bin/python scripts/perspective-tools/quality_gate.py --judge satyanadella` | exit 0，`结论: PASS · PASS 13/13 · warn 0 · exempt 0` |
| `.venv/bin/python scripts/perspective-tools/quality_gate.py --judge tests/quality/fixtures/fake-judge` | exit 1，`结论: FAIL`（A-2/A-3 fail、C-3 warn，见 §2(c)） |
| `.venv/bin/python -m pytest tests/quality -q` | `18 passed in 26.11s` |
| `.venv/bin/python -m pytest tests/quality tests/panels tests/_contract -q` | `90 passed in 27.23s`（T4 基线 86 + T5 新增 4） |

新增测试 4 条（`tests/quality/test_t5_acceptance.py`）：文档密钥扫描断言、
使用文档要点防漂移、豁免台账纪律（P1-only / ≤3 条）、归档范例复现一致性。

## 三、偏差与说明

- 无功能性偏差。PRD 风险条「文档与示例中不得出现真实内部主机名、IP、账号或
  密钥」以 §1.3 硬测试固化。
- 归档报告文件名日期取验收当日（2026-10-25）；PRD/任务创建于 2026-10-23，
  T1–T4 顺延合并至 2026-10-24，不属偏差。
- 豁免台账 0 条：T4 已把范例修至 13/13 全绿，无需豁免；台账为后续 P1 缺口预留。
