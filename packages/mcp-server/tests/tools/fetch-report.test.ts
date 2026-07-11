import { describe, it, expect, vi } from 'vitest';
import type { AuditState, AuditPhase } from '../../src/types.js';
import type { FilesystemStore } from '../../src/store/filesystem.js';
import { fetchReport } from '../../src/tools/fetch-report.js';

// ── fixtures ─────────────────────────────────────────────────────────────────

function makeState(phase: AuditPhase = 'done'): AuditState {
  return {
    audit_id: 'a1',
    brand: 'Acme',
    brand_slug: 'acme',
    panel: 'default',
    mode: 'fresh',
    phase,
    started_at: '2026-01-01T00:00:00Z',
    last_progress_at: '2026-01-02T03:04:05Z',
    completed_phases: [],
    failed_phases: [],
    errors: [],
    tokens_used: { input: 0, output: 0 },
    options: { skip_wuying: false, language: 'auto' },
  };
}

function makeStore(state: AuditState | null, files: Record<string, string> = {}): FilesystemStore {
  return {
    readState: vi
      .fn()
      .mockImplementation((id: string) =>
        Promise.resolve(state && state.audit_id === id ? state : null),
      ),
    readFile: vi
      .fn()
      .mockImplementation((id: string, path: string) =>
        Promise.resolve(files[`${id}/${path}`] ?? null),
      ),
    writeFile: vi.fn(),
    writeState: vi.fn(),
    initAudit: vi.fn(),
    listAudits: vi.fn(),
    listFiles: vi.fn(),
  } as unknown as FilesystemStore;
}

// ── tests ────────────────────────────────────────────────────────────────────

describe('fetchReport', () => {
  it('returns markdown by default with version + generated_at', async () => {
    const store = makeStore(makeState(), { 'a1/report.md': '# Report' });
    const out = await fetchReport({ audit_id: 'a1' }, store);
    expect(out.markdown).toBe('# Report');
    expect(out.html).toBeUndefined();
    expect(out.version).toBe(1);
    expect(out.generated_at).toBe('2026-01-02T03:04:05Z'); // from state.last_progress_at
    expect(store.readFile).toHaveBeenCalledWith('a1', 'report.md');
  });

  it('returns html only for format=html', async () => {
    const store = makeStore(makeState(), { 'a1/report.html': '<h1>R</h1>' });
    const out = await fetchReport({ audit_id: 'a1', format: 'html' }, store);
    expect(out.html).toBe('<h1>R</h1>');
    expect(out.markdown).toBeUndefined();
    expect(store.readFile).toHaveBeenCalledWith('a1', 'report.html');
    expect(store.readFile).not.toHaveBeenCalledWith('a1', 'report.md');
  });

  it('returns both markdown and html for format=both', async () => {
    const store = makeStore(makeState(), { 'a1/report.md': 'MD', 'a1/report.html': 'HTML' });
    const out = await fetchReport({ audit_id: 'a1', format: 'both' }, store);
    expect(out.markdown).toBe('MD');
    expect(out.html).toBe('HTML');
  });

  it('throws AUDIT_NOT_FOUND for an unknown audit', async () => {
    const store = makeStore(null);
    await expect(fetchReport({ audit_id: 'nope' }, store)).rejects.toThrow('AUDIT_NOT_FOUND');
  });

  it('throws AUDIT_NOT_DONE (with the phase) for an incomplete audit', async () => {
    const store = makeStore(makeState('judging'));
    await expect(fetchReport({ audit_id: 'a1' }, store)).rejects.toThrow(/AUDIT_NOT_DONE.*judging/);
  });

  it('throws REPORT_MISSING when report.md is absent', async () => {
    const store = makeStore(makeState(), {}); // done but no files
    await expect(fetchReport({ audit_id: 'a1' }, store)).rejects.toThrow(/REPORT_MISSING.*report\.md/);
  });

  it('throws REPORT_MISSING for report.html even after markdown succeeds (format=both)', async () => {
    const store = makeStore(makeState(), { 'a1/report.md': 'MD' }); // md present, html absent
    await expect(fetchReport({ audit_id: 'a1', format: 'both' }, store)).rejects.toThrow(
      /REPORT_MISSING.*report\.html/,
    );
  });
});
