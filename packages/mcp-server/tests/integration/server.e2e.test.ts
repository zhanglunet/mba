import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createServer } from '../../src/server.js';
import { SERVER_VERSION } from '../../src/version.js';

/**
 * End-to-end: drive the real McpServer (all 14 registered tools) over an
 * in-memory transport with a real MCP Client. No network — only tools that
 * don't require ANTHROPIC_API_KEY are exercised for happy paths; API-gated
 * tools are checked for the correct error.
 */
describe('MCP server e2e', () => {
  let client: Client;
  let storeDir: string;

  beforeAll(async () => {
    storeDir = mkdtempSync(join(tmpdir(), 'mba-e2e-'));
    // Deterministic env: temp store, no API key (so no scheduler, no LLM calls)
    vi.stubEnv('MBA_STORE_DIR', storeDir);
    vi.stubEnv('ANTHROPIC_API_KEY', '');

    const server = createServer();
    client = new Client({ name: 'e2e-test', version: '1.0.0' });
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
  });

  afterAll(async () => {
    await client.close();
    vi.unstubAllEnvs();
    rmSync(storeDir, { recursive: true, force: true });
  });

  function parse(result: { content: Array<{ type: string; text?: string }> }): any {
    const text = result.content.find(c => c.type === 'text')?.text ?? '{}';
    return JSON.parse(text);
  }

  it('advertises the SERVER_VERSION over the MCP handshake', async () => {
    // pins server.ts's McpServer registration to the single-source-of-truth const, so a
    // re-hardcoded version literal there cannot silently drift from package.json.
    expect(client.getServerVersion()?.version).toBe(SERVER_VERSION);
  });

  it('registers all 14 tools', async () => {
    const { tools } = await client.listTools();
    const names = tools.map(t => t.name).sort();
    expect(names).toEqual(
      [
        'add_judge',
        'confirm_audit',
        'fetch_report',
        'get_brand_trend',
        'get_delta_report',
        'get_status',
        'list_audits',
        'list_panels',
        'list_subscriptions',
        'propose_audit',
        'resume_audit',
        'subscribe_brand',
        'trigger_evolution',
        'unsubscribe_brand',
      ].sort(),
    );
  });

  it('propose_audit returns an audit_id and PRD', async () => {
    const result = await client.callTool({
      name: 'propose_audit',
      arguments: { brand: 'E2E Test Brand' },
    });
    const out = parse(result as any);
    expect(out.audit_id).toBeTruthy();
    expect(out.proposal_markdown).toContain('E2E Test Brand');
    expect(out.estimated_token_cost_usd).toBeGreaterThan(0);
  });

  it('proposed audit shows up in list_audits and get_status', async () => {
    const proposeRes = await client.callTool({
      name: 'propose_audit',
      arguments: { brand: 'Listable Brand' },
    });
    const { audit_id } = parse(proposeRes as any);

    const listRes = await client.callTool({ name: 'list_audits', arguments: {} });
    const list = parse(listRes as any);
    expect(list.audits.some((a: any) => a.audit_id === audit_id)).toBe(true);

    const statusRes = await client.callTool({ name: 'get_status', arguments: { audit_id } });
    const status = parse(statusRes as any);
    expect(status.audit_id).toBe(audit_id);
    expect(status.phase).toBe('proposed');
    expect(status.progress_pct).toBe(5);
  });

  it('confirm_audit without API key returns MISSING_API_KEY error', async () => {
    const proposeRes = await client.callTool({
      name: 'propose_audit',
      arguments: { brand: 'NoKey Brand' },
    });
    const { audit_id } = parse(proposeRes as any);

    const result = await client.callTool({ name: 'confirm_audit', arguments: { audit_id } });
    // MCP surfaces thrown errors as isError results
    expect((result as any).isError).toBe(true);
    const text = (result as any).content.map((c: any) => c.text).join('');
    expect(text).toContain('MISSING_API_KEY');
  });

  it('subscribe_brand → list_subscriptions → unsubscribe_brand round-trips', async () => {
    const subRes = await client.callTool({
      name: 'subscribe_brand',
      arguments: { brand: 'Subbed Brand', min_interval_days: 14 },
    });
    const sub = parse(subRes as any);
    expect(sub.subscription_id).toBeTruthy();
    expect(sub.triggers[0].type).toBe('cron');

    const listRes = await client.callTool({ name: 'list_subscriptions', arguments: {} });
    const list = parse(listRes as any);
    expect(list.subscriptions.some((s: any) => s.subscription_id === sub.subscription_id)).toBe(true);

    const unsubRes = await client.callTool({
      name: 'unsubscribe_brand',
      arguments: { subscription_id: sub.subscription_id },
    });
    const unsub = parse(unsubRes as any);
    expect(unsub.unsubscribed).toBe(true);

    const list2Res = await client.callTool({ name: 'list_subscriptions', arguments: {} });
    const list2 = parse(list2Res as any);
    expect(list2.subscriptions.some((s: any) => s.subscription_id === sub.subscription_id)).toBe(false);
  });

  it('add_judge validate_only checks a persona without registering', async () => {
    const persona = `# Test Judge

## Decision heuristics
- Prefers evidence over hype
- Focuses on category coinage

## Anti-fabrication
Never invent private knowledge; reason only from the brief. If unclear, say so.

This persona exists purely to exercise the validator path end to end with enough length to clear the minimum content threshold that the validator applies to registered judge personas.`;

    const result = await client.callTool({
      name: 'add_judge',
      arguments: { name: 'e2e-judge', persona_markdown: persona, validate_only: true },
    });
    const out = parse(result as any);
    expect(out.validation).toBeDefined();
    expect(out.validation.has_anti_fabrication).toBe(true);
    expect(out.registered).toBe(false); // validate_only
  });

  it('list_panels returns default + 10 industry panels with rosters', async () => {
    const result = await client.callTool({ name: 'list_panels', arguments: {} });
    const out = parse(result as any);
    expect(out.panels).toHaveLength(11); // default + 10
    const names = out.panels.map((p: any) => p.name);
    expect(names).toContain('default');
    expect(names).toContain('luxury-en');
    const luxury = out.panels.find((p: any) => p.name === 'luxury-en');
    expect(luxury.judges.map((j: any) => j.slug)).toContain('arnault');
    expect(luxury.judges[0].name_cn).toBeTruthy();
  });

  it('get_brand_trend on a brand with no audits returns count 0', async () => {
    const result = await client.callTool({ name: 'get_brand_trend', arguments: { brand: 'Never Audited Co' } });
    const out = parse(result as any);
    expect(out.count).toBe(0);
    expect(out.points).toEqual([]);
    expect(out.trend).toBe('flat');
  });

  it('resume_audit on a not-yet-started (proposed) audit returns RESUME_NOT_APPLICABLE', async () => {
    const proposeRes = await client.callTool({
      name: 'propose_audit',
      arguments: { brand: 'Resumable Brand' },
    });
    const { audit_id } = parse(proposeRes as any);

    const result = await client.callTool({ name: 'resume_audit', arguments: { audit_id } });
    expect((result as any).isError).toBe(true);
    const text = (result as any).content.map((c: any) => c.text).join('');
    expect(text).toContain('RESUME_NOT_APPLICABLE');
  });

  it('resume_audit on unknown audit returns AUDIT_NOT_FOUND', async () => {
    const result = await client.callTool({
      name: 'resume_audit',
      arguments: { audit_id: 'does-not-exist' },
    });
    expect((result as any).isError).toBe(true);
    const text = (result as any).content.map((c: any) => c.text).join('');
    expect(text).toContain('AUDIT_NOT_FOUND');
  });

  it('get_status on unknown audit returns AUDIT_NOT_FOUND', async () => {
    const result = await client.callTool({
      name: 'get_status',
      arguments: { audit_id: 'does-not-exist' },
    });
    expect((result as any).isError).toBe(true);
    const text = (result as any).content.map((c: any) => c.text).join('');
    expect(text).toContain('AUDIT_NOT_FOUND');
  });
});
