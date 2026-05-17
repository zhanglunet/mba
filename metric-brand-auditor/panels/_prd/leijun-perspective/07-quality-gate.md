# Lei Jun Perspective — 07 Quality Gate

**Status:** Review checkpoint for draft promotion
**Created:** 2026-05-17
**Reviewed artifact:** `SKILL-draft.md`
**Decision:** Not ready to promote to production `leijun-perspective/SKILL.md`

This quality gate checks whether the Lei Jun draft can become a real MBA
perspective skill. It should remain in `_prd` until the blockers below are
resolved. This is deliberate: creating a sibling `leijun-perspective/SKILL.md`
would make the panel resolver treat `leijun` as available.

## Gate Summary

| Gate | Status | Notes |
|---|---|---|
| Required SKILL structure | Pass | Frontmatter, role rules, decision models, expression DNA, anti-fabrication boundaries all exist |
| Research file set | Pass | `01` through `06` exist, plus prescan, draft, and this gate |
| Decision heuristics | Pass | Draft has 8 heuristics, above the 5-item floor |
| Expression samples | Pass | Draft has 4 representative sentences; `03-expression-dna.md` has 13 short source-anchored fragments |
| Anti-fabrication | Pass | Draft explicitly blocks private claims, 2025+ unstated facts, Xiaomi-neutral judging, and unsourced numbers |
| Source density | Conditional pass | `rg` finds 44 URL occurrences across the prescan packet, but this includes duplicates and secondary commentary |
| Primary-source ratio | Needs review | Strong speech layer, weaker conversational layer; not yet safe to claim the repo's 80% primary-source quality bar |
| Xiaomi conflict rule | Partial pass | Draft states the rule, but MBA/panel runtime does not yet enforce it |
| Dogfood test | Blocked | No production skill exists, so `/mba <brand> --panel-add leijun --quick` cannot run yet |
| Promotion readiness | Blocked | Need either temporary local production copy for dogfood or a gated promotion PR |

## What Is Strong Enough

### 1. Distinct Point Of View

The draft now has a view that is meaningfully different from default panel
members:

- not Jobs: less taste absolutism, more delivery / service trust
- not Fusheng: less anti-consensus pressure, more patient decision path
- not Zhang Yiming: less cold systems thinking, more user-trust and founder
  accountability
- not generic Xiaomi PR: external-view file forces criticism around margin,
  premium ceiling, delivery, service, and price-war risk

Core voice is stable:

```text
warm founder accountability under industrial pressure
```

### 2. Auto-Panel Relevance

The draft is useful for the first auto panel because it gives concrete scoring
pressure on:

- post-purchase trust
- delivery and service after launch
- safety / quality as brand proof
- long-cycle manufacturing humility
- founder IP as risk-bearing collateral
- ecosystem claims as user-friction reduction, not SKU stacking

### 3. Conflict Handling Is Explicit

The draft does not pretend Lei Jun can neutrally score Xiaomi. It requires a
visible conflict disclaimer and recommends `--panel-drop leijun` for official
MBA Xiaomi audits.

## Blockers Before Promotion

### Blocker 1 — Conversation Evidence Is Still Too Recap-Heavy

`02-conversations.md` has useful Q&A and interview recaps, but several entries
are press summaries rather than full first-person transcripts. This is enough
for draft shape, not enough for production voice fidelity.

Needed:

- one fuller SU7 Q&A transcript or video-derived transcript
- one non-launch long-form interview where follow-up questions shape the answer
- clear labels for exact Lei Jun wording vs reporter paraphrase

### Blocker 2 — Book Dependency Is Not Resolved

`00-prescan.md` and `01-writings.md` mention `小米创业思考`, but the draft does
not yet have chapter-level notes from a legitimate copy. The current
`SKILL-draft.md` mostly works without the book, but the source inventory still
implies it is part of the backbone.

Options:

1. Add legitimate chapter notes before promotion.
2. Remove the book as a production dependency and treat it as a future refresh.

### Blocker 3 — Low-Point Voice Needs One Cleaner Primary Quote

The 2022 annual speech is the best source for failure / low-point voice, but
`03-expression-dna.md` still lacks a short, clean quote from it. Without that,
the draft may over-index on SU7-era courage and underrepresent the warmer
failure-processing register.

Needed:

- one short failure / low-point fragment from the 2022 PDF
- source note in `03-expression-dna.md`
- optional adjustment in `SKILL-draft.md` identity / expression sections

### Blocker 4 — Runtime Conflict Rule Is Not Enforced

The draft states:

```text
MBA 正式跑分时，建议使用 --panel-drop leijun。
```

But the MBA runtime / panel config does not enforce this. Promotion is safer if
the product has at least one of:

- a documented manual rule in `panels/README.md`
- a panel-level warning convention for self-conflicted judges
- a runtime check that drops or flags `leijun` when brand slug matches Xiaomi
  family terms

### Blocker 5 — No Dogfood Review Yet

The repo standard says a new perspective should be tested with:

```text
/mba <demo brand> --panel-add <new-judge> --quick
```

Because this draft is intentionally not installed as a production skill, dogfood
has not run. The next safe step is a staged dogfood:

1. Create a temporary production copy only on a branch or local scratch path.
2. Run one non-Xiaomi auto brand, for example BYD / NIO / Li Auto / XPeng.
3. Compare the Lei Jun review against Jobs or Fusheng to confirm it surfaces
   distinct issues.
4. Delete or keep gated until promotion decision.

## Promotion Criteria

Promote only when all are true:

- [ ] The six research files have enough primary / first-person source coverage
  to satisfy the repo quality bar.
- [ ] `03-expression-dna.md` has one low-point quote and one conversational
  quote with source labels.
- [ ] `SKILL-draft.md` no longer depends on unresolved book notes, or those
  notes exist.
- [ ] Xiaomi conflict handling is documented outside the draft itself.
- [ ] One non-Xiaomi dogfood run produces an in-character, non-generic review.
- [ ] Local `scripts/validate_panels.py` still treats `auto.yaml` as skeleton
  until promotion is intentional.

## Recommended Next Step

Do **not** promote yet. The highest-leverage next task is:

```text
Add 08-dogfood-plan.md with a staged promotion plan and a non-Xiaomi test brand.
```

That plan should choose one demo brand, define what "distinct from Jobs /
Fusheng / Zhang Yiming" means, and specify how to temporarily expose the draft
without accidentally making `leijun` look production-ready in `auto.yaml`.
