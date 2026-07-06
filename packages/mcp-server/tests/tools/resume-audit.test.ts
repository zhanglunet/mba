import { describe, it, expect, vi } from 'vitest';
import type { AuditState, AuditPhase } from '../../src/types.js';
import type { FilesystemStore } from '../../src/store/filesystem.js';
import { StateMachine } from '../../src/orchestrator/state-machine.js';
import { resumeAudit } from '../../src/tools/resume-audit.js';

function makeState(phase: AuditPhase, completed: string[] = []): AuditState {
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

function makeStore(state: AuditState | null): FilesystemStore {
  let current = state ? { ...state } : null;
  return {
    readState: vi.fn().mockImplementation(() => Promise.resolve(current ? { ...current } : null)),
    writeState: vi.fn().mockImplementation((s: AuditState) => {
      current = { ...s };
      return Promise.resolve();
    }),
  } as unknown as FilesystemStore;
}

function deps(store: FilesystemStore, opts: { hasApiKey?: boolean } = {}) {
  const run = vi.fn();
  const sm = new StateMachine(store, () => {});
  return { run, d: { store, sm, hasApiKey: opts.hasApiKey ?? true, run } };
}

describe('resumeAudit', () => {
  it('throws AUDIT_NOT_FOUND for an unknown audit', async () => {
    const store = makeStore(null);
    const { d } = deps(store);
    await expect(resumeAudit({ audit_id: 'nope' }, d)).rejects.toThrow('AUDIT_NOT_FOUND');
  });

  it('refuses a done audit', async () => {
    const store = makeStore(makeState('done'));
    const { d, run } = deps(store);
    await expect(resumeAudit({ audit_id: 'acme-20260101-1200' }, d)).rejects.toThrow(
      'RESUME_NOT_APPLICABLE',
    );
    expect(run).not.toHaveBeenCalled();
  });

  it('refuses a not-yet-started (proposed) audit and points to confirm_audit', async () => {
    const store = makeStore(makeState('proposed'));
    const { d } = deps(store);
    await expect(resumeAudit({ audit_id: 'acme-20260101-1200' }, d)).rejects.toThrow(
      /RESUME_NOT_APPLICABLE.*confirm_audit/,
    );
  });

  it('requires an API key', async () => {
    const store = makeStore(makeState('judging', ['proposed', 'researching', 'synthesizing']));
    const { d, run } = deps(store, { hasApiKey: false });
    await expect(resumeAudit({ audit_id: 'acme-20260101-1200' }, d)).rejects.toThrow(
      'MISSING_API_KEY',
    );
    expect(run).not.toHaveBeenCalled();
  });

  it('resumes a stalled judging audit from the judging phase', async () => {
    const store = makeStore(makeState('judging', ['proposed', 'researching', 'synthesizing']));
    const { d, run } = deps(store);
    const out = await resumeAudit({ audit_id: 'acme-20260101-1200' }, d);

    expect(out.resumed_from).toBe('judging');
    expect(out.resume_point).toBe('judging');
    expect(out.phase).toBe('judging');
    expect(run).toHaveBeenCalledTimes(1);
    expect((run.mock.calls[0][0] as AuditState).phase).toBe('judging');
  });

  it('resumes a failed audit from the first incomplete phase', async () => {
    // failed while judging → research + synthesis done → resume at judging
    const store = makeStore(makeState('failed', ['proposed', 'researching', 'synthesizing']));
    const { d, run } = deps(store);
    const out = await resumeAudit({ audit_id: 'acme-20260101-1200' }, d);
    expect(out.resumed_from).toBe('failed');
    expect(out.resume_point).toBe('judging');
    expect(run).toHaveBeenCalledTimes(1);
  });

  it('resumes an interrupted audit from synthesizing when only research completed', async () => {
    const store = makeStore(makeState('interrupted', ['proposed', 'researching']));
    const { d, run } = deps(store);
    const out = await resumeAudit({ audit_id: 'acme-20260101-1200' }, d);
    expect(out.resume_point).toBe('synthesizing');
    expect((run.mock.calls[0][0] as AuditState).phase).toBe('synthesizing');
  });

  it('threads max_cost_usd through to the runner state', async () => {
    const store = makeStore(makeState('merging', ['proposed', 'researching', 'synthesizing', 'judging']));
    const { d, run } = deps(store);
    await resumeAudit({ audit_id: 'acme-20260101-1200', max_cost_usd: 2.5 }, d);
    expect((run.mock.calls[0][0] as AuditState).options.max_cost_usd).toBe(2.5);
  });
});
