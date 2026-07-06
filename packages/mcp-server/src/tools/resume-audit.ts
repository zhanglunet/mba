import type { AuditState, ResumeAuditInput, ResumeAuditOutput } from '../types.js';
import type { FilesystemStore } from '../store/filesystem.js';
import type { StateMachine } from '../orchestrator/state-machine.js';

export interface ResumeAuditDeps {
  store: FilesystemStore;
  sm: StateMachine;
  hasApiKey: boolean;
  // Fire-and-forget kickoff of the (resume-aware) runner. Reads maxCostUsd from
  // the passed state's options, so the caller doesn't need to know it up front.
  run: (state: AuditState) => void;
}

/**
 * Resume a stalled audit — one whose process died mid-run, hit an error, or was
 * interrupted — without creating a new audit. It keeps the same `audit_id`,
 * proposal, panel, and options, reloads the artifacts of any completed phase
 * from disk, and re-enters the pipeline at the first phase that never finished.
 * Non-blocking: returns immediately; poll `get_status` for progress.
 */
export async function resumeAudit(
  input: ResumeAuditInput,
  deps: ResumeAuditDeps,
): Promise<ResumeAuditOutput> {
  const { store, sm } = deps;
  const state = await store.readState(input.audit_id);
  if (!state) throw new Error(`AUDIT_NOT_FOUND: ${input.audit_id}`);

  if (state.phase === 'done') {
    throw new Error('RESUME_NOT_APPLICABLE: audit is already done — use fetch_report');
  }
  if (state.phase === 'proposed') {
    throw new Error('RESUME_NOT_APPLICABLE: audit has not started — use confirm_audit');
  }
  if (!sm.isResumable(state)) {
    throw new Error(`RESUME_NOT_APPLICABLE: cannot resume from phase '${state.phase}'`);
  }
  if (!deps.hasApiKey) {
    throw new Error('MISSING_API_KEY: set ANTHROPIC_API_KEY env var');
  }

  if (input.max_cost_usd !== undefined) {
    state.options.max_cost_usd = input.max_cost_usd;
  }

  const resumedFrom = state.phase;
  const resumePoint = sm.resumePhase(state);
  const next = await sm.resumeInto(state, resumePoint);
  deps.run(next);

  return {
    audit_id: next.audit_id,
    phase: next.phase,
    resumed_from: resumedFrom,
    resume_point: resumePoint,
    message: `Resuming from ${resumePoint} (was '${resumedFrom}'). Poll get_status for progress.`,
  };
}
