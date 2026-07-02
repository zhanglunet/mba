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

## Development

```bash
pnpm install          # from repo root
pnpm test             # run vitest
pnpm typecheck        # tsc --noEmit
pnpm build            # compile to dist/
```

See [`docs/mcp-server-design.md`](../../docs/mcp-server-design.md) for full architecture.

## Status

**v0.1.0 — complete**  
- ✅ Project scaffold (TypeScript, vitest, MCP SDK)  
- ✅ State machine with all valid transitions  
- ✅ Filesystem store with atomic writes  
- ✅ `propose_audit` + `confirm_audit` + `get_status` + `fetch_report` + `list_audits` + `add_judge` tools  
- ✅ Judge persona validator  
- ✅ Phase 2-5 LLM orchestration — 22 tests passing  
- ⏳ npm publish (PR-05)  
