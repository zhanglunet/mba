# Lei Jun Runtime Dogfood Eval — Resolver Check

**Dogfood mode:** Option B resolver-only check
**Executed:** 2026-05-17
**Production skill committed:** No
**Decision:** Pass for resolver discovery; full `/mba` runtime review still not executed

## What Was Tested

This check tested whether MBA's panel resolver would discover a production
`leijun-perspective/SKILL.md` if the draft is promoted.

Steps performed:

1. Confirmed no production `leijun-perspective/SKILL.md` existed.
2. Ran `/usr/bin/python3 scripts/validate_panels.py`.
3. Temporarily copied `_prd/leijun-perspective/SKILL-draft.md` to
   `leijun-perspective/SKILL.md`.
4. Ran `/usr/bin/python3 scripts/validate_panels.py` again.
5. Deleted the temporary `leijun-perspective/SKILL.md`.
6. Re-ran validation and confirmed `auto.yaml` returned to skeleton state with
   5 missing skills.

## Observed Result

Before temporary copy:

```text
OK skeleton: auto.yaml (5 judges, 5 missing skills)
```

With temporary production copy:

```text
OK skeleton: auto.yaml (5 judges, 4 missing skills)
OK skeleton: vc-cn.yaml (5 judges, 4 missing skills)
```

After cleanup:

```text
OK skeleton: auto.yaml (5 judges, 5 missing skills)
```

## Interpretation

The resolver behavior is correct:

- Promoting `leijun-perspective/SKILL.md` will make `leijun` available to
  `auto.yaml`.
- It will also affect any other panel that lists `leijun`, such as `vc-cn.yaml`.
- Keeping the draft under `_prd` prevents premature availability.
- Cleanup restored the expected skeleton state.

## What Was Not Tested

This was not a full end-to-end `/mba BYD --industry auto --quick --panel-add
leijun` run. It did not generate a fresh MBA synthesis or run the judge through
the app's full Phase 4 output path.

The earlier Option A BYD review still covers voice distinctiveness:

- `dogfood/byd-review.md`
- `dogfood/byd-eval.md`

This file covers resolver safety only.

## Cleanup Evidence

Cleanup checks passed:

- `test ! -f leijun-perspective/SKILL.md`
- `/usr/bin/python3 scripts/validate_panels.py` returned `auto.yaml` to 5
  missing skills
- `git status --short` did not show `leijun-perspective/`

## Recommendation

Promotion is mechanically feasible. The next decision is product-level:

1. Promote `leijun-perspective/SKILL.md` in a dedicated PR, copy the research
   packet into `leijun-perspective/references/research/`, and leave
   `auto.yaml` as skeleton until more auto judges exist.
2. Or keep this PR as research-only and merge it as the full prescan packet.

Do not accidentally mix the two. A production skill changes resolver behavior
across panels.
