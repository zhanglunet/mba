import type { GetStatusOutput } from '../types.js';
import type { FilesystemStore } from '../store/filesystem.js';
import { StateMachine } from '../orchestrator/state-machine.js';

export async function getStatus(
  auditId: string,
  store: FilesystemStore,
  sm: StateMachine,
): Promise<GetStatusOutput> {
  const state = await store.readState(auditId);
  if (!state) throw new Error(`AUDIT_NOT_FOUND: ${auditId}`);

  return {
    audit_id: state.audit_id,
    brand: state.brand,
    phase: state.phase,
    progress_pct: sm.progressPct(state.phase),
    started_at: state.started_at,
    last_progress_at: state.last_progress_at,
    completed_phases: state.completed_phases,
    errors: state.errors,
    tokens_used: state.tokens_used,
  };
}
