import { describe, it, expect, vi, beforeEach } from 'vitest';
import { StateMachine, makeAuditId, slugify } from '../../src/orchestrator/state-machine.js';
import type { FilesystemStore } from '../../src/store/filesystem.js';
import type { AuditState } from '../../src/types.js';

function makeState(phase: AuditState['phase'] = 'proposed'): AuditState {
  return {
    audit_id: 'test-brand-20260630-1200',
    brand: 'Test Brand',
    brand_slug: 'test-brand',
    panel: 'default',
    mode: 'fresh',
    phase,
    started_at: '2026-06-30T12:00:00.000Z',
    last_progress_at: '2026-06-30T12:00:00.000Z',
    completed_phases: [],
    failed_phases: [],
    errors: [],
    tokens_used: { input: 0, output: 0 },
    options: { skip_wuying: false, language: 'auto' },
  };
}

describe('StateMachine', () => {
  let store: FilesystemStore;
  let sm: StateMachine;
  const log = vi.fn();

  beforeEach(() => {
    store = { writeState: vi.fn().mockResolvedValue(undefined) } as unknown as FilesystemStore;
    sm = new StateMachine(store, log);
  });

  it('allows proposed → researching', async () => {
    const state = makeState('proposed');
    const next = await sm.transition(state, 'researching');
    expect(next.phase).toBe('researching');
    expect(next.completed_phases).toContain('proposed');
  });

  it('allows full happy path', async () => {
    let state = makeState('proposed');
    for (const to of ['researching', 'synthesizing', 'judging', 'merging', 'done'] as const) {
      state = await sm.transition(state, to);
    }
    expect(state.phase).toBe('done');
    expect(state.completed_phases).toHaveLength(5);
  });

  it('rejects invalid transition', async () => {
    const state = makeState('proposed');
    await expect(sm.transition(state, 'done')).rejects.toThrow('Invalid transition');
  });

  it('transitions to failed with error', async () => {
    const state = makeState('researching');
    const err = {
      phase: 'researching',
      code: 'ANTHROPIC_RATE_LIMIT',
      message: 'rate limited',
      timestamp: new Date().toISOString(),
    };
    const next = await sm.transition(state, 'failed', { error: err });
    expect(next.phase).toBe('failed');
    expect(next.errors).toHaveLength(1);
    expect(next.failed_phases).toContain('researching');
  });

  it('interrupted → researching (resume)', async () => {
    const state = makeState('interrupted');
    expect(sm.canResume(state)).toBe(true);
    const next = await sm.transition(state, 'researching');
    expect(next.phase).toBe('researching');
  });

  it('done cannot transition further', async () => {
    const state = makeState('done');
    await expect(sm.transition(state, 'failed')).rejects.toThrow('Invalid transition');
  });

  it('progressPct returns correct values', () => {
    expect(sm.progressPct('proposed')).toBe(5);
    expect(sm.progressPct('done')).toBe(100);
    expect(sm.progressPct('failed')).toBe(0);
  });
});

describe('slugify', () => {
  it('lowercases and replaces spaces', () => {
    expect(slugify('美团 Meituan')).toBe('meituan');
  });

  it('removes special characters', () => {
    expect(slugify('Hermès / 爱马仕')).toBe('herms');
  });

  it('handles pure ASCII', () => {
    expect(slugify('Genki Forest')).toBe('genki-forest');
  });

  it('truncates to 50 chars', () => {
    const long = 'a'.repeat(60);
    expect(slugify(long).length).toBeLessThanOrEqual(50);
  });
});

describe('makeAuditId', () => {
  it('follows format <slug>-<yyyymmdd>-<HHMM>', () => {
    const id = makeAuditId('test-brand');
    expect(id).toMatch(/^test-brand-\d{8}-\d{4}$/);
  });
});
