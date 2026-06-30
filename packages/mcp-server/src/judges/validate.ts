import type { AddJudgeOutput } from '../types.js';

const ANTI_FAB_PATTERNS = [
  /不要激活/,
  /不可编造/,
  /anti-fabrication/i,
  /do not fabricate/i,
  /don't fabricate/i,
];

const HEURISTIC_PATTERNS = [
  /决策启发式/,
  /心智模型/,
  /decision heuristic/i,
  /mental model/i,
];

export function validateJudgePersona(markdown: string): AddJudgeOutput['validation'] {
  const warnings: string[] = [];

  const has_anti_fabrication = ANTI_FAB_PATTERNS.some(p => p.test(markdown));
  if (!has_anti_fabrication) {
    warnings.push(
      '缺少 anti-fabrication 红线（需包含"不要激活"/"不可编造"/"anti-fabrication" 之一）',
    );
  }

  const has_decision_heuristics = HEURISTIC_PATTERNS.some(p => p.test(markdown));
  if (!has_decision_heuristics) {
    warnings.push('缺少决策启发式/心智模型章节（推荐包含 ≥5 条编号项）');
  }

  if (!markdown.includes('---')) {
    warnings.push('未检测到 YAML front matter 分隔符（---）');
  }

  if (markdown.length < 500) {
    warnings.push('persona_markdown 内容过短（< 500 字符），建议提供更丰富的人格描述');
  }

  return { has_anti_fabrication, has_decision_heuristics, warnings };
}
