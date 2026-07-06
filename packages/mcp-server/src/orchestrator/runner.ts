import type { AuditState } from '../types.js';
import type { FilesystemStore } from '../store/filesystem.js';
import type { StateMachine } from './state-machine.js';
import type { LLMClient } from '../llm/client.js';
import { runPhase2Research } from './phase-2-research.js';
import { runPhase2Evolution } from './phase-2-evolution.js';
import { runPhase3Synthesis } from './phase-3-synthesis.js';
import { runPhase4Judging } from './phase-4-judging.js';
import { runPhase5Merge } from './phase-5-merge.js';

export interface RunnerConfig {
  maxParallel: number;
  maxCostUsd?: number;
  judgesDir: string;
}

// Cost estimates per token (USD) — Sonnet pricing as of 2026
const INPUT_COST_PER_TOKEN = 3 / 1_000_000;
const OUTPUT_COST_PER_TOKEN = 15 / 1_000_000;

function estimateCostUsd(inputTokens: number, outputTokens: number): number {
  return inputTokens * INPUT_COST_PER_TOKEN + outputTokens * OUTPUT_COST_PER_TOKEN;
}

// Rank of each work phase in the pipeline. `runAudit` enters at `state.phase`;
// on a normal run that's `researching` (rank 1) and every phase executes. On a
// resume it's a later phase — earlier phases are skipped and their persisted
// artifacts are reloaded from disk instead.
const PHASE_RANK: Record<string, number> = {
  researching: 1,
  synthesizing: 2,
  judging: 3,
  merging: 4,
};

// ── Resume artifact loaders ────────────────────────────────────────────────────
// Reconstruct a completed phase's in-memory outputs from what it wrote to disk,
// so a resume can pick up without re-running (and re-paying for) that phase.

export async function loadResearchOutputs(
  store: FilesystemStore,
  auditId: string,
): Promise<Record<string, string>> {
  const files = await store.listFiles(auditId, '_raw');
  const outputs: Record<string, string> = {};
  for (const f of files) {
    const m = /^dimension_\d+_(.+)\.md$/.exec(f);
    if (!m) continue; // skip synthesis.md, evolution_probes.md, etc.
    const content = await store.readFile(auditId, `_raw/${f}`);
    if (content !== null) outputs[m[1]] = content;
  }
  return outputs;
}

export async function loadSynthesis(store: FilesystemStore, auditId: string): Promise<string> {
  const synthesis = await store.readFile(auditId, '_raw/synthesis.md');
  if (synthesis === null) {
    throw new Error('RESUME_MISSING_ARTIFACT: _raw/synthesis.md not found');
  }
  return synthesis;
}

export async function loadReviews(
  store: FilesystemStore,
  auditId: string,
): Promise<Record<string, string>> {
  const files = await store.listFiles(auditId, 'reviews');
  const reviews: Record<string, string> = {};
  for (const f of files) {
    if (!f.endsWith('.md')) continue;
    const content = await store.readFile(auditId, `reviews/${f}`);
    if (content !== null) reviews[f.slice(0, -3)] = content;
  }
  return reviews;
}

export async function runAudit(
  state: AuditState,
  store: FilesystemStore,
  sm: StateMachine,
  config: RunnerConfig,
  client: LLMClient,
  log: (level: string, msg: string) => void,
  onComplete?: (finalState: AuditState) => Promise<void>,
): Promise<void> {
  const id = state.audit_id;
  let totalInputTokens = 0;
  let totalOutputTokens = 0;

  function checkCostLimit(inputTokens: number, outputTokens: number): void {
    totalInputTokens += inputTokens;
    totalOutputTokens += outputTokens;
    if (config.maxCostUsd !== undefined) {
      const costSoFar = estimateCostUsd(totalInputTokens, totalOutputTokens);
      if (costSoFar > config.maxCostUsd) {
        throw new Error(
          `COST_LIMIT_EXCEEDED: estimated cost $${costSoFar.toFixed(4)} exceeds limit $${config.maxCostUsd}`,
        );
      }
    }
  }

  // Where to enter the pipeline. Normal run: 'researching' (rank 1 → run all).
  // Resume: a later phase, whose predecessors are reloaded from disk below.
  const entryRank = PHASE_RANK[state.phase] ?? 1;

  try {
    let researchOutputs: Record<string, string> | undefined;
    let synthesis: string | undefined;
    let reviews: Record<string, string> | undefined;

    // Resuming past a phase → reload its persisted outputs instead of re-running.
    if (entryRank > 1) {
      researchOutputs = await loadResearchOutputs(store, id);
      log('info', `[${id}] resume: reloaded ${Object.keys(researchOutputs).length} research dimensions from disk`);
    }
    if (entryRank > 2) synthesis = await loadSynthesis(store, id);
    if (entryRank > 3) reviews = await loadReviews(store, id);

    // ── Phase 2: Research ───────────────────────────────────────────────────
    // EVOLUTION mode with a baseline → incremental probe-then-rerun (cheaper).
    // Otherwise → full fresh research of all dimensions.
    if (entryRank <= 1) {
      const previousAuditId = state.options.previous_audit_id;
      const phase2 =
        state.mode === 'evolution' && previousAuditId
          ? await runPhase2Evolution(state, previousAuditId, store, client, config.maxParallel, log)
          : await runPhase2Research(state, store, client, config.maxParallel, log);
      checkCostLimit(phase2.total_input_tokens, phase2.total_output_tokens);
      researchOutputs = phase2.outputs;
      state = await sm.transition(state, 'synthesizing');
    }

    // ── Phase 3: Synthesis ──────────────────────────────────────────────────
    if (entryRank <= 2) {
      const phase3 = await runPhase3Synthesis(state, researchOutputs!, store, client, log);
      checkCostLimit(phase3.input_tokens, phase3.output_tokens);
      synthesis = phase3.synthesis;
      state = await sm.transition(state, 'judging');
    }

    // ── Phase 4: Judging ────────────────────────────────────────────────────
    if (entryRank <= 3) {
      const phase4 = await runPhase4Judging(
        state,
        synthesis!,
        store,
        client,
        config.judgesDir,
        log,
      );
      checkCostLimit(phase4.total_input_tokens, phase4.total_output_tokens);
      reviews = phase4.reviews;
      state = await sm.transition(state, 'merging');
    }

    // ── Phase 5: Merge ──────────────────────────────────────────────────────
    const phase5 = await runPhase5Merge(state, synthesis!, reviews!, store, client, log);
    checkCostLimit(phase5.input_tokens, phase5.output_tokens);

    // Persist token totals before marking done
    const finalState = await store.readState(id);
    if (finalState) {
      finalState.tokens_used = { input: totalInputTokens, output: totalOutputTokens };
      await store.writeState(finalState);
      state = finalState;
    }

    await sm.transition(state, 'done');
    log('info', `[${id}] Audit complete — report.md written`);

    // Post-completion hook (e.g. delta computation + notifications). Best-effort.
    if (onComplete) {
      try {
        await onComplete(state);
      } catch (hookErr) {
        log('error', `[${id}] onComplete hook failed: ${hookErr}`);
      }
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    log('error', `[${id}] Audit failed: ${msg}`);

    try {
      const failedState = await store.readState(id);
      if (failedState && failedState.phase !== 'done') {
        const withError = { ...failedState, error: msg };
        await sm.transition(withError, 'failed');
      }
    } catch (innerErr) {
      log('error', `[${id}] Could not write failed state: ${innerErr}`);
    }
  }
}
