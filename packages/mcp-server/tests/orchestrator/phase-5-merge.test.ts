import { describe, it, expect, vi } from 'vitest';
import type { AuditState } from '../../src/types.js';
import type { FilesystemStore } from '../../src/store/filesystem.js';
import type { LLMClient } from '../../src/llm/client.js';
import { runPhase5Merge } from '../../src/orchestrator/phase-5-merge.js';

function makeState(overrides: Partial<AuditState> = {}): AuditState {
  return {
    audit_id: 'anthropic-x',
    brand: 'Anthropic',
    brand_slug: 'anthropic',
    panel: 'vc-en',
    mode: 'fresh',
    phase: 'merging',
    started_at: '2026-07-10T00:00:00Z',
    last_progress_at: '2026-07-10T00:00:00Z',
    completed_phases: [],
    failed_phases: [],
    errors: [],
    tokens_used: { input: 0, output: 0 },
    options: { skip_wuying: false, language: 'auto' },
    ...overrides,
  };
}

function makeStore(): FilesystemStore & { written: Record<string, string> } {
  const written: Record<string, string> = {};
  return {
    written,
    writeFile: vi.fn().mockImplementation((id: string, path: string, content: string) => {
      written[`${id}/${path}`] = content;
      return Promise.resolve();
    }),
    readFile: vi.fn().mockResolvedValue(null),
    readState: vi.fn().mockResolvedValue(null),
    writeState: vi.fn().mockResolvedValue(undefined),
    listFiles: vi.fn().mockResolvedValue([]),
    listAudits: vi.fn().mockResolvedValue([]),
    initAudit: vi.fn().mockResolvedValue(undefined),
    exists: vi.fn().mockResolvedValue(false),
  } as unknown as FilesystemStore & { written: Record<string, string> };
}

function makeClient(content = 'FINAL REPORT BODY') {
  const complete = vi.fn().mockResolvedValue({ content, input_tokens: 2000, output_tokens: 1500 });
  return { model: 'claude-sonnet-4-6', complete } as unknown as LLMClient & {
    complete: ReturnType<typeof vi.fn>;
  };
}

const noop = () => {};
const REVIEWS = { fusheng: 'review A', jobs: 'review B' };

describe('runPhase5Merge', () => {
  it('calls the model once with an 8192 token budget and returns its tokens', async () => {
    const client = makeClient();
    const result = await runPhase5Merge(makeState(), 'SYNTH', REVIEWS, makeStore(), client, noop);
    expect(client.complete).toHaveBeenCalledTimes(1);
    expect(client.complete.mock.calls[0]?.[2]).toBe(8192);
    expect(result.input_tokens).toBe(2000);
    expect(result.output_tokens).toBe(1500);
  });

  it('writes report.md with brand/panel/mode header, the body, and a legal footer', async () => {
    const store = makeStore();
    const result = await runPhase5Merge(makeState(), 'SYNTH', REVIEWS, store, makeClient('BODY-XYZ'), noop);

    const md = store.written['anthropic-x/report.md'];
    expect(md).toBeDefined();
    expect(md).toContain('# Anthropic · MBA Audit Report · v1');
    expect(md).toContain('Panel: vc-en');
    expect(md).toContain('Mode: FRESH');
    expect(md).toContain('BODY-XYZ');
    expect(md).toContain('## Legal / IP / Disclaimer');
    expect(md).toContain('does not constitute investment advice');
    // the returned report_md is exactly what was persisted
    expect(result.report_md).toBe(md);
  });

  it('writes an HTML report that HTML-escapes the markdown body', async () => {
    const store = makeStore();
    await runPhase5Merge(makeState(), 'SYNTH', REVIEWS, store, makeClient('<b>bold</b> & <script>x</script>'), noop);

    const html = store.written['anthropic-x/report.html'];
    expect(html).toBeDefined();
    expect(html).toContain('&lt;b&gt;bold&lt;/b&gt; &amp; &lt;script&gt;');
    // the raw, unescaped injected tag must NOT survive into the HTML
    expect(html).not.toContain('<script>x</script>');
  });

  it('snapshots the report into versions/v1_<date>.md identical to report.md', async () => {
    const store = makeStore();
    await runPhase5Merge(makeState(), 'SYNTH', REVIEWS, store, makeClient(), noop);

    const versionKey = Object.keys(store.written).find(k =>
      k.startsWith('anthropic-x/versions/v1_'),
    );
    expect(versionKey).toBeDefined();
    expect(versionKey).toMatch(/versions\/v1_\d{4}-\d{2}-\d{2}\.md$/);
    expect(store.written[versionKey!]).toBe(store.written['anthropic-x/report.md']);
  });

  it('passes the panel judges into the merge prompt', async () => {
    const client = makeClient();
    const state = makeState({ options: { skip_wuying: false, language: 'auto', judges: ['jobs', 'naval'] } });
    await runPhase5Merge(state, 'SYNTH', REVIEWS, makeStore(), client, noop);
    const userPrompt = client.complete.mock.calls[0]?.[1] as string;
    expect(userPrompt).toContain('jobs');
    expect(userPrompt).toContain('naval');
  });
});
