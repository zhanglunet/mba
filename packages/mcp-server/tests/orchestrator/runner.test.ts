import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AuditState } from '../../src/types.js';
import type { FilesystemStore } from '../../src/store/filesystem.js';
import type { StateMachine } from '../../src/orchestrator/state-machine.js';
import type { LLMClient } from '../../src/llm/client.js';
import { runAudit } from '../../src/orchestrator/runner.js';

// ── helpers ───────────────────────────────────────────────────────────────────

function makeState(overrides: Partial<AuditState> = {}): AuditState {
  return {
    audit_id: 'test-brand-20260101-1200',
    brand: 'Test Brand',
    brand_slug: 'test-brand',
    panel: 'default',
    mode: 'fresh',
    phase: 'researching',
    started_at: new Date().toISOString(),
    last_progress_at: new Date().toISOString(),
    completed_phases: [],
    failed_phases: [],
    errors: [],
    tokens_used: { input: 0, output: 0 },
    options: { skip_wuying: false, language: 'auto' },
    ...overrides,
  };
}

function makeLLMClient(content = 'mock response'): LLMClient {
  return {
    model: 'claude-sonnet-4-6',
    complete: vi.fn().mockResolvedValue({
      content,
      input_tokens: 100,
      output_tokens: 50,
    }),
  } as unknown as LLMClient;
}

function makeStore(state: AuditState): FilesystemStore {
  let current = { ...state };
  return {
    readState: vi.fn().mockImplementation(() => Promise.resolve({ ...current })),
    writeState: vi.fn().mockImplementation((s: AuditState) => {
      current = { ...s };
      return Promise.resolve();
    }),
    writeFile: vi.fn().mockResolvedValue(undefined),
    readFile: vi.fn().mockResolvedValue(null),
    listAudits: vi.fn().mockResolvedValue([]),
    initAudit: vi.fn().mockResolvedValue(undefined),
    exists: vi.fn().mockResolvedValue(false),
  } as unknown as FilesystemStore;
}

function makeStateMachine(store: FilesystemStore): StateMachine {
  return {
    transition: vi.fn().mockImplementation(async (s: AuditState, phase: string) => {
      const next = { ...s, phase };
      await store.writeState(next);
      return next;
    }),
    progressPct: vi.fn().mockReturnValue(50),
    canResume: vi.fn().mockReturnValue(true),
  } as unknown as StateMachine;
}

const defaultConfig = {
  maxParallel: 2,
  judgesDir: '/tmp/judges',
};

const noop = () => {};

// ── tests ─────────────────────────────────────────────────────────────────────

describe('runAudit', () => {
  it('runs phases 2-5 in order and transitions to done', async () => {
    const state = makeState();
    const store = makeStore(state);
    const sm = makeStateMachine(store);
    const client = makeLLMClient('**SCORES:**\n- Origin authenticity: 7 — ok\n- Category coinage: 7 — ok\n- Leverage quality: 7 — ok\n- Identity coherence: 7 — ok\n- Real-world signal: 7 — ok\n\n**TOTAL: 35/50**\n\n**VERDICT:** Good brand.');

    await runAudit(state, store, sm, defaultConfig, client, noop);

    const transitions = (sm.transition as ReturnType<typeof vi.fn>).mock.calls.map(
      (c: unknown[]) => (c[1] as string),
    );
    expect(transitions).toEqual(['synthesizing', 'judging', 'merging', 'done']);
  });

  it('calls LLM for each of 7 dimensions + synthesis + 5 judges + merge', async () => {
    const state = makeState();
    const store = makeStore(state);
    const sm = makeStateMachine(store);
    const client = makeLLMClient();

    await runAudit(state, store, sm, defaultConfig, client, noop);

    // 7 dimensions + 1 synthesis + 5 judges + 1 merge = 14
    expect((client.complete as ReturnType<typeof vi.fn>).mock.calls.length).toBe(14);
  });

  it('writes state to failed on LLM error', async () => {
    const state = makeState();
    const store = makeStore(state);
    const sm = makeStateMachine(store);
    const client: LLMClient = {
      model: 'claude-sonnet-4-6',
      complete: vi.fn().mockRejectedValue(new Error('API_ERROR')),
    } as unknown as LLMClient;

    await runAudit(state, store, sm, defaultConfig, client, noop);

    const transitions = (sm.transition as ReturnType<typeof vi.fn>).mock.calls.map(
      (c: unknown[]) => (c[1] as string),
    );
    expect(transitions).toContain('failed');
    expect(transitions).not.toContain('done');
  });

  it('enforces max_cost_usd limit and marks failed', async () => {
    const state = makeState();
    const store = makeStore(state);
    const sm = makeStateMachine(store);
    // Each call returns 100k input + 50k output tokens — well above any small limit
    const client: LLMClient = {
      model: 'claude-sonnet-4-6',
      complete: vi.fn().mockResolvedValue({
        content: 'ok',
        input_tokens: 100_000,
        output_tokens: 50_000,
      }),
    } as unknown as LLMClient;

    const configWithLimit = { ...defaultConfig, maxCostUsd: 0.01 };
    await runAudit(state, store, sm, configWithLimit, client, noop);

    const transitions = (sm.transition as ReturnType<typeof vi.fn>).mock.calls.map(
      (c: unknown[]) => (c[1] as string),
    );
    expect(transitions).toContain('failed');
  });

  it('persists token totals to state before marking done', async () => {
    const state = makeState();
    const store = makeStore(state);
    const sm = makeStateMachine(store);
    const client = makeLLMClient();

    await runAudit(state, store, sm, defaultConfig, client, noop);

    const writeCalls = (store.writeState as ReturnType<typeof vi.fn>).mock.calls;
    // Find the write right before done (tokens_used update)
    const tokenWrite = writeCalls.find(
      (c: unknown[]) => (c[0] as AuditState).tokens_used?.input > 0,
    );
    expect(tokenWrite).toBeDefined();
    // 14 calls × 100 input = 1400 total
    expect((tokenWrite![0] as AuditState).tokens_used.input).toBe(1400);
  });
});
