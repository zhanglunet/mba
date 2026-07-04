import type {
  TriggerEvolutionInput,
  TriggerEvolutionOutput,
  AuditState,
  AuditOptions,
} from '../types.js';
import type { FilesystemStore } from '../store/filesystem.js';
import type { SubscriptionStore } from '../store/subscriptions.js';
import type { StateMachine } from '../orchestrator/state-machine.js';
import type { LLMClient } from '../llm/client.js';
import type { RunnerConfig } from '../orchestrator/runner.js';
import { runAudit } from '../orchestrator/runner.js';
import { makeAuditId, slugify } from '../orchestrator/state-machine.js';
import { getDeltaReport } from './get-delta-report.js';
import { dispatchNotifications } from '../notify/dispatch.js';

const DEFAULT_PANEL = 'default';

export async function triggerEvolution(
  input: TriggerEvolutionInput,
  store: FilesystemStore,
  subStore: SubscriptionStore,
  sm: StateMachine,
  runnerConfig: RunnerConfig,
  client: LLMClient,
  log: (level: string, msg: string) => void,
): Promise<TriggerEvolutionOutput> {
  const brand_slug = slugify(input.brand);

  // Find active subscription to get panel and cadence
  const subs = await subStore.findByBrand(brand_slug);
  const sub = subs[0]; // use first active subscription

  const panel = sub?.panel ?? DEFAULT_PANEL;
  const minIntervalDays = sub?.cadence.min_interval_days ?? 7;

  // Cadence guard (unless force=true)
  if (!input.force && sub?.last_triggered_at) {
    const lastMs = new Date(sub.last_triggered_at).getTime();
    const elapsedDays = (Date.now() - lastMs) / (1000 * 60 * 60 * 24);
    if (elapsedDays < minIntervalDays) {
      const nextAt = new Date(lastMs + minIntervalDays * 86_400_000).toISOString().slice(0, 10);
      return {
        audit_id: '',
        phase: 'proposed',
        message: `Cadence guard: next evolution allowed after ${nextAt}`,
        skipped: true,
        skip_reason: `min_interval_days=${minIntervalDays}, last triggered ${Math.floor(elapsedDays)} days ago`,
      };
    }
  }

  // Monthly cap guard
  if (!input.force && sub) {
    const monthReset = new Date(sub.month_reset_at);
    const now = new Date();
    const isNewMonth =
      now.getUTCFullYear() > monthReset.getUTCFullYear() ||
      now.getUTCMonth() > monthReset.getUTCMonth();

    let count = sub.trigger_count_this_month;
    if (isNewMonth) {
      count = 0;
    }

    if (count >= sub.cadence.max_per_month) {
      return {
        audit_id: '',
        phase: 'proposed',
        message: `Monthly cap reached: ${count}/${sub.cadence.max_per_month} triggers used this month`,
        skipped: true,
        skip_reason: `max_per_month=${sub.cadence.max_per_month}`,
      };
    }
  }

  // Find the most recent completed audit for this brand to link as previous
  const allIds = await store.listAudits();
  let previousAuditId: string | undefined;
  let latestDoneAt = '';

  for (const id of allIds) {
    const s = await store.readState(id);
    if (s && s.brand_slug === brand_slug && s.phase === 'done' && s.started_at > latestDoneAt) {
      previousAuditId = s.audit_id;
      latestDoneAt = s.started_at;
    }
  }

  // Create EVOLUTION audit state
  const audit_id = makeAuditId(brand_slug);
  const evolutionContext = input.event_summary
    ? `${input.event_type ?? 'event'}: ${input.event_summary}${input.source_url ? ` (${input.source_url})` : ''}`
    : undefined;
  const options: AuditOptions = {
    skip_wuying: false,
    language: 'auto',
    previous_audit_id: previousAuditId,
    ...(evolutionContext ? { evolution_context: evolutionContext } : {}),
  };

  const state: AuditState = {
    audit_id,
    brand: input.brand,
    brand_slug,
    panel,
    mode: 'evolution',
    phase: 'proposed',
    started_at: new Date().toISOString(),
    last_progress_at: new Date().toISOString(),
    completed_phases: [],
    failed_phases: [],
    errors: [],
    tokens_used: { input: 0, output: 0 },
    options,
  };

  await store.initAudit(state);
  const next = await sm.transition(state, 'researching');

  // Update subscription counters
  if (sub) {
    const now = new Date();
    const monthReset = new Date(sub.month_reset_at);
    const isNewMonth =
      now.getUTCFullYear() > monthReset.getUTCFullYear() ||
      now.getUTCMonth() > monthReset.getUTCMonth();

    sub.last_triggered_at = now.toISOString();
    sub.last_audit_id = audit_id;
    sub.trigger_count_this_month = isNewMonth ? 1 : sub.trigger_count_this_month + 1;
    if (isNewMonth) {
      sub.month_reset_at = new Date(now.getUTCFullYear(), now.getUTCMonth(), 1).toISOString();
    }
    await subStore.write(sub);
  }

  const eventDesc = input.event_summary
    ? ` (${input.event_type ?? 'event'}: ${input.event_summary.slice(0, 80)})`
    : '';
  log('info', `[${audit_id}] Evolution triggered for ${input.brand}${eventDesc}`);

  // On completion: compute delta vs baseline and push notifications to the
  // subscription's notify targets (best-effort — hook errors don't fail the audit).
  const notifyTargets = sub?.notify ?? [];
  const onComplete = async (finalState: AuditState): Promise<void> => {
    if (notifyTargets.length === 0) return;

    let summary = `${finalState.brand}: evolution audit ${finalState.audit_id} complete`;
    let overall_delta: number | undefined;
    let previous_audit_id: string | undefined = previousAuditId;
    let delta_markdown: string | undefined;

    if (previousAuditId) {
      try {
        const delta = await getDeltaReport(
          { audit_id: finalState.audit_id, previous_audit_id: previousAuditId, narrative: true },
          store,
          client,
          log,
        );
        overall_delta = delta.overall_delta;
        previous_audit_id = delta.previous_audit_id;
        delta_markdown = delta.delta_markdown;
        summary = `${finalState.brand}: overall ${delta.overall_delta >= 0 ? '+' : ''}${delta.overall_delta} vs ${delta.previous_audit_id}`;
      } catch (err) {
        log('warn', `[${finalState.audit_id}] delta computation failed, notifying without delta: ${err}`);
      }
    }

    await dispatchNotifications(
      notifyTargets,
      {
        event: 'mba.evolution.done',
        brand: finalState.brand,
        audit_id: finalState.audit_id,
        previous_audit_id,
        overall_delta,
        summary,
        delta_markdown,
      },
      log,
    );
  };

  // Fire-and-forget
  runAudit(next, store, sm, runnerConfig, client, log, onComplete).catch(err => {
    log('error', `Evolution runner crashed for ${audit_id}: ${err}`);
  });

  return {
    audit_id,
    phase: 'researching',
    message: `Evolution audit started for ${input.brand}. Previous baseline: ${previousAuditId ?? 'none (first run)'}. Poll get_status for progress.`,
  };
}
