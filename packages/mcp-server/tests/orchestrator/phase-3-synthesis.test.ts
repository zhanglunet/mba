import { describe, it, expect, vi } from 'vitest';
import type { AuditState } from '../../src/types.js';
import type { FilesystemStore } from '../../src/store/filesystem.js';
import type { LLMClient } from '../../src/llm/client.js';
import { runPhase3Synthesis } from '../../src/orchestrator/phase-3-synthesis.js';

function makeState(overrides: Partial<AuditState> = {}): AuditState {
  return {
    audit_id: 'anthropic-x',
    brand: 'Anthropic',
    brand_slug: 'anthropic',
    panel: 'vc-en',
    mode: 'fresh',
    phase: 'synthesizing',
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

function makeClient(content = 'SYNTHESIS BODY') {
  const complete = vi.fn().mockResolvedValue({ content, input_tokens: 1200, output_tokens: 900 });
  return { model: 'claude-sonnet-4-6', complete } as unknown as LLMClient & {
    complete: ReturnType<typeof vi.fn>;
  };
}

const noop = () => {};

describe('runPhase3Synthesis', () => {
  it('calls the model once with a 4096 token budget and returns its tokens', async () => {
    const state = makeState();
    const store = makeStore();
    const client = makeClient();

    const result = await runPhase3Synthesis(
      state,
      { dimension_1_origin: 'origin findings', dimension_2_category: 'category findings' },
      store,
      client,
      noop,
    );

    expect(client.complete).toHaveBeenCalledTimes(1);
    expect(client.complete.mock.calls[0]?.[2]).toBe(4096);
    expect(result).toEqual({ synthesis: 'SYNTHESIS BODY', input_tokens: 1200, output_tokens: 900 });
  });

  it('writes _raw/synthesis.md with a metadata header + the model body', async () => {
    const state = makeState();
    const store = makeStore();
    await runPhase3Synthesis(state, { d1: 'x' }, store, makeClient('BODY-123'), noop);

    const written = store.written['anthropic-x/_raw/synthesis.md'];
    expect(written).toBeDefined();
    expect(written).toContain('# MBA Synthesis — Anthropic');
    expect(written).toContain('**Audit ID:** anthropic-x');
    expect(written).toContain('**Panel:** vc-en');
    expect(written).toContain('BODY-123');
  });

  it('feeds every dimension output into the synthesis prompt', async () => {
    const state = makeState();
    const store = makeStore();
    const client = makeClient();
    await runPhase3Synthesis(
      state,
      { dim_a: 'ALPHA-FINDINGS', dim_b: 'BETA-FINDINGS' },
      store,
      client,
      noop,
    );
    const userPrompt = client.complete.mock.calls[0]?.[1] as string;
    expect(userPrompt).toContain('ALPHA-FINDINGS');
    expect(userPrompt).toContain('BETA-FINDINGS');
  });
});
