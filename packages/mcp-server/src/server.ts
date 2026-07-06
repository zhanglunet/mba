import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { homedir } from 'node:os';
import { join } from 'node:path';

import { FilesystemStore } from './store/filesystem.js';
import { SubscriptionStore } from './store/subscriptions.js';
import { StateMachine } from './orchestrator/state-machine.js';
import { CronScheduler } from './orchestrator/scheduler.js';
import { runAudit } from './orchestrator/runner.js';
import { LLMClient } from './llm/client.js';
import { proposeAudit } from './tools/propose-audit.js';
import { resumeAudit } from './tools/resume-audit.js';
import { getStatus } from './tools/get-status.js';
import { fetchReport } from './tools/fetch-report.js';
import { listAudits } from './tools/list-audits.js';
import { addJudge } from './tools/add-judge.js';
import { subscribeBrand } from './tools/subscribe-brand.js';
import { triggerEvolution } from './tools/trigger-evolution.js';
import { listSubscriptions } from './tools/list-subscriptions.js';
import { unsubscribeBrand } from './tools/unsubscribe-brand.js';
import { getDeltaReport } from './tools/get-delta-report.js';
import { listPanels } from './tools/list-panels.js';
import { getBrandTrend } from './tools/get-brand-trend.js';
import type { ServerConfig } from './types.js';

export function buildConfig(): ServerConfig {
  return {
    store_dir: process.env['MBA_STORE_DIR'] ?? join(homedir(), '.mba'),
    max_parallel: Number(process.env['MBA_MAX_PARALLEL'] ?? 5),
    max_concurrent_audits: Number(process.env['MBA_MAX_CONCURRENT_AUDITS'] ?? 3),
    max_tokens_per_audit_input: Number(process.env['MBA_MAX_TOKENS_INPUT'] ?? 1_500_000),
    max_tokens_per_audit_output: Number(process.env['MBA_MAX_TOKENS_OUTPUT'] ?? 200_000),
    max_audit_runtime_ms: Number(process.env['MBA_MAX_AUDIT_RUNTIME_MIN'] ?? 30) * 60_000,
    log_level: (process.env['MBA_LOG_LEVEL'] ?? 'info') as ServerConfig['log_level'],
  };
}

function makeLogger(level: ServerConfig['log_level']) {
  const LEVELS = { error: 0, warn: 1, info: 2, debug: 3, trace: 4 };
  const threshold = LEVELS[level];
  return (l: string, msg: string) => {
    if (LEVELS[l as keyof typeof LEVELS] <= threshold) {
      process.stderr.write(`[mba-mcp] [${l.toUpperCase()}] ${msg}\n`);
    }
  };
}

