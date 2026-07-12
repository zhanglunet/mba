import type { WatchEvent, WatchTriggerEvaluation } from '../types.js';

/**
 * 触发规则运行时评估(docs/15 §5.3;与 scripts/watch-tools/evaluate_triggers.py 同一套语义):
 * 滚动 windowDays 天窗口(闭区间)内,R1 P0≥1 / R2 P1≥2 / R3 加权 4·2·0.5 ≥5 任一命中
 * → 建议 EVOLUTION 重审。默认只数未消费事件;includeConsumed 切 PRD 严格口径。
 *
 * 边界:只建议、不改分——命中只产生「建议重审」,任何分数都必须来自评委重审。
 */

const WEIGHTS: Record<string, number> = { P0: 4, P1: 2, P2: 0.5, P3: 0 };
const WEIGHTED_THRESHOLD = 5;

export function evaluateTrigger(
  events: WatchEvent[],
  opts: { asOf?: string; windowDays?: number; includeConsumed?: boolean } = {},
): WatchTriggerEvaluation {
  const asOf = opts.asOf ?? new Date().toISOString().slice(0, 10);
  const windowDays = opts.windowDays ?? 30;
  const windowStart = new Date(new Date(`${asOf}T00:00:00Z`).getTime() - windowDays * 86_400_000)
    .toISOString()
    .slice(0, 10);

  const counts: Record<string, number> = { P0: 0, P1: 0, P2: 0, P3: 0 };
  for (const e of events) {
    if (!e?.date || e.date < windowStart || e.date > asOf) continue;
    if (!opts.includeConsumed && e.consumed_by) continue;
    if (e.severity in counts) counts[e.severity] += 1;
  }
  const weighted =
    counts['P0'] * WEIGHTS['P0'] + counts['P1'] * WEIGHTS['P1'] + counts['P2'] * WEIGHTS['P2'];

  const rulesHit: string[] = [];
  if (counts['P0'] >= 1) rulesHit.push('R1:P0>=1');
  if (counts['P1'] >= 2) rulesHit.push('R2:P1>=2');
  if (weighted >= WEIGHTED_THRESHOLD) rulesHit.push(`R3:weighted ${weighted}>=${WEIGHTED_THRESHOLD}`);

  return {
    as_of: asOf,
    window_days: windowDays,
    include_consumed: Boolean(opts.includeConsumed),
    p0: counts['P0'],
    p1: counts['P1'],
    p2: counts['P2'],
    weighted,
    rules_hit: rulesHit,
    hit: rulesHit.length > 0,
    recommendation: rulesHit.length > 0
      ? '触发规则命中 → 建议 EVOLUTION 重审(watch 只建议、不改分)'
      : '未命中触发规则',
  };
}
