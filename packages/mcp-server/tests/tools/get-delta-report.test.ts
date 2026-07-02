import { describe, it, expect, vi } from 'vitest';
import type { AuditState, AuditScores } from '../../src/types.js';
import type { FilesystemStore } from '../../src/store/filesystem.js';
import { getDeltaReport } from '../../src/tools/get-delta-report.js';

function makeState(overrides: Partial<AuditState> = {}): AuditState {
  return {
    audit_id: 'brand-new',
    brand: 'Brand',
    brand_slug: 'brand',
    panel: 'default',
    mode: 'evolution',
    phase: 'done',
    started_at: '2026-07-01T00:00:00Z',
    last_progress_at: '2026-07-01T00:30:00Z',
    completed_phases: [],
    failed_phases: [],
    errors: [],
    tokens_used: { input: 0, output: 0 },
    options: { skip_wuying: false, language: 'auto', previous_audit_id: 'brand-old' },
    ...overrides,
  };
}

function makeScores(auditId: string, originMean: number, total: number): AuditScores {
  return {
    audit_id: auditId,
    brand: 'Brand',
    generated_at: '2026-07-01T00:00:00Z',
    judges: [{ judge: 'jobs', lenses: { origin: originMean, category: 5, leverage: 5, identity: 5, signal: 5 }, total }],
    means: { origin: originMean, category: 5, leverage: 5, identity: 5, signal: 5 },
    overall_mean: total,
  };
}

function makeStore(files: Record<string, string>, states: Record<string, AuditState>): FilesystemStore {
  return {
    readState: vi.fn().mockImplementation((id: string) => Promise.resolve(states[id] ?? null)),
    readFile: vi.fn().mockImplementation((id: string, path: string) =>
      Promise.resolve(files[`${id}/${path}`] ?? null),
    ),
    writeFile: vi.fn().mockResolvedValue(undefined),
    listFiles: vi.fn().mockResolvedValue([]),
    listAudits: vi.fn().mockResolvedValue(Object.keys(states)),
    writeState: vi.fn().mockResolvedValue(undefined),
    initAudit: vi.fn().mockResolvedValue(undefined),
    exists: vi.fn().mockResolvedValue(false),
  } as unknown as FilesystemStore;
}

const noop = () => {};

describe('getDeltaReport', () => {
  it('computes delta between explicit new and baseline scores.json', async () => {
    const newState = makeState();
    const oldState = makeState({ audit_id: 'brand-old', started_at: '2026-06-01T00:00:00Z' });
    const files = {
      'brand-new/scores.json': JSON.stringify(makeScores('brand-new', 8, 40)),
      'brand-old/scores.json': JSON.stringify(makeScores('brand-old', 6, 30)),
    };
    const store = makeStore(files, { 'brand-new': newState, 'brand-old': oldState });

    const result = await getDeltaReport({ audit_id: 'brand-new', narrative: false }, store, null, noop);

    expect(result.previous_audit_id).toBe('brand-old');
    expect(result.overall_delta).toBe(10); // 40 - 30
    const originDelta = result.lens_deltas.find(d => d.lens === 'origin')!;
    expect(originDelta.delta).toBe(2); // 8 - 6
    expect(result.delta_markdown).toContain('MBA Delta Report');
  });

  it('persists delta report files', async () => {
    const newState = makeState();
    const oldState = makeState({ audit_id: 'brand-old' });
    const files = {
      'brand-new/scores.json': JSON.stringify(makeScores('brand-new', 8, 40)),
      'brand-old/scores.json': JSON.stringify(makeScores('brand-old', 6, 30)),
    };
    const store = makeStore(files, { 'brand-new': newState, 'brand-old': oldState });

    await getDeltaReport({ audit_id: 'brand-new', narrative: false }, store, null, noop);

    const writeCalls = (store.writeFile as ReturnType<typeof vi.fn>).mock.calls;
    const paths = writeCalls.map((c: unknown[]) => c[1] as string);
    expect(paths).toContain('delta/vs_brand-old.md');
    expect(paths).toContain('delta/vs_brand-old.json');
  });

  it('throws NO_BASELINE when no previous audit', async () => {
    const newState = makeState({ options: { skip_wuying: false, language: 'auto' } });
    const files = { 'brand-new/scores.json': JSON.stringify(makeScores('brand-new', 8, 40)) };
    const store = makeStore(files, { 'brand-new': newState });

    await expect(
      getDeltaReport({ audit_id: 'brand-new', narrative: false }, store, null, noop),
    ).rejects.toThrow('NO_BASELINE');
  });

  it('generates narrative when client provided', async () => {
    const newState = makeState();
    const oldState = makeState({ audit_id: 'brand-old' });
    const files = {
      'brand-new/scores.json': JSON.stringify(makeScores('brand-new', 8, 40)),
      'brand-old/scores.json': JSON.stringify(makeScores('brand-old', 6, 30)),
    };
    const store = makeStore(files, { 'brand-new': newState, 'brand-old': oldState });
    const client = {
      model: 'claude-sonnet-4-6',
      complete: vi.fn().mockResolvedValue({ content: 'Origin rose notably.', input_tokens: 10, output_tokens: 5 }),
    } as never;

    const result = await getDeltaReport({ audit_id: 'brand-new', narrative: true }, store, client, noop);
    expect(result.narrative).toBe('Origin rose notably.');
    expect(result.delta_markdown).toContain('Narrative');
  });
});
