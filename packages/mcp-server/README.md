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
| `resume_audit` | Resume a stalled/failed audit — reloads finished phases, re-runs the rest |
| `get_status` | Poll phase / progress / token usage |
| `fetch_report` | Pull finished report (markdown / html / both) |
| `list_audits` | List all audits in `MBA_STORE_DIR` |
| `list_panels` | Discover the available panels + their judge rosters |
| `add_judge` | Register a custom judge persona |

**Evolution tracking** (P3-B)

| Tool | Description |
|---|---|
| `subscribe_brand` | Subscribe a brand for auto re-audit (cron / webhook triggers) |
| `trigger_evolution` | Manually fire an EVOLUTION re-audit (cadence-guarded) |
| `list_subscriptions` | List active subscriptions |
| `unsubscribe_brand` | Remove a subscription |
| `get_delta_report` | Compare two audits — per-lens score delta + narrative |
| `get_brand_trend` | A brand's score trajectory across all its audits (N-audit view) |

An internal `CronScheduler` polls subscriptions and fires overdue cron triggers automatically (started when `ANTHROPIC_API_KEY` is set).

## Panels (43 judges across 10 panels)

`propose_audit` accepts a `panel` — the same industry rosters the published reports use, so you can reproduce any of them (e.g. Hermès on `luxury-en`, Anthropic on `vc-en`):

```jsonc
{ "brand": "Hermès", "panel": "luxury-en" }
```

| Panel | Roster |
|---|---|
| `default` | 傅盛 · Jobs · 李可佳 · 吴俊东 · 张一鸣 |
| `auto` | 新能源汽车 5 位（马斯克 / 雷军 / 李想 / 何小鹏 / 李斌） |
| `luxury-en` | Arnault · Wintour · Cucinelli · Tom Ford · Burton |
| `vc-en` | pmarca · paulg · pthiel · naval · rhoffman |
| `vc-cn` | 朱啸虎 · 张磊 · 徐新 · 雷军 · 沈南鹏 |
| `consumer-cn` · `ai-app-cn` · `edu-cn` · `cross-border` · `security-cn-global` | 各领域 5–6 位 |

The 43 judge personas are bundled from the project's authored `perspectives/*` files (regenerate with `pnpm generate:personas`). Pass an explicit `judges` array to override a panel, or register your own with `add_judge`.

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

## Webhook receiver (inbound triggers)

The MCP server speaks stdio, so external systems (news monitors, PR bots, CI)
can't reach it directly. The package also ships a small HTTP receiver that turns
an inbound event POST into an EVOLUTION re-audit — the inbound counterpart to the
outbound notifications above.

```bash
ANTHROPIC_API_KEY=sk-ant-... MBA_WEBHOOK_SECRET=your-secret \
  npx -p mba-mcp-server mba-webhook-receiver
# listening on http://0.0.0.0:8787

curl -X POST http://localhost:8787/webhooks/trigger \
  -H "authorization: Bearer your-secret" \
  -H "content-type: application/json" \
  -d '{"brand":"Xiaomi","event_type":"product_launch","event_summary":"YU7 launched"}'
# → 202 { "audit_id": "...", "phase": "researching" }
```

| Route | Purpose |
|---|---|
| `POST /webhooks/trigger` | `{ brand, event_type?, event_summary?, source_url?, force? }` → starts an EVOLUTION audit (202), or 200 if a subscription's cadence guard skips it |
| `GET /status?audit_id=…` | poll an audit's phase / progress |
| `GET /health` | liveness check |

It shares `MBA_STORE_DIR` with the MCP server, so audits triggered by webhook show
up in `list_audits` / `get_status` there too. Config:

| Var | Default | Description |
|---|---|---|
| `MBA_WEBHOOK_PORT` | `8787` | Listen port |
| `MBA_WEBHOOK_HOST` | `0.0.0.0` | Listen host |
| `MBA_WEBHOOK_SECRET` | *(optional)* | If set, POSTs must send `Authorization: Bearer <secret>` |

Run it wherever you can keep a long-lived process (a small VM, a container, a
`systemd` unit). Always set `MBA_WEBHOOK_SECRET` when exposing it publicly.

## Development

```bash
pnpm install          # from repo root
pnpm test             # run vitest (unit + e2e)
pnpm typecheck        # tsc --noEmit
pnpm build            # compile to dist/
```

Tests include an end-to-end suite (`tests/integration/server.e2e.test.ts`) that
drives the real `createServer()` over an in-memory MCP transport with an actual
`Client`, verifying tool registration and request/response wiring for all 14 tools.

See [`docs/mcp-server-design.md`](../../docs/mcp-server-design.md) for full architecture.

## Publishing

### Automated (recommended) — GitHub Actions

One-time: add an npm **granular access token** as the repo secret `NPM_TOKEN`
(npmjs.com → Access Tokens → Generate → *Granular Access Token*, Read and write).
A granular token can publish under a 2FA-protected account; classic automation
tokens are rejected with `E403` when the account enforces 2FA.

Then, to publish: bump `version` in `package.json`, commit, and run the
**Publish npm** workflow (`.github/workflows/publish-npm.yml`) from the Actions
tab — or via the API/MCP. It installs, runs `prepublishOnly` (typecheck + tests +
build) and publishes. It's idempotent (a version already on npm is a no-op), and
supports a `dry_run` input to rehearse without publishing.

### Manual

```bash
cd packages/mcp-server
npm login                 # or: npm config set //registry.npmjs.org/:_authToken=<token>
npm publish               # prepublishOnly runs typecheck + tests + build first
```

- `prepublishOnly` gates publish on a green typecheck, full test run, and a fresh build — a broken tree cannot be published.
- `files` ships only `dist/`, `README.md`, `LICENSE` (verify with `npm pack --dry-run`).
- `publishConfig.access: public` — no scope, published publicly.
- Bump `version` before each release (`npm version patch|minor|major`).

## Status

**v0.1.0 — published to npm · 14 tools · 113 tests**  
- ✅ Project scaffold (TypeScript, vitest, MCP SDK)  
- ✅ State machine with all valid transitions  
- ✅ Filesystem store with atomic writes  
- ✅ 8 core tools (incl. `list_panels`, `resume_audit`) + Phase 2-5 LLM orchestration  
- ✅ Judge persona validator + full 10-panel / 43-judge roster  
- ✅ Evolution tracking — subscriptions, cron scheduler, `trigger_evolution`, `get_delta_report`, `get_brand_trend`  
- ✅ Incremental EVOLUTION re-run (change probes — cost ~$3 → ~$0.4/run)  
- ✅ Notifications — webhook + email push on audit completion  
- ✅ Webhook receiver (`mba-webhook-receiver`) for inbound triggers  
- ✅ End-to-end tests over a real MCP Client / in-memory transport  
- ✅ Published to npm (`npx -y mba-mcp-server@latest`)  
