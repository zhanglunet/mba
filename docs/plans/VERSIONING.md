# mba 品牌技能版本与变更规范（PRD-234/T4，trend #1173）

> 范围：perspectives/*-perspective/SKILL.md 品牌评委技能包；
> 标准对齐：PRD-199 / agentskills-2026-10（与 234/T2 aligner 口径一致）；
> 机检：scripts/check_perspective_discoverability.py（version semver 逐项校验）；
> 本文档是规范正本，机检是其执法面。

## 1. 版本规则（metadata.version）

- 技能条目 `metadata.version` 必须 semver（`X.Y.Z`），**禁止 v 前缀与预发布
  后缀**（预发布走分支）；**0.0.0 拒绝**（未定版不发布）。
- **MAJOR**：视角判定框架变化（mental_models 增删、判定词表变化——下游消费
  等报告形态变化）。
- **MINOR**：新增触发句式（Explicit triggers）、新增 mental_model 条目、
  description 实质扩展（内容实质变更至少升 MINOR——沿 PRD-227 §6.3）。
- **PATCH**：错别字、排版、引用链接修订（不改变行为与触发）。
- 0.x 阶段 MINOR 视同 MAJOR（不稳定期），1.0.0 冻结契约。

## 2. 变更日志（CHANGELOG）

- 每技能包目录内 `CHANGELOG.md`（与 SKILL.md 同目录），行格式：
  `## <version> - <YYYY-MM-DD>` + `- <变更条目>`（Keep a Changelog 精简形态）。
- 每次版本号变更必须同步 CHANGELOG 条目。
- 变更条目写「变更了什么 + 为什么」，不写「改了哪个文件」。

## 3. 变更流程

1. 改 SKILL.md（或 references 研究语料）；
2. 跑 `python3 scripts/check_perspective_discoverability.py`（对照本文件逐项核对）；
3. 按 §1 判级更新 `metadata.version`；
4. 按 §2 追加 CHANGELOG 条目；
5. PR 提交——评审人核对版本判级与 CHANGELOG。

## 4. 机检增补（本 PR）

- `check_perspective_discoverability.py` 增补：version semver 形态校验
  （v 前缀拒绝、0.0.0 拒绝）——规范正本+机检执法面一体交付。
