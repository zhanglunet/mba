import { homedir } from 'node:os';
import { join } from 'node:path';

import { FilesystemStore } from './store/filesystem.js';
import { SubscriptionStore } from './store/subscriptions.js';
import { StateMachine } from './orchestrator/state-machine.js';
import { LLMClient } from './llm/client.js';
import { triggerEvolution } from './tools/trigger-evolution.js';
import { getStatus } from './tools/get-status.js';
import { createReceiver, HttpError } from './http/receiver.js';
import { buildConfig } from './server.js';

function makeLogger(level: string) {
  const LEVELS: Record<string, number> = { error: 0, warn: 1, info: 2, debug: 3, trace: 4 };
  const threshold = LEVELS[level] ?? 2;
  return (l: string, msg: string) => {
    if ((LEVELS[l] ?? 2) <= threshold) {
      process.stderr.write(`[mba-webhook] [${l.toUpperCase()}] ${msg}\n`);
    }
  };
}

function main(): void {
  const config = buildConfig();
  const log = makeLogger(config.log_level);
  const store = new FilesystemStore(config.store_dir);
  const subStore = new SubscriptionStore(config.store_dir);
  const sm = new StateMachine(store, log);
  const judgesDir = join(config.store_dir, 'judges');

  const port = Number(process.env['MBA_WEBHOOK_PORT'] ?? 8787);
  const host = process.env['MBA_WEBHOOK_HOST'] ?? '0.0.0.0';
  const secret = process.env['MBA_WEBHOOK_SECRET'] || undefined;

  const server = createReceiver({
    secret,
    log,
    handleTrigger: async (input) => {
      const apiKey = process.env['ANTHROPIC_API_KEY'];
      if (!apiKey) throw new HttpError(503, 'MISSING_API_KEY', 'set ANTHROPIC_API_KEY to run audits');
      const client = new LLMClient(apiKey);
      const runnerConfig = { maxParallel: config.max_parallel, judgesDir };
      return triggerEvolution(input, store, subStore, sm, runnerConfig, client, log);
    },
    handleStatus: async (auditId) => {
      try {
        return await getStatus(auditId, store, sm);
      } catch {
        return null;
      }
    },
  });

  server.listen(port, host, () => {
    log('info', `webhook receiver listening on http://${host}:${port}`);
    log('info', `  POST /webhooks/trigger   { "brand": "...", "event_type": "...", "event_summary": "..." }`);
    log('info', `  GET  /status?audit_id=…  ·  GET /health`);
    if (!secret) log('warn', 'MBA_WEBHOOK_SECRET not set — endpoint is unauthenticated');
    if (!process.env['ANTHROPIC_API_KEY']) log('warn', 'ANTHROPIC_API_KEY not set — triggers will 503');
  });

  const shutdown = () => {
    log('info', 'shutting down…');
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(0), 3000).unref();
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

main();
