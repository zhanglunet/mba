import type { AuditState } from '../types.js';
import type { FilesystemStore } from '../store/filesystem.js';
import type { LLMClient } from '../llm/client.js';
import { DIMENSIONS, dimensionSystemPrompt, dimensionUserPrompt } from '../llm/prompts.js';

export interface ResearchResult {
  outputs: Record<string, string>;
  total_input_tokens: number;
  total_output_tokens: number;
}

export async function runPhase2Research(
  state: AuditState,
  store: FilesystemStore,
  client: LLMClient,
  maxParallel = 5,
  log: (level: string, msg: string) => void,
): Promise<ResearchResult> {
  const dims = state.options.focus_dimensions
    ? DIMENSIONS.filter(d => state.options.focus_dimensions!.includes(d.slug) || state.options.focus_dimensions!.includes(d.title))
    : DIMENSIONS;

  const systemPrompt = dimensionSystemPrompt();
  let total_input_tokens = 0;
  let total_output_tokens = 0;
  const outputs: Record<string, string> = {};

  // Process in batches of maxParallel
  for (let i = 0; i < dims.length; i += maxParallel) {
    const batch = dims.slice(i, i + maxParallel);
    log('info', `[${state.audit_id}] Phase 2: researching dimensions ${batch.map(d => d.slug).join(', ')}`);

    const results = await Promise.allSettled(
      batch.map(async dim => {
        const userPrompt = dimensionUserPrompt(state.brand, dim);
        const result = await client.complete(systemPrompt, userPrompt, 2048);

        const content = `# ${dim.title} / ${dim.title_en}\n\n${result.content}`;
        await store.writeFile(state.audit_id, `_raw/dimension_${DIMENSIONS.indexOf(dim) + 1}_${dim.slug}.md`, content);

        return { slug: dim.slug, ...result };
      }),
    );

    for (const r of results) {
      if (r.status === 'fulfilled') {
        outputs[r.value.slug] = r.value.content;
        total_input_tokens += r.value.input_tokens;
        total_output_tokens += r.value.output_tokens;
      } else {
        log('warn', `[${state.audit_id}] Dimension research failed: ${r.reason}`);
        // Mark as incomplete rather than failing the whole audit
        const failedDim = batch[results.indexOf(r)];
        if (failedDim) {
          outputs[failedDim.slug] = `[RESEARCH FAILED: ${r.reason}]`;
        }
      }
    }
  }

  return { outputs, total_input_tokens, total_output_tokens };
}
