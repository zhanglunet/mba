# Naval Ravikant — Conversations (Podcasts, Interviews, Talks)

**Status:** v1 — built 2026-07-07. For Naval the *conversation* and the *writing*
are the same artifact: the nav.al corpus is a podcast he co-hosts with **Nivi**
(Babak Nivi) and publishes as edited transcripts. Those transcripts are quoted
directly (verified against `naval_corpus.txt`) and their content lives mostly in
`01-writings.md`. This file records the conversational *form*, the interview
partners, and the sources that are **confirmed events but not text-verifiable in
this pass** — catalogued and flagged, never invented.
**Scope:** the "How to Get Rich" / "Naval" podcast, the Kapil Gupta
conversations, the origin tweetstorm, and downstream interviews.
**Sources Policy:** nav.al published transcripts (primary, verbatim, Naval-owned)
> confirmed-but-unverified appearances (event confirmed, transcript pending) >
third-party recaps (secondary → `04-external-views.md`).

> **Honesty note.** Because Naval’s own site publishes the transcripts, the
> primary/secondary problem that dogs a pure-podcast figure is mostly solved
> here — the words are his, edited by his team, on his domain. The remaining gap
> is the handful of nav.al posts that are *pointers only* (the Kapil Gupta
> "conversations" whose bodies were **not present as text on disk** in this
> pass) and the many YouTube/Twitter appearances that were never text-verified.
> Those are listed and flagged; no quotes are reconstructed from them.

---

## A. The "Naval" / "How to Get Rich" Podcast (first-party, verbatim)

The cleanest conversational primary source: Naval speaks, Nivi questions, Naval’s
team edits and posts the transcript on nav.al.

### A1. "How to Get Rich (without getting lucky)" series — Feb–May 2019 (compiled Dec 28 2019)

- Master compilation: https://nav.al/rich (dated **Dec 28 2019**).
- Format, in Naval’s own framing (seek-wealth, Feb 28 2019): "This is my first
  interview on How to Get Rich, based on my tweetstorm on the same topic… These
  transcripts have been edited for clarity."
- Origin: the **2018 tweetstorm** "How to get rich (without getting lucky)"
  (opening line: seek wealth, not money or status). The tweetstorm itself is
  pre-corpus (2018); the posts expand it tweet-by-tweet. Do NOT quote the raw
  2018 tweets as if text-verified here — quote the published transcripts.
- Individual episodes (all first-party, dates in `01`/`06`): seek-wealth, money-luck,
  ethical-wealth, long-term, specific-knowledge, accountability-leverage,
  business-models, judgment, stupid-games, reject-advice, productize-yourself,
  finding-time.
- Verbatim example (Naval): "In an age of infinite leverage, judgment becomes the
  most important skill." — judgment, Apr 29 2019.

### A2. Interlocutor note — Nivi (Babak Nivi)

- Nivi is the **interviewer / co-host** (AngelList co-founder, Venture Hacks). In
  the transcripts, questions and some framings are *his*, answers are Naval’s.
  `01-writings.md` flags the lines that are Nivi’s (e.g., "Leverage is a force
  multiplier for your judgment." which Nivi attributes to Naval’s tweet; and the
  "Long-term players make each other rich" formulation Naval calls "a brilliant
  formulation").
- Discipline: when the MBA judge "quotes Naval," use a line the transcript marks
  as **Naval:**, not **Nivi:**.

### A3. The happiness / practical-philosophy episodes — 2020–2021

- Same podcast, philosophy branch: desire (Feb 10 2020), happiness compilation
  (Mar 12 2021, https://nav.al/happiness). First-party, verbatim, verified.
- Register shift: warmer, more first-person-confessional ("I’ve gone from being a
  mostly unhappy person to being very happy. That was deliberate.").

---

## B. Conversations Confirmed but NOT Text-Verified in This Pass (FLAGGED)

These nav.al slugs exist and are dated, but their **transcript bodies were not
present as readable text on disk** in this pass — only the page chrome (title,
date, subtitle, related-links). **No quotes are drawn from them.**

### B1. "A conversation with Kapil Gupta" posts — Dec 2018 / Jan 2019

- "The truth about hard work" — Dec 25 2018 — https://nav.al/the-truth-about-hard-work
- "The Need for Indifference" — Jan 4 2019 — https://nav.al/the-need-for-indifference
- "A Founder’s Anxiety" — Jan 4 2019 — https://nav.al/a-founders-anxiety
- **Status: transcript not verified.** On-disk files contain only the header and
  the subtitle "A conversation with Kapil Gupta" — the dialogue body did not
  render as text. Catalogued for completeness; do NOT quote. If the topic is
  Naval-on-Kapil-Gupta (radical honesty, "truth", non-self-help), live-verify the
  transcript before using any line.

### B2. Downstream interviews / podcasts (events real, transcripts pending)

- **Joe Rogan Experience**, **Tim Ferriss Show**, **Knowledge Project (Shane
  Parrish)**, **Lex Fridman Podcast** — Naval has appeared on all of these and
  they are the raw material for much of his public reputation. **None were
  text-verified in this pass.** Treat any specific line from them as **requires
  live verification**; do not reconstruct.

---

## C. The Almanack of Naval Ravikant (a compilation — SECONDARY for quoting)

- *The Almanack of Naval Ravikant* (Eric Jorgenson, ed., 2020) is the widely
  cited book. **It is a third-party compilation** of Naval’s tweets, podcasts and
  posts — Jorgenson curated and arranged it (Naval endorsed it; it’s free online).
- **Policy:** for verbatim quoting, prefer the **nav.al original** over the
  Almanack, because the Almanack sometimes tightens tweet-form wording. The seed
  `quotes.md` leaned on the Almanack; the upgraded bank re-anchors every line to
  the nav.al transcript that was `grep`-verified. Cite the Almanack only as a
  finding aid / secondary index, not as the verbatim source of record.

---

## D. Conversational Register vs. Written Register (for the SKILL author)

| Trait | In the wealth transcripts | In the happiness transcripts |
|---|---|---|
| Stance | Declarative, almost lecturing; compressed maxims | Warmer, confessional, self-implicating |
| Examples | Buffett, Rogan, Facebook/Uber, his own Epinions | Osho, Confucius, "one monkey" everyman |
| Sentence | Short axiom → crisp unpacking → concrete case | Same rhythm, more hedging ("this is not math") |
| Ego | Confident, occasionally provocative | Deliberately humble about physical health |

Because the whole corpus is *spoken*, the judge’s default voice is conversational
by nature — but it should stay in the **wealth/judgment register** (A1) for vc-en
work, and reach for the happiness register only when the topic is durability,
motivation, or founder well-being.

---

## E. Anti-Fabrication Notes

- The only verbatim conversational quotes used are from nav.al transcripts Naval
  published (A1, A3), each `grep -F`-verified.
- The Kapil Gupta posts (B1) and the Rogan/Ferriss/Parrish/Fridman appearances
  (B2) are **confirmed events with unverified transcripts** — do not quote.
- The Almanack (C) is a **secondary compilation** — do not treat its phrasing as
  the verbatim source; re-anchor to nav.al.
- Do not invent podcast quotes to fill a gap. A plausible-sounding "Naval-ism"
  fabricated from memory is exactly the failure the SOP forbids.

---

## F. Sequence Anchor

For the spoken voice, start with **seek-wealth (Feb 2019)** — it states the
format ("edited for clarity") and the three-games thesis in one sitting — then
**judgment (Apr 2019)** for the reflective, slow-down register.
