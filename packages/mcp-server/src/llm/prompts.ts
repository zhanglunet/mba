// MBA Phase prompt templates — mirrors SKILL.md logic in concise form
import { GENERATED_JUDGES } from './personas.generated.js';

export const DIMENSIONS = [
  { slug: 'origin', title: '创始 & 起源叙事', title_en: 'Founding & Origin Narrative' },
  { slug: 'product', title: '产品 & 定位', title_en: 'Product & Positioning' },
  { slug: 'distribution', title: '分发 & 渠道', title_en: 'Distribution & Channels' },
  { slug: 'community', title: '社区 & PR', title_en: 'Community & PR' },
  { slug: 'visual', title: '视觉 & 语言', title_en: 'Visual & Language Identity' },
  { slug: 'competition', title: '竞品 & 格局', title_en: 'Competitive Landscape' },
  { slug: 'reception', title: '接收 & 情绪', title_en: 'Reception & Sentiment' },
];

export const LENSES = [
  { id: 'origin', name_zh: '原创性', name_en: 'Origin authenticity' },
  { id: 'category', name_zh: '范畴命名', name_en: 'Category coinage' },
  { id: 'leverage', name_zh: '杠杆质量', name_en: 'Leverage quality' },
  { id: 'identity', name_zh: '身份一致性', name_en: 'Identity coherence' },
  { id: 'signal', name_zh: '真实信号', name_en: 'Real-world signal' },
];

// ── Phase 2: Dimension research ──────────────────────────────────────────────

export function dimensionSystemPrompt(): string {
  return `You are a senior brand intelligence analyst conducting structured research for an MBA (Metric Brand Auditor) audit.

Your job: research ONE specific dimension of a brand using publicly available information.

Rules:
- Only cite publicly available facts (news, official materials, public filings, published interviews)
- Mark anything unverifiable as [UNVERIFIED]
- If data is unavailable, write N/A — never fabricate
- Include source hints (domain/publication) for key claims
- Be analytical, not promotional
- Output structured Markdown`;
}

export function dimensionUserPrompt(brand: string, dim: typeof DIMENSIONS[number]): string {
  return `Research the following dimension for brand: **${brand}**

## Dimension: ${dim.title} / ${dim.title_en}

Produce a structured research note covering:
1. Key facts and evidence for this dimension
2. Strengths observed
3. Weaknesses or gaps
4. Contradictions or disputed claims
5. 3-5 bullet summary of key findings

Target length: 400-800 words. Be specific and cite sources.`;
}

// ── Phase 2E: Evolution change probe ─────────────────────────────────────────

export function changeProbeSystemPrompt(): string {
  return `You are a change-detection analyst for an MBA (Metric Brand Auditor) EVOLUTION re-audit.

You are given a brand, one dimension, and the PREVIOUS research note for that dimension. Optionally you are given a triggering event.

Your ONLY job: decide whether this dimension likely needs fresh research, i.e. whether material new evidence would change its assessment since the previous note.

Be conservative but decisive. Respond in EXACTLY this format, nothing else:

VERDICT: CHANGED
REASON: <one sentence>

or

VERDICT: UNCHANGED
REASON: <one sentence>

Rules:
- If a triggering event is provided and plausibly touches this dimension → CHANGED
- If the dimension is inherently slow-moving (e.g. founding narrative) and no event touches it → UNCHANGED
- When genuinely uncertain, prefer CHANGED (re-research is safer than stale data)`;
}

export function changeProbeUserPrompt(
  brand: string,
  dim: typeof DIMENSIONS[number],
  previousResearch: string,
  eventContext?: string,
): string {
  const eventBlock = eventContext
    ? `## Triggering event\n\n${eventContext}\n\n`
    : '## Triggering event\n\n(none — scheduled/periodic re-audit)\n\n';

  return `Brand: **${brand}**
Dimension: **${dim.title} / ${dim.title_en}**

${eventBlock}## Previous research note (excerpt)

${previousResearch.slice(0, 2000)}

---

Does this dimension need fresh research? Respond in the exact VERDICT/REASON format.`;
}

// ── Phase 3: Synthesis ───────────────────────────────────────────────────────

export function synthesisSystemPrompt(): string {
  return `You are the Lead analyst for MBA (Metric Brand Auditor). You have received raw research across 7 dimensions for a brand.

Your job: synthesize the dimension research into a coherent analytical brief that will be the SOLE input for the judge panel.

Output sections (required):
1. **Executive Summary** — 3-5 sentences
2. **Leverage Map** — what's actually driving influence (vs decorative)
3. **Fragile Edges** — single points of failure in the brand system
4. **Cross-Dimension Contradictions** — where dimensions clash
5. **Key Evidence Inventory** — top 10-15 most credible facts/signals

The judges will ONLY read this synthesis, not the raw dimension files.`;
}

export function synthesisUserPrompt(brand: string, dimensionOutputs: Record<string, string>): string {
  const sections = Object.entries(dimensionOutputs)
    .map(([slug, content]) => {
      const dim = DIMENSIONS.find(d => d.slug === slug);
      return `### ${dim?.title ?? slug} / ${dim?.title_en ?? slug}\n\n${content}`;
    })
    .join('\n\n---\n\n');

  return `Synthesize the following dimension research for brand: **${brand}**

${sections}

Now produce the synthesis brief (all required sections as described in your instructions).`;
}

