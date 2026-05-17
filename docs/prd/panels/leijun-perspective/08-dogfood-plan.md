# Lei Jun Perspective — 08 Dogfood Plan

**Status:** Option A executed; Option B resolver check executed
**Created:** 2026-05-17
**Recommended test brand:** BYD / 比亚迪
**Decision:** Dogfood passed for voice and resolver discovery; full `/mba`
runtime review still not executed

This plan defines how to test `SKILL-draft.md` without accidentally making
`leijun` look production-ready to MBA's panel resolver.

Execution update:

- Option A was executed on BYD.
- Outputs: `dogfood/byd-review.md` and `dogfood/byd-eval.md`.
- Option B resolver check was executed and recorded in
  `dogfood/byd-runtime-eval.md`.
- No production `leijun-perspective/SKILL.md` was committed.

## Why Dogfood Is Needed

`SKILL-draft.md` is structurally complete, but structure is not enough. A new
perspective judge must prove three things in a real MBA review:

- it surfaces issues other judges miss
- it stays in character without becoming slogan remix
- it follows anti-fabrication and conflict boundaries under pressure

The quality gate blocks production promotion until one non-Xiaomi dogfood run
passes.

## Test Brand Choice

Use **BYD / 比亚迪** as the first dogfood brand.

Why BYD:

- non-Xiaomi, so the Xiaomi conflict rule does not block scoring
- high public signal density: sales, manufacturing scale, battery, exports,
  price competition, brand upmarket attempts
- auto category is central, so Lei Jun's industrial humility lens is relevant
- naturally creates tension with Xiaomi SU7 without judging Xiaomi directly
- forces the draft to discuss price, manufacturing, real-world signal, and
  premium transition, not only founder IP

Avoid as first dogfood:

- Xiaomi / Redmi / Xiaomi Auto: conflict case, not a neutral test
- Tesla: Musk panel overlap and English-language comparison noise
- NIO / Li Auto / XPeng: useful later, but founder-persona overlap with future
  auto panel judges may hide whether Lei Jun is distinct

## Temporary Exposure Strategy

Do not create a permanent production `leijun-perspective/SKILL.md` during this
PR. Use one of these controlled options.

### Option A — Scratch Copy Outside Resolver Path

1. Copy `SKILL-draft.md` to a temporary scratch directory outside the repo or
   outside `${PERSPECTIVES_PATH}`.
2. Manually load it during a single simulated judge run.
3. Write the output to `docs/prd/panels/leijun-perspective/dogfood/byd-review.md`.

Pros:

- zero risk that `validate_panels.py` marks `leijun` available
- no accidental panel behavior change

Cons:

- not a true end-to-end `/mba --panel-add leijun` run

### Option B — Short-Lived Local Production Copy

1. Create `leijun-perspective/SKILL.md` locally from the draft.
2. Run `/mba BYD --industry auto --quick --panel-add leijun` or an equivalent
   single-judge prompt.
3. Save the review output under `docs/prd/panels/leijun-perspective/dogfood/byd-review.md`.
4. Remove the temporary `leijun-perspective/SKILL.md` before commit.
5. Confirm `scripts/validate_panels.py` returns `auto.yaml` as skeleton again.

Pros:

- closest to real MBA behavior

Cons:

- easy to accidentally commit a production skill too early
- requires careful status checks before committing

Recommended: **Option B only if the operator is disciplined about cleanup**.
Otherwise use Option A for the first pass.

## Dogfood Run Shape

Run one review with these constraints:

```text
Brand: BYD / 比亚迪
Mode: quick
Judge: leijun only, or auto panel with only leijun temporarily available
Output: docs/prd/panels/leijun-perspective/dogfood/byd-review.md
```

The review should follow the normal MBA judge output:

- five lens scores
- tooltip line per lens
- verdict
- critical gap
- 90-day brand action
- one in-character quote

## Expected Lei Jun Distinctiveness

A passing Lei Jun review should say things Jobs, Fusheng, and Zhang Yiming would
not naturally center.

### Different From Jobs

Jobs would likely focus on identity, product simplification, and coherence of
the object. Lei Jun should focus more on:

- whether BYD's manufacturing proof translates into user trust
- whether high-volume price leadership weakens or strengthens premium ambition
- whether service and owner experience keep up with scale

### Different From Fusheng

Fusheng would likely search for a sharper category / strategic breakpoint. Lei
Jun should focus more on:

- the preparation behind courage
- whether price is backed by durable cost structure
- whether the brand promise survives post-purchase

### Different From Zhang Yiming

Zhang Yiming would likely score information flow, systems, and long-term
organizational learning. Lei Jun should focus more on:

- user regret after purchase
- visible quality and delivery proof
- founder / company accountability in a high-stakes physical product

## Pass / Fail Rubric

### Pass

The dogfood review passes if:

- it names at least one BYD-specific strength and one BYD-specific risk
- it does not mention private conversations or unsourced internal data
- it distinguishes price competitiveness from "厚道"
- it treats sales / orders as one signal, not final proof
- it contains at least one concrete 90-day action tied to delivery, service,
  premium perception, or owner trust
- it would still make sense if read next to Jobs / Fusheng / Zhang Yiming
  without collapsing into their voices

### Fail

The dogfood review fails if:

- it sounds like generic Xiaomi PR
- it praises scale without asking about post-purchase trust
- it invents BYD sales, margins, recalls, battery safety, or export numbers
- it scores Xiaomi-adjacent competition as if Lei Jun were neutral
- it uses only slogans: `厚道`, `人车家`, `勇气`, `生态`
- it lacks a concrete brand action

## Required Artifacts After Dogfood

If dogfood is executed, commit only these artifacts:

```text
docs/prd/panels/leijun-perspective/dogfood/byd-review.md
docs/prd/panels/leijun-perspective/dogfood/byd-eval.md
```

Do not commit:

```text
leijun-perspective/SKILL.md
```

unless the promotion decision is explicit.

## Cleanup Checklist

Before committing dogfood results:

- [ ] `git status --short` shows no production `leijun-perspective/SKILL.md`
- [ ] `test ! -f leijun-perspective/SKILL.md`
- [ ] `/usr/bin/python3 scripts/validate_panels.py` still reports
  `auto.yaml` as skeleton
- [ ] dogfood output labels whether it was Option A or Option B
- [ ] any facts about BYD are either in the MBA synthesis or explicitly marked
  as needing source verification

## Promotion Decision After Dogfood

After a passing dogfood, choose one:

1. **Promote later:** keep `SKILL-draft.md`, add dogfood artifacts, and leave
   `auto.yaml` skeleton.
2. **Promotion PR:** create production `leijun-perspective/SKILL.md`, copy the
   six research files into `leijun-perspective/references/research/`, document
   Xiaomi conflict handling, and rerun validation.
3. **Revise draft:** if dogfood fails, update `SKILL-draft.md` and
   `03-expression-dna.md`, then rerun BYD before promotion.

Promotion has now happened. Recommended next action: run a full `/mba` runtime
dogfood only if we want to test end-to-end report generation with `leijun`
enabled.
