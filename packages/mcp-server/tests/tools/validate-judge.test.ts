import { describe, it, expect } from 'vitest';
import { validateJudgePersona } from '../../src/judges/validate.js';

const VALID_PERSONA = `---
name: test-judge
description: A test judge persona for MBA unit tests
expertise: testing, quality assurance, system validation
---

## 决策启发式 / Decision Heuristics

1. Always check primary sources before forming an opinion.
2. Prefer falsifiable claims over unfalsifiable narratives.
3. Weight recent evidence more heavily when trends are visible.
4. Distinguish between signal and noise by looking for convergence across sources.
5. Acknowledge uncertainty explicitly rather than papering over it.

## 表达 DNA

Speaks plainly and directly. Uses numbered lists when presenting evidence.
Avoids jargon unless the domain demands it. Says "I don't know" when appropriate.
Provides concrete examples to anchor abstract points.

## 红线 / Boundaries

重要限制：不要激活超出公开资料范围的内容推断，不允许编造私下场景或未公开的个人信息。
评委应只基于已有公开资料（访谈、文章、演讲等）进行 in-character 分析。
如遇到无从查证的信息，应明确标注 N/A 而非推断填充。
`;

describe('validateJudgePersona', () => {
  it('passes a valid persona', () => {
    const v = validateJudgePersona(VALID_PERSONA);
    expect(v.has_anti_fabrication).toBe(true);
    expect(v.has_decision_heuristics).toBe(true);
    expect(v.warnings).toHaveLength(0);
  });

  it('flags missing anti-fabrication', () => {
    // Remove all known anti-fab trigger words
    const bad = VALID_PERSONA
      .replace(/不要激活/g, '')
      .replace(/不可编造/g, '')
      .replace(/不允许编造/g, '');
    const v = validateJudgePersona(bad);
    expect(v.has_anti_fabrication).toBe(false);
    expect(v.warnings.some(w => w.includes('anti-fabrication'))).toBe(true);
  });

  it('accepts English anti-fabrication keyword', () => {
    const eng = VALID_PERSONA.replace('不要激活', 'Do not fabricate');
    const v = validateJudgePersona(eng);
    expect(v.has_anti_fabrication).toBe(true);
  });

  it('flags missing decision heuristics', () => {
    const bad = VALID_PERSONA
      .replace('决策启发式', '其他章节')
      .replace('Decision Heuristics', '其他内容')
      .replace('心智模型', '')
      .replace(/mental model/gi, '');
    const v = validateJudgePersona(bad);
    expect(v.has_decision_heuristics).toBe(false);
  });

  it('flags short content', () => {
    const short = '---\nname: x\n---\n不要激活\n决策启发式\n';
    const v = validateJudgePersona(short);
    expect(v.warnings.some(w => w.includes('500'))).toBe(true);
  });
});