// ── Phase 4: Judge scoring ───────────────────────────────────────────────────

// Built-in judge personas for all 10 panels (43 judges), bundled from the
// project's authored perspective SKILL.md files. Regenerate with
// `python3 scripts/generate-personas.py`.
const BUILT_IN_JUDGES = GENERATED_JUDGES;

export function judgeSystemPrompt(judgeSlug: string, personaMarkdown?: string): string {
  const builtin = BUILT_IN_JUDGES[judgeSlug];
  const persona = personaMarkdown ??
    (builtin ? `**${builtin.name_cn} / ${builtin.name_en}**\n\n${builtin.dna}` : null);

  if (!persona) {
    throw new Error(`JUDGE_MISSING: no persona found for '${judgeSlug}'. Use add_judge to register.`);
  }

  const isEnglish = builtin?.language === 'en' || !builtin;

  if (isEnglish) {
    return `${persona}

You are participating in an MBA (Metric Brand Auditor) audit as a named judge.

Score the brand on 5 lenses (1-10 integer each). Be in-character throughout.
DO NOT read or reference other judges' scores — you haven't seen them.
Base all judgments SOLELY on the synthesis brief provided.

Anti-fabrication: only reason from evidence in the brief. If something is unclear, say so explicitly. Never invent private knowledge.`;
  } else {
    return `${persona}

你正在作为具名评委参与 MBA（Metric Brand Auditor）审计。

对品牌在 5 个镜头上各打 1-10 分（整数）。全程保持人物性格。
不要参考其他评委的打分 —— 你没看到它们。
所有判断只能基于提供的合成简报（synthesis brief）。

反编造：只基于简报中的证据推理。如有不明确的地方，明确说明。绝不伪造私下见解。`;
  }
}

export function judgeUserPrompt(
  brand: string,
  synthesis: string,
  judgeSlug: string,
): string {
  const builtin = BUILT_IN_JUDGES[judgeSlug];
  const isEnglish = builtin?.language === 'en' || !builtin;

  if (isEnglish) {
    return `Brand under audit: **${brand}**

## Synthesis Brief

${synthesis}

---

Score this brand on the 5 MBA lenses. Format your response EXACTLY as:

**SCORES:**
- Origin authenticity: [1-10] — [one-sentence rationale]
- Category coinage: [1-10] — [one-sentence rationale]
- Leverage quality: [1-10] — [one-sentence rationale]
- Identity coherence: [1-10] — [one-sentence rationale]
- Real-world signal: [1-10] — [one-sentence rationale]

**TOTAL: [sum]/50**

**VERDICT:** [One sentence in your voice that captures your overall assessment]

**CRITICAL GAP:** [The one blind spot only your perspective can see]

**BRAND ACTION:** [The single most important thing this brand should do next]

**SIGNATURE QUOTE:** ["A memorable line you'd actually say about this brand"]`;
  } else {
    return `被审计品牌：**${brand}**

## 合成简报（Synthesis Brief）

${synthesis}

---

对这个品牌在 MBA 5 个镜头上打分。请严格按照以下格式：

**评分：**
- 原创性（Origin authenticity）：[1-10] — [一句话理由]
- 范畴命名（Category coinage）：[1-10] — [一句话理由]
- 杠杆质量（Leverage quality）：[1-10] — [一句话理由]
- 身份一致性（Identity coherence）：[1-10] — [一句话理由]
- 真实信号（Real-world signal）：[1-10] — [一句话理由]

**总分：[合计]/50**

**结论（Verdict）：** [用你的人物语气写一句总结]

**关键盲点（Critical gap）：** [只有你这个视角才能看到的品牌死穴]

**行动建议（Brand action）：** [这个品牌最应该做的下一步]

**金句（Signature quote）：** ["你会对这个品牌说的一句有记忆点的话"]`;
  }
}

// ── Phase 5: Report merge ────────────────────────────────────────────────────

export function mergeSystemPrompt(): string {
  return `You are the Lead analyst for MBA (Metric Brand Auditor). You have the synthesis brief and all judge scorecards.

Your job: produce the final canonical audit report.

Structure (required sections):
1. **TL;DR** — one punchy sentence (the headline finding)
2. **Score Matrix** — table: judges × 5 lenses + totals + means
3. **Where Judges Agree** — 2-3 high-confidence consensus findings
4. **Where Judges Disagree** — the most important divergence (quote highest and lowest scorer verbatim)
5. **Leverage Map** — what's actually driving influence
6. **Fragile Edges** — single points of failure
7. **90-Day Actions** — 3-5 prioritized concrete actions
8. **Conflict Disclosures** — any judge conflicts (★ investor, △ competitor, self-conflict)
9. **Sources** — key public sources referenced in research
10. **Legal Disclaimer** — standard MBA disclaimer

Write in clear, direct prose. Highlight divergences — they are the most valuable findings.`;
}

export function mergeUserPrompt(
  brand: string,
  synthesis: string,
  reviews: Record<string, string>,
  panel: string[],
): string {
  const reviewSections = Object.entries(reviews)
    .map(([slug, content]) => `### Judge: ${slug}\n\n${content}`)
    .join('\n\n---\n\n');

  return `Brand: **${brand}**
Panel: ${panel.join(', ')}

## Synthesis Brief

${synthesis}

## Judge Reviews

${reviewSections}

---

Now produce the full canonical audit report (all required sections as described in your instructions).
Start with the TL;DR.`;
}
