import type { FetchReportInput, FetchReportOutput } from '../types.js';
import type { FilesystemStore } from '../store/filesystem.js';

export async function fetchReport(
  input: FetchReportInput,
  store: FilesystemStore,
): Promise<FetchReportOutput> {
  const state = await store.readState(input.audit_id);
  if (!state) throw new Error(`AUDIT_NOT_FOUND: ${input.audit_id}`);
  if (state.phase !== 'done') {
    throw new Error(`AUDIT_NOT_DONE: audit is in phase '${state.phase}', not 'done'`);
  }

  const format = input.format ?? 'markdown';
  const result: FetchReportOutput = {
    version: 1,
    generated_at: state.last_progress_at,
  };

  if (format === 'markdown' || format === 'both') {
    const md = await store.readFile(input.audit_id, 'report.md');
    if (!md) throw new Error('REPORT_MISSING: report.md not found');
    result.markdown = md;
  }

  if (format === 'html' || format === 'both') {
    const html = await store.readFile(input.audit_id, 'report.html');
    if (!html) throw new Error('REPORT_MISSING: report.html not found');
    result.html = html;
  }

  return result;
}
