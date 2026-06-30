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
