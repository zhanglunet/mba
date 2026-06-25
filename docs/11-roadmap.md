# MBA 开发路线图与进度日志

> **文档定位**：本文件同时承担两个职责——  
> 1. **路线图**：记录下一步开发计划，优先级和理由  
> 2. **进度日志**：每次开发动作在此追加记录，形成可查历史

---

## 当前状态快照（2026-06-25）

| 维度 | 状态 | 备注 |
|------|------|------|
| 版本 | v0.2.36 | |
| 5阶段流水线 | ✅ 生产就绪 | Phase 0-5 稳定 |
| 评委面板数量 | ✅ 10/10 全部可运行 | default / auto / security-cn-global / ai-app-cn / edu-cn / vc-en / vc-cn / consumer-cn / cross-border / luxury-en |
| 评委全档进度 | ⚠️ 15/43 全档 | 28 人仍在 seed 层，待深化 |
| mbabrand.com | ✅ 上线 | Cloudflare Pages |
| 公开报告 | ✅ 2 份 | Lenovo + 成市 Auto |
| CI/CD | ✅ 运行中 | 面板校验 + 结构检查 + 站点构建 |
| 单元/集成测试 | ❌ 缺失 | 仅有 smoke test |
| --dry-run 标志 | ❌ 未实现 | 设计已在 docs/08 中标注 |
| MCP Server 形态 | ❌ 未实现 | 设计稿在 mcp-server-design.md |

### 评委全档分布（v0.2.36）

**已完成全档（15 人）**

| 面板 | 评委 slug |
|------|-----------|
| default | fusheng, jobs, likejia, wu-jundong, zhang-yiming |
| auto | musk, leijun, lixiang, hexiaopeng, libin |
| security-cn-global | zhouhongyi, zhangmingzheng, renzhengfei |
| vc-en | jensenhuang, satyanadella |

**待深化（28 人）**

| 面板 | 待深化评委 | 可用资料情况 |
|------|-----------|-------------|
| ai-app-cn | 3 人（wangxiaochuan, wanghuiwen, limuou） | 中文为主，需 Wuying Pro |
| edu-cn | 3 人（salkhan, shouzicheng, huangzheng） | 部分有英文 PDF |
| vc-en | 3 人（paulgraham, bhorowitz, marcandreessen） | **英文 essay 可直接 WebFetch** |
| vc-cn | 3 人（zhanglei, xuxin, shennp） | 中文为主，需 Wuying Pro |
| consumer-cn | 5 人（jiangnanc, zhongsc, luoyonghao, yangm, zhangl） | 中文为主，需 Wuying Pro |
| cross-border | 4 人（huangzheng-cr, zhoushouzi, chennnian, zhuangshuai） | 中文为主，需 Wuying Pro |

---

## 关键阻断项

| 阻断项 | 影响范围 | 解法 | 状态 |
|--------|----------|------|------|
| Wuying 免费版 `GetLink` 返回 400 | 25 位中文评委无法深化 | 升级到 Pro/Ultra | ❌ 待解 |
| 沙箱 WebFetch 对 paulgraham.com / Wikipedia 返回 403 | vc-en 3 位英文评委受阻 | Wuying 代理访问，或 Jina Reader | ❌ 待解 |

---

## 开发路线图

### 优先级 P0 — 立即可执行，不依赖外部解锁

#### P0-A：深化 vc-en 英文评委（3 人）

**目标**：将 paulgraham、bhorowitz、marcandreessen 从 seed 升级到 full 档  
**理由**：英文 essay 无访问限制，当前环境即可完成，且 vc-en 面板是对海外品牌最常用的面板  
**输出物**：每位评委的 `references/research/01-06.md` + `quotes.md`  
**参考 SOP**：`docs/10-deepening-perspectives.md`

- [ ] paulgraham — paulgraham.com essays 6 路径研究
- [ ] bhorowitz — a16z.com blog + hard thing about hard things
- [ ] marcandreessen — pmarca.com archive + 近期 X 发言

#### P0-B：实现 `--dry-run` 标志

**目标**：`/mba 小米 --dry-run` 打印 PRD + 面板选择 + 维度计划，不触发真实搜索  
**理由**：文档已设计，用户需要在正式审计前预览和调整计划  
**实现位置**：`metric-brand-auditor/SKILL.md` Phase 0/1 路由逻辑  
**验收标准**：dry-run 后无网络请求，输出包含：品牌名、选定面板、7 个维度描述、预计评委列表

