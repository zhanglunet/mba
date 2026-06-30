import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { homedir } from 'node:os';
import { join } from 'node:path';

import { FilesystemStore } from './store/filesystem.js';
import { StateMachine } from './orchestrator/state-machine.js';
import { runAudit } from './orchestrator/runner.js';
import { LLMClient } from './llm/client.js';
import { proposeAudit } from './tools/propose-audit.js';
import { getStatus } from './tools/get-status.js';
import { fetchReport } from './tools/fetch-report.js';
import { listAudits } from './tools/list-audits.js';
import { addJudge } from './tools/add-judge.js';
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
        focus_dimensions: z
          .array(z.string())
          .optional()
          .describe('只调研这些维度（默认全 7 个）'),
        judges: z
          .array(z.string())
          .optional()
          .describe('评委列表（默认使用 default panel）'),
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

      // Fire-and-forget: runner writes state.json as it progresses
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

  return server;
}
