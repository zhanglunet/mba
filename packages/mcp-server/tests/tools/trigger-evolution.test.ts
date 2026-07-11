import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// CRITICAL: stub the runner so a "proceed" path never launches the real 5-judge LLM audit.
// triggerEvolution fires runAudit(...) fire-and-forget; the mock lets us assert called/not-called
// (the whole point of the cadence guard is to NOT spend, so we verify the spy directly).
vi.mock('../../src/orchestrator/runner.js', () => ({
  runAudit: vi.fn().mockResolvedValue(undefined),
}));

import type { AuditState, Subscription } from '../../src/types.js';
import type { FilesystemStore } from '../../src/store/filesystem.js';
import type { SubscriptionStore } from '../../src/store/subscriptions.js';
import type { LLMClient } from '../../src/llm/client.js';
import type { RunnerConfig } from '../../src/orchestrator/runner.js';
import { StateMachine } from '../../src/orchestrator/state-machine.js';
import { runAudit } from '../../src/orchestrator/runner.js';
import { triggerEvolution } from '../../src/tools/trigger-evolution.js';

const runAuditMock = vi.mocked(runAudit);

// Fixed "now" so cadence math is deterministic. All last_triggered_at / month_reset_at are
// expressed relative to this instant.
const NOW = new Date('2026-06-15T12:00:00Z');
const DAY = 86_400_000;
const daysAgo = (n: number) => new Date(NOW.getTime() - n * DAY).toISOString();

// ── fixtures ─────────────────────────────────────────────────────────────────

function makeStore(existing: AuditState[] = []): FilesystemStore & { created: AuditState[] } {
  const created: AuditState[] = [];
  const byId = new Map(existing.map(s => [s.audit_id, s]));
  return {
    created,
    listAudits: vi.fn().mockImplementation(async () => [...byId.keys()]),
    readState: vi.fn().mockImplementation(async (id: string) => byId.get(id) ?? null),
    initAudit: vi.fn().mockImplementation(async (s: AuditState) => {
      created.push(s);
      byId.set(s.audit_id, s);
    }),
    writeState: vi.fn().mockImplementation(async (s: AuditState) => {
      byId.set(s.audit_id, s);
    }),
  } as unknown as FilesystemStore & { created: AuditState[] };
}

function makeSubStore(subs: Subscription[] = []): SubscriptionStore & { _data: Map<string, Subscription> } {
  const _data = new Map(subs.map(s => [s.id, s]));
  return {
    _data,
    findByBrand: vi
      .fn()
      .mockImplementation(async (slug: string) =>
        [..._data.values()].filter(s => s.brand_slug === slug && s.active),
      ),
    write: vi.fn().mockImplementation(async (s: Subscription) => {
      _data.set(s.id, s);
    }),
  } as unknown as SubscriptionStore & { _data: Map<string, Subscription> };
}

function makeSub(overrides: Partial<Subscription> = {}): Subscription {
  return {
    id: 'sub-1',
    brand: 'Acme',
    brand_slug: 'acme',
    panel: 'vc-en',
    triggers: [],
    notify: [],
    cadence: { min_interval_days: 7, max_per_month: 4 },
    created_at: '2026-01-01T00:00:00Z',
    trigger_count_this_month: 0,
    month_reset_at: '2026-06-01T00:00:00Z', // current month → cap applies by default
    active: true,
    ...overrides,
  };
}

function makeDone(audit_id: string, started_at: string, brand_slug = 'acme'): AuditState {
  return {
    audit_id,
    brand: 'Acme',
    brand_slug,
    panel: 'vc-en',
    mode: 'fresh',
    phase: 'done',
    started_at,
    last_progress_at: started_at,
    completed_phases: [],
    failed_phases: [],
    errors: [],
    tokens_used: { input: 0, output: 0 },
    options: { skip_wuying: false, language: 'auto' },
  };
}

const cfg = { maxParallel: 1, judgesDir: '/tmp' } as unknown as RunnerConfig;
const client = {} as unknown as LLMClient;
const noop = () => {};

function trigger(
  store: FilesystemStore,
  subStore: SubscriptionStore,
  input: Parameters<typeof triggerEvolution>[0],
) {
  const sm = new StateMachine(store, () => {});
  return triggerEvolution(input, store, subStore, sm, cfg, client, noop);
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(NOW);
  runAuditMock.mockClear();
});
afterEach(() => {
  vi.useRealTimers();
});

// ── cadence guard (the runaway-spend guard) ──────────────────────────────────

