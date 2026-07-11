import { describe, it, expect } from 'vitest';
import {
  parseJudgeScores,
  aggregateScores,
  computeDelta,
  buildDeltaMarkdown,
} from '../../src/orchestrator/scores.js';

// ── fixtures ────────────────────────────────────────────────────────────────

const EN_REVIEW = `**SCORES:**
- Origin authenticity: 8 — strong founding story
- Category coinage: 6 — partial category ownership
- Leverage quality: 9 — excellent network effects
- Identity coherence: 7 — mostly consistent
- Real-world signal: 5 — modest external validation

**TOTAL: 35/50**

**VERDICT:** A leverage-driven brand with room to grow signal.`;

const ZH_REVIEW = `**评分：**
- 原创性（Origin authenticity）：7 — 起源叙事扎实
- 范畴命名（Category coinage）：5 — 品类归属模糊
- 杠杆质量（Leverage quality）：8 — 渠道势能强
- 身份一致性（Identity coherence）：6 — 基本一致
- 真实信号（Real-world signal）：4 — 外部验证有限

**总分：30/50**

**结论（Verdict）：** 杠杆驱动，信号偏弱。`;

// ── parseJudgeScores ──────────────────────────────────────────────────────────

describe('parseJudgeScores', () => {
  it('parses English judge output', () => {
    const scores = parseJudgeScores('jobs', EN_REVIEW);
    expect(scores).not.toBeNull();
    expect(scores!.lenses.origin).toBe(8);
    expect(scores!.lenses.category).toBe(6);
    expect(scores!.lenses.leverage).toBe(9);
    expect(scores!.lenses.identity).toBe(7);
    expect(scores!.lenses.signal).toBe(5);
    expect(scores!.total).toBe(35);
  });

  it('parses Chinese judge output (English lens anchor)', () => {
    const scores = parseJudgeScores('fusheng', ZH_REVIEW);
    expect(scores).not.toBeNull();
    expect(scores!.lenses.origin).toBe(7);
    expect(scores!.lenses.signal).toBe(4);
    expect(scores!.total).toBe(30);
  });

  it('handles score of 10 correctly', () => {
    const review = 'Origin authenticity: 10 — perfect';
    const scores = parseJudgeScores('x', review);
    expect(scores!.lenses.origin).toBe(10);
  });

  it('returns null when no scores present', () => {
    const scores = parseJudgeScores('x', 'This review has no structured scores at all.');
    expect(scores).toBeNull();
  });

  it('ignores digits in rationale after the score', () => {
    const review = 'Leverage quality: 6 — grew 300% in 2024 across 5 channels';
    const scores = parseJudgeScores('x', review);
    expect(scores!.lenses.leverage).toBe(6);
  });
});

// ── skill⇄MCP parity ─────────────────────────────────────────────────────────
// The MCP orchestrator and the `/mba` skill must agree at the score layer: a review
// authored in the skill's real formats (bilingual table rows, section headers) must
// parse into the same JudgeScores shape as the MCP's own bullet format. These fixtures
// are lifted verbatim from published/reports (dji, anthropic) — see F5.

// dji/reviews/huangzheng.md — table rows "| Origin / 起源叙事 | 9 | tooltip | why |"
const SKILL_TABLE = `## Score Matrix

| Lens | Score | Tooltip | Why |
|---|---|---|---|
| Origin / 起源叙事 | 9 | 技术极客，不是机会主义者 | 汪滔从课程项目出发，真正把想飞变成产业。|
| Category / 品类定义 | 8 | 真正的 0→1，稀缺 | DJI 创造了消费无人机这个品类。|
| Leverage / 杠杆点 | 8 | 技术垂直整合=真护城河 | 视觉感知 + 运动控制被复用到无人机、稳定器、农业植保。|
| Identity / 身份系统 | 5 | 产品即品牌，叙事空洞 | DJI 几乎没有品牌叙事。|
| Signal / 真实信号 | 9 | 70% 市场份额是最好的投票 | 全球 70% 市场份额，美国 80%+。|`;

// anthropic/reviews/pthiel_v2.md — EVOLUTION v2 delta headers "### Origin — 8 ↔"
const SKILL_HEADER_DELTA = `### Origin — 8 ↔
Nothing in fourteen days touches the founding. The 2021 secret was a genuine contrarian bet.

### Category — 6 ↑1
This is where the delta earns its move; the model layer is commoditizing into table stakes.

### Leverage — 7 ↑1
Claude Code at ~$8B run-rate and ~54% enterprise coding share is a genuine switching-cost moat.

### Identity — 6 ↔
The naming ladder tidied up, but taxonomy is not vision.

### Signal — 7 ↓1
The $47B ARR now carries a visible cleanliness flag — partly gross reseller passthrough.

**Net: 34/50 vs v1's 33 — up one point.**`;

// anthropic/reviews/zhuxiaohu.md — numbered bilingual headers "### 1. Origin 起源真实性 — 7",
// followed by a panel-merge divergence paragraph that name-drops "Signal ... 从 10 压到 7".
const SKILL_NUMBERED_CJK = `### 1. Origin 起源真实性 — 7
起源是真的，故事也讲得好，可它是个使命故事，我只信七成。

### 2. Category 品类定义 — 6
Safety-First 能变成采购门槛，这是真付费场景，不是造词。

### 3. Leverage 杠杆点 — 6
护城河吊在华盛顿一根绳上，真杠杆，但脆。

### 4. Identity 身份系统 — 5
嘴上说一套，做的是另外一套，叙事错位。

### 5. Signal 真实信号 — 7
带 flag 的头条数字，我不敢当审计过的事实认账。

我这套是反过来——我就把 Signal 从 10 压到 7。这一压，就是最大的分叉点。`;

