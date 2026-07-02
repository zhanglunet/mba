import { describe, it, expect } from 'vitest';
import {
  parseJudgeScores,
  aggregateScores,
  computeDelta,
  buildDeltaMarkdown,
} from '../../src/orchestrator/scores.js';

// ── fixtures ────────────────────────────────────────────────────────────────

const EN_REVIEW = `**SCORES:**
- Origin authenticity: 8 — strong founding story
- Category coinage: 6 — partial category ownership
- Leverage quality: 9 — excellent network effects
- Identity coherence: 7 — mostly consistent
- Real-world signal: 5 — modest external validation

**TOTAL: 35/50**

**VERDICT:** A leverage-driven brand with room to grow signal.`;

const ZH_REVIEW = `**评分：**
- 原创性（Origin authenticity）：7 — 起源叙事扎实
- 范畴命名（Category coinage）：5 — 品类归属模糊
- 杠杆质量（Leverage quality）：8 — 渠道势能强
- 身份一致性（Identity coherence）：6 — 基本一致
- 真实信号（Real-world signal）：4 — 外部验证有限

**总分：30/50**

**结论（Verdict）：** 杠杆驱动，信号偏弱。`;

// ── parseJudgeScores ──────────────────────────────────────────────────────────

describe('parseJudgeScores', () => {
  it('parses English judge output', () => {
    const scores = parseJudgeScores('jobs', EN_REVIEW);
    expect(scores).not.toBeNull();
    expect(scores!.lenses.origin).toBe(8);
    expect(scores!.lenses.category).toBe(6);
    expect(scores!.lenses.leverage).toBe(9);
    expect(scores!.lenses.identity).toBe(7);
    expect(scores!.lenses.signal).toBe(5);
    expect(scores!.total).toBe(35);
  });

  it('parses Chinese judge output (English lens anchor)', () => {
    const scores = parseJudgeScores('fusheng', ZH_REVIEW);
    expect(scores).not.toBeNull();
    expect(scores!.lenses.origin).toBe(7);
    expect(scores!.lenses.signal).toBe(4);
    expect(scores!.total).toBe(30);
  });

  it('handles score of 10 correctly', () => {
    const review = 'Origin authenticity: 10 — perfect';
    const scores = parseJudgeScores('x', review);
    expect(scores!.lenses.origin).toBe(10);
  });

  it('returns null when no scores present', () => {
    const scores = parseJudgeScores('x', 'This review has no structured scores at all.');
    expect(scores).toBeNull();
  });

  it('ignores digits in rationale after the score', () => {
    const review = 'Leverage quality: 6 — grew 300% in 2024 across 5 channels';
    const scores = parseJudgeScores('x', review);
    expect(scores!.lenses.leverage).toBe(6);
  });
});

// ── aggregateScores ───────────────────────────────────────────────────────────

describe('aggregateScores', () => {
  it('computes per-lens means and overall mean', () => {
    const a = parseJudgeScores('jobs', EN_REVIEW)!;
    const b = parseJudgeScores('fusheng', ZH_REVIEW)!;
    const agg = aggregateScores('test-1', 'Test', '2026-07-01T00:00:00Z', [a, b]);

    expect(agg.means.origin).toBe(7.5); // (8+7)/2
    expect(agg.means.leverage).toBe(8.5); // (9+8)/2
    expect(agg.overall_mean).toBe(32.5); // (35+30)/2
    expect(agg.judges).toHaveLength(2);
  });
});

// ── computeDelta ──────────────────────────────────────────────────────────────

describe('computeDelta', () => {
  it('computes per-lens and overall deltas', () => {
    const old = aggregateScores('old', 'Test', '2026-06-01T00:00:00Z', [
      parseJudgeScores('fusheng', ZH_REVIEW)!, // origin 7, total 30
    ]);
    const neu = aggregateScores('new', 'Test', '2026-07-01T00:00:00Z', [
      parseJudgeScores('jobs', EN_REVIEW)!, // origin 8, total 35
    ]);

    const { overall_delta, lens_deltas } = computeDelta(old, neu);
    expect(overall_delta).toBe(5); // 35 - 30
    const originDelta = lens_deltas.find(d => d.lens === 'origin')!;
    expect(originDelta.delta).toBe(1); // 8 - 7
    const signalDelta = lens_deltas.find(d => d.lens === 'signal')!;
    expect(signalDelta.delta).toBe(1); // 5 - 4
  });
});

// ── buildDeltaMarkdown ────────────────────────────────────────────────────────

describe('buildDeltaMarkdown', () => {
  it('renders a delta table with arrows', () => {
    const old = aggregateScores('old-1', 'Test', '2026-06-01T00:00:00Z', [
      parseJudgeScores('fusheng', ZH_REVIEW)!,
    ]);
    const neu = aggregateScores('new-1', 'Test', '2026-07-01T00:00:00Z', [
      parseJudgeScores('jobs', EN_REVIEW)!,
    ]);
    const { overall_delta, lens_deltas } = computeDelta(old, neu);
    const md = buildDeltaMarkdown('Test', old, neu, overall_delta, lens_deltas);

    expect(md).toContain('# MBA Delta Report — Test');
    expect(md).toContain('old-1');
    expect(md).toContain('new-1');
    expect(md).toContain('▲'); // some lens went up
    expect(md).toContain('Overall');
    expect(md).toContain('Biggest Movements');
  });

  it('reports no movement when scores identical', () => {
    const s = aggregateScores('a', 'Test', '2026-06-01T00:00:00Z', [
      parseJudgeScores('jobs', EN_REVIEW)!,
    ]);
    const s2 = aggregateScores('b', 'Test', '2026-07-01T00:00:00Z', [
      parseJudgeScores('jobs', EN_REVIEW)!,
    ]);
    const { overall_delta, lens_deltas } = computeDelta(s, s2);
    const md = buildDeltaMarkdown('Test', s, s2, overall_delta, lens_deltas);
    expect(md).toContain('No material movement');
  });
});
