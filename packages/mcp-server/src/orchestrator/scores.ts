import type { JudgeScores, AuditScores, LensDelta } from '../types.js';

// The 5 MBA lenses, anchored on their English names (present in both zh & en judge output)
export const LENS_IDS = ['origin', 'category', 'leverage', 'identity', 'signal'] as const;

export const LENS_LABELS: Record<string, string> = {
  origin: 'Origin authenticity',
  category: 'Category coinage',
  leverage: 'Leverage quality',
  identity: 'Identity coherence',
  signal: 'Real-world signal',
};

const LENS_ANCHORS: Array<{ id: string; pattern: RegExp }> = [
  { id: 'origin', pattern: /Origin authenticity[^\d\n]*?(\d{1,2})/i },
  { id: 'category', pattern: /Category coinage[^\d\n]*?(\d{1,2})/i },
  { id: 'leverage', pattern: /Leverage quality[^\d\n]*?(\d{1,2})/i },
  { id: 'identity', pattern: /Identity coherence[^\d\n]*?(\d{1,2})/i },
  { id: 'signal', pattern: /Real-world signal[^\d\n]*?(\d{1,2})/i },
];

function round(n: number): number {
  return Math.round(n * 100) / 100;
}

/**
 * Parse a single judge's review markdown into structured lens scores.
 * Returns null if no lens scores could be extracted.
 */
export function parseJudgeScores(judge: string, markdown: string): JudgeScores | null {
  const lenses: Record<string, number> = {};
  for (const { id, pattern } of LENS_ANCHORS) {
    const m = markdown.match(pattern);
    if (m && m[1]) {
      const val = parseInt(m[1], 10);
      if (val >= 1 && val <= 10) lenses[id] = val;
    }
  }
  if (Object.keys(lenses).length === 0) return null;
  const total = Object.values(lenses).reduce((a, b) => a + b, 0);
  return { judge, lenses, total };
}

/**
 * Aggregate per-judge scores into an AuditScores with per-lens means and overall mean.
 */
export function aggregateScores(
  auditId: string,
  brand: string,
  generatedAt: string,
  judgeScores: JudgeScores[],
): AuditScores {
  const means: Record<string, number> = {};
  for (const lens of LENS_IDS) {
    const vals = judgeScores
      .map(j => j.lenses[lens])
      .filter((v): v is number => v !== undefined);
    means[lens] = vals.length ? round(vals.reduce((a, b) => a + b, 0) / vals.length) : 0;
  }
  const totals = judgeScores.map(j => j.total);
  const overall_mean = totals.length ? round(totals.reduce((a, b) => a + b, 0) / totals.length) : 0;
  return { audit_id: auditId, brand, generated_at: generatedAt, judges: judgeScores, means, overall_mean };
}

/**
 * Compute per-lens and overall delta between an old and a new AuditScores.
 */
export function computeDelta(
  oldScores: AuditScores,
  newScores: AuditScores,
): { overall_delta: number; lens_deltas: LensDelta[] } {
  const lens_deltas: LensDelta[] = LENS_IDS.map(lens => {
    const old_mean = oldScores.means[lens] ?? 0;
    const new_mean = newScores.means[lens] ?? 0;
    return { lens, old_mean, new_mean, delta: round(new_mean - old_mean) };
  });
  const overall_delta = round(newScores.overall_mean - oldScores.overall_mean);
  return { overall_delta, lens_deltas };
}

function arrow(delta: number): string {
  if (delta > 0.05) return '▲';
  if (delta < -0.05) return '▼';
  return '—';
}

function signed(delta: number): string {
  if (delta > 0) return `+${delta}`;
  return `${delta}`;
}

/**
 * Build a human-readable markdown delta table.
 */
export function buildDeltaMarkdown(
  brand: string,
  oldScores: AuditScores,
  newScores: AuditScores,
  overall_delta: number,
  lens_deltas: LensDelta[],
): string {
  const rows = lens_deltas
    .map(
      d =>
        `| ${LENS_LABELS[d.lens]} | ${d.old_mean.toFixed(2)} | ${d.new_mean.toFixed(2)} | ${signed(d.delta)} ${arrow(d.delta)} |`,
    )
    .join('\n');

  return `# MBA Delta Report — ${brand}

**Baseline:** \`${oldScores.audit_id}\` (${oldScores.generated_at.slice(0, 10)})
**Current:** \`${newScores.audit_id}\` (${newScores.generated_at.slice(0, 10)})

## Score Delta (panel means)

| Lens | Before | After | Δ |
|---|---|---|---|
${rows}
| **Overall** | **${oldScores.overall_mean.toFixed(2)}** | **${newScores.overall_mean.toFixed(2)}** | **${signed(overall_delta)} ${arrow(overall_delta)}** |

## Biggest Movements

${topMovements(lens_deltas)}
`;
}

function topMovements(lens_deltas: LensDelta[]): string {
  const sorted = [...lens_deltas].sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
  const moved = sorted.filter(d => Math.abs(d.delta) > 0.05).slice(0, 3);
  if (moved.length === 0) return '_No material movement across any lens (all Δ ≤ 0.05)._';
  return moved
    .map(d => {
      const dir = d.delta > 0 ? 'up' : 'down';
      return `- **${LENS_LABELS[d.lens]}** ${dir} ${signed(d.delta)} (${d.old_mean.toFixed(2)} → ${d.new_mean.toFixed(2)})`;
    })
    .join('\n');
}
