# Lei Jun Perspective — 07 Quality Gate

**Status:** Review checkpoint for draft promotion
**Created:** 2026-05-17
**Reviewed artifact:** `SKILL-draft.md`
**Decision:** Promoted to production v1 by user request
**Dogfood update:** Option A BYD dogfood executed; resolver-only Option B check
executed; see `dogfood/`
**Quote update:** 2022 low-point and 2024 SU7 livestream fragments added to
`03-expression-dna.md`

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
| Xiaomi conflict rule | Partial pass | Draft and panel docs state the rule; runtime still does not enforce it |
| Dogfood test | Partial pass | Option A BYD review passed; Option B resolver discovery passed; full `/mba` runtime review not executed |
| Promotion readiness | Promoted | Production `leijun-perspective/SKILL.md` now exists; full `/mba` runtime dogfood remains optional |

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

### Resolved 2 — Book Dependency Removed From V1

`00-prescan.md` and `01-writings.md` mention `小米创业思考`, but the draft does
not yet have chapter-level notes from a legitimate copy. The current
`SKILL-draft.md` works without the book, so production v1 should not depend on
it.

Decision:

- `小米创业思考` is downgraded to future refresh only.
- Production v1 must rely on speeches, launch scripts, Q&A, external views,
  decision notes, and timeline.
- Do not cite the book in production `SKILL.md` unless legitimate chapter notes
  or reliable short excerpts are added later.

### Blocker 3 — Low-Point / Conversation Voice Needs Review, Not Extraction

The 2022 annual speech and 2024 SU7 livestream now have short fragments in
`03-expression-dna.md`. This reduces the extraction blocker, but the final
production skill still needs a human source review to ensure those fragments are
used as calibration anchors, not as over-repeated slogans.

Needed:

- confirm the 2022 fragments stay short and source-accurate
- confirm the 2024 livestream fragment is treated as a recap-backed source
- optional: add a fuller transcript later if available

### Partial 4 — Conflict Rule Documented, Runtime Enforcement Still Future

The draft states:

```text
MBA 正式跑分时，建议使用 --panel-drop leijun。
```

External documentation now exists in `panels/README.md §5.3` and `auto.yaml`
comments. This is enough for a manual v1 promotion path, but the MBA runtime /
panel resolver still does not enforce it automatically.

Future runtime enhancement:

- drop or flag `leijun` when brand slug matches Xiaomi family terms
- keep conflicted judge output out of average scoring unless explicitly allowed
- print a Phase 0 warning when a self-conflict rule matches

### Partial 5 — Runtime Resolver Dogfood Done, Full MBA Run Not Done

The repo standard says a new perspective should be tested with:

```text
/mba <demo brand> --panel-add <new-judge> --quick
```

At the time of the first dogfood, the draft was intentionally not installed as
a production skill, so Option A used a manual single-judge simulation on BYD.
That passed the distinctiveness check.

The short-lived Option B resolver check also passed:

- temporary `leijun-perspective/SKILL.md` made `auto.yaml` report 4 missing
  skills instead of 5
- cleanup restored `auto.yaml` to 5 missing skills
- no production skill was committed during that resolver check; production
  promotion happened later by user request

Still not done:

- a full `/mba BYD --industry auto --quick --panel-add leijun` runtime review
  through Phase 4

## Promotion Criteria

Promote only when all are true:

- [ ] The six research files have enough primary / first-person source coverage
  to satisfy the repo quality bar.
- [x] `03-expression-dna.md` has one low-point quote and one conversational
  quote with source labels.
- [x] `SKILL-draft.md` no longer depends on unresolved book notes, or those
  notes exist.
- [x] Xiaomi conflict handling is documented outside the draft itself.
- [x] One non-Xiaomi Option A dogfood run produces an in-character,
  non-generic review.
- [x] One short-lived Option B resolver check passes and cleans up production
  `SKILL.md`.
- [ ] One full runtime dogfood run passes, or the promotion PR explicitly
  accepts Option A + resolver check as sufficient for first release.
- [ ] Local `scripts/validate_panels.py` still treats `auto.yaml` as skeleton
  until promotion is intentional.

## Recommended Next Step

Do **not** promote yet. The highest-leverage next task is now:

```text
Production `leijun-perspective/SKILL.md` now exists. Next optional step is a
full `/mba` runtime dogfood, or opening follow-up issues for resolver-level
self-conflict enforcement.
```

The BYD dogfood suggests the point of view is distinct enough to keep refining.
The remaining risk is source review and promotion mechanics, not conceptual
differentiation, book dependency, or external conflict documentation.
