# PRD-282/T1：评委包配置快照 + 新旧口径复算对照设计（judge-config-snapshot-v1）

- 日期：2026-10-29
- 来源：2026-10-28 趋势日报 mba 第 1 条（⭐），用户当日拍板采纳
- trend issue：[zhanglunet/trend#1411](https://github.com/zhanglunet/trend/issues/1411)
- 中央 PRD：`trend/adopted/PRD-282-mba-judge-config-snapshot.md`
- 状态：T1 设计稿，待评审；实现类任务（T2–T4）只开 PR 不合并
- 同批主题：本批「可逆改动包」14 仓同构——先快照、再改动、一键回上一版

## 1. 目标与非目标

**目标**：更换评委包或改评分口径版本前自动留配置快照（包清单 + 口径版本指纹 + taken_at）；一键回滚到上一版；新旧口径在样例集上复算对照（`recalc_diff(old, new, samples)`），差异写机读复算记录，口径漂移可视化；口径变更 / 回滚 / 复算三类记录可审计。

**非目标**：

- **不改评分逻辑本身**——快照 / 回滚 / 复算组件对评分零判定权，评分引擎与提示词装配流程零改动；
- **不做多口径并行评审**——`recalc_diff` 是样例集上的一次性对照留痕，不构成双口径同时服务正式评审；
- 不替代 PRD-262 安检——262 管"进池先扫"（包干不干净），本条管"已进池配置变更可不可逆"；
- 不做配置版本历史树——一键只回"上一版"；更早版本走 git 历史与快照 archive 对账，不另造版本体系。

## 2. 与既有能力的划界

| 既有能力 | 关系 |
|---|---|
| PRD-233 评委包分层 | 233 管"包长什么样"（分层 / 目录 / 字段标准）；本条管"配置怎么安全地变回去"。快照只按封闭清单采文件，**不定义、不新增包结构字段**（frontmatter 是否强制 `version` 归 233/262 领地，本设计以指纹为版本事实，见 3.2） |
| PRD-262 评委包安检 | 262 管进池前置安检（HIGH 不进池）；本条管进池后的配置变更可逆。回滚**不触发安检重扫**——只留指纹供 262 既有的"哈希变更自动重扫"机制对账 |
| PRD-151 评委质量门 | 151 管评得好不好；本条的复算记录是口径漂移证据，可被 151 档案**只读引用**（`recalc_ref`），不改 151 判定逻辑 |
| git 历史 | git 记录"变更怎么发生"（PR 合并历史）；快照记录"运行时回滚点"（包清单 + 指纹 + taken_at），一键执行、不依赖 git 操作权限；两者指纹互相对账 |
| validate_panels / CI 质量门 | 面板结构校验与 CI 门照旧；回滚后同样过既有校验——校验不过 = 回滚失败告警，不静默半还原 |

## 3. 方案设计

### 3.1 快照对象与时机

**快照对象（封闭清单，全部为 git 已跟踪的口径文件）**：

| 对象 | 路径 | 说明 |
|---|---|---|
| P-1 评委包 | `perspectives/<slug>-perspective/`（SKILL.md + `references/**`） | 人设与评分标准本体（任一包变更即触发） |
| P-2 panel 名册 | `metric-brand-auditor/panels/<name>.yaml` | 评委名册 / 权重 / 题组口径 |
| P-3 评委提示词模板 | `metric-brand-auditor/references/judge-prompt-template.md` | 全评委共用的口径公共部分 |

- **不在清单**：`reports/`、`founders/`、`research/` 等业务与语料面——评审产物与品牌数据不进快照、不被回滚；
- **时机：挂在口径变更确认动作前强制触发**——panel yaml / 评委包变更进入应用（合并 / 发布）前先快照；快照失败 ⇒ 变更中止（fail-close：宁可不能改，不可不可回）；
- 对象均在 git 内 ⇒ 快照副本与 git 双写，`base_commit` + 指纹互相对账（防"改了口径却忘记快照"）。

### 3.2 快照 schema：`judge-config-snapshot-v1`

```json
{
  "schema": "judge-config-snapshot-v1",
  "snapshot_id": "jcs-20261029-a1b2c3d4",
  "taken_at": "2026-10-29T09:00:00+08:00",
  "trigger": {
    "kind": "rubric_change_apply",
    "ref": "<变更单号占位，如 PR 编号>",
    "actor_role": "<operator|system，只记角色不记个人身份>"
  },
  "base_commit": "<git 短哈希占位，如 1a2b3c4>",
  "packs": [
    {
      "kind": "perspective|panel|prompt_template",
      "path": "perspectives/example-skeptic-perspective/",
      "declared_version": null,
      "content_sha256": "sha256:<占位>",
      "bytes": 12345
    }
  ],
  "rubric_manifest_fingerprint": {
    "algorithm": "sha256-canonical-json",
    "file_count": 3,
    "fingerprint": "sha256:<占位>"
  },
  "snapshot_dir": "docs/quality/judge-config-snapshots/jcs-20261029-a1b2c3d4/",
  "notes": []
}
```

- **口径版本指纹**：封闭清单内每个文件取 sha256，按路径排序后对 `{path, content_sha256}` 的 canonical JSON 取 sha256——两次快照指纹相同 ⇒ 口径语义面未变（防"改了口径却忘记快照"或"快照与实际不符"）；
- `declared_version`：frontmatter `version` 若有则记（PRD-262 J-4-01 会提示缺失）；本设计**不强制新增 version 字段**（包结构标准归 PRD-233）——`rubric_version = declared_version ?? "fp:<指纹前 8 位>"`，指纹即版本事实；
- 快照目录内含 `snapshot.json`（本 schema）+ 封闭清单文件完整副本（可逐字节还原）；存放 `docs/quality/judge-config-snapshots/`（与 PRD-151 档案、安检报告同域，进 git）；
- **保留策略：最近一份快照即"上一版"一键回滚点**；被新快照覆盖前转入 `archive/` 只读留档（不参与一键回滚，仅审计追溯），与 git 历史互为对账。

### 3.3 回滚接口与语义

**接口（T2 实现）**：

```
snapshot_judge_config(trigger) -> judge-config-snapshot-v1   # 变更确认动作前强制调用
rollback_judge_config(snapshot_id?, reason) -> rollback-record-v1
```

**回滚语义（全部为硬规则）**：

1. **只回上一版**：无参调用回滚到最近一份快照；带 `snapshot_id` 仅限 archive 里存在的快照（并显式记录非默认回滚）；
2. **逐字节还原**：从快照目录复制文件回原路径；还原后**重算清单指纹必须与快照记录一致**，不一致即回滚失败并告警（绝不静默半还原）；还原后再跑既有结构校验（validate_panels 等），不过同样告警——校验归既有工具，本条不新增判定；
3. **回滚不含评分语义审批**：恢复的是旧版原样，不因回滚产生"新口径"，不重解释、不重打分；
4. **回滚留审计、可再回滚**：回滚完成即写一条 `rollback-record-v1`（append-only）；回滚前把当前（问题）状态的清单指纹记入记录；快照槽在回滚后**保留不覆盖**；若要把"回滚前的新口径"装回来，走正常变更流程（新变更 + 新快照），全程留审计——不存在"回滚后无路可走"的状态。

**`rollback-record-v1`**（追加进 `docs/quality/judge-config-snapshots/audit.jsonl`）：

```json
{
  "schema": "rollback-record-v1",
  "rollback_id": "rcr-20261029-e5f6a7b8",
  "at": "2026-10-29T14:30:00+08:00",
  "actor_role": "operator",
  "snapshot_id": "jcs-20261029-a1b2c3d4",
  "from_fingerprint": "sha256:<占位>",
  "to_fingerprint": "sha256:<占位>",
  "verify": "passed",
  "reason": "<必填一句话，如：新口径误压信任维度权重，回上一版>"
}
```

### 3.4 新旧口径复算对照：`recalc_diff`（T3 核心交付）

**接口**：`recalc_diff(old_ref, new_ref, samples) -> recalc-record-v1`

- `old_ref` / `new_ref`：快照号或 `"current"`（现行口径）；`samples`：样例品牌集（`tests/fixtures` 虚构样例，封闭清单）；
- **执行方式**：对每个样例分别在 old / new 口径下跑同一评分流程——评分引擎与提示词装配零改动，只把口径装载入口指向快照副本（复用质量门既有 `--panels-dir` / `--judges-dir` 参数化形态），得到双份评分；
- **差异粒度**：样例 × 评分维度（分数 delta）+ 结论翻转（`verdict_changed`）；全部写入机读记录；
- **对照不评审（硬规则）**：`recalc_diff` 产物只入库留痕与可视化，**不回写任何正式评审结论、不触发重评、不参与双口径并行服务**（N-3 负向钉住）。

**`recalc-record-v1`**（入库：`docs/quality/judge-config-snapshots/recalc/<recalc_id>.json` + 摘要行追加 `audit.jsonl`）：

```json
{
  "schema": "recalc-record-v1",
  "recalc_id": "rcd-20261029-b2c3d4e5",
  "at": "2026-10-29T15:00:00+08:00",
  "trigger": { "kind": "rubric_change_apply", "ref": "<变更单号占位>" },
  "old": { "ref": "jcs-20261029-a1b2c3d4", "fingerprint": "sha256:<占位>" },
  "new": { "ref": "current", "fingerprint": "sha256:<占位>" },
  "samples": [
    {
      "sample_id": "brand-example-01",
      "dimensions": [
        { "dim": "<维度代号，如 trust>", "old_score": 3.5, "new_score": 4.0, "delta": 0.5 }
      ],
      "verdict_changed": true
    }
  ],
  "drift_summary": {
    "sample_count": 8, "dimension_count": 5,
    "changed_dimensions": 2, "max_abs_delta": 1.0, "flipped_count": 1
  },
  "notes": []
}
```

- **口径漂移可视化（T3/T4）**：由 `recalc-record-v1` 渲染静态漂移视图——维度 × 样例 delta 热力表 + 结论翻转清单（Markdown/HTML，落 `docs/quality/`），零新基础设施、零外部服务。

### 3.5 三类记录可审计（T4）

| 记录 | schema | 触发 |
|---|---|---|
| 变更记录 | `change-record-v1` | 快照创建即变更登记（snapshot_id / trigger / fingerprint / taken_at） |
| 回滚记录 | `rollback-record-v1` | 回滚完成 |
| 复算记录 | `recalc-record-v1` | `recalc_diff` 完成 |

- 三类记录统一 append-only `audit.jsonl`（一行一 JSON，`ensure_ascii=False`，权限 600）；
- **导出（T4）**：按 schema / 时间段 / 指纹过滤导出机读 JSONL + 人读摘要（口径变更史一页可查）；
- **对账断言**：每条 rollback / recalc 记录引用的 `snapshot_id` 必须存在于快照库；指纹链一致（如 `rollback.from_fingerprint` == 该时刻现行快照指纹）；断言失败即审计不通过。

### 3.6 演练样本（T2 夹具、T5 回放，全虚构）

| 样本 | 内容（全虚构） | 预期 |
|---|---|---|
| P-1 常规口径变更 | 虚构评委包 `example-skeptic-perspective` 评分标准改一条 | 变更前自动出快照；可一键回滚；指纹一致 |
| P-2 复算对照 | P-1 后对 8 个虚构样例跑 `recalc_diff` | 记录字段齐全机读可解析；漂移视图可渲染 |
| N-1 快照被跳过 | 模拟跳过 snapshot 直接应用变更 | 变更中止（fail-close），口径无变化 |
| N-2 还原后指纹不符 | 人为篡改快照副本一个字节 | rollback 报错退出；`verify: failed` 入审计，无成功回滚记录 |
| N-3 对照夹带回写 | 试图把复算结果写回正式评审结论 | 拒绝：复算产物只入库不回写（3.4 断言） |

## 4. 安全红线

1. **评分引擎是真相**：快照 / 回滚 / 复算组件对评分零判定权，评分逻辑与提示词装配零改动；
2. **对照不评审**：复算结果不回写正式结论、不触发重评、不做双口径并行服务；
3. **fail-close**：该快照时快不了 ⇒ 变更中止；还原后指纹对不上 ⇒ 回滚失败告警；
4. **回滚可再回滚**：全程 append-only 审计，快照槽不覆盖；
5. **评委均为合成人设**（模拟角色，非真实人物）；样例品牌、分数、快照号全虚构；
6. 本地零外联（快照 / 回滚 / 复算纯本地文件操作）；文档与示例无真实内部主机名 / IP / 账号 / 密钥，占位符一律 `<占位>` 形态。

## 5. T2–T5 任务拆分（按 PRD）

| 任务 | 内容 | 验收标准（PRD 原文口径） |
|---|---|---|
| T2 | 快照存储与回滚最小实现（snapshot / restore / 审计记录） | 样例可快照可回滚，审计可查，有测试 |
| T3 | 新旧口径复算对照：`recalc_diff` 对样例集跑双口径，差异写复算记录（机读） | 复算记录字段齐全，有测试 |
| T4 | 口径变更审计断言：变更 / 回滚 / 复算三类记录可审计导出 | 审计断言通过 |
| T5 | 验收试运行：样例全流程回放 + 回滚演练 + 文档无密钥 | 快照回滚全链通过；红线断言全过；文档无密钥 |

依赖关系：T1 → T2 → T3 → T4 → T5。

## 6. T5 验收标准

1. P-1 全链：变更前快照自动发生 → 应用 → 复算对照 → 回滚 → 指纹一致；N-1 fail-close 生效（跳过快照的变更被中止）；
2. P-2 复算记录字段齐全、机读可解析，漂移视图可渲染（维度 × 样例 delta + 翻转清单）；N-3 回写被拒；
3. N-2 篡改被检出：`verify: failed` 入审计且不产生成功回滚记录；
4. 三类记录（`change-record-v1` / `rollback-record-v1` / `recalc-record-v1`）在 `audit.jsonl` 齐全、可导出、对账断言通过（`snapshot_id` 引用与指纹链一致）；
5. 全部 schema / 记录 / 文档密钥扫描 0 命中、真实主机名 / IP / 账号 0 命中；示例全虚构。

## 7. 借鉴划界

- [Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv)：GitHub License API 实测 **NOASSERTION（无协议）**。**仅借鉴「先快照再改动、一键还原」的形态思路，不复用其任何代码与文案**；`judge-config-snapshot-v1` schema、口径清单指纹算法、回滚语义（fail-close / 可再回滚）、`recalc_diff` 复算对照与漂移可视化、三类审计记录均为本仓原创设计。
- 与日报原文的差异修正：日报未核实许可证，实测无协议——借鉴口径据此收紧为"仅形态思路零复用"（同批 14 仓统一口径）。