describe('parseJudgeScores — skill⇄MCP parity', () => {
  it('parses the skill bilingual table format', () => {
    const s = parseJudgeScores('huangzheng', SKILL_TABLE)!;
    expect(s).not.toBeNull();
    expect(s.lenses).toEqual({ origin: 9, category: 8, leverage: 8, identity: 5, signal: 9 });
    expect(s.total).toBe(39);
  });

  it('parses the EVOLUTION v2 delta-header format (ignoring ↑1/↓1 suffixes)', () => {
    const s = parseJudgeScores('pthiel', SKILL_HEADER_DELTA)!;
    // score is the header number, not the delta-arrow digit: "### Category — 6 ↑1" → 6
    expect(s.lenses).toEqual({ origin: 8, category: 6, leverage: 7, identity: 6, signal: 7 });
    expect(s.total).toBe(34); // matches the review's own "Net: 34/50"
  });

  it('parses numbered bilingual headers without a prose mention hijacking the score', () => {
    const s = parseJudgeScores('zhuxiaohu', SKILL_NUMBERED_CJK)!;
    // "### 5. Signal 真实信号 — 7" wins over the later prose "Signal 从 10 压到 7"
    expect(s.lenses).toEqual({ origin: 7, category: 6, leverage: 6, identity: 5, signal: 7 });
    expect(s.total).toBe(31);
  });

  it('yields the same JudgeScores shape whether authored in MCP or skill format', () => {
    // Same five scores (8/6/9/7/5), one written as MCP bullets, one as a skill table.
    const asMcp = parseJudgeScores('j', EN_REVIEW)!;
    const asSkillTable = parseJudgeScores(
      'j',
      `| Origin / 起源 | 8 | · | · |
| Category / 品类 | 6 | · | · |
| Leverage / 杠杆 | 9 | · | · |
| Identity / 身份 | 7 | · | · |
| Signal / 信号 | 5 | · | · |`,
    )!;
    expect(asSkillTable.lenses).toEqual(asMcp.lenses);
    expect(asSkillTable.total).toBe(asMcp.total);
  });
});

// ── aggregateScores ───────────────────────────────────────────────────────────

describe('aggregateScores', () => {
  it('computes per-lens means and overall mean', () => {
    const a = parseJudgeScores('jobs', EN_REVIEW)!;
    const b = parseJudgeScores('fusheng', ZH_REVIEW)!;
    const agg = aggregateScores('test-1', 'Test', '2026-07-01T00:00:00Z', [a, b]);

    expect(agg.means.origin).toBe(7.5); // (8+7)/2
    expect(agg.means.leverage).toBe(8.5); // (9+8)/2
    expect(agg.overall_mean).toBe(32.5); // (35+30)/2
    expect(agg.judges).toHaveLength(2);
  });
});

// ── computeDelta ──────────────────────────────────────────────────────────────

describe('computeDelta', () => {
  it('computes per-lens and overall deltas', () => {
    const old = aggregateScores('old', 'Test', '2026-06-01T00:00:00Z', [
      parseJudgeScores('fusheng', ZH_REVIEW)!, // origin 7, total 30
    ]);
    const neu = aggregateScores('new', 'Test', '2026-07-01T00:00:00Z', [
      parseJudgeScores('jobs', EN_REVIEW)!, // origin 8, total 35
    ]);

    const { overall_delta, lens_deltas } = computeDelta(old, neu);
    expect(overall_delta).toBe(5); // 35 - 30
    const originDelta = lens_deltas.find(d => d.lens === 'origin')!;
    expect(originDelta.delta).toBe(1); // 8 - 7
    const signalDelta = lens_deltas.find(d => d.lens === 'signal')!;
    expect(signalDelta.delta).toBe(1); // 5 - 4
  });
});

// ── buildDeltaMarkdown ────────────────────────────────────────────────────────

describe('buildDeltaMarkdown', () => {
  it('renders a delta table with arrows', () => {
    const old = aggregateScores('old-1', 'Test', '2026-06-01T00:00:00Z', [
      parseJudgeScores('fusheng', ZH_REVIEW)!,
    ]);
    const neu = aggregateScores('new-1', 'Test', '2026-07-01T00:00:00Z', [
      parseJudgeScores('jobs', EN_REVIEW)!,
    ]);
    const { overall_delta, lens_deltas } = computeDelta(old, neu);
    const md = buildDeltaMarkdown('Test', old, neu, overall_delta, lens_deltas);

    expect(md).toContain('# MBA Delta Report — Test');
    expect(md).toContain('old-1');
    expect(md).toContain('new-1');
    expect(md).toContain('▲'); // some lens went up
    expect(md).toContain('Overall');
    expect(md).toContain('Biggest Movements');
  });

  it('reports no movement when scores identical', () => {
    const s = aggregateScores('a', 'Test', '2026-06-01T00:00:00Z', [
      parseJudgeScores('jobs', EN_REVIEW)!,
    ]);
    const s2 = aggregateScores('b', 'Test', '2026-07-01T00:00:00Z', [
      parseJudgeScores('jobs', EN_REVIEW)!,
    ]);
    const { overall_delta, lens_deltas } = computeDelta(s, s2);
    const md = buildDeltaMarkdown('Test', s, s2, overall_delta, lens_deltas);
    expect(md).toContain('No material movement');
  });
});
