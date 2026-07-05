import type { ListPanelsOutput } from '../types.js';
import { GENERATED_PANELS } from '../llm/panels.generated.js';
import { GENERATED_JUDGES } from '../llm/personas.generated.js';

const DEFAULT_JUDGES = ['fusheng', 'jobs', 'likejia', 'wu-jundong', 'zhang-yiming'];

/**
 * List the available judge panels + their rosters, so a caller can discover
 * what to pass as `propose_audit({ panel })` before running an audit.
 */
export function listPanels(): ListPanelsOutput {
  const enrich = (slug: string) => {
    const j = GENERATED_JUDGES[slug];
    return {
      slug,
      name_cn: j?.name_cn ?? slug,
      name_en: j?.name_en ?? slug,
      language: j?.language ?? 'zh',
    };
  };

  const panels: ListPanelsOutput['panels'] = [
    {
      name: 'default',
      display_name: 'Default Panel',
      description: '默认 5 人面板（傅盛 / Jobs / 李可佳 / 吴俊东 / 张一鸣）',
      judges: DEFAULT_JUDGES.map(enrich),
    },
    ...Object.values(GENERATED_PANELS).map(p => ({
      name: p.name,
      display_name: p.display_name,
      description: p.description,
      judges: p.judges.map(enrich),
    })),
  ];

  return { panels };
}
