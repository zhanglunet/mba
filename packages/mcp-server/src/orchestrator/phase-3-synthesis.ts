import type { AuditState } from '../types.js';
import type { FilesystemStore } from '../store/filesystem.js';
import type { LLMClient } from '../llm/client.js';
import { synthesisSystemPrompt, synthesisUserPrompt } from '../llm/prompts.js';

export interface SynthesisResult {
  synthesis: string;
  input_tokens: number;
  output_tokens: number;
}

export async function runPhase3Synthesis(
  state: AuditState,
  dimensionOutputs: Record<string, string>,
  store: FilesystemStore,
  client: LLMClient,
  log: (level: string, msg: string) => void,
): Promise<SynthesisResult> {
  log('info', `[${state.audit_id}] Phase 3: synthesizing ${Object.keys(dimensionOutputs).length} dimensions`);

  const result = await client.complete(
    synthesisSystemPrompt(),
    synthesisUserPrompt(state.brand, dimensionOutputs),
    4096,
  );

  const header = `# MBA Synthesis — ${state.brand}\n\n**Audit ID:** ${state.audit_id}  \n**Panel:** ${state.panel}  \n**Generated:** ${new Date().toISOString()}\n\n---\n\n`;
  const content = header + result.content;

  await store.writeFile(state.audit_id, '_raw/synthesis.md', content);

  return {
    synthesis: result.content,
    input_tokens: result.input_tokens,
    output_tokens: result.output_tokens,
  };
}
