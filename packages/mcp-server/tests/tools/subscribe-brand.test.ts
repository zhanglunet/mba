import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Subscription } from '../../src/types.js';
import type { SubscriptionStore } from '../../src/store/subscriptions.js';
import { subscribeBrand } from '../../src/tools/subscribe-brand.js';
import { unsubscribeBrand } from '../../src/tools/unsubscribe-brand.js';
import { listSubscriptions } from '../../src/tools/list-subscriptions.js';

// ── mock store ────────────────────────────────────────────────────────────────

function makeMockStore(): SubscriptionStore & { _data: Map<string, Subscription> } {
  const _data = new Map<string, Subscription>();
  return {
    _data,
    write: vi.fn().mockImplementation(async (sub: Subscription) => { _data.set(sub.id, sub); }),
    read: vi.fn().mockImplementation(async (id: string) => _data.get(id) ?? null),
    list: vi.fn().mockImplementation(async () => [..._data.values()]),
    delete: vi.fn().mockImplementation(async (id: string) => { _data.delete(id); return true; }),
    findByBrand: vi.fn().mockImplementation(async (slug: string) =>
      [..._data.values()].filter(s => s.brand_slug === slug && s.active),
    ),
  } as unknown as SubscriptionStore & { _data: Map<string, Subscription> };
}

// ── tests ─────────────────────────────────────────────────────────────────────

describe('subscribeBrand', () => {
  it('creates a subscription with default cron trigger', async () => {
    const store = makeMockStore();
    const result = await subscribeBrand({ brand: 'Xiaomi' }, store);

    expect(result.brand).toBe('Xiaomi');
    expect(result.panel).toBe('default');
    expect(result.triggers).toHaveLength(1);
    expect(result.triggers[0].type).toBe('cron');
    expect(result.subscription_id).toBeTruthy();
  });

  it('persists subscription to store', async () => {
    const store = makeMockStore();
    const result = await subscribeBrand({ brand: 'Apple', panel: 'vc-en' }, store);

    const stored = store._data.get(result.subscription_id)!;
    expect(stored.brand).toBe('Apple');
    expect(stored.panel).toBe('vc-en');
    expect(stored.active).toBe(true);
    expect(stored.trigger_count_this_month).toBe(0);
  });

  it('uses custom triggers and cadence', async () => {
    const store = makeMockStore();
    const result = await subscribeBrand({
      brand: 'Tesla',
      triggers: [{ type: 'cron', config: { interval_days: 30 } }],
      min_interval_days: 30,
      max_per_month: 2,
    }, store);

    const stored = store._data.get(result.subscription_id)!;
    expect(stored.cadence.min_interval_days).toBe(30);
    expect(stored.cadence.max_per_month).toBe(2);
    expect((stored.triggers[0].config as { interval_days: number }).interval_days).toBe(30);
  });

  it('slugifies brand name for brand_slug', async () => {
    const store = makeMockStore();
    await subscribeBrand({ brand: 'Metric Brand Auditor' }, store);

    const [stored] = [...store._data.values()];
    expect(stored.brand_slug).toBe('metric-brand-auditor');
  });
});

describe('listSubscriptions', () => {
  it('returns empty list when no subscriptions', async () => {
    const store = makeMockStore();
    const result = await listSubscriptions(store);
    expect(result.subscriptions).toHaveLength(0);
  });

  it('returns all subscriptions', async () => {
    const store = makeMockStore();
    await subscribeBrand({ brand: 'Brand A' }, store);
    await subscribeBrand({ brand: 'Brand B' }, store);

    const result = await listSubscriptions(store);
    expect(result.subscriptions).toHaveLength(2);
    expect(result.subscriptions.map(s => s.brand)).toContain('Brand A');
    expect(result.subscriptions.map(s => s.brand)).toContain('Brand B');
  });
});

describe('unsubscribeBrand', () => {
  it('removes subscription by id', async () => {
    const store = makeMockStore();
    const { subscription_id } = await subscribeBrand({ brand: 'Nike' }, store);

    const result = await unsubscribeBrand({ subscription_id }, store);
    expect(result.unsubscribed).toBe(true);
    expect(store._data.has(subscription_id)).toBe(false);
  });

  it('throws when subscription not found', async () => {
    const store = makeMockStore();
    await expect(unsubscribeBrand({ subscription_id: 'nonexistent' }, store)).rejects.toThrow(
      'SUBSCRIPTION_NOT_FOUND',
    );
  });
});
