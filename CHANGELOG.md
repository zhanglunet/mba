# Changelog

All notable changes to MBA (Metric Brand Auditor) are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/); versions
track `metric-brand-auditor/SKILL.md`'s `version:` field (the release tag).

## Unreleased

### Added
- **Webhook receiver** (`mba-webhook-receiver`) — a small HTTP server that turns
  an inbound event `POST /webhooks/trigger` into an EVOLUTION re-audit, the
  inbound counterpart to the outbound notifications. Optional `MBA_WEBHOOK_SECRET`
  Bearer auth, `GET /status` + `/health`, shares `MBA_STORE_DIR` with the MCP
  server. Completes the four evolution triggers: subscription cron, manual,
  notify-out, and webhook-in. (`src/http/receiver.ts`, 18 tests.)

### Fixed
- Chart.js infinite-growth on the kimichat & qianxin report charts (radar + Lens
  Means bar): canvases now sit in a fixed-height `.chart-wrap` container.

### Added
- `scripts/qa_report_render.mjs` — headless-render QA for published reports.
  Catches chart infinite-growth, collapsed canvases, unrendered Mermaid, and JS
  errors that static validators miss. Run before publishing: `node
  scripts/qa_report_render.mjs` (needs network for the chart/mermaid CDNs, or
  `--offline-libs <dir>` in air-gapped environments).
- Real public Sources sections backfilled into the hermes / genki-forest /
  meituan / tal-education reports.

### Changed
- Report validators (`validate_report.py`, `validate_html_report.py`) split into
  hard (block CI) vs advisory (warn) rules, with advisory anchors covering MBA's
  real bilingual section variants (TL;DR / Core Insight / 最大分歧 / Judge Total …).
- `release.yml` now sources release notes from the matching CHANGELOG section and
  updates an existing release instead of no-oping.

## v0.4.0 — 2026-07-04

The MCP-server + evolution-tracking milestone. MBA is now runnable not just as a
Claude Code skill but as a standalone **MCP server** any MCP-capable agent can
drive, with brand subscriptions, automatic re-audits, and delta reporting.

### Added — MCP Server (`packages/mcp-server`, `mba-mcp-server`)
- TypeScript MCP server (Node ≥ 20, stdio), **11 tools**, **67 tests**.
- **Core audit (6):** `propose_audit`, `confirm_audit`, `get_status`,
  `fetch_report`, `list_audits`, `add_judge` — non-blocking Phase 2-5 LLM
  orchestration (research → synthesis → judging → merge), atomic `state.json`,
  8-phase state machine, retry/backoff client, 5 built-in judges + persona validator.
- **Evolution tracking (5):** `subscribe_brand`, `trigger_evolution`,
  `list_subscriptions`, `unsubscribe_brand`, `get_delta_report`.
  - Cron scheduler + cadence guards (min interval, monthly cap).
  - **Incremental EVOLUTION re-run**: change-probes re-run only moved dimensions
    → cost ~$3 → ~$0.4/run (80%+ savings); triggering event steers the probes.
  - Structured `scores.json` + delta reports (per-lens mean Δ, LLM narrative).
  - **Notifications**: webhook + email push on completion, best-effort per-target.
- End-to-end tests over a real MCP `Client` / in-memory transport.
- Publish-ready: MIT `LICENSE`, `prepublishOnly` guard, clean `npm pack`.

### Added — Pipeline & reports
- **10 published audits** — every panel now has a public sample (Hermès 8.64 sets
  three MBA all-time records; Meituan is the first double-★ investor conflict).
- `--dry-run` flag — print PRD + panel/judge/dimension plan, zero side effects.
- `--panel-merge` flag — cross-panel comparison report with delta heatmap (Phase 5M).

### Added — CI / quality
- `report-validation.yml` — structural validators for report.md + report.html.
- Validators use a hard/advisory rule split (title + score matrix + legal are
  hard; verdict / dissent heatmap / sources are advisory) so bilingual report
  formats pass while real gaps still fail.

### Fixed
- Added the standard MBA Legal/IP/Disclaimer footer to 4 reports that shipped
  without one (hermes, genki-forest, meituan, tal-education), in `.md` and `.html`.
- Regenerated `site/api/` for all 10 reports; added the MCP server to the
  agents-API install manifest.

### Docs & site
- New `docs/13-mcp-quickstart.md` (user-facing) and `docs/12-evolution-tracking.md`.
- README §5.1 MCP section; `site/agents.html`, `site/roadmap.html` synced.

**Full range:** everything since the last published release, v0.2.36.

## v0.2.36 — 2026-06-18
- `cross-border` and `luxury-en` panels made runnable → 10/10 panels operational.

See GitHub Releases for earlier versions.
