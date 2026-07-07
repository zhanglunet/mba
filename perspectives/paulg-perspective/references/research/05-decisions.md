# Paul Graham — Key Decisions (What He Did + Result)

**Status:** v1 — built 2026-07-07. Each decision has a date, what he actually
did, the result, and a source. Where PG documented the decision himself (his
essays), that is the primary anchor; Wikipedia supplies dates/figures as
secondary and is flagged.
**Scope:** the load-bearing decisions of PG's career as builder, essayist, and
investor — the ones that reveal the operating system behind the advice.
**Sources Policy:** PG's own essays (primary) > Wikipedia (secondary,
timeline/figures) > press (flagged). Dollar figures not verified in this pass
are marked "requires live verification."
**Cutoff:** 2026-05.

---

## A. Builder Decisions

### A1. Build Viaweb in Lisp for competitive advantage — 1995–1996

- What: With **Robert Morris** (co-founder) and **Trevor Blackwell** (recruited
  shortly after), PG built Viaweb — an early web-based application (they believed
  the first application service provider) — deliberately in **Lisp**, betting a
  more powerful language was a business weapon competitors couldn't match.
- Primary source: PG documents the reasoning himself in **"Beating the Averages"
  (April 2001, avg.html)** — the "Blub Paradox": programmers can't see the power
  of languages above their own. He treated language choice as strategy.
- Result: Viaweb shipped fast, out-featured rivals, and was acquired by **Yahoo
  in 1998**, becoming **Yahoo! Store** (Wikipedia). Acquisition dollar figure
  (commonly cited ~$49M in Yahoo stock) — **requires live verification**.
- Lens it reveals: technical leverage as competitive edge; "measurement and
  leverage" (wealth.html) enacted.

### A2. Become an essayist / publish on paulgraham.com — 2001 onward

- What: Rather than a blog platform, PG published long-form essays on his own
  plain-HTML site (avg.html, April 2001, is among the earliest). He kept full
  editorial control and the full text public.
- Result: the essays became canonical startup/craft literature and the
  distribution engine for everything after (YC applications, HN, his influence).
- Lens: "clear writing is clear thinking" (words.html) as a life strategy, not
  just advice.

---

## B. The Y Combinator Bet (the defining institutional decision)

### B1. Found Y Combinator — 2005

- What: **In 2005, after giving "How to Start a Startup" at the Harvard Computer
  Society** (later published as start.html), PG — with **Jessica Livingston,
  Robert Morris, and Trevor Blackwell** — founded Y Combinator and ran the first
  **Summer Founders Program** (Wikipedia; start.html is the talk).
- The model innovations (each a deliberate "do things that don't scale" choice
  at the accelerator level): fund **batches** of startups, write **small
  standardized checks**, give **intense in-person mentorship / office hours**,
  end each batch with **Demo Day**, and organize the whole thing around one
  motto — **"make something people want."**
- Result: YC became the most influential startup accelerator; early cohorts
  produced **Reddit, Twitch (Justin.tv), Dropbox, Airbnb, Stripe** and others
  (Wikipedia).
- Lens: the founder-craft essays are the *operating manual* PG wrote from running
  YC — the advice and the institution co-evolved.

### B2. Launch Hacker News — 2007 (originally "Startup News")

- What: PG built and ran HN, a news aggregator + forum (written in his Lisp
  dialect Arc), as both a community for founders and an experiment in online
  discourse quality.
- Result: one of tech's most influential forums; extended his reach far beyond
  the essays.

---

## C. Investment Decisions (the power-law lens in action)

### C1. Back ideas that "look like bad ideas" — Airbnb, Dropbox

- Principle (primary): **"Black Swan Farming" (Sept 2012, swan.html)** — "The two
  most important things to understand about startup investing... are (1) that
  effectively all the returns are concentrated in a few big winners, and (2) that
  the best ideas look initially like bad ideas."
- Enacted: YC funded **Airbnb** when "rent an air mattress in a stranger's
  apartment" read as a bad idea; PG later held it up as the type-example of
  unscalable, heroic early work — **"going door to door in New York, recruiting
  new users"** (ds.html). YC also funded **Dropbox** despite skepticism (famously
  panned on Hacker News at launch).
