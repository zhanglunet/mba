import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import type { AuditState, AuditScores } from '../../src/types.js';
import type { FilesystemStore } from '../../src/store/filesystem.js';
import type { LLMClient } from '../../src/llm/client.js';
import { runPhase4Judging } from '../../src/orchestrator/phase-4-judging.js';

const PARSEABLE_REVIEW = [
  '## Scores',
  '- Origin authenticity: 8',
  '- Category coinage: 7',
  '- Leverage quality: 6',
  '- Identity coherence: 7',
  '- Real-world signal: 9',
  '',
  'Verdict: solid.',
].join('\n');

function makeState(overrides: Partial<AuditState> = {}): AuditState {
  return {
    audit_id: 'anthropic-x',
    brand: 'Anthropic',
    brand_slug: 'anthropic',
    panel: 'default',
    mode: 'fresh',
    phase: 'judging',
    started_at: '2026-07-10T00:00:00Z',
    last_progress_at: '2026-07-10T00:00:00Z',
    completed_phases: [],
    failed_phases: [],
    errors: [],
    tokens_used: { input: 0, output: 0 },
    options: { skip_wuying: false, language: 'auto' },
    ...overrides,
  };
}

function makeStore(): FilesystemStore & { written: Record<string, string> } {
  const written: Record<string, string> = {};
  return {
    written,
    writeFile: vi.fn().mockImplementation((id: string, path: string, content: string) => {
      written[`${id}/${path}`] = content;
      return Promise.resolve();
    }),
    readFile: vi.fn().mockResolvedValue(null),
    readState: vi.fn().mockResolvedValue(null),
    writeState: vi.fn().mockResolvedValue(undefined),
    listFiles: vi.fn().mockResolvedValue([]),
    listAudits: vi.fn().mockResolvedValue([]),
    initAudit: vi.fn().mockResolvedValue(undefined),
    exists: vi.fn().mockResolvedValue(false),
  } as unknown as FilesystemStore & { written: Record<string, string> };
}

/** Client that returns a parseable review for every judge. */
function makeClient(content = PARSEABLE_REVIEW) {
  const complete = vi.fn().mockResolvedValue({ content, input_tokens: 300, output_tokens: 200 });
  return { model: 'claude-sonnet-4-6', complete } as unknown as LLMClient & {
    complete: ReturnType<typeof vi.fn>;
  };
}

const noop = () => {};
const NO_CUSTOM = '/tmp/mba-nonexistent-custom-judges-dir';

describe('runPhase4Judging', () => {
  it('scores the default 5-judge panel and writes one review file each', async () => {
    const state = makeState();
    const store = makeStore();
    const client = makeClient();

    const result = await runPhase4Judging(state, 'SYNTH', store, client, NO_CUSTOM, noop);

    expect(client.complete).toHaveBeenCalledTimes(5);
    expect(Object.keys(result.reviews).sort()).toEqual(
      ['fusheng', 'jobs', 'likejia', 'wu-jundong', 'zhang-yiming'].sort(),
    );
    for (const slug of ['fusheng', 'jobs', 'likejia', 'wu-jundong', 'zhang-yiming']) {
      expect(store.written[`anthropic-x/reviews/${slug}.md`]).toContain('# Judge Review');
    }
    // tokens summed across all 5
    expect(result.total_input_tokens).toBe(5 * 300);
    expect(result.total_output_tokens).toBe(5 * 200);
  });

  it('honors an explicit judge list from options.judges', async () => {
    const state = makeState({ options: { skip_wuying: false, language: 'auto', judges: ['jobs', 'naval'] } });
    const store = makeStore();
    const client = makeClient();

    const result = await runPhase4Judging(state, 'SYNTH', store, client, NO_CUSTOM, noop);
    expect(client.complete).toHaveBeenCalledTimes(2);
    expect(Object.keys(result.reviews).sort()).toEqual(['jobs', 'naval']);
  });

  it('tolerates a single judge failure (allSettled) and keeps the survivors', async () => {
    const state = makeState();
    const store = makeStore();
    let calls = 0;
    const complete = vi.fn().mockImplementation(() => {
      calls += 1;
      if (calls === 2) return Promise.reject(new Error('boom'));
      return Promise.resolve({ content: PARSEABLE_REVIEW, input_tokens: 300, output_tokens: 200 });
    });
    const client = { model: 'm', complete } as unknown as LLMClient;

    const result = await runPhase4Judging(state, 'SYNTH', store, client, NO_CUSTOM, noop);
    expect(Object.keys(result.reviews)).toHaveLength(4); // 5 - 1 failed
    expect(result.total_input_tokens).toBe(4 * 300); // failed judge not counted
  });

  it('throws JUDGING_FAILED when every judge fails', async () => {
    const state = makeState();
    const store = makeStore();
    const client = {
      model: 'm',
      complete: vi.fn().mockRejectedValue(new Error('all down')),
    } as unknown as LLMClient;

    await expect(runPhase4Judging(state, 'SYNTH', store, client, NO_CUSTOM, noop)).rejects.toThrow(
      /JUDGING_FAILED/,
    );
  });

  it('parses reviews into a structured scores.json with per-lens means', async () => {
    const state = makeState({ options: { skip_wuying: false, language: 'auto', judges: ['jobs', 'naval'] } });
    const store = makeStore();
    await runPhase4Judging(state, 'SYNTH', store, makeClient(), NO_CUSTOM, noop);

    const raw = store.written['anthropic-x/scores.json'];
    expect(raw).toBeDefined();
    const scores = JSON.parse(raw!) as AuditScores;
    expect(scores.judges).toHaveLength(2);
    expect(scores.means.origin).toBe(8);
    expect(scores.means.signal).toBe(9);
    // total per judge = 8+7+6+7+9 = 37
    expect(scores.overall_mean).toBe(37);
  });

  it('skips scores.json when no review is machine-parseable', async () => {
    const state = makeState({ options: { skip_wuying: false, language: 'auto', judges: ['jobs'] } });
    const store = makeStore();
    await runPhase4Judging(state, 'SYNTH', store, makeClient('no numbers here at all'), NO_CUSTOM, noop);
    expect(store.written['anthropic-x/scores.json']).toBeUndefined();
    // but the (unparseable) review is still persisted
    expect(store.written['anthropic-x/reviews/jobs.md']).toBeDefined();
  });

  describe('custom personas', () => {
    let customDir: string;
    beforeEach(async () => {
      customDir = await mkdtemp(join(tmpdir(), 'mba-judges-'));
    });
    afterEach(async () => {
      await rm(customDir, { recursive: true, force: true });
    });

    it('loads a custom persona file and embeds it in the judge system prompt', async () => {
      await writeFile(join(customDir, 'custom-judge.md'), 'SENTINEL_PERSONA_DNA', 'utf-8');
      const state = makeState({
        options: { skip_wuying: false, language: 'auto', judges: ['custom-judge'] },
      });
      const store = makeStore();
      const client = makeClient();

      const result = await runPhase4Judging(state, 'SYNTH', store, client, customDir, noop);

      expect(Object.keys(result.reviews)).toEqual(['custom-judge']);
      const systemPrompt = client.complete.mock.calls[0]?.[0] as string;
      expect(systemPrompt).toContain('SENTINEL_PERSONA_DNA');
    });
  });
});
