import type {
  GetDeltaReportInput,
  GetDeltaReportOutput,
  AuditScores,
} from '../types.js';
import type { FilesystemStore } from '../store/filesystem.js';
import type { LLMClient } from '../llm/client.js';
import {
  parseJudgeScores,
  aggregateScores,
  computeDelta,
  buildDeltaMarkdown,
  LENS_LABELS,
} from '../orchestrator/scores.js';

/**
 * Load AuditScores for an audit — prefers scores.json, falls back to
 * reconstructing from reviews/*.md for audits created before scores.json existed.
 */
async function loadScores(auditId: string, store: FilesystemStore): Promise<AuditScores | null> {
  const raw = await store.readFile(auditId, 'scores.json');
  if (raw) {
    return JSON.parse(raw) as AuditScores;
  }

  // Fallback: reconstruct from review files
  const state = await store.readState(auditId);
  const reviewFiles = await store.listFiles(auditId, 'reviews');
  if (reviewFiles.length === 0) return null;

  const judgeScores = [];
  for (const file of reviewFiles) {
    if (!file.endsWith('.md')) continue;
    const content = await store.readFile(auditId, `reviews/${file}`);
    if (!content) continue;
    const slug = file.replace(/\.md$/, '');
    const parsed = parseJudgeScores(slug, content);
    if (parsed) judgeScores.push(parsed);
  }
  if (judgeScores.length === 0) return null;

  return aggregateScores(
    auditId,
    state?.brand ?? auditId,
    state?.last_progress_at ?? new Date().toISOString(),
    judgeScores,
  );
}

async function findPreviousAudit(
  auditId: string,
  brandSlug: string,
  startedAt: string,
  store: FilesystemStore,
): Promise<string | undefined> {
  const allIds = await store.listAudits();
  let best: string | undefined;
  let bestAt = '';
  for (const id of allIds) {
    if (id === auditId) continue;
    const s = await store.readState(id);
    if (
      s &&
      s.brand_slug === brandSlug &&
      s.phase === 'done' &&
      s.started_at < startedAt &&
      s.started_at > bestAt
    ) {
      best = s.audit_id;
      bestAt = s.started_at;
    }
  }
  return best;
}

export async function getDeltaReport(
  input: GetDeltaReportInput,
  store: FilesystemStore,
  client: LLMClient | null,
  log: (level: string, msg: string) => void,
): Promise<GetDeltaReportOutput> {
  const state = await store.readState(input.audit_id);
  if (!state) throw new Error(`AUDIT_NOT_FOUND: ${input.audit_id}`);

  // Resolve the baseline audit
  let previousId =
    input.previous_audit_id ??
    state.options.previous_audit_id ??
    (await findPreviousAudit(input.audit_id, state.brand_slug, state.started_at, store));

  if (!previousId) {
    throw new Error(
      `NO_BASELINE: no previous completed audit found for brand '${state.brand}'. Pass previous_audit_id explicitly.`,
    );
  }

  const newScores = await loadScores(input.audit_id, store);
  if (!newScores) throw new Error(`SCORES_MISSING: cannot load scores for ${input.audit_id}`);

  const oldScores = await loadScores(previousId, store);
  if (!oldScores) throw new Error(`SCORES_MISSING: cannot load scores for baseline ${previousId}`);

  const { overall_delta, lens_deltas } = computeDelta(oldScores, newScores);
  const delta_markdown = buildDeltaMarkdown(
    state.brand,
    oldScores,
    newScores,
    overall_delta,
    lens_deltas,
  );

  // Optional LLM narrative
  let narrative: string | undefined;
  const wantNarrative = input.narrative ?? true;
  if (wantNarrative && client) {
    try {
      const movements = lens_deltas
        .map(d => `${LENS_LABELS[d.lens]}: ${d.old_mean.toFixed(2)} → ${d.new_mean.toFixed(2)} (Δ ${d.delta >= 0 ? '+' : ''}${d.delta})`)
        .join('\n');
      const result = await client.complete(
        `You are an MBA (Metric Brand Auditor) analyst writing a concise "what changed" note comparing two audits of the same brand. Be specific about which lens moved and hypothesize plausible causes from the score shifts alone. 3-5 sentences. Do not fabricate events — reason only from the score movements provided.`,
        `Brand: ${state.brand}\nOverall mean: ${oldScores.overall_mean.toFixed(2)} → ${newScores.overall_mean.toFixed(2)} (Δ ${overall_delta >= 0 ? '+' : ''}${overall_delta})\n\nPer-lens movements:\n${movements}\n\nWrite the delta narrative.`,
        512,
      );
      narrative = result.content;
    } catch (err) {
      log('warn', `[${input.audit_id}] Delta narrative generation failed: ${err}`);
    }
  }

  const full_md = narrative
    ? `${delta_markdown}\n## Narrative\n\n${narrative}\n`
    : delta_markdown;

  // Persist delta report
  await store.writeFile(input.audit_id, `delta/vs_${previousId}.md`, full_md);
  await store.writeFile(
    input.audit_id,
    `delta/vs_${previousId}.json`,
    JSON.stringify({ overall_delta, lens_deltas, previous_audit_id: previousId }, null, 2),
  );

  return {
    audit_id: input.audit_id,
    previous_audit_id: previousId,
    brand: state.brand,
    overall_delta,
    lens_deltas,
    delta_markdown: full_md,
    narrative,
  };
}
