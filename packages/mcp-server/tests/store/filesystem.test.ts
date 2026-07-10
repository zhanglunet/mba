import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtemp, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { FilesystemStore } from '../../src/store/filesystem.js';
import type { AuditState } from '../../src/types.js';

function makeState(overrides: Partial<AuditState> = {}): AuditState {
  return {
    audit_id: 'anthropic-2026-07-10',
    brand: 'Anthropic',
    brand_slug: 'anthropic',
    panel: 'vc-en',
    mode: 'fresh',
    phase: 'proposed',
    started_at: '2026-07-10T00:00:00Z',
    last_progress_at: '2026-07-10T00:00:00Z',
    completed_phases: [],
    failed_phases: [],
    errors: [],
    tokens_used: { input: 0, output: 0 },
    options: { skip_wuying: false, language: 'auto' },
    ...overrides,
  };
}

describe('FilesystemStore', () => {
  let dir: string;
  let store: FilesystemStore;

  beforeEach(async () => {
    dir = await mkdtemp(join(tmpdir(), 'mba-fsstore-'));
    store = new FilesystemStore(dir);
  });
  afterEach(async () => {
    await rm(dir, { recursive: true, force: true });
  });

  it('initAudit creates the audit scaffold and persists state', async () => {
    const state = makeState();
    await store.initAudit(state);

    expect(existsSync(join(dir, 'audits', state.audit_id, '_raw'))).toBe(true);
    expect(existsSync(join(dir, 'audits', state.audit_id, 'reviews'))).toBe(true);
    expect(await store.exists(state.audit_id)).toBe(true);

    const read = await store.readState(state.audit_id);
    expect(read).toEqual(state);
  });

  it('readState returns null for an unknown audit', async () => {
    expect(await store.readState('does-not-exist')).toBeNull();
    expect(await store.exists('does-not-exist')).toBe(false);
  });

  it('writeState round-trips and overwrites', async () => {
    const state = makeState();
    await store.writeState(state);
    expect((await store.readState(state.audit_id))?.phase).toBe('proposed');

    await store.writeState({ ...state, phase: 'done', tokens_used: { input: 10, output: 20 } });
    const updated = await store.readState(state.audit_id);
    expect(updated?.phase).toBe('done');
    expect(updated?.tokens_used).toEqual({ input: 10, output: 20 });
  });

  it('writeFile/readFile round-trip, creating nested subdirs', async () => {
    const id = 'anthropic-2026-07-10';
    await store.writeFile(id, '_raw/synthesis.md', '# synthesis');
    await store.writeFile(id, 'reviews/pthiel.md', '# thiel');
    await store.writeFile(id, 'versions/v1_2026-07-10.md', '# v1');

    expect(await store.readFile(id, '_raw/synthesis.md')).toBe('# synthesis');
    expect(await store.readFile(id, 'reviews/pthiel.md')).toBe('# thiel');
    expect(await store.readFile(id, 'versions/v1_2026-07-10.md')).toBe('# v1');
  });

  it('readFile returns null for a missing relative path', async () => {
    await store.initAudit(makeState());
    expect(await store.readFile('anthropic-2026-07-10', 'reviews/nobody.md')).toBeNull();
  });

  it('listAudits returns every audit directory (and [] when none)', async () => {
    expect(await store.listAudits()).toEqual([]);
    await store.initAudit(makeState({ audit_id: 'a-1' }));
    await store.initAudit(makeState({ audit_id: 'a-2' }));
    expect((await store.listAudits()).sort()).toEqual(['a-1', 'a-2']);
  });

  it('listFiles lists files in a subdir only (not subdirs), [] when absent', async () => {
    const id = 'anthropic-2026-07-10';
    await store.writeFile(id, 'reviews/pthiel.md', 'x');
    await store.writeFile(id, 'reviews/naval.md', 'y');
    expect((await store.listFiles(id, 'reviews')).sort()).toEqual(['naval.md', 'pthiel.md']);
    expect(await store.listFiles(id, 'nope')).toEqual([]);
  });

  it('isolates two audits under distinct directories', async () => {
    await store.writeFile('brand-a', 'report.md', 'A report');
    await store.writeFile('brand-b', 'report.md', 'B report');
    expect(await store.readFile('brand-a', 'report.md')).toBe('A report');
    expect(await store.readFile('brand-b', 'report.md')).toBe('B report');
  });
});
