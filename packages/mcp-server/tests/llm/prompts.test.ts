import { describe, it, expect } from 'vitest';
import {
  DIMENSIONS,
  LENSES,
  dimensionUserPrompt,
  changeProbeUserPrompt,
  synthesisUserPrompt,
  judgeSystemPrompt,
  judgeUserPrompt,
  mergeUserPrompt,
} from '../../src/llm/prompts.js';

// Pure string builders — no mocking. Judge fixtures use REAL bundled personas
// (jobs = en, fusheng = zh) plus a guaranteed-absent slug.
const EN_JUDGE = 'jobs';
const ZH_JUDGE = 'fusheng';
const ABSENT = '__no_such_judge__';

// ── structural constants ─────────────────────────────────────────────────────

describe('DIMENSIONS / LENSES tables', () => {
  it('hold the audit contract: 7 dimensions, 5 lenses, all unique & non-empty', () => {
    expect(DIMENSIONS).toHaveLength(7);
    expect(new Set(DIMENSIONS.map(d => d.slug)).size).toBe(7);
    for (const d of DIMENSIONS) {
      expect(d.title.length).toBeGreaterThan(0);
      expect(d.title_en.length).toBeGreaterThan(0);
    }
    expect(LENSES).toHaveLength(5);
    expect(new Set(LENSES.map(l => l.id)).size).toBe(5);
    for (const l of LENSES) {
      expect(l.name_zh.length).toBeGreaterThan(0);
      expect(l.name_en.length).toBeGreaterThan(0);
    }
  });
});

// ── dimension research ───────────────────────────────────────────────────────

describe('dimensionUserPrompt', () => {
  it('embeds the brand and the dimension title (zh + en)', () => {
    const p = dimensionUserPrompt('Nike', DIMENSIONS[0]);
    expect(p).toContain('**Nike**');
    expect(p).toContain(DIMENSIONS[0].title);
    expect(p).toContain(DIMENSIONS[0].title_en);
    expect(p).not.toContain('undefined');
  });
});

// ── evolution change-probe ───────────────────────────────────────────────────

describe('changeProbeUserPrompt', () => {
  it('includes the triggering event when provided', () => {
    const p = changeProbeUserPrompt('Acme', DIMENSIONS[0], 'prev note', 'Sonnet 5 shipped');
    expect(p).toContain('Sonnet 5 shipped');
    expect(p).not.toContain('(none — scheduled/periodic re-audit)');
  });

  it('falls back to the "none" placeholder for a scheduled re-audit', () => {
    const p = changeProbeUserPrompt('Acme', DIMENSIONS[0], 'prev note');
    expect(p).toContain('(none — scheduled/periodic re-audit)');
  });

  it('truncates previous research to 2000 chars (per-call cost guard)', () => {
    const previous = 'A'.repeat(1990) + 'ZZ_BEYOND_2000_MARKER' + 'B'.repeat(3000);
    const p = changeProbeUserPrompt('Acme', DIMENSIONS[0], previous);
    expect(p).not.toContain('ZZ_BEYOND_2000_MARKER'); // marker sits past index 2000 → sliced off
    expect(p).toContain('A'.repeat(100)); // content before the cut survives
  });
});

// ── synthesis ────────────────────────────────────────────────────────────────

describe('synthesisUserPrompt', () => {
  it('renders a titled section per dimension output under the right header', () => {
    const p = synthesisUserPrompt('Nike', { origin: 'ORIGIN_BODY', product: 'PRODUCT_BODY' });
    const originDim = DIMENSIONS.find(d => d.slug === 'origin')!;
    expect(p).toContain('**Nike**');
    expect(p).toContain(`### ${originDim.title} / ${originDim.title_en}`);
    expect(p).toContain('ORIGIN_BODY');
    expect(p).toContain('PRODUCT_BODY');
    expect(p).toContain('---'); // section separator
  });

  it('falls back to the slug (never leaks "undefined") for an unknown dimension', () => {
    const p = synthesisUserPrompt('Nike', { bogusslug: 'BODY' });
    expect(p).toContain('### bogusslug / bogusslug');
    expect(p).not.toContain('undefined');
  });
});

// ── judge scoring ────────────────────────────────────────────────────────────

