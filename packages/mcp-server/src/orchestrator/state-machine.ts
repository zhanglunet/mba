import type { AuditState, AuditPhase, AuditError } from '../types.js';
import type { FilesystemStore } from '../store/filesystem.js';

const VALID_TRANSITIONS: Record<AuditPhase, AuditPhase[]> = {
  proposed:     ['researching', 'failed'],
  researching:  ['synthesizing', 'failed', 'interrupted'],
  synthesizing: ['judging', 'failed', 'interrupted'],
  judging:      ['merging', 'failed', 'interrupted'],
  merging:      ['done', 'failed', 'interrupted'],
  done:         [],
  failed:       [],
  interrupted:  ['researching'],
};

const PHASE_PROGRESS: Record<AuditPhase, number> = {
  proposed:     5,
  researching:  25,
  synthesizing: 50,
  judging:      75,
  merging:      90,
  done:         100,
  failed:       0,
  interrupted:  0,
};

export class StateMachine {
  constructor(
    private readonly store: FilesystemStore,
    private readonly log: (level: string, msg: string) => void,
  ) {}

  async transition(
    state: AuditState,
    to: AuditPhase,
    opts: { error?: AuditError } = {},
  ): Promise<AuditState> {
    const allowed = VALID_TRANSITIONS[state.phase];
    if (!allowed.includes(to)) {
      throw new Error(
        `Invalid transition ${state.phase} → ${to} for audit ${state.audit_id}`,
      );
    }

    const now = new Date().toISOString();
    const next: AuditState = {
      ...state,
      phase: to,
      last_progress_at: now,
      completed_phases:
        to !== 'failed' && to !== 'interrupted'
          ? [...state.completed_phases, state.phase]
          : state.completed_phases,
      failed_phases:
        to === 'failed'
          ? [...state.failed_phases, state.phase]
          : state.failed_phases,
      errors: opts.error ? [...state.errors, opts.error] : state.errors,
    };

    await this.store.writeState(next);
    this.log('info', `[${state.audit_id}] ${state.phase} → ${to}`);
    return next;
  }

  progressPct(phase: AuditPhase): number {
    return PHASE_PROGRESS[phase];
  }

  canResume(state: AuditState): boolean {
    return state.phase === 'interrupted';
  }

  // ── Resume support ─────────────────────────────────────────────────────────
  // A stalled audit (process died mid-run, an error, or an explicit interrupt)
  // can be resumed. It is resumable in any non-terminal *work* phase, plus the
  // 'interrupted' and 'failed' terminal-ish states. 'proposed' (never started)
  // and 'done' (finished) are not resumable.
  private static readonly RESUMABLE: AuditPhase[] = [
    'researching',
    'synthesizing',
    'judging',
    'merging',
    'interrupted',
    'failed',
  ];

  private static readonly WORK_PHASES: AuditPhase[] = [
    'researching',
    'synthesizing',
    'judging',
    'merging',
  ];

  isResumable(state: AuditState): boolean {
    return StateMachine.RESUMABLE.includes(state.phase);
  }

  // The work phase to resume execution from: the first one that never completed.
  // `completed_phases` only records phases the audit transitioned *out* of, so a
  // phase listed there wrote its artifacts to disk and can be reloaded instead of
  // re-run. Falls back to 'merging' if all four somehow completed without 'done'.
  resumePhase(state: AuditState): AuditPhase {
    for (const p of StateMachine.WORK_PHASES) {
      if (!state.completed_phases.includes(p)) return p;
    }
    return 'merging';
  }

  // Re-enter a work phase for a resume. Unlike `transition`, this bypasses the
  // forward-only transition table (we're stepping back into an in-progress phase)
  // and does not touch `completed_phases` — no phase is being completed here.
  async resumeInto(state: AuditState, to: AuditPhase): Promise<AuditState> {
    const next: AuditState = {
      ...state,
      phase: to,
      last_progress_at: new Date().toISOString(),
    };
    await this.store.writeState(next);
    this.log('info', `[${state.audit_id}] resume → ${to}`);
    return next;
  }
}

export function makeAuditId(brandSlug: string): string {
  const now = new Date();
  const date = now.toISOString().slice(0, 10).replace(/-/g, '');
  const time = now.toTimeString().slice(0, 5).replace(':', '');
  return `${brandSlug}-${date}-${time}`;
}

export function slugify(brand: string): string {
  return brand
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 50);
}
