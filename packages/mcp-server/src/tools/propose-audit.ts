import type { ProposeAuditInput, ProposeAuditOutput, AuditState, AuditOptions } from '../types.js';
import type { FilesystemStore } from '../store/filesystem.js';
import { makeAuditId, slugify } from '../orchestrator/state-machine.js';

const DEFAULT_JUDGES = ['fusheng', 'jobs', 'likejia', 'wu-jundong', 'zhang-yiming'];
const DEFAULT_DIMENSIONS = [
  '创始 & 起源叙事',
  '产品 & 定位',
  '分发 & 渠道',
  '社区 & PR',
  '视觉 & 语言',
  '竞品 & 格局',
  '接收 & 情绪',
];

// Rough token estimates based on MBA pipeline experience
const TOKENS_PER_DIMENSION = 15_000;   // input
const TOKENS_PER_JUDGE = 8_000;         // input
const OUTPUT_RATIO = 0.4;
const SONNET_INPUT_COST_PER_M = 3.0;   // USD per 1M tokens
const SONNET_OUTPUT_COST_PER_M = 15.0;

export async function proposeAudit(
  input: ProposeAuditInput,
  store: FilesystemStore,
): Promise<ProposeAuditOutput> {
  const brandSlug = slugify(input.brand);
  if (!brandSlug) throw new Error('INVALID_BRAND: 品牌名无法解析为合法 slug');

  const audit_id = makeAuditId(brandSlug);
  const mode = input.mode === 'auto' || !input.mode ? 'fresh' : input.mode;

  const opts: AuditOptions = {
    focus_dimensions: input.focus_dimensions,
    judges: input.judges ?? DEFAULT_JUDGES,
    skip_wuying: input.skip_wuying ?? false,
    language: input.language ?? 'auto',
  };

  const dims = input.focus_dimensions ?? DEFAULT_DIMENSIONS;
  const judges = opts.judges ?? DEFAULT_JUDGES;

  const inputTokens = dims.length * TOKENS_PER_DIMENSION + judges.length * TOKENS_PER_JUDGE;
  const outputTokens = inputTokens * OUTPUT_RATIO;
  const estimatedCostUsd =
    (inputTokens / 1_000_000) * SONNET_INPUT_COST_PER_M +
    (outputTokens / 1_000_000) * SONNET_OUTPUT_COST_PER_M;
  const estimatedMinutes = dims.length * 3 + judges.length * 2;

  const now = new Date().toISOString();
  const state: AuditState = {
    audit_id,
    brand: input.brand,
    brand_slug: brandSlug,
    panel: 'default',
    mode,
    phase: 'proposed',
    started_at: now,
    last_progress_at: now,
    completed_phases: [],
    failed_phases: [],
    errors: [],
    tokens_used: { input: 0, output: 0 },
    options: opts,
  };

  await store.initAudit(state);

  const proposal_markdown = buildProposalMarkdown({
    audit_id,
    brand: input.brand,
    brand_slug: brandSlug,
    mode,
    dims,
    judges,
    opts,
    estimatedMinutes,
    estimatedCostUsd,
  });

  await store.writeFile(audit_id, 'proposal.md', proposal_markdown);

  return {
    audit_id,
    proposal_markdown,
    estimated_runtime_min: estimatedMinutes,
    estimated_token_cost_usd: Math.round(estimatedCostUsd * 100) / 100,
  };
}

function buildProposalMarkdown(p: {
  audit_id: string;
  brand: string;
  brand_slug: string;
  mode: string;
  dims: string[];
  judges: string[];
  opts: AuditOptions;
  estimatedMinutes: number;
  estimatedCostUsd: number;
}): string {
  return `# MBA Audit Proposal

**Audit ID:** \`${p.audit_id}\`
**Brand:** ${p.brand}
**Mode:** ${p.mode.toUpperCase()}
**Panel:** ${p.opts.judges?.join(' · ') ?? 'default'}
**Language:** ${p.opts.language}
**Wuying browser leg:** ${p.opts.skip_wuying ? '❌ skipped (--skip-wuying)' : '✅ enabled'}

## 调研维度（${p.dims.length} 个）

${p.dims.map((d, i) => `${i + 1}. ${d}`).join('\n')}

## 评委阵容（${p.judges.length} 位）

${p.judges.map(j => `- \`${j}\``).join('\n')}

## 预估

| 项目 | 估值 |
|---|---|
| 预计耗时 | ~${p.estimatedMinutes} 分钟 |
| Token 成本 | ~$${p.estimatedCostUsd.toFixed(2)} USD（±50%） |

---

调用 \`confirm_audit({ audit_id: "${p.audit_id}" })\` 开始审计，或通过 \`edits\` 字段调整维度/评委后再确认。
`;
}
