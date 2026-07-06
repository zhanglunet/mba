import { describe, it, expect, vi } from 'vitest';
import type { AuditState, AuditPhase } from '../../src/types.js';
import type { FilesystemStore } from '../../src/store/filesystem.js';
import type { LLMClient } from '../../src/llm/client.js';
import { StateMachine } from '../../src/orchestrator/state-machine.js';
import { runAudit } from '../../src/orchestrator/runner.js';

function makeState(phase: AuditPhase, completed: string[]): AuditState {
  return {
    audit_id: 'acme-20260101-1200',
    brand: 'Acme',
    brand_slug: 'acme',
    panel: 'default',
    mode: 'fresh',
    phase,
    started_at: '2026-01-01T00:00:00Z',
    last_progress_at: '2026-01-01T00:00:00Z',
    completed_phases: completed,
    failed_phases: [],
    errors: [],
    tokens_used: { input: 0, output: 0 },
    options: { skip_wuying: false, language: 'auto' },
  };
}

function makeLLMClient(): LLMClient {
  return {
    model: 'claude-sonnet-4-6',
    complete: vi.fn().mockResolvedValue({ content: 'mock response', input_tokens: 100, output_tokens: 50 }),
  } as unknown as LLMClient;
}

// Store that serves persisted phase artifacts from disk (for the resume path).
function makeArtifactStore(
  state: AuditState,
  files: { raw?: string[]; reviews?: string[]; contents?: Record<string, string> },
) {
  let current = { ...state };
  const contents = files.contents ?? {};
  const listFiles = vi.fn().mockImplementation((_id: string, subdir: string) =>
    Promise.resolve(subdir === '_raw' ? files.raw ?? [] : subdir === 'reviews' ? files.reviews ?? [] : []),
  );
  const readFile = vi.fn().mockImplementation((_id: string, path: string) =>
    Promise.resolve(contents[path] ?? null),
  );
  const store = {
    readState: vi.fn().mockImplementation(() => Promise.resolve({ ...current })),
    writeState: vi.fn().mockImplementation((s: AuditState) => {
      current = { ...s };
      return Promise.resolve();
    }),
    writeFile: vi.fn().mockResolvedValue(undefined),
    readFile,
    listFiles,
    listAudits: vi.fn().mockResolvedValue([]),
    initAudit: vi.fn().mockResolvedValue(undefined),
    exists: vi.fn().mockResolvedValue(false),
  } as unknown as FilesystemStore;
  return { store, listFiles, readFile };
}

const config = { maxParallel: 2, judgesDir: '/tmp/judges' };
const noop = () => {};

describe('runAudit resume', () => {
  it('resuming at judging reloads research + synthesis and runs only judging + merge', async () => {
    const state = makeState('judging', ['proposed', 'researching', 'synthesizing']);
    const raw = ['dimension_1_origin.md', 'dimension_2_category.md', '_raw/synthesis.md'];
    const { store, listFiles, readFile } = makeArtifactStore(state, {
      raw,
      reviews: [],
      contents: {
        '_raw/dimension_1_origin.md': 'origin research',
        '_raw/dimension_2_category.md': 'category research',
        '_raw/synthesis.md': 'the synthesis',
      },
    });
    const sm = new StateMachine(store, noop);
    const transSpy = vi.spyOn(sm, 'transition');
    const client = makeLLMClient();

    await runAudit(state, store, sm, config, client, noop);

    // Only Phase 4 (5 default judges) + Phase 5 (1 merge) hit the LLM — no
    // research (7) or synthesis (1) re-run.
    expect((client.complete as ReturnType<typeof vi.fn>).mock.calls.length).toBe(6);
    // Forward transitions from judging only.
    expect(transSpy.mock.calls.map(c => c[1])).toEqual(['merging', 'done']);
    // Prior artifacts were reloaded from disk.
    expect(listFiles).toHaveBeenCalledWith('acme-20260101-1200', '_raw');
    expect(readFile).toHaveBeenCalledWith('acme-20260101-1200', '_raw/synthesis.md');
  });

  it('resuming at merging reloads everything and runs only the merge', async () => {
    const state = makeState('merging', ['proposed', 'researching', 'synthesizing', 'judging']);
    const { store } = makeArtifactStore(state, {
      raw: ['dimension_1_origin.md', '_raw/synthesis.md'],
      reviews: ['fusheng.md', 'jobs.md'],
      contents: {
        '_raw/dimension_1_origin.md': 'origin research',
        '_raw/synthesis.md': 'the synthesis',
        'reviews/fusheng.md': 'fusheng review',
        'reviews/jobs.md': 'jobs review',
      },
    });
    const sm = new StateMachine(store, noop);
    const transSpy = vi.spyOn(sm, 'transition');
    const client = makeLLMClient();

    await runAudit(state, store, sm, config, client, noop);

    expect((client.complete as ReturnType<typeof vi.fn>).mock.calls.length).toBe(1); // merge only
    expect(transSpy.mock.calls.map(c => c[1])).toEqual(['done']);
  });

  it('resuming at synthesizing reloads research and runs synthesis + judging + merge', async () => {
    const state = makeState('synthesizing', ['proposed', 'researching']);
    const { store } = makeArtifactStore(state, {
      raw: ['dimension_1_origin.md', 'dimension_2_category.md'],
      contents: {
        '_raw/dimension_1_origin.md': 'origin research',
        '_raw/dimension_2_category.md': 'category research',
      },
    });
    const sm = new StateMachine(store, noop);
    const transSpy = vi.spyOn(sm, 'transition');
    const client = makeLLMClient();

    await runAudit(state, store, sm, config, client, noop);

    // 1 synthesis + 5 judges + 1 merge = 7 (no 7 research calls)
    expect((client.complete as ReturnType<typeof vi.fn>).mock.calls.length).toBe(7);
    expect(transSpy.mock.calls.map(c => c[1])).toEqual(['judging', 'merging', 'done']);
  });

  it('fails cleanly if a required resume artifact is missing', async () => {
    const state = makeState('judging', ['proposed', 'researching', 'synthesizing']);
    // synthesis.md absent from contents → loadSynthesis throws
    const { store } = makeArtifactStore(state, { raw: ['dimension_1_origin.md'], contents: {} });
    const sm = new StateMachine(store, noop);
    const transSpy = vi.spyOn(sm, 'transition');
    const client = makeLLMClient();

    await runAudit(state, store, sm, config, client, noop);

    // Runner catches, marks failed, never reaches done.
    const seen = transSpy.mock.calls.map(c => c[1]);
    expect(seen).toContain('failed');
    expect(seen).not.toContain('done');
  });
});
