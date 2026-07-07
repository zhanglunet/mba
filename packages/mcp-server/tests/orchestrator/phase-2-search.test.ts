import { describe, it, expect, vi } from 'vitest';
import type { AuditState } from '../../src/types.js';
import type { FilesystemStore } from '../../src/store/filesystem.js';
import type { LLMClient } from '../../src/llm/client.js';
import { runPhase2Research } from '../../src/orchestrator/phase-2-research.js';

function makeState(): AuditState {
  return {
    audit_id: 'acme-1',
    brand: 'Acme',
    brand_slug: 'acme',
    panel: 'default',
    mode: 'fresh',
    phase: 'researching',
    started_at: '2026-01-01T00:00:00Z',
    last_progress_at: '2026-01-01T00:00:00Z',
    completed_phases: [],
    failed_phases: [],
    errors: [],
    tokens_used: { input: 0, output: 0 },
    options: { skip_wuying: false, language: 'auto' },
  };
}

describe('runPhase2Research web search opt-in', () => {
  it('requests { search: true } on every dimension research call', async () => {
    const complete = vi.fn().mockResolvedValue({ content: 'note', input_tokens: 1, output_tokens: 1 });
    const client = { model: 'claude-sonnet-4-6', complete } as unknown as LLMClient;
    const store = { writeFile: vi.fn().mockResolvedValue(undefined) } as unknown as FilesystemStore;

    await runPhase2Research(makeState(), store, client, 5, () => {});

    expect(complete).toHaveBeenCalled();
    // Every call passes the opt-in options object as the 4th argument.
    for (const call of complete.mock.calls) {
      expect(call[3]).toEqual({ search: true });
    }
  });
});
