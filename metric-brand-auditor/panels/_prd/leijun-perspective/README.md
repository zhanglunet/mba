# Lei Jun Perspective Build Queue

This folder tracks the first real auto-panel judge build.

Do **not** create `leijun-perspective/SKILL.md` until the research files exist
and pass review. MBA treats any `<slug>-perspective/SKILL.md` as an available
judge, so a half-built skill would make `auto.yaml` look healthier than it is.

## Current State

- `00-prescan.md` exists with source inventory and hypotheses.
- No production perspective skill exists yet.
- `auto.yaml` should remain `status: skeleton`.

## Recommended Sequence

1. Build `01-writings.md` from annual speeches and book material.
2. Build `02-conversations.md` from long-form interviews / Q&A.
3. Build `03-expression-dna.md` from direct quotes only.
4. Build `05-decisions.md` before `04-external-views`; decisions are the spine.
5. Build `06-timeline.md`.
6. Draft `leijun-perspective/SKILL.md`.
7. Run quality checks against the draft.
8. Only then update `auto.yaml` and panel validation expectations.

## Done Criteria For This Phase

- At least six P0/P1 sources are cited with URLs and dates.
- Direct Lei Jun / Xiaomi first-person material is clearly separated from press coverage.
- Conflict rule for Xiaomi audits is specified before enabling the judge.