- [ ] SKILL.md 增加 `--dry-run` 参数解析
- [ ] Phase 0 增加 dry-run 分支（打印计划后退出）
- [ ] docs/05-usage.md 补充 `--dry-run` 示例

---

### 优先级 P1 — 依赖 Wuying Pro 升级

#### P1-A：批量深化中文评委（25 人）

**触发条件**：Wuying 升级到 Pro/Ultra，`GetLink` 可用  
**执行顺序建议**（按面板使用频率排序）：

1. consumer-cn 5 人（使用频率高，国内品牌大量需求）
2. vc-cn 3 人（投资/创业类品牌需要）
3. ai-app-cn 3 人（AI 产品审计核心面板）
4. cross-border 4 人（出海品牌需求）
5. edu-cn 3 人（教育类）

**每人标准工作量**：约 6 个研究文件（`01-06.md`）+ `quotes.md` 更新  
**验收标准**：`scripts/perspective-tools/quality_check.py` 通过（80% 一手来源）

- [ ] 升级 Wuying 套餐
- [ ] 跑 smoke test 确认 `GetLink` 可用
- [ ] 按顺序深化 25 人

#### P1-B：`--panel-merge` 跨面板对比报告

**目标**：支持将两次不同面板的审计结果合并到同一报告的对比章节  
**场景**：同一品牌用 default + vc-en 两套视角对比，形成"内行 vs 外行"差异热力图  
**复杂度**：Phase 5 Merge 需支持跨面板 diff 视图，版本控制需记录面板变更

- [ ] 设计跨面板对比数据结构
- [ ] SKILL.md Phase 5 增加 panel-merge 逻辑
- [ ] HTML 模板增加对比视图组件

---

### 优先级 P2 — 质量与基础设施

#### P2-A：集成测试 Workflow

**目标**：CI 中增加轻量级集成测试，验证 `--quick --no-judges --dry-run` 路径  
**文件位置**：`.github/workflows/integration-test.yml`  
**测试策略**：用 mock 品牌数据跑完 Phase 0-1，验证输出格式；不触发真实 WebSearch

- [ ] 编写 integration-test.yml
- [ ] 创建 mock 测试数据（`tests/fixtures/`）
- [ ] 验证报告 Markdown 结构符合 schema
- [ ] 验证 HTML 报告含必要组件（radar chart、Mermaid 图）

#### P2-B：扩充公开报告（各面板至少 1 份）

**目标**：10 个面板各有 1 份公开样本报告  
**理由**：当前仅 2 份（default + auto），其他 8 个面板无演示  
**优先补充**：vc-en（海外品牌）、security-cn-global（安全企业）、luxury-en（奢侈品）

- [ ] 选定 8 个品牌（每面板 1 个）
- [ ] 运行完整审计
- [ ] 发布到 `published/reports/`
- [ ] 更新 `site/published-reports.txt` 和 `reports-meta.yaml`

---

### 优先级 P3 — 未来形态

#### P3-A：MCP Server 封装

**文档**：`docs/mcp-server-design.md`（已有完整设计草稿）  
**前置条件**：P0/P1 评委档案质量达标，流水线稳定  
**核心工具暴露**：

```
run_audit(brand, panel, quick, refresh) → report_url
list_panels() → panels[]
get_report(brand) → report_md
```

- [ ] 确认 MCP Server 框架选型
- [ ] 实现 tool 定义和路由
- [ ] 文档 + 示例调用

#### P3-B：报告订阅 / 品牌演化追踪

**目标**：用户订阅某品牌，当品牌有重大新闻时自动触发 EVOLUTION 模式重新审计  
**场景**：品牌发布新产品、高管变动、负面事件后自动更新报告  
**依赖**：需要外部触发机制（webhook / cron）

---

## 进度日志

> **记录格式**：每次完成一项开发动作后，在此追加一条记录，包括日期、完成事项、commit hash、备注。

---

### 2026-06-25

**事项**：整理开发路线图，创建本文档  
**完成内容**：
- 分析全量代码库（43 评委、10 面板、5阶段流水线、完整文档集）
- 整理当前状态快照（v0.2.36）
- 制定 P0-P3 四级优先级路线图
- 识别关键阻断项（Wuying 免费版限制）

**关键发现**：
- 最高杠杆单点：升级 Wuying 套餐，可解锁 25 位评委深化
- 不依赖 Wuying 的立即可执行项：vc-en 英文评委深化 + `--dry-run` 实现
- 测试覆盖是当前最大技术债（无集成测试）

**commit**：— （文档创建）

---

<!-- 在此追加后续进度记录，格式参考上方 -->
