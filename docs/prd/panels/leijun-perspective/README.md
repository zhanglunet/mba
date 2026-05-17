# Lei Jun Perspective Build Queue

This folder tracks the first real auto-panel judge build.

`leijun-perspective/SKILL.md` now exists as a production v1 perspective skill.
MBA treats any `<slug>-perspective/SKILL.md` as an available judge, so future
edits must be made with normal production-skill care.

## Current State

- `00-prescan.md` exists with source inventory and hypotheses.
- Production `leijun-perspective/SKILL.md` exists.
- `auto.yaml` still remains `status: skeleton` because the other auto judges
  are missing.

## Recommended Sequence

1. Build `01-writings.md` from annual speeches and launch scripts. Treat book
   material as future refresh unless legitimate chapter notes are added.
2. Build `02-conversations.md` from long-form interviews / Q&A.
3. Build `03-expression-dna.md` from direct quotes only.
4. Build `05-decisions.md` before `04-external-views`; decisions are the spine.
5. Build `06-timeline.md`.
6. Draft `leijun-perspective/SKILL.md`. Done.
7. Run quality checks against the draft. Done.
8. Promote production `leijun-perspective/SKILL.md`. Done.
9. Keep `auto.yaml` as skeleton until the rest of the auto panel exists.

## Done Criteria For This Phase

- At least six P0/P1 sources are cited with URLs and dates.
- Direct Lei Jun / Xiaomi first-person material is clearly separated from press coverage.
- Conflict rule for Xiaomi audits is specified before enabling the judge.
  External rule now lives in `metric-brand-auditor/panels/README.md §5.3` and
  `auto.yaml` comments.
