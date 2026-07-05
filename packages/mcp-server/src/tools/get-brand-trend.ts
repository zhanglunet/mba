import type {
  GetBrandTrendInput,
  GetBrandTrendOutput,
  BrandTrendPoint,
  AuditScores,
} from '../types.js';
import type { FilesystemStore } from '../store/filesystem.js';
import { slugify } from '../orchestrator/state-machine.js';

const ROUND = (n: number) => Math.round(n * 100) / 100;

/**
 * A brand's score trajectory across all of its completed audits — the multi-audit
 * view that `get_delta_report` (which compares exactly two) doesn't give.
 */
export async function getBrandTrend(
  input: GetBrandTrendInput,
  store: FilesystemStore,
): Promise<GetBrandTrendOutput> {
  const brandSlug = slugify(input.brand);
  const ids = await store.listAudits();

  const points: BrandTrendPoint[] = [];
  for (const id of ids) {
    const state = await store.readState(id);
    if (!state || state.brand_slug !== brandSlug || state.phase !== 'done') continue;
    const raw = await store.readFile(id, 'scores.json');
    if (!raw) continue;
    const scores = JSON.parse(raw) as AuditScores;
    points.push({
      audit_id: id,
      date: state.started_at,
      panel: state.panel,
      overall_mean: scores.overall_mean,
      lens_means: scores.means,
    });
  }

  // Chronological
  points.sort((a, b) => a.date.localeCompare(b.date));

  let overall_delta = 0;
  let trend: 'up' | 'down' | 'flat' = 'flat';
  if (points.length >= 2) {
    overall_delta = ROUND(points[points.length - 1].overall_mean - points[0].overall_mean);
    trend = overall_delta > 0.05 ? 'up' : overall_delta < -0.05 ? 'down' : 'flat';
  }

  return {
    brand: input.brand,
    count: points.length,
    points,
    overall_delta,
    trend,
  };
}
