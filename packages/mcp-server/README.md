# mba-mcp-server

MBA (Metric Brand Auditor) — MCP server.  
Run `/mba` brand influence audits from any MCP-capable agent (Claude Desktop, Cursor, OpenClaw, CI, …).

## Quick start

```jsonc
// Claude Desktop / claude_desktop_config.json
{
  "mcpServers": {
    "mba": {
      "command": "npx",
      "args": ["-y", "mba-mcp-server@latest"],
      "env": { "ANTHROPIC_API_KEY": "sk-ant-..." }
    }
  }
}
```

Then in Claude: *"用 mba 审一下 OpenClaw"* → Claude calls `propose_audit` → shows you the PRD → you say OK → `confirm_audit` → poll `get_status` → `fetch_report`.

## Tools

**Core audit**

| Tool | Description |
|---|---|
| `propose_audit` | Generate PRD for a brand, returns `audit_id` |
| `confirm_audit` | Start Phase 2-5 after reviewing proposal |
| `get_status` | Poll phase / progress / token usage |
| `fetch_report` | Pull finished report (markdown / html / both) |
| `list_audits` | List all audits in `MBA_STORE_DIR` |
| `add_judge` | Register a custom judge persona |

**Evolution tracking** (P3-B)

| Tool | Description |
|---|---|
| `subscribe_brand` | Subscribe a brand for auto re-audit (cron / webhook triggers) |
| `trigger_evolution` | Manually fire an EVOLUTION re-audit (cadence-guarded) |
| `list_subscriptions` | List active subscriptions |
| `unsubscribe_brand` | Remove a subscription |
| `get_delta_report` | Compare two audits — per-lens score delta + narrative |

An internal `CronScheduler` polls subscriptions and fires overdue cron triggers automatically (started when `ANTHROPIC_API_KEY` is set).

## Environment variables

| Var | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required)* | Your Anthropic API key |
| `MBA_STORE_DIR` | `~/.mba` | Where audit artifacts are stored |
| `MBA_MAX_PARALLEL` | `5` | Max concurrent sub-agents per audit |
| `MBA_MAX_CONCURRENT_AUDITS` | `3` | Max simultaneous audits |
| `MBA_LOG_LEVEL` | `info` | `error / warn / info / debug / trace` |
| `MBA_RESEND_API_KEY` | *(optional)* | [Resend](https://resend.com) API key — enables email notifications |
| `MBA_NOTIFY_FROM` | *(optional)* | From-address for email notifications (required with Resend key) |

### Notifications

When an evolution audit (via `trigger_evolution` or the cron scheduler) finishes,
the server automatically computes the delta vs. the baseline and pushes it to the
subscription's `notify` targets:

- **`webhook`** — HTTP POST of the delta payload (`event: "mba.evolution.done"`) to your URL
- **`email`** — sent via Resend (needs `MBA_RESEND_API_KEY` + `MBA_NOTIFY_FROM`)
- **`mcp-push`** — served passively; just poll `get_status` / `get_delta_report`

Delivery is best-effort and per-target: one failing target never blocks the others,
and notification errors never fail the audit itself.

## Development

```bash
pnpm install          # from repo root
pnpm test             # run vitest (unit + e2e)
pnpm typecheck        # tsc --noEmit
pnpm build            # compile to dist/
```

Tests include an end-to-end suite (`tests/integration/server.e2e.test.ts`) that
drives the real `createServer()` over an in-memory MCP transport with an actual
`Client`, verifying tool registration and request/response wiring for all 11 tools.

See [`docs/mcp-server-design.md`](../../docs/mcp-server-design.md) for full architecture.

## Publishing

The package is publish-ready. Once you have an npm token with publish rights:

```bash
cd packages/mcp-server
npm login                 # or: npm config set //registry.npmjs.org/:_authToken=<token>
npm publish               # prepublishOnly runs typecheck + 67 tests + build first
```

- `prepublishOnly` gates publish on a green typecheck, full test run, and a fresh build — a broken tree cannot be published.
- `files` ships only `dist/`, `README.md`, `LICENSE` (verify with `npm pack --dry-run`).
- `publishConfig.access: public` — no scope, published publicly.
- Bump `version` in `package.json` before each release (`npm version patch|minor|major`).

## Status

**v0.1.0 — complete · 11 tools · 67 tests**  
- ✅ Project scaffold (TypeScript, vitest, MCP SDK)  
- ✅ State machine with all valid transitions  
- ✅ Filesystem store with atomic writes  
- ✅ 6 core tools + Phase 2-5 LLM orchestration  
- ✅ Judge persona validator  
- ✅ Evolution tracking — subscriptions, cron scheduler, `trigger_evolution`, `get_delta_report`  
- ✅ Incremental EVOLUTION re-run (change probes — cost ~$3 → ~$0.4/run)  
- ✅ Notifications — webhook + email push on audit completion  
- ✅ End-to-end tests over a real MCP Client / in-memory transport  
- ⏳ npm publish  