describe('judgeSystemPrompt', () => {
  it('gives an English judge English instructions + their persona DNA', () => {
    const p = judgeSystemPrompt(EN_JUDGE);
    expect(p).toContain('Score the brand on 5 lenses');
    expect(p).not.toContain('5 个镜头'); // not the zh instructions
    // pin a DNA-body fragment (not the name header) so a stripped/empty persona is caught —
    // a bare length check passes on the ~400-char static block alone.
    expect(p).toContain('Stanford Jobs Archive');
  });

  it('gives a Chinese judge Chinese instructions + their persona DNA', () => {
    const p = judgeSystemPrompt(ZH_JUDGE);
    expect(p).toContain('5 个镜头');
    expect(p).toContain('反编造');
    expect(p).not.toContain('Score the brand on 5 lenses');
    // fusheng DNA-body fragment (his company, not in the name header)
    expect(p).toContain('猎豹移动');
  });

  it('honors a personaMarkdown override and defaults an unknown judge to English', () => {
    const p = judgeSystemPrompt(ABSENT, 'CUSTOM_PERSONA_DNA');
    expect(p).toContain('CUSTOM_PERSONA_DNA');
    expect(p).toContain('Score the brand on 5 lenses'); // !builtin → English
  });

  it('throws JUDGE_MISSING for an unknown judge with no override', () => {
    expect(() => judgeSystemPrompt(ABSENT)).toThrow(/JUDGE_MISSING.*add_judge/s);
  });
});

describe('judgeUserPrompt', () => {
  it('en scorecard lists every LENSES.name_en + TOTAL/50 (the Phase-4 parser contract)', () => {
    const p = judgeUserPrompt('Tesla', 'SYN_BRIEF', EN_JUDGE);
    expect(p).toContain('**Tesla**');
    expect(p).toContain('SYN_BRIEF');
    // The 5 lens labels are HARD-CODED in the template; assert each LENSES.name_en appears so
    // the template and the LENSES table (and F5's parseJudgeScores anchors) cannot silently drift.
    for (const lens of LENSES) {
      expect(p).toContain(lens.name_en);
    }
    expect(p).toContain('TOTAL: [sum]/50');
    expect(p).toContain('SIGNATURE QUOTE:');
  });

  it('zh scorecard lists every lens bilingually with zh scoring labels', () => {
    const p = judgeUserPrompt('小米', 'SYN', ZH_JUDGE);
    expect(p).toContain('被审计品牌：**小米**');
    expect(p).toContain('总分：[合计]/50');
    for (const lens of LENSES) {
      expect(p).toContain(lens.name_zh);
      expect(p).toContain(lens.name_en); // en parenthetical
    }
    expect(p).toContain('金句');
  });

  it('defaults an unknown judge to the English scorecard', () => {
    const p = judgeUserPrompt('Brand', 'SYN', ABSENT);
    expect(p).toContain('TOTAL: [sum]/50');
    expect(p).not.toContain('总分');
  });
});

// ── report merge ─────────────────────────────────────────────────────────────

describe('mergeUserPrompt', () => {
  it('embeds the panel roster and one section per review', () => {
    const p = mergeUserPrompt(
      'Airbnb',
      'SYN_BRIEF',
      { jobs: 'REVIEW_1', fusheng: 'REVIEW_2' },
      ['jobs', 'fusheng'],
    );
    expect(p).toContain('Panel: jobs, fusheng');
    expect(p).toContain('**Airbnb**');
    expect(p).toContain('SYN_BRIEF');
    expect(p).toContain('### Judge: jobs');
    expect(p).toContain('### Judge: fusheng');
    expect(p).toContain('REVIEW_1');
    expect(p).toContain('REVIEW_2');
    // one section per review — a dropped scorecard would change this count
    expect((p.match(/### Judge:/g) ?? []).length).toBe(2);
  });
});

// ── purity ───────────────────────────────────────────────────────────────────

describe('prompt builders are pure', () => {
  it('return identical output for identical inputs (deterministic → cache-safe)', () => {
    const args = ['Airbnb', 'SYN', { jobs: 'r1' }, ['jobs']] as const;
    expect(mergeUserPrompt(...args)).toBe(mergeUserPrompt(...args));
    expect(judgeUserPrompt('X', 'S', EN_JUDGE)).toBe(judgeUserPrompt('X', 'S', EN_JUDGE));
  });
});
