import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { SubscriptionStore } from '../../src/store/subscriptions.js';
import type { Subscription } from '../../src/types.js';

function makeSub(overrides: Partial<Subscription> = {}): Subscription {
  return {
    id: 'sub-anthropic',
    brand: 'Anthropic',
    brand_slug: 'anthropic',
    panel: 'vc-en',
    triggers: [{ type: 'cron', config: { interval_days: 30 } }],
    notify: [{ type: 'mcp-push' }],
    cadence: { min_interval_days: 7, max_per_month: 4 },
    created_at: '2026-07-10T00:00:00Z',
    trigger_count_this_month: 0,
    month_reset_at: '2026-08-01T00:00:00Z',
    active: true,
    ...overrides,
  };
}

describe('SubscriptionStore', () => {
  let dir: string;
  let store: SubscriptionStore;

  beforeEach(async () => {
    dir = await mkdtemp(join(tmpdir(), 'mba-subs-'));
    store = new SubscriptionStore(dir);
  });
  afterEach(async () => {
    await rm(dir, { recursive: true, force: true });
  });

  it('write/read round-trips a subscription', async () => {
    const sub = makeSub();
    await store.write(sub);
    expect(await store.read(sub.id)).toEqual(sub);
  });

  it('read returns null for an unknown id', async () => {
    expect(await store.read('nope')).toBeNull();
  });

  it('list returns [] before any subscriptions exist', async () => {
    expect(await store.list()).toEqual([]);
  });

  it('list returns subscriptions sorted by created_at', async () => {
    await store.write(makeSub({ id: 's-late', created_at: '2026-07-10T00:00:00Z' }));
    await store.write(makeSub({ id: 's-early', created_at: '2026-01-01T00:00:00Z' }));
    await store.write(makeSub({ id: 's-mid', created_at: '2026-05-05T00:00:00Z' }));
    expect((await store.list()).map(s => s.id)).toEqual(['s-early', 's-mid', 's-late']);
  });

  it('list ignores non-json files in the subscriptions dir', async () => {
    await store.write(makeSub({ id: 's-1' }));
    await writeFile(join(dir, 'subscriptions', 'README.txt'), 'not a sub', 'utf-8');
    const all = await store.list();
    expect(all).toHaveLength(1);
    expect(all[0]?.id).toBe('s-1');
  });

  it('delete removes an existing subscription and reports true/false', async () => {
    const sub = makeSub();
    await store.write(sub);
    expect(await store.delete(sub.id)).toBe(true);
    expect(await store.read(sub.id)).toBeNull();
    // second delete is a no-op that reports false
    expect(await store.delete(sub.id)).toBe(false);
  });

  it('findByBrand returns only active subs for that brand_slug', async () => {
    await store.write(makeSub({ id: 's-anthropic-1', brand_slug: 'anthropic', active: true }));
    await store.write(makeSub({ id: 's-anthropic-2', brand_slug: 'anthropic', active: false }));
    await store.write(makeSub({ id: 's-openai', brand_slug: 'openai', active: true }));

    const hits = await store.findByBrand('anthropic');
    expect(hits.map(s => s.id)).toEqual(['s-anthropic-1']);

    expect(await store.findByBrand('nobody')).toEqual([]);
  });
});
