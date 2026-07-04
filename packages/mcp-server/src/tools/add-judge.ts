import { writeFile, mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import type { AddJudgeInput, AddJudgeOutput } from '../types.js';
import { validateJudgePersona } from '../judges/validate.js';

export async function addJudge(
  input: AddJudgeInput,
  judgesDir: string,
): Promise<AddJudgeOutput> {
  if (!/^[a-z][a-z0-9-]{1,30}$/.test(input.name)) {
    throw new Error('JUDGE_PERSONA_INVALID: name must match ^[a-z][a-z0-9-]{1,30}$');
  }

  const validation = validateJudgePersona(input.persona_markdown);
  const hasBlockingErrors =
    !validation.has_anti_fabrication;

  if (input.validate_only) {
    return { registered: false, validation };
  }

  if (hasBlockingErrors) {
    throw new Error(
      `JUDGE_PERSONA_INVALID: ${validation.warnings.join('; ')}`,
    );
  }

  await mkdir(judgesDir, { recursive: true });
  await writeFile(join(judgesDir, `${input.name}.md`), input.persona_markdown, 'utf-8');

  return { registered: true, validation };
}
