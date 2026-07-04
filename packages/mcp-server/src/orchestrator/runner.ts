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

  try {
    // ── Phase 2: Research ───────────────────────────────────────────────────
    // EVOLUTION mode with a baseline → incremental probe-then-rerun (cheaper).
    // Otherwise → full fresh research of all dimensions.
    const previousAuditId = state.options.previous_audit_id;
    const phase2 =
      state.mode === 'evolution' && previousAuditId
        ? await runPhase2Evolution(state, previousAuditId, store, client, config.maxParallel, log)
        : await runPhase2Research(state, store, client, config.maxParallel, log);
    checkCostLimit(phase2.total_input_tokens, phase2.total_output_tokens);

    state = await sm.transition(state, 'synthesizing');

    // ── Phase 3: Synthesis ──────────────────────────────────────────────────
    const phase3 = await runPhase3Synthesis(state, phase2.outputs, store, client, log);
    checkCostLimit(phase3.input_tokens, phase3.output_tokens);

    state = await sm.transition(state, 'judging');

    // ── Phase 4: Judging ────────────────────────────────────────────────────
    const phase4 = await runPhase4Judging(
      state,
      phase3.synthesis,
      store,
      client,
      config.judgesDir,
      log,
    );
    checkCostLimit(phase4.total_input_tokens, phase4.total_output_tokens);

    state = await sm.transition(state, 'merging');

    // ── Phase 5: Merge ──────────────────────────────────────────────────────
    const phase5 = await runPhase5Merge(state, phase3.synthesis, phase4.reviews, store, client, log);
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
