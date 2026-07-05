import { describe, it, expect, vi } from 'vitest';
import type { FilesystemStore } from '../../src/store/filesystem.js';
import { proposeAudit } from '../../src/tools/propose-audit.js';
import { GENERATED_PANELS, PANEL_NAMES } from '../../src/llm/panels.generated.js';
import { GENERATED_JUDGES } from '../../src/llm/personas.generated.js';

function mockStore(): FilesystemStore {
  return {
    initAudit: vi.fn().mockResolvedValue(undefined),
    writeFile: vi.fn().mockResolvedValue(undefined),
    readState: vi.fn(),
    writeState: vi.fn(),
    readFile: vi.fn(),
    listAudits: vi.fn(),
    listFiles: vi.fn(),
    exists: vi.fn(),
  } as unknown as FilesystemStore;
}

describe('panel data integrity', () => {
  it('bundles 10 industry panels', () => {
    expect(PANEL_NAMES.length).toBe(10);
    expect(GENERATED_PANELS['luxury-en']).toBeDefined();
    expect(GENERATED_PANELS['vc-en']).toBeDefined();
  });

  it('every judge in every panel has a bundled persona', () => {
    for (const [panel, def] of Object.entries(GENERATED_PANELS)) {
      for (const slug of def.judges) {
        const persona = GENERATED_JUDGES[slug];
        expect(persona, `${panel} → ${slug} persona`).toBeDefined();
        expect(persona.dna.length, `${slug} dna`).toBeGreaterThan(30);
        expect(['zh', 'en']).toContain(persona.language);
      }
    }
  });

  it('bundles all 43 unique judges', () => {
    expect(Object.keys(GENERATED_JUDGES).length).toBe(43);
  });
});

describe('proposeAudit panel resolution', () => {
  it('default panel → the built-in 5 judges', async () => {
    const store = mockStore();
    await proposeAudit({ brand: 'Test' }, store);
    const state = (store.initAudit as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(state.panel).toBe('default');
    expect(state.options.judges).toEqual(['fusheng', 'jobs', 'likejia', 'wu-jundong', 'zhang-yiming']);
  });

  it('named panel → its authored roster', async () => {
    const store = mockStore();
    const result = await proposeAudit({ brand: 'Hermès', panel: 'luxury-en' }, store);
    const state = (store.initAudit as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(state.panel).toBe('luxury-en');
    expect(state.options.judges).toEqual(GENERATED_PANELS['luxury-en'].judges);
    expect(state.options.judges).toContain('arnault');
    expect(result.proposal_markdown).toContain('luxury-en');
  });

  it('vc-en panel resolves to the English VC roster', async () => {
    const store = mockStore();
    await proposeAudit({ brand: 'Anthropic', panel: 'vc-en' }, store);
    const state = (store.initAudit as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(state.options.judges).toContain('paulg');
    expect(state.options.judges).toContain('pmarca');
  });

  it('explicit judges override the panel', async () => {
    const store = mockStore();
    await proposeAudit({ brand: 'Test', panel: 'luxury-en', judges: ['jobs'] }, store);
    const state = (store.initAudit as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(state.options.judges).toEqual(['jobs']);
  });

  it('unknown panel → PANEL_NOT_FOUND', async () => {
    const store = mockStore();
    await expect(proposeAudit({ brand: 'Test', panel: 'nope' }, store)).rejects.toThrow('PANEL_NOT_FOUND');
  });
});