- Result: both became defining YC winners — the power-law "big winners" the swan
  essay predicts.
- Lens: judge the *slope of user love and growth*, not the plausibility of the
  pitch. This is the core of the MBA scoring bias.

### C2. Back the founders' resourcefulness — Stripe (the Collison brothers)

- What: YC funded the Collison brothers; PG names their onboarding move — the
  **"Collison installation"** (take the user's laptop and set it up on the spot,
  ds.html) — as the model of founder-driven, unscalable growth.
- Result: Stripe became one of YC's largest outcomes.
- Lens: "relentlessly resourceful" (relres.html) is the trait he funds.

---

## D. The Step-Back Decision

### D1. Hand YC to Sam Altman; step down from the day-to-day — February 2014

- What: **In February 2014, Graham stepped down from his day-to-day role at Y
  Combinator** (Wikipedia); Sam Altman took over as president. PG returned to
  writing and (later) language work.
- Result: YC scaled beyond him; PG's output shifted back to essays.
- Lens: a founder choosing to stop running the thing he founded — an interesting
  counterpoint he'd later complicate in "Founder Mode" (2024).

### D2. Keep building Lisp dialects — Arc (HN, ~2008) and Bel (spec Oct 2019)

- What: PG continued designing languages — **Arc** (used to build HN) and **Bel**
  (a specification announced **October 2019**, per Wikipedia).
- Lens: the maker never stops making; taste and craft (taste.html, hp.html) are
  lifelong, not a phase.

---

## E. The Late Intervention

### E1. Publish "Founder Mode" — September 2024

- What: After **Brian Chesky's YC talk**, PG wrote foundermode.html arguing there
  are "two different ways to run a company: founder mode and manager mode," and
  that the standard advice to switch to manager mode as you scale is often wrong.
- Result: immediate, polarized debate (see `04-external-views.md` §B).
- Lens: PG using the essay as a real-time intervention in startup orthodoxy —
  and a partial revision of his own earlier delegation-friendly framing.
  **Date-lock to 2024.**

---

## F. Decision Rationale Patterns (= the playbook)

| Pattern | Decisions that fit it |
|---|---|
| **Technical / craft leverage as competitive edge** | Viaweb-in-Lisp (A1); Arc/Bel (D2) |
| **Own your distribution and editorial control** | paulgraham.com essays (A2); Hacker News (B2) |
| **Do things that don't scale — even at the meta level** | YC's batch + office-hours model (B1) |
| **Judge user-love slope, not pitch plausibility** | Airbnb / Dropbox (C1); Stripe (C2) |
| **Compress the founder test to a trait** | "relentlessly resourceful" funding filter (C2) |
| **Revise your own orthodoxy in public when the evidence changes** | Founder Mode (E1) vs. earlier delegation advice |

---

## G. Anti-Fabrication Notes

- Dates from Wikipedia (Viaweb 1996; Yahoo 1998; YC 2005; step-down Feb 2014;
  Bel Oct 2019) are secondary anchors — solid, but if a formal figure is needed
  (e.g., Viaweb sale price, YC batch sizes, portfolio valuations) it **requires
  live verification** before use.
- Investment "results" (Airbnb/Dropbox/Stripe as winners) are matters of public
  record via the YC portfolio; specific valuations are NOT asserted here.
- Do NOT fabricate YC internal selection criteria, acceptance rates, or
  per-company check sizes. None of that is in the primary essays.

---

## H. Sequence Anchor (for the SKILL.md author)

The decisions that most define PG's operating system, by analytic weight:

1. **Found Y Combinator (2005)** — the institution that generated the canon.
2. **Build Viaweb in Lisp (1996) → Yahoo (1998)** — leverage-as-strategy, proven.
3. **Back "bad-looking" ideas (Airbnb/Dropbox) on the power law (swan.html)** —
   the investing lens the MBA judge inherits.
4. **Step down from YC (2014)** — the founder who stops running his own thing.
5. **Publish "Founder Mode" (2024)** — public revision of his own orthodoxy.
