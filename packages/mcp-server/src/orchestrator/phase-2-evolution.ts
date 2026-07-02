import type { AuditState } from '../types.js';
import type { FilesystemStore } from '../store/filesystem.js';
import type { LLMClient } from '../llm/client.js';
import {
  DIMENSIONS,
  dimensionSystemPrompt,
  dimensionUserPrompt,
  changeProbeSystemPrompt,
  changeProbeUserPrompt,
} from '../llm/prompts.js';
import type { ResearchResult } from './phase-2-research.js';

export interface ProbeResult {
  slug: string;
  verdict: 'CHANGED' | 'UNCHANGED';
  reason: string;
  reused: boolean;
}

export interface EvolutionResearchResult extends ResearchResult {
  probes: ProbeResult[];
  dimensions_rerun: number;
  dimensions_reused: number;
}

function parseVerdict(content: string): { verdict: 'CHANGED' | 'UNCHANGED'; reason: string } {
  const verdictMatch = content.match(/VERDICT:\s*(CHANGED|UNCHANGED)/i);
  const reasonMatch = content.match(/REASON:\s*(.+)/i);
  // Default to CHANGED on parse failure — re-research is safer than stale data
  const verdict = (verdictMatch?.[1]?.toUpperCase() as 'CHANGED' | 'UNCHANGED') ?? 'CHANGED';
  const reason = reasonMatch?.[1]?.trim() ?? '(unparseable probe response — defaulting to CHANGED)';
  return { verdict, reason };
}

/**
 * EVOLUTION-mode Phase 2: probe each dimension against the previous audit's
 * research, and only re-run the ones that materially changed. Unchanged
 * dimensions reuse the previous research output verbatim.
 *
 * Cost: ~7 cheap probes + a few full re-runs, vs. 7 full re-runs for a fresh audit.
 */
export async function runPhase2Evolution(
  state: AuditState,
  previousAuditId: string,
  store: FilesystemStore,
  client: LLMClient,
  maxParallel: number,
  log: (level: string, msg: string) => void,
): Promise<EvolutionResearchResult> {
  const dims = state.options.focus_dimensions
    ? DIMENSIONS.filter(
        d =>
          state.options.focus_dimensions!.includes(d.slug) ||
          state.options.focus_dimensions!.includes(d.title),
      )
    : DIMENSIONS;

  const eventContext = state.options.evolution_context;
  const probeSystem = changeProbeSystemPrompt();
  const researchSystem = dimensionSystemPrompt();

  let total_input_tokens = 0;
  let total_output_tokens = 0;
  const outputs: Record<string, string> = {};
  const probes: ProbeResult[] = [];

  log(
    'info',
    `[${state.audit_id}] Phase 2E: evolution probe of ${dims.length} dimensions vs baseline ${previousAuditId}`,
  );

  for (let i = 0; i < dims.length; i += maxParallel) {
    const batch = dims.slice(i, i + maxParallel);

    const results = await Promise.allSettled(
      batch.map(async dim => {
        const dimIndex = DIMENSIONS.indexOf(dim) + 1;
        const relPath = `_raw/dimension_${dimIndex}_${dim.slug}.md`;

        // Load previous research for this dimension
        const previous = await store.readFile(previousAuditId, relPath);

        // No previous research → must do full research (treat as CHANGED)
        if (!previous) {
          const userPrompt = dimensionUserPrompt(state.brand, dim);
          const res = await client.complete(researchSystem, userPrompt, 2048);
          const content = `# ${dim.title} / ${dim.title_en}\n\n${res.content}`;
          await store.writeFile(state.audit_id, relPath, content);
          return {
            slug: dim.slug,
            content: res.content,
            input_tokens: res.input_tokens,
            output_tokens: res.output_tokens,
            probe: { slug: dim.slug, verdict: 'CHANGED' as const, reason: 'no baseline research found', reused: false },
          };
        }

        // Run the cheap change probe
        const probeRes = await client.complete(
          probeSystem,
          changeProbeUserPrompt(state.brand, dim, previous, eventContext),
          256,
        );
        const { verdict, reason } = parseVerdict(probeRes.content);

        let dimInput = probeRes.input_tokens;
        let dimOutput = probeRes.output_tokens;
        let content: string;
        let reused: boolean;

        if (verdict === 'CHANGED') {
          // Full re-research
          const userPrompt = dimensionUserPrompt(state.brand, dim);
          const res = await client.complete(researchSystem, userPrompt, 2048);
          content = res.content;
          dimInput += res.input_tokens;
          dimOutput += res.output_tokens;
          const written = `# ${dim.title} / ${dim.title_en}\n\n${res.content}`;
          await store.writeFile(state.audit_id, relPath, written);
          reused = false;
        } else {
          // Reuse previous research verbatim (strip the header for the outputs map)
          content = previous.replace(/^#[^\n]*\n\n/, '');
          await store.writeFile(state.audit_id, relPath, previous);
          reused = true;
        }

        return {
          slug: dim.slug,
          content,
          input_tokens: dimInput,
          output_tokens: dimOutput,
          probe: { slug: dim.slug, verdict, reason, reused },
        };
      }),
    );

    for (const r of results) {
      if (r.status === 'fulfilled') {
        outputs[r.value.slug] = r.value.content;
        total_input_tokens += r.value.input_tokens;
        total_output_tokens += r.value.output_tokens;
        probes.push(r.value.probe);
      } else {
        log('warn', `[${state.audit_id}] Evolution probe/research failed: ${r.reason}`);
      }
    }
  }

  const dimensions_rerun = probes.filter(p => !p.reused).length;
  const dimensions_reused = probes.filter(p => p.reused).length;

  log(
    'info',
    `[${state.audit_id}] Phase 2E complete: ${dimensions_rerun} re-run, ${dimensions_reused} reused`,
  );

  // Persist a probe summary for transparency
  const probeSummary =
    `# Evolution Probe Summary — ${state.brand}\n\n` +
    `**Baseline:** ${previousAuditId}\n` +
    `**Re-run:** ${dimensions_rerun} · **Reused:** ${dimensions_reused}\n\n` +
    probes
      .map(p => `- **${p.slug}**: ${p.verdict}${p.reused ? ' (reused)' : ' (re-researched)'} — ${p.reason}`)
      .join('\n') +
    '\n';
  await store.writeFile(state.audit_id, '_raw/evolution_probes.md', probeSummary);

  return {
    outputs,
    total_input_tokens,
    total_output_tokens,
    probes,
    dimensions_rerun,
    dimensions_reused,
  };
}
