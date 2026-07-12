import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mkdtemp, mkdir, writeFile, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { parse } from 'yaml';
import type { Subscription } from '../../src/types.js';
import type { SubscriptionStore } from '../../src/store/subscriptions.js';
import { WatchStore } from '../../src/watch/store.js';
import { evaluateTrigger } from '../../src/watch/trigger.js';
import { getWatchEvents } from '../../src/tools/get-watch-events.js';
import { recordWatchEvent } from '../../src/tools/record-watch-event.js';

const log = vi.fn();

// ── fixtures ──────────────────────────────────────────────────────────────────

const MATRIX = `brands:
  demo:
    W1: on
    W2: "off"
    W3: core
    W4: on
    W5: on
    W6: "off"
    W7: on
    W8: on
    W9: on
`;

// 与 watch/*/events.yaml 同款格式(含注释 + 块标量),验证解析与追加都不破坏它。
const EVENTS = `# watch/demo/events.yaml — 测试事件流
- id: 2026-06-20-demo-001
  date: 2026-06-20
  dim: W3
  severity: P1
  direction: neg
  direction_by: model-judged
  title: 既有事件一
  quote: "verbatim quote one"
  quote_type: title
  url: https://example.com/a
  fetched_at: "2026-06-21T00:00:00Z"
  lens_map: [signal]
  note: >-
    多行块标量
    注记。

- id: 2026-06-25-demo-002
  date: 2026-06-25
  dim: W5
  severity: P1
  direction: pos
  direction_by: model-judged
  title: 既有事件二(已消费)
  quote: "verbatim quote two"
  quote_type: title
  url: https://example.com/b
  fetched_at: "2026-06-26T00:00:00Z"
  consumed_by: v2
  lens_map: [signal, leverage]
`;

function baseEvent(over: Record<string, unknown> = {}) {
  return {
    date: '2026-07-01',
    dim: 'W3',
    severity: 'P2',
    direction: 'neg',
    title: '新事件',
    quote: 'verbatim new quote',
    quote_type: 'title' as const,
    url: 'https://example.com/new',
    fetched_at: '2026-07-02T00:00:00Z',
    lens_map: ['signal'],
    ...over,
  };
}

function makeMockSubStore(subs: Subscription[] = []): SubscriptionStore {
  return {
    findByBrand: vi.fn().mockImplementation(async (slug: string) =>
      subs.filter(s => s.brand_slug === slug && s.active),
    ),
  } as unknown as SubscriptionStore;
}

let dir: string;
let store: WatchStore;

beforeEach(async () => {
  dir = await mkdtemp(join(tmpdir(), 'mba-watch-'));
  await writeFile(join(dir, 'matrix.yaml'), MATRIX);
  await mkdir(join(dir, 'demo'), { recursive: true });
  await writeFile(join(dir, 'demo', 'events.yaml'), EVENTS);
  store = new WatchStore(dir);
});

afterEach(async () => {
  await rm(dir, { recursive: true, force: true });
});

// ── evaluateTrigger ───────────────────────────────────────────────────────────

describe('evaluateTrigger', () => {
  const ev = (date: string, severity: string, consumed?: string) =>
    ({ date, severity, consumed_by: consumed }) as never;

  it('R1: one P0 in window hits', () => {
    const r = evaluateTrigger([ev('2026-07-01', 'P0')], { asOf: '2026-07-10' });
    expect(r.hit).toBe(true);
    expect(r.rules_hit[0]).toContain('R1');
  });

  it('R2: three P1 hit, two P1 do not (2026-07-12 校准)', () => {
    expect(
      evaluateTrigger([ev('2026-07-01', 'P1'), ev('2026-07-02', 'P1')], { asOf: '2026-07-10' }).hit,
    ).toBe(false);
    expect(
      evaluateTrigger(
        [ev('2026-07-01', 'P1'), ev('2026-07-02', 'P1'), ev('2026-07-03', 'P1')],
        { asOf: '2026-07-10' },
      ).hit,
    ).toBe(true);
  });

  it('R3: weighted 2×P1 + 4×P2 = 6 hits, P1 + 6×P2 = 5 does not (校准后)', () => {
    const hit = [ev('2026-07-01', 'P1'), ev('2026-07-02', 'P1'), ...Array.from({ length: 4 }, (_, i) =>
      ev(`2026-07-0${i + 3}`, 'P2'))];
    const r = evaluateTrigger(hit, { asOf: '2026-07-10' });
    expect(r.weighted).toBe(6);
    expect(r.hit).toBe(true);
    const miss = [ev('2026-07-01', 'P1'), ...Array.from({ length: 6 }, (_, i) =>
      ev(`2026-07-0${i + 2}`, 'P2'))];
    expect(evaluateTrigger(miss, { asOf: '2026-07-10' }).hit).toBe(false);
  });

  it('events outside the rolling window are ignored (edge day counts)', () => {
    expect(evaluateTrigger([ev('2026-06-10', 'P0')], { asOf: '2026-07-10' }).hit).toBe(true); // 恰 30 天
    expect(evaluateTrigger([ev('2026-06-09', 'P0')], { asOf: '2026-07-10' }).hit).toBe(false); // 31 天
  });

  it('consumed events are skipped by default, counted with includeConsumed', () => {
    const events = [ev('2026-07-01', 'P0', 'v2')];
    expect(evaluateTrigger(events, { asOf: '2026-07-10' }).hit).toBe(false);
    expect(evaluateTrigger(events, { asOf: '2026-07-10', includeConsumed: true }).hit).toBe(true);
  });
});

// ── getWatchEvents ────────────────────────────────────────────────────────────

