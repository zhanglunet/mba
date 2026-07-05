import { describe, it, expect, vi } from 'vitest';
import type { FilesystemStore } from '../../src/store/filesystem.js';
import type { AuditState, AuditScores } from '../../src/types.js';
import { listPanels } from '../../src/tools/list-panels.js';
import { getBrandTrend } from '../../src/tools/get-brand-trend.js';

// ── list_panels ───────────────────────────────────────────────────────────────

describe('listPanels', () => {
  it('returns default + 10 industry panels, each with an enriched roster', () => {
    const { panels } = listPanels();
    expect(panels).toHaveLength(11);
    const vcEn = panels.find(p => p.name === 'vc-en')!;
    expect(vcEn.judges.map(j => j.slug)).toContain('paulg');
    for (const j of vcEn.judges) {
      expect(j.name_en).toBeTruthy();
      expect(['zh', 'en']).toContain(j.language);
    }
  });
});

// ── get_brand_trend ────────────────────────────────────────────────────────────

function state(id: string, brand_slug: string, phase: string, started_at: string, panel = 'default'): AuditState {
  return {
    audit_id: id, brand: brand_slug, brand_slug, panel,
    mode: 'fresh', phase: phase as AuditState['phase'],
    started_at, last_progress_at: started_at,
    completed_phases: [], failed_phases: [], errors: [],
    tokens_used: { input: 0, output: 0 },
    options: { skip_wuying: false, language: 'auto' },
  };
}

function scores(id: string, overall: number, origin: number): AuditScores {
  return {
    audit_id: id, brand: 'Acme', generated_at: '2026-01-01',
    judges: [], means: { origin, category: 5, leverage: 5, identity: 5, signal: 5 },
    overall_mean: overall,
  };
}

function trendStore(states: Record<string, AuditState>, scoreFiles: Record<string, AuditScores>): FilesystemStore {
  return {
    listAudits: vi.fn().mockResolvedValue(Object.keys(states)),
    readState: vi.fn().mockImplementation((id: string) => Promise.resolve(states[id] ?? null)),
    readFile: vi.fn().mockImplementation((id: string, path: string) =>
      Promise.resolve(path === 'scores.json' && scoreFiles[id] ? JSON.stringify(scoreFiles[id]) : null),
    ),
  } as unknown as FilesystemStore;
}

describe('getBrandTrend', () => {
  it('builds a chronological trajectory across the brand\'s done audits', async () => {
    const states = {
      'acme-1': state('acme-1', 'acme', 'done', '2026-01-01T00:00:00Z'),
      'acme-2': state('acme-2', 'acme', 'done', '2026-03-01T00:00:00Z', 'auto'),
      'acme-3': state('acme-3', 'acme', 'done', '2026-02-01T00:00:00Z'),
      'other-1': state('other-1', 'other', 'done', '2026-01-15T00:00:00Z'),   // different brand
      'acme-4': state('acme-4', 'acme', 'researching', '2026-04-01T00:00:00Z'), // not done
    };
    const scoreFiles = {
      'acme-1': scores('acme-1', 6.0, 6),
      'acme-2': scores('acme-2', 7.5, 8),
      'acme-3': scores('acme-3', 6.8, 7),
      'other-1': scores('other-1', 9.0, 9),
    };
    const store = trendStore(states, scoreFiles);

    const out = await getBrandTrend({ brand: 'Acme' }, store);
    expect(out.count).toBe(3); // only acme done audits with scores
    expect(out.points.map(p => p.audit_id)).toEqual(['acme-1', 'acme-3', 'acme-2']); // chronological
    expect(out.overall_delta).toBe(1.5); // 7.5 - 6.0
    expect(out.trend).toBe('up');
    expect(out.points[2].panel).toBe('auto');
  });

  it('returns count 0 / flat for a brand with no audits', async () => {
    const store = trendStore({}, {});
    const out = await getBrandTrend({ brand: 'Nobody' }, store);
    expect(out.count).toBe(0);
    expect(out.trend).toBe('flat');
    expect(out.overall_delta).toBe(0);
  });

  it('a declining brand trends down', async () => {
    const states = {
      'x-1': state('x-1', 'x', 'done', '2026-01-01T00:00:00Z'),
      'x-2': state('x-2', 'x', 'done', '2026-06-01T00:00:00Z'),
    };
    const scoreFiles = { 'x-1': scores('x-1', 8.0, 8), 'x-2': scores('x-2', 6.0, 5) };
    const out = await getBrandTrend({ brand: 'X' }, trendStore(states, scoreFiles));
    expect(out.trend).toBe('down');
    expect(out.overall_delta).toBe(-2);
  });
});
