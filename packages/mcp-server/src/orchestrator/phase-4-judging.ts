import type { AuditState, JudgeScores } from '../types.js';
import type { FilesystemStore } from '../store/filesystem.js';
import type { LLMClient } from '../llm/client.js';
import { judgeSystemPrompt, judgeUserPrompt } from '../llm/prompts.js';
import { parseJudgeScores, aggregateScores } from './scores.js';

const DEFAULT_JUDGES = ['fusheng', 'jobs', 'likejia', 'wu-jundong', 'zhang-yiming'];

export interface JudgingResult {
  reviews: Record<string, string>;
  total_input_tokens: number;
  total_output_tokens: number;
}

export async function runPhase4Judging(
  state: AuditState,
  synthesis: string,
  store: FilesystemStore,
  client: LLMClient,
  customJudgesDir: string,
  log: (level: string, msg: string) => void,
): Promise<JudgingResult> {
  const judges = state.options.judges ?? DEFAULT_JUDGES;
  log('info', `[${state.audit_id}] Phase 4: ${judges.length} judges scoring in parallel`);

  let total_input_tokens = 0;
  let total_output_tokens = 0;
  const reviews: Record<string, string> = {};

  const results = await Promise.allSettled(
    judges.map(async judgeSlug => {
      // Try loading custom persona first
      let personaMarkdown: string | undefined;
      const customPath = `${customJudgesDir}/${judgeSlug}.md`;
      try {
        const { readFile } = await import('node:fs/promises');
        personaMarkdown = await readFile(customPath, 'utf-8');
      } catch {
        // Fall back to built-in
      }

      const systemPrompt = judgeSystemPrompt(judgeSlug, personaMarkdown);
      const userPrompt = judgeUserPrompt(state.brand, synthesis, judgeSlug);
      const result = await client.complete(systemPrompt, userPrompt, 2048);

      const content = `# Judge Review — ${judgeSlug}\n\n**Brand:** ${state.brand}  \n**Audit ID:** ${state.audit_id}  \n**Generated:** ${new Date().toISOString()}\n\n---\n\n${result.content}`;
      await store.writeFile(state.audit_id, `reviews/${judgeSlug}.md`, content);

      return { slug: judgeSlug, ...result };
    }),
  );

  for (const r of results) {
    if (r.status === 'fulfilled') {
      reviews[r.value.slug] = r.value.content;
      total_input_tokens += r.value.input_tokens;
      total_output_tokens += r.value.output_tokens;
    } else {
      log('warn', `[${state.audit_id}] Judge scoring failed: ${r.reason}`);
    }
  }

  if (Object.keys(reviews).length === 0) {
    throw new Error('JUDGING_FAILED: all judges failed to score');
  }

  // Persist structured scores for delta/evolution comparisons
  const judgeScores: JudgeScores[] = [];
  for (const [slug, content] of Object.entries(reviews)) {
    const parsed = parseJudgeScores(slug, content);
    if (parsed) judgeScores.push(parsed);
    else log('warn', `[${state.audit_id}] Could not parse scores for judge '${slug}'`);
  }
  if (judgeScores.length > 0) {
    const auditScores = aggregateScores(
      state.audit_id,
      state.brand,
      new Date().toISOString(),
      judgeScores,
    );
    await store.writeFile(state.audit_id, 'scores.json', JSON.stringify(auditScores, null, 2));
  }

  return { reviews, total_input_tokens, total_output_tokens };
}