export function createServer(): McpServer {
  const config = buildConfig();
  const log = makeLogger(config.log_level);
  const store = new FilesystemStore(config.store_dir);
  const subStore = new SubscriptionStore(config.store_dir);
  const sm = new StateMachine(store, log);
  const judgesDir = join(config.store_dir, 'judges');

  const server = new McpServer({
    name: 'mba-mcp-server',
    version: '0.1.0',
  });

  // ── Tool: propose_audit ──────────────────────────────────────────────────
  server.registerTool(
    'propose_audit',
    {
      description:
        '给品牌名生成审计 PRD（proposal），返回 audit_id。不立即开始研究 — 调用方需要再调 confirm_audit。',
      inputSchema: {
        brand: z.string().min(1).describe('品牌名或主页 URL'),
        mode: z.enum(['fresh', 'evolution', 'auto']).optional().default('auto'),
        panel: z
          .string()
          .optional()
          .describe(
            '评委面板：default / auto / luxury-en / vc-en / vc-cn / consumer-cn / ai-app-cn / edu-cn / cross-border / security-cn-global（默认 default 的 5 位）',
          ),
        focus_dimensions: z
          .array(z.string())
          .optional()
          .describe('只调研这些维度（默认全 7 个）'),
        judges: z
          .array(z.string())
          .optional()
          .describe('显式指定评委列表（会覆盖 panel）'),
        skip_wuying: z.boolean().optional().default(false),
        language: z.enum(['zh', 'en', 'auto']).optional().default('auto'),
      },
    },
    async (input) => {
      const result = await proposeAudit(input, store);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    },
  );

  // ── Tool: confirm_audit ──────────────────────────────────────────────────
  server.registerTool(
    'confirm_audit',
    {
      description:
        '确认 proposal 并启动 Phase 2 开始研究。非阻塞 — 立即返回 { phase: "researching" }，用 get_status 轮询进度。',
      inputSchema: {
        audit_id: z.string().describe('propose_audit 返回的 audit_id'),
        edits: z
          .object({
            drop_dimensions: z.array(z.string()).optional(),
            add_dimensions: z.array(z.string()).optional(),
            drop_judges: z.array(z.string()).optional(),
          })
          .optional(),
        max_cost_usd: z
          .number()
          .positive()
          .optional()
          .describe('成本上限（USD），超过则中断'),
      },
    },
    async (input) => {
      const state = await store.readState(input.audit_id);
      if (!state) throw new Error(`AUDIT_NOT_FOUND: ${input.audit_id}`);
      if (state.phase !== 'proposed') {
        throw new Error(`AUDIT_ALREADY_RUNNING: audit is in phase '${state.phase}'`);
      }

      if (input.max_cost_usd !== undefined) {
        state.options.max_cost_usd = input.max_cost_usd;
      }

      const apiKey = process.env['ANTHROPIC_API_KEY'];
      if (!apiKey) throw new Error('MISSING_API_KEY: set ANTHROPIC_API_KEY env var');

      const next = await sm.transition(state, 'researching');

      const client = new LLMClient(apiKey);
      const runnerConfig = {
        maxParallel: config.max_parallel,
        maxCostUsd: state.options.max_cost_usd,
        judgesDir,
      };

      runAudit(next, store, sm, runnerConfig, client, log).catch(err => {
        log('error', `confirm_audit background runner crashed: ${err}`);
      });

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              audit_id: next.audit_id,
              phase: next.phase,
              message: 'Audit started. Poll get_status for progress.',
            }),
          },
        ],
      };
    },
  );

  // ── Tool: resume_audit ───────────────────────────────────────────────────
  server.registerTool(
    'resume_audit',
    {
      description:
        '续跑一个卡住的审计（进程中断 / 出错 / interrupted），复用同一 audit_id 与配置。已完成的阶段从磁盘复用产物、不重跑，从第一个未完成的阶段继续。非阻塞，用 get_status 轮询。',
      inputSchema: {
        audit_id: z.string().describe('要续跑的 audit_id'),
        max_cost_usd: z
          .number()
          .positive()
          .optional()
          .describe('成本上限（USD），超过则中断'),
      },
    },
    async (input) => {
      const apiKey = process.env['ANTHROPIC_API_KEY'];
      const result = await resumeAudit(input, {
        store,
        sm,
        hasApiKey: Boolean(apiKey),
        run: (s) => {
          const client = new LLMClient(apiKey!);
          const runnerConfig = {
            maxParallel: config.max_parallel,
            maxCostUsd: s.options.max_cost_usd,
            judgesDir,
          };
          runAudit(s, store, sm, runnerConfig, client, log).catch(err => {
            log('error', `resume_audit background runner crashed: ${err}`);
          });
        },
      });
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    },
  );

  // ── Tool: get_status ─────────────────────────────────────────────────────
  server.registerTool(
    'get_status',
    {
      description: '查询 audit 的当前状态、进度百分比和 token 用量。',
      inputSchema: {
        audit_id: z.string(),
      },
    },
    async (input) => {
      const result = await getStatus(input.audit_id, store, sm);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    },
  );

  // ── Tool: fetch_report ───────────────────────────────────────────────────
  server.registerTool(
    'fetch_report',
    {
      description: '拉取已完成 audit 的报告（markdown / html / both）。',
      inputSchema: {
        audit_id: z.string(),
        format: z.enum(['markdown', 'html', 'both']).optional().default('markdown'),
      },
    },
    async (input) => {
      const result = await fetchReport(input, store);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    },
  );

  // ── Tool: list_audits ────────────────────────────────────────────────────
  server.registerTool(
    'list_audits',
    {
      description: '列出本机 MBA_STORE_DIR 下所有 audit（最新在前）。',
      inputSchema: {},
    },
    async () => {
      const result = await listAudits(store);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    },
  );

  // ── Tool: add_judge ──────────────────────────────────────────────────────
  server.registerTool(
    'add_judge',
    {
      description:
        '注册自定义评委 persona。persona_markdown 需符合 perspective-skill schema（含 anti-fabrication 红线）。',
      inputSchema: {
        name: z.string().regex(/^[a-z][a-z0-9-]{1,30}$/),
        persona_markdown: z.string().min(1),
        validate_only: z
          .boolean()
          .optional()
          .default(false)
          .describe('只做校验，不注册'),
      },
    },
    async (input) => {
      const result = await addJudge(input, judgesDir);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    },
  );

  // ── Tool: subscribe_brand ────────────────────────────────────────────────
  server.registerTool(
    'subscribe_brand',
    {
      description:
        '订阅品牌自动演化追踪。支持 cron（定期）、webhook（外部推送）触发器。触发时自动启动 EVOLUTION 模式重审。',
      inputSchema: {
        brand: z.string().min(1).describe('品牌名'),
        panel: z.string().optional().describe('评委面板（默认 default）'),
        triggers: z
          .array(
            z.object({
              type: z.enum(['cron', 'webhook', 'keyword', 'news']),
              config: z.record(z.unknown()).optional(),
            }),
          )
          .optional()
          .describe('触发器列表（默认 cron interval_days:7）'),
        notify: z
          .array(
            z.object({
              type: z.enum(['webhook', 'email', 'mcp-push']),
              url: z.string().optional(),
              address: z.string().optional(),
            }),
          )
          .optional()
          .describe('推送目标列表'),
        min_interval_days: z.number().positive().optional().default(7),
        max_per_month: z.number().positive().optional().default(4),
      },
    },
    async (input) => {
      const result = await subscribeBrand(input, subStore);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    },
  );

  // ── Tool: trigger_evolution ──────────────────────────────────────────────
  server.registerTool(
    'trigger_evolution',
    {
      description:
        '手动触发品牌 EVOLUTION 模式重审（比较上次基线）。cadence guard 默认生效，可用 force:true 跳过。',
      inputSchema: {
        brand: z.string().min(1),
        event_type: z
          .string()
          .optional()
          .describe('触发类型（product_launch / executive_change / negative_event / …）'),
        event_summary: z.string().optional().describe('事件摘要（可选，写入 log）'),
        source_url: z.string().optional(),
        force: z.boolean().optional().default(false).describe('跳过 cadence guard'),
      },
    },
    async (input) => {
      const apiKey = process.env['ANTHROPIC_API_KEY'];
      if (!apiKey) throw new Error('MISSING_API_KEY: set ANTHROPIC_API_KEY env var');
      const client = new LLMClient(apiKey);
      const runnerConfig = { maxParallel: config.max_parallel, judgesDir };
      const result = await triggerEvolution(input, store, subStore, sm, runnerConfig, client, log);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    },
  );

  // ── Tool: list_subscriptions ─────────────────────────────────────────────
  server.registerTool(
    'list_subscriptions',
    {
      description: '列出所有活跃品牌订阅及其触发器、最近触发时间。',
      inputSchema: {},
    },
    async () => {
      const result = await listSubscriptions(subStore);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    },
  );

  // ── Tool: unsubscribe_brand ──────────────────────────────────────────────
  server.registerTool(
    'unsubscribe_brand',
    {
      description: '删除品牌订阅，停止自动触发。',
      inputSchema: {
        subscription_id: z.string().describe('list_subscriptions 返回的 subscription_id'),
      },
    },
    async (input) => {
      const result = await unsubscribeBrand(input, subStore);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    },
  );

  // ── Tool: list_panels ────────────────────────────────────────────────────
  server.registerTool(
    'list_panels',
    {
      description:
        '列出可用的评委面板及各自评委阵容（10 个行业面板 + default）。在 propose_audit 选 panel 前用它发现有哪些面板。',
      inputSchema: {},
    },
    async () => {
      const result = listPanels();
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    },
  );

  // ── Tool: get_brand_trend ────────────────────────────────────────────────
  server.registerTool(
    'get_brand_trend',
    {
      description:
        '某品牌跨多次审计的评分轨迹（overall + per-lens 随时间变化）。delta 只比两次，trend 比 N 次。',
      inputSchema: {
        brand: z.string().min(1),
      },
    },
    async (input) => {
      const result = await getBrandTrend(input, store);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    },
  );

  // ── Tool: get_delta_report ───────────────────────────────────────────────
  server.registerTool(
    'get_delta_report',
    {
      description:
        '对比两次审计（新 vs 旧基线）的评分变化，产出 delta 报告（per-lens 均值差 + 变化叙述）。previous_audit_id 缺省时自动找同品牌上一份 done 审计。',
      inputSchema: {
        audit_id: z.string().describe('新审计 audit_id'),
        previous_audit_id: z
          .string()
          .optional()
          .describe('基线 audit_id（缺省自动查找同品牌上一份）'),
        narrative: z
          .boolean()
          .optional()
          .default(true)
          .describe('是否生成 LLM 变化叙述（需 ANTHROPIC_API_KEY）'),
      },
    },
    async (input) => {
      const apiKey = process.env['ANTHROPIC_API_KEY'];
      const client = apiKey ? new LLMClient(apiKey) : null;
      const result = await getDeltaReport(input, store, client, log);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    },
  );

  // ── Start cron scheduler ─────────────────────────────────────────────────
  const apiKey = process.env['ANTHROPIC_API_KEY'];
  if (apiKey) {
    const schedulerClient = new LLMClient(apiKey);
    const runnerConfig = { maxParallel: config.max_parallel, judgesDir };
    const scheduler = new CronScheduler(subStore, store, sm, runnerConfig, schedulerClient, log);
    scheduler.start();
  }

  return server;
}