describe('getWatchEvents', () => {
  it('reads events newest-first with trigger evaluation attached', async () => {
    const r = await getWatchEvents({ brand: 'demo' }, store);
    expect(r.count).toBe(2);
    expect(r.events[0].id).toBe('2026-06-25-demo-002');
    expect(r.events[0].date).toBe('2026-06-25'); // YAML date → 字符串归一化
    expect(r.trigger).toHaveProperty('hit');
  });

  it('filters by since / dim / severity / unconsumed_only', async () => {
    expect((await getWatchEvents({ brand: 'demo', since: '2026-06-25' }, store)).count).toBe(1);
    expect((await getWatchEvents({ brand: 'demo', dim: 'W5' }, store)).count).toBe(1);
    expect((await getWatchEvents({ brand: 'demo', severity: 'P1' }, store)).count).toBe(2);
    const un = await getWatchEvents({ brand: 'demo', unconsumed_only: true }, store);
    expect(un.count).toBe(1);
    expect(un.events[0].id).toBe('2026-06-20-demo-001');
  });

  it('returns empty for a brand with no events file', async () => {
    const r = await getWatchEvents({ brand: 'ghost' }, store);
    expect(r.count).toBe(0);
    expect(r.trigger.hit).toBe(false);
  });
});

// ── recordWatchEvent ──────────────────────────────────────────────────────────

describe('recordWatchEvent', () => {
  it('appends a valid event with sequential id and preserves existing file text', async () => {
    const before = await readFile(join(dir, 'demo', 'events.yaml'), 'utf-8');
    const r = await recordWatchEvent(
      { brand: 'demo', event: baseEvent() }, store, makeMockSubStore(), log,
    );
    expect(r.recorded).toBe(true);
    expect(r.id).toBe('2026-07-01-demo-003'); // 顺延既有最大序号 002

    const after = await readFile(join(dir, 'demo', 'events.yaml'), 'utf-8');
    expect(after.startsWith(before.trimEnd())).toBe(true); // 只追加,不重写
    const parsed = parse(after) as unknown[];
    expect(parsed).toHaveLength(3);
  });

  it('creates the events file for a new brand in the matrix', async () => {
    const demo2Block = MATRIX.slice(MATRIX.indexOf('  demo:')).replace('  demo:', '  demo2:');
    await writeFile(join(dir, 'matrix.yaml'), MATRIX + demo2Block);
    const r = await recordWatchEvent(
      { brand: 'demo2', event: baseEvent() }, store, makeMockSubStore(), log,
    );
    expect(r.id).toBe('2026-07-01-demo2-001');
    const parsed = parse(await readFile(join(dir, 'demo2', 'events.yaml'), 'utf-8')) as unknown[];
    expect(parsed).toHaveLength(1);
  });

  it.each([
    ['brand not in matrix', { brand: 'ghost', event: baseEvent() }, /不在适用性矩阵/],
    ['dim off in matrix', { brand: 'demo', event: baseEvent({ dim: 'W2' }) }, /off/],
    ['quote over 100 chars', { brand: 'demo', event: baseEvent({ quote: '长'.repeat(101) }) }, /quote 超/],
    ['future date', { brand: 'demo', event: baseEvent({ date: '2099-01-01' }) }, /在未来/],
    ['non-http url', { brand: 'demo', event: baseEvent({ url: 'ftp://x' }) }, /http/],
    ['bad fetched_at', { brand: 'demo', event: baseEvent({ fetched_at: 'yesterday' }) }, /fetched_at/],
    ['lens out of set', { brand: 'demo', event: baseEvent({ lens_map: ['vibe'] }) }, /lens_map/],
    ['consumed_by rejected', { brand: 'demo', event: baseEvent({ consumed_by: 'v3' }) }, /consumed_by/],
  ])('rejects invalid input: %s', async (_name, input, msg) => {
    await expect(
      recordWatchEvent(input as never, store, makeMockSubStore(), log),
    ).rejects.toThrow(msg);
  });

  it('forces direction_by to model-judged regardless of input', async () => {
    await recordWatchEvent(
      { brand: 'demo', event: { ...baseEvent(), direction_by: 'human' } as never },
      store, makeMockSubStore(), log,
    );
    const parsed = parse(await readFile(join(dir, 'demo', 'events.yaml'), 'utf-8')) as
      Array<{ direction_by: string }>;
    expect(parsed[2].direction_by).toBe('model-judged');
  });

  it('dispatches watch_alert via subscription pipeline on P0', async () => {
    const sub = {
      id: 's1', brand: 'demo', brand_slug: 'demo', active: true,
      notify: [{ type: 'mcp-push' }],
    } as unknown as Subscription;
    const today = new Date().toISOString().slice(0, 10);
    const r = await recordWatchEvent(
      { brand: 'demo', event: baseEvent({ severity: 'P0', date: today }) },
      store, makeMockSubStore([sub]), log,
    );
    expect(r.notified).toHaveLength(1);
    expect(r.notified[0].ok).toBe(true);
    expect(r.trigger.hit).toBe(true); // P0 in window → R1
  });

  it('stays quiet (no dispatch) when nothing triggers', async () => {
    const sub = {
      id: 's1', brand: 'demo', brand_slug: 'demo', active: true,
      notify: [{ type: 'mcp-push' }],
    } as unknown as Subscription;
    const r = await recordWatchEvent(
      { brand: 'demo', event: baseEvent({ severity: 'P3' }) },
      store, makeMockSubStore([sub]), log,
    );
    expect(r.trigger.hit).toBe(false);
    expect(r.notified).toHaveLength(0);
  });
});
