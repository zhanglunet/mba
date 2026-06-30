import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { Subscription } from '../../src/types.js';
import type { SubscriptionStore } from '../../src/store/subscriptions.js';
import type { FilesystemStore } from '../../src/store/filesystem.js';
import type { StateMachine } from '../../src/orchestrator/state-machine.js';
import type { LLMClient } from '../../src/llm/client.js';
import { CronScheduler } from '../../src/orchestrator/scheduler.js';

// ── helpers ───────────────────────────────────────────────────────────────────

function makeSub(overrides: Partial<Subscription> = {}): Subscription {
  return {
    id: 'sub-1',
    brand: 'Test Brand',
    brand_slug: 'test-brand',
    panel: 'default',
    triggers: [{ type: 'cron', config: { interval_days: 1 } }],
    notify: [],
    cadence: { min_interval_days: 1, max_per_month: 10 },
    created_at: new Date(Date.now() - 2 * 86_400_000).toISOString(), // 2 days ago
    trigger_count_this_month: 0,
    month_reset_at: new Date().toISOString(),
    active: true,
    ...overrides,
  };
}

function makeSubStore(subs: Subscription[]): SubscriptionStore {
  return {
    list: vi.fn().mockResolvedValue(subs),
    read: vi.fn(),
    write: vi.fn().mockResolvedValue(undefined),
    delete: vi.fn(),
    findByBrand: vi.fn().mockResolvedValue(subs.filter(s => s.active)),
  } as unknown as SubscriptionStore;
}

function makeAuditStore(): FilesystemStore {
  return {
    listAudits: vi.fn().mockResolvedValue([]),
    readState: vi.fn().mockResolvedValue(null),
    writeState: vi.fn().mockResolvedValue(undefined),
    writeFile: vi.fn().mockResolvedValue(undefined),
    readFile: vi.fn().mockResolvedValue(null),
    initAudit: vi.fn().mockResolvedValue(undefined),
    exists: vi.fn().mockResolvedValue(false),
  } as unknown as FilesystemStore;
}

function makeSM(): StateMachine {
  return {
    transition: vi.fn().mockImplementation(async (s, phase) => ({ ...s, phase })),
    progressPct: vi.fn().mockReturnValue(0),
    canResume: vi.fn().mockReturnValue(true),
  } as unknown as StateMachine;
}

function makeLLMClient(): LLMClient {
  return {
    model: 'claude-sonnet-4-6',
    complete: vi.fn().mockResolvedValue({ content: 'ok', input_tokens: 10, output_tokens: 5 }),
  } as unknown as LLMClient;
}

const noop = () => {};
const runnerConfig = { maxParallel: 2, judgesDir: '/tmp/judges' };

// ── tests ─────────────────────────────────────────────────────────────────────

describe('CronScheduler', () => {
  it('tick() fires trigger_evolution for overdue cron subscription', async () => {
    const sub = makeSub(); // created 2 days ago, interval_days: 1 → overdue
    const subStore = makeSubStore([sub]);
    const auditStore = makeAuditStore();
    const sm = makeSM();
    const client = makeLLMClient();

    const scheduler = new CronScheduler(subStore, auditStore, sm, runnerConfig, client, noop);
    await scheduler.tick();

    // sm.transition should have been called (audit started)
    expect((sm.transition as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThan(0);
  });

  it('tick() skips subscription not yet due', async () => {
    const sub = makeSub({
      created_at: new Date().toISOString(), // just created — not yet due
      last_triggered_at: new Date().toISOString(),
    });
    const subStore = makeSubStore([sub]);
    const auditStore = makeAuditStore();
    const sm = makeSM();
    const client = makeLLMClient();

    const scheduler = new CronScheduler(subStore, auditStore, sm, runnerConfig, client, noop);
    await scheduler.tick();

    expect((sm.transition as ReturnType<typeof vi.fn>).mock.calls.length).toBe(0);
  });

  it('tick() skips inactive subscriptions', async () => {
    const sub = makeSub({ active: false });
    const subStore = makeSubStore([sub]);
    const auditStore = makeAuditStore();
    const sm = makeSM();
    const client = makeLLMClient();

    const scheduler = new CronScheduler(subStore, auditStore, sm, runnerConfig, client, noop);
    await scheduler.tick();

    expect((sm.transition as ReturnType<typeof vi.fn>).mock.calls.length).toBe(0);
  });

  it('start() / stop() manage the interval', () => {
    vi.useFakeTimers();
    const subStore = makeSubStore([]);
    const auditStore = makeAuditStore();
    const sm = makeSM();
    const client = makeLLMClient();

    const scheduler = new CronScheduler(subStore, auditStore, sm, runnerConfig, client, noop);
    scheduler.start();
    // Calling start() twice should not create two timers
    scheduler.start();
    scheduler.stop();

    // After stop, advancing time should not fire tick
    vi.advanceTimersByTime(120_000);
    expect((subStore.list as ReturnType<typeof vi.fn>).mock.calls.length).toBe(0);

    vi.useRealTimers();
  });
});
