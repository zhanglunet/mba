import { describe, it, expect, vi } from 'vitest';
import type { AuditState } from '../../src/types.js';
import type { FilesystemStore } from '../../src/store/filesystem.js';
import type { LLMClient } from '../../src/llm/client.js';
import { runPhase2Evolution } from '../../src/orchestrator/phase-2-evolution.js';

function makeState(overrides: Partial<AuditState> = {}): AuditState {
  return {
    audit_id: 'brand-new',
    brand: 'Brand',
    brand_slug: 'brand',
    panel: 'default',
    mode: 'evolution',
    phase: 'researching',
    started_at: '2026-07-01T00:00:00Z',
    last_progress_at: '2026-07-01T00:00:00Z',
    completed_phases: [],
    failed_phases: [],
    errors: [],
    tokens_used: { input: 0, output: 0 },
    options: { skip_wuying: false, language: 'auto', previous_audit_id: 'brand-old' },
    ...overrides,
  };
}

/**
 * Store that returns a canned previous research file for every dimension.
 */
function makeStore(previousExists = true): FilesystemStore & { written: Record<string, string> } {
  const written: Record<string, string> = {};
  return {
    written,
    readFile: vi.fn().mockImplementation((id: string, path: string) => {
      if (id === 'brand-old' && previousExists && path.startsWith('_raw/dimension_')) {
        return Promise.resolve(`# Some Dim / Some Dim\n\nPrevious research content for ${path}.`);
      }
      return Promise.resolve(null);
    }),
    writeFile: vi.fn().mockImplementation((id: string, path: string, content: string) => {
      written[`${id}/${path}`] = content;
      return Promise.resolve();
    }),
    readState: vi.fn().mockResolvedValue(null),
    writeState: vi.fn().mockResolvedValue(undefined),
    listFiles: vi.fn().mockResolvedValue([]),
    listAudits: vi.fn().mockResolvedValue([]),
    initAudit: vi.fn().mockResolvedValue(undefined),
    exists: vi.fn().mockResolvedValue(false),
  } as unknown as FilesystemStore & { written: Record<string, string> };
}

/**
 * Client whose probe verdict is controlled by `verdict`, and whose full-research
 * calls return a marker string. Distinguishes probe vs research by max_tokens.
 */
function makeClient(verdict: 'CHANGED' | 'UNCHANGED') {
  const complete = vi.fn().mockImplementation((_sys: string, _user: string, maxTokens: number) => {
    if (maxTokens === 256) {
      // probe call
      return Promise.resolve({
        content: `VERDICT: ${verdict}\nREASON: test reason`,
        input_tokens: 50,
        output_tokens: 10,
      });
    }
    // full research call
    return Promise.resolve({
      content: 'FRESH RESEARCH',
      input_tokens: 500,
      output_tokens: 400,
    });
  });
  return { model: 'claude-sonnet-4-6', complete } as unknown as LLMClient & { complete: typeof complete };
}

const noop = () => {};

describe('runPhase2Evolution', () => {
  it('reuses all dimensions when probe says UNCHANGED', async () => {
    const state = makeState();
    const store = makeStore(true);
    const client = makeClient('UNCHANGED');

    const result = await runPhase2Evolution(state, 'brand-old', store, client, 7, noop);

    expect(result.dimensions_reused).toBe(7);
    expect(result.dimensions_rerun).toBe(0);
    // Only probe calls (7), no full research calls
    expect((client.complete as ReturnType<typeof vi.fn>).mock.calls.length).toBe(7);
    // Reused output should NOT contain FRESH RESEARCH
    expect(Object.values(result.outputs).join('')).not.toContain('FRESH RESEARCH');
  });

  it('re-runs all dimensions when probe says CHANGED', async () => {
    const state = makeState();
    const store = makeStore(true);
    const client = makeClient('CHANGED');

    const result = await runPhase2Evolution(state, 'brand-old', store, client, 7, noop);

    expect(result.dimensions_rerun).toBe(7);
    expect(result.dimensions_reused).toBe(0);
    // 7 probes + 7 full research = 14 calls
    expect((client.complete as ReturnType<typeof vi.fn>).mock.calls.length).toBe(14);
    expect(Object.values(result.outputs).join('')).toContain('FRESH RESEARCH');
  });

  it('treats missing baseline research as CHANGED (full research, no probe)', async () => {
    const state = makeState();
    const store = makeStore(false); // no previous files
    const client = makeClient('UNCHANGED'); // verdict irrelevant — no baseline to probe

    const result = await runPhase2Evolution(state, 'brand-old', store, client, 7, noop);

    expect(result.dimensions_rerun).toBe(7);
    expect(result.dimensions_reused).toBe(0);
    // No probe calls (256), only full research (7 calls)
    const probeCalls = (client.complete as ReturnType<typeof vi.fn>).mock.calls.filter(
      (c: unknown[]) => c[2] === 256,
    );
    expect(probeCalls.length).toBe(0);
  });

  it('writes an evolution_probes.md summary', async () => {
    const state = makeState();
    const store = makeStore(true);
    const client = makeClient('UNCHANGED');

    await runPhase2Evolution(state, 'brand-old', store, client, 7, noop);

    expect(store.written['brand-new/_raw/evolution_probes.md']).toBeDefined();
    expect(store.written['brand-new/_raw/evolution_probes.md']).toContain('Evolution Probe Summary');
  });

  it('defaults to CHANGED when probe response is unparseable', async () => {
    const state = makeState();
    const store = makeStore(true);
    const client = {
      model: 'claude-sonnet-4-6',
      complete: vi.fn().mockImplementation((_s: string, _u: string, maxTokens: number) => {
        if (maxTokens === 256) {
          return Promise.resolve({ content: 'garbled nonsense', input_tokens: 50, output_tokens: 10 });
        }
        return Promise.resolve({ content: 'FRESH RESEARCH', input_tokens: 500, output_tokens: 400 });
      }),
    } as unknown as LLMClient;

    const result = await runPhase2Evolution(state, 'brand-old', store, client, 7, noop);
    expect(result.dimensions_rerun).toBe(7); // all defaulted to CHANGED
  });
});