describe('triggerEvolution — cadence guard', () => {
  it('SKIPS (no spend) when the last trigger was more recent than min_interval_days', async () => {
    const store = makeStore();
    const subStore = makeSubStore([makeSub({ last_triggered_at: daysAgo(2) })]); // 2d < 7d
    const out = await trigger(store, subStore, { brand: 'Acme' });

    expect(out.skipped).toBe(true);
    expect(out.audit_id).toBe('');
    expect(out.phase).toBe('proposed');
    expect(out.skip_reason).toContain('min_interval_days=7');
    // the essential guarantee: no re-audit was launched
    expect(runAuditMock).not.toHaveBeenCalled();
    expect(store.initAudit).not.toHaveBeenCalled();
  });

  it('force=true BYPASSES the cadence guard and spends', async () => {
    const store = makeStore();
    const subStore = makeSubStore([makeSub({ last_triggered_at: daysAgo(2) })]);
    const out = await trigger(store, subStore, { brand: 'Acme', force: true });

    expect(out.skipped).toBeFalsy();
    expect(out.phase).toBe('researching');
    expect(runAuditMock).toHaveBeenCalledTimes(1);
  });

  it('proceeds at the exact boundary (elapsed === min_interval_days)', async () => {
    const store = makeStore();
    const subStore = makeSubStore([makeSub({ last_triggered_at: daysAgo(7) })]); // exactly 7d
    const out = await trigger(store, subStore, { brand: 'Acme' });

    expect(out.phase).toBe('researching'); // `< min` is false at the boundary → proceed
    expect(runAuditMock).toHaveBeenCalledTimes(1);
  });

  it('skips just under the boundary (elapsed = min − 1min)', async () => {
    const store = makeStore();
    const justUnder = new Date(NOW.getTime() - (7 * DAY - 60_000)).toISOString();
    const subStore = makeSubStore([makeSub({ last_triggered_at: justUnder })]);
    const out = await trigger(store, subStore, { brand: 'Acme' });

    expect(out.skipped).toBe(true);
    expect(runAuditMock).not.toHaveBeenCalled();
  });

  it('allows the first-ever trigger (no last_triggered_at)', async () => {
    const store = makeStore();
    const subStore = makeSubStore([makeSub({ last_triggered_at: undefined })]);
    const out = await trigger(store, subStore, { brand: 'Acme' });

    expect(out.phase).toBe('researching');
    expect(runAuditMock).toHaveBeenCalledTimes(1);
  });
});

// ── monthly cap guard ────────────────────────────────────────────────────────

describe('triggerEvolution — monthly cap', () => {
  it('SKIPS (no spend) when the monthly trigger cap is reached this month', async () => {
    const store = makeStore();
    const subStore = makeSubStore([
      makeSub({ trigger_count_this_month: 4, month_reset_at: '2026-06-01T00:00:00Z' }), // 4/4, same month
    ]);
    const out = await trigger(store, subStore, { brand: 'Acme' });

    expect(out.skipped).toBe(true);
    expect(out.skip_reason).toContain('max_per_month=4');
    expect(runAuditMock).not.toHaveBeenCalled();
  });

  it('force=true BYPASSES the monthly cap (distinct from the cadence bypass)', async () => {
    const store = makeStore();
    const subStore = makeSubStore([
      makeSub({ trigger_count_this_month: 4, month_reset_at: '2026-06-01T00:00:00Z' }), // capped, same month
    ]);
    const out = await trigger(store, subStore, { brand: 'Acme', force: true });

    expect(out.skipped).toBeFalsy();
    expect(out.phase).toBe('researching');
    expect(runAuditMock).toHaveBeenCalledTimes(1); // force overrides the monthly cap too
  });

  it('resets the count in a new month and proceeds', async () => {
    const store = makeStore();
    const subStore = makeSubStore([
      makeSub({ trigger_count_this_month: 4, month_reset_at: '2026-05-01T00:00:00Z' }), // prior month
    ]);
    const out = await trigger(store, subStore, { brand: 'Acme' });

    expect(out.phase).toBe('researching'); // June > May → count reset to 0 → cap not hit
    expect(runAuditMock).toHaveBeenCalledTimes(1);
    const written = [...subStore._data.values()][0];
    expect(written.trigger_count_this_month).toBe(1); // reset then incremented for this run
  });
});

// ── proceed path ─────────────────────────────────────────────────────────────

describe('triggerEvolution — proceed path', () => {
  it('with no subscription, uses the default panel and launches without touching subStore', async () => {
    const store = makeStore();
    const subStore = makeSubStore([]); // no subscription
    const out = await trigger(store, subStore, { brand: 'Acme' });

    expect(out.phase).toBe('researching');
    expect(out.message).toContain('none (first run)');
    expect(runAuditMock).toHaveBeenCalledTimes(1);
    expect(store.created[0].mode).toBe('evolution');
    expect(store.created[0].panel).toBe('default');
    expect(subStore.write).not.toHaveBeenCalled();
    // the state handed to the runner has advanced past 'proposed'
    expect((runAuditMock.mock.calls[0][0] as AuditState).phase).toBe('researching');
  });

  it('uses the subscription panel and bumps its counters on a green light', async () => {
    const store = makeStore();
    const subStore = makeSubStore([
      makeSub({ panel: 'vc-cn', last_triggered_at: daysAgo(30), trigger_count_this_month: 1 }),
    ]);
    const out = await trigger(store, subStore, { brand: 'Acme' });

    expect(store.created[0].panel).toBe('vc-cn');
    const sub = subStore._data.get('sub-1')!;
    expect(sub.last_triggered_at).toBe(NOW.toISOString());
    expect(sub.last_audit_id).toBe(out.audit_id);
    expect(sub.trigger_count_this_month).toBe(2); // 1 → 2 (same month)
  });

  it('links the most-recent completed audit as the previous baseline', async () => {
    const store = makeStore([
      makeDone('acme-old', '2026-05-01T00:00:00Z'),
      makeDone('acme-new', '2026-06-10T00:00:00Z'), // most recent done
      { ...makeDone('acme-running', '2026-06-14T00:00:00Z'), phase: 'judging' }, // not done → ignored
    ]);
    const subStore = makeSubStore([]);
    const out = await trigger(store, subStore, { brand: 'Acme' });

    expect(out.message).toContain('acme-new');
    expect(store.created[0].options.previous_audit_id).toBe('acme-new');
  });
});
