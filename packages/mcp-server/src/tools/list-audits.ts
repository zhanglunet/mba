import type { ListAuditsOutput } from '../types.js';
import type { FilesystemStore } from '../store/filesystem.js';

export async function listAudits(store: FilesystemStore): Promise<ListAuditsOutput> {
  const ids = await store.listAudits();
  const audits = await Promise.all(
    ids.map(async id => {
      const state = await store.readState(id);
      if (!state) return null;
      return {
        audit_id: state.audit_id,
        brand: state.brand,
        phase: state.phase,
        started_at: state.started_at,
        last_progress_at: state.last_progress_at,
      };
    }),
  );

  return {
    audits: audits
      .filter((a): a is NonNullable<typeof a> => a !== null)
      .sort((a, b) => b.started_at.localeCompare(a.started_at)),
  };
}
