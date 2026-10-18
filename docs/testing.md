# mba 测试说明（PRD-022/T5）

> 面向第一次跑测试的新人：照着"三、怎么跑"把命令粘一遍，全部通过即算环境就绪。
> 规范原文见 `docs/plans/2026-10-17-panel-test-spec.md`（PRD-022/T1）。

## 一、测什么

仓库里和 panel（评委阵容）相关的测试分三层，**全部是静态检查**——只读文件、做断言，不调 LLM、不跑真实打分、不碰网络。

| 层 | 位置 | 测什么 | 数量 |
|---|---|---|---|
| 单 panel 测试 | `tests/panels/test_<panel>.py`（10 个文件，一 panel 一文件） | 每个 panel 7 项：① yaml 可解析 ② 顶层字段齐全（name/display_name/description/judges） ③ `name` 与文件名一致 ④ 评委数量符合预期 ⑤ 每位评委字段齐全（slug/display_name_cn/display_name_en/language/weight） ⑥ 同一 panel 内 slug 无重复 ⑦ weight 合法（`0 < weight <= 2.0` 的数字） | 70 |
| 结构契约测试 | `tests/_contract/test_panels.py` | ① 注册清单一致：`metric-brand-auditor/panels/` 下的 yaml 集合（排除 `industries.yaml`）== 预期的 10 个 panel，多一个少一个都报错 ② portrait 存在：每位评委 `portrait` 字段引用的图片在 `assets/judges/` 下真实存在 | 2 |
| CI 结构校验 | `scripts/validate_panels.py`（纯标准库，CI 里跑） | ① `name` 与文件名一致 ② judges 非空 ③ slug 无重复 ④ language 只能是 zh/en ⑤ weight 是数字且 > 0 ⑥ 每个 slug 在 `perspectives/<slug>-perspective/SKILL.md` 真实存在（不存在 = 硬错误，CI 变红；skeleton 状态的 panel 除外） ⑦ `industries.yaml` 的行业→panel 映射指向真实存在的 panel 文件 | — |

三层加起来 `pytest` 一次跑 **72 个**（70 + 2）。

几个容易踩的坑，提前说明：

- `industries.yaml` 是"行业→panel 映射表"，**不是 panel**，不计入 10 个，也不参与单 panel 测试——但它的映射关系由 `validate_panels.py` 校验（指错文件会 CI 红）。
- 跨 panel 的评委 slug **允许复用**（有意设计，如 `fusheng` 同时在 ai-app-cn 和 default 里），不要加"全局唯一"断言；panel 内的 slug 唯一由各 panel 测试第 ⑥ 项保证。
- 评委"视角"文案是自然语言，只断言字段存在，不断言写得好不好（写不出强断言）。

## 二、不测什么（为什么不测真实打分）

**不调 LLM 跑真实打分**，三个原因：

1. **贵且不稳定**：一次全量打分要调几十次 LLM，又花钱又慢，CI 里跑不起。
2. **没有标准答案**：报告里的分数是 AI 基于评委公开资料的 in-character 模拟推断（见任一报告底部的声明），不是评委本人的真实意见。写不出 `assert score == 8` 这样的断言——因为不存在"8 分一定对"的 ground truth。
3. **分歧是设计如此**：评委视角本就该有分歧（详见 PRD-063 元评审），"分歧大"不等于"打错了"。

那我们改测什么？两样：**结构合法**（上面的三层测试：yaml 对不对、字段齐不齐、引用断没断链）+ **计算确定性**（同样的输入，算两次结果必须逐字节一致）。第二样可以用一条命令亲手验证：

```bash
python3 scripts/meta_review.py published/reports/deepseek/report.md > /tmp/a1.md
python3 scripts/meta_review.py published/reports/deepseek/report.md > /tmp/a2.md
diff -q /tmp/a1.md /tmp/a2.md && echo "确定性 OK"
```

（审计引擎 `scripts/meta_review.py` 是纯计算，不重新打分；确定性的完整验收见 PRD-063/T5 的 `scripts/e2e_meta_review.py`。）

同样不测的：报告 HTML 渲染（另一条链路）、MCP server（另一个包的事）。

## 三、怎么跑

以下三条命令都在仓库根目录执行，**已在干净环境逐条验证通过**（2026-10-18）：

```bash
# 0. 装依赖（一次性；CI 里也是这两样）
pip install pyyaml pytest

# 1. 跑全部 panel 测试：期望 72 passed
python -m pytest tests/panels tests/_contract -q

# 2. 跑 panel 结构校验（CI 同款，纯标准库无需安装）：
#    期望每行 "OK panel: xxx.yaml (N judges)"，最后 "OK industries.yaml"，exit 0
python scripts/validate_panels.py
```

如果第 1 步报 `ModuleNotFoundError: No module named 'yaml'`，说明第 0 步没装好，重装 `pyyaml` 即可。
如果第 2 步报 `ERROR: ...`，按报错信息修对应 panel yaml（字段漏了、slug 重了、perspective 对不上），不要改测试去"迁就"——测试是防线。

想只跑某一个 panel（比如刚改了 `vc-cn.yaml`）：

```bash
python -m pytest tests/panels/test_vc-cn.py -q
```

## 四、CI 规则

- **Workflow**：`.github/workflows/panel-validation.yml`，job 名 `validate-panels`。
- **触发时机**：每个 PR（`pull_request`）和推到 main 的提交（`push: branches: [main]`）都会跑。
- **关键步骤**（按执行顺序）：
  1. `pip install pyyaml pytest`
  2. `python scripts/validate_panels.py` —— "Validate panel configs"
  3. `python -m pytest tests/panels tests/_contract -q` —— "Run panel pytest suite (PRD-022/T2)"
  4. 之后还有 perspective SKILL 结构、Brand Watch、founder/investor 等校验（与 panel 测试无关，不展开）。
- **改坏能拦住**：PR 里故意改坏一个 panel yaml（比如把两个评委的 slug 写重、删掉一个必填字段），上面第 2 或第 3 步会变红，PR 合并不通过。这是 PRD-022/T3 的验收标准，已验证过。
- **meta-review job**（PRD-063/T4 加进来，同一个 workflow 文件里）：`needs: validate-panels`，只在 PR 上跑；用 `git diff` 判断本 PR 是否改动了 `metric-brand-auditor/panels/` 下的 yaml，改了才跑 `scripts/ci_meta_review.py`，把审计摘要贴到 job summary。**只报告、不设合并门禁**（`continue-on-error: true` + 脚本永远 exit 0 + 不在分支保护的 required 列表里），所以它红了也不拦合并——看到它飘红先看是不是审计本身的问题，而不是 panel 改坏了。

## 五、新增 panel / 评委时怎么加测试

1. 在 `metric-brand-auditor/panels/` 下新增 `<name>.yaml`（字段照抄任一现有 panel）。
2. 在 `tests/panels/` 下新增 `test_<name>.py`：**照抄 `test_default.py`**，只改两处——文件头部的 `PANEL` 路径和 `EXPECTED_JUDGES` 人数。
3. 跑 `python -m pytest tests/panels/test_<name>.py -q`，一次通过；再跑全套 `python -m pytest tests/panels tests/_contract -q`，确认注册清单测试也认得新 panel（`_contract` 里的 `EXPECTED_PANELS` 集合要同步加一个名字）。
4. 跑 `python scripts/validate_panels.py`，确认新 panel 的每个 slug 都有对应的 `perspectives/<slug>-perspective/SKILL.md`。
