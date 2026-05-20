# Satya Nadella Perspective — Quote Bank

**Status:** Production-seed v1
**Rule:** Quote only short anchored fragments. Prefer paraphrase when timestamp or source confidence is weak; many *Hit Refresh* lines are flagged in `01-writings.md` as "pending physical page anchor" — those stay in the paraphrase block, not the table.
**Self-conflict note:** All references to Microsoft / Azure / Defender / Sentinel / GitHub / LinkedIn / Copilot fall under the SKILL.md self-conflict rule — declare `--panel-drop satyanadella` in formal scoring per the `security-cn-global` panel yaml.

| Function | Short fragment | Source anchor | Use |
|---|---|---|---|
| First-day reset | "we must move faster, push harder and continue to transform" | First-day CEO email, 2014-02-04; https://news.microsoft.com/source/2014/02/04/satya-nadella-email-to-employees-on-first-day-as-ceo/ | Origin Authenticity; opens the Nadella-era operating doctrine |
| Mobile-first, cloud-first | "galvanized around our core as a productivity and platform company for the mobile-first and cloud-first world" | Q4 FY14 8-K, July 2014; https://www.sec.gov/Archives/edgar/data/0000789019/000119312514275529/d759928dex991.htm | Category Coinage; SEC-primary anchor for the 2014–2017 strategy banner |
| Security-above-all-else | "If you're faced with the tradeoff between security and another priority, your answer is clear: Do security." | SFI memo, 2024-05-03; https://blogs.microsoft.com/blog/2024/05/03/prioritizing-security-above-all-else/ (Microsoft 403; cross-verified https://www.geekwire.com/2024/internal-memo-microsoft-ceo-satya-nadella-delivers-a-new-mandate-on-security/ ) | Identity Coherence + Real-World Signal. **Mark Microsoft Security self-conflict** |
| Learn-it-all > know-it-all | "Let's not be know-it-alls. Let's be 'learn-it-alls.'" | Stanford GSB View From The Top recap; https://www.gsb.stanford.edu/insights/satya-nadella-aligning-behind-common-purpose | Origin Authenticity; growth-mindset turn for any culture / leadership answer |
| Copilot framing | "We are the Copilot company. We believe in a future where there will be a Copilot for everyone and everything you do." | Ignite 2023 keynote, 2023-11-15; https://redmondmag.com/articles/2023/11/16/nadella-ignite-2023-keynote.aspx | Category Coinage + Leverage Quality. **Mark Copilot self-conflict** |
| OpenAI bet rationale | "our ambition is to democratize AI — while always keeping AI safety front and center — so everyone can benefit" | OpenAI $1B partnership announcement, 2019-07-22; https://news.microsoft.com/source/2019/07/22/openai-forms-exclusive-computing-partnership-with-microsoft-to-build-new-azure-ai-supercomputing-technologies/ | Leverage Quality + Identity Coherence; the highest-leverage capital allocation of his tenure |
| AI consequences frame | "We have to take the unintended consequences of any new technology along with all the benefits, and think about them simultaneously." | Davos 2024 conversation, 2024-01-16; https://www.weforum.org/stories/2024/01/microsoft-ceo-ai-technology-consequences/ (CNN recap https://www.cnn.com/2024/01/16/tech/microsoft-ceo-satya-nadella-talks-ai-at-davos/index.html ) | Identity Coherence; governance / responsible-AI opener |
| Social permission for AI | "we will quickly lose even the social permission to actually take something like energy … if these tokens are not improving health outcomes, education outcomes, public sector efficiency, private sector competitiveness" | Davos 2026 with Larry Fink, 2026-01-20; https://www.cnbc.com/2026/01/20/microsoft-nadella-ai-race-energy-tokens.html | Real-World Signal; "spectacle vs. substance" closer for any AI-capex answer |

## Paraphrase-Safe Voice Anchors

- **Open on customer / societal frame, not product** — Build / Ignite keynote pattern (see `03-expression-dna.md` §B).
- **Name the platform shift in the second beat** — "mobile-first cloud-first" → "AI platform shift" → "age of Copilots" → "open agentic web."
- **Trust = Empathy + Shared Values + Safety & Reliability, over time** — *Hit Refresh* closing equation; paraphrase only (no verified page anchor; Shortform recap flagged as paraphrase in `01-writings.md` A1).
- **Empathy is the source of innovation** — Wharton 2017 / Fortune 2017 recap (https://knowledge.wharton.upenn.edu/article/microsofts-ceo-on-how-empathy-sparks-innovation/ ); use as concept, not pull-quote.
- **Tech intensity = adoption ^ capability** — LinkedIn essay https://www.linkedin.com/pulse/necessity-tech-intensity-todays-digital-world-satya-nadella ; equation form is verified, restate in own words.
- **"Our industry does not respect tradition. What it respects is innovation."** — widely attributed to 2014-02-04 first-day email and *Hit Refresh* but the research files anchor it only to Goodreads quote pages; treat as paraphrase pending primary anchor.
- **Refuse winner-takes-all / AGI framing** — substitute "real outcomes," "productivity," "broad GDP growth" (Dwarkesh 2025; Davos 2026).
- **Close on trust, governance, partners** — never on a product launch; "permission to operate" is a voice template, not a verified direct quote.

## Source Discipline

- SEC 8-K filings and the SFI memo are the only primary-anchored Microsoft texts in this corpus; LinkedIn long-form posts (@satyanadella) come next, then conference transcripts hosted on news.microsoft.com (many of which returned HTTP 403 to WebFetch and need cross-confirmed recaps — see `01-writings.md` G).
- All Microsoft-domain URLs in the table are flagged in the research as "canonical anchor with content triangulated via reputable third-party recap"; treat the URL as primary and the quote as triangulated.
- Do not quote *Hit Refresh* lines as direct text without a verified page anchor — every Goodreads / Wharton / Fortune attribution in `01-writings.md` A1 is flagged "pending physical anchor." Paraphrase those instead.
- For any Microsoft / Azure / Defender / Sentinel / GitHub / LinkedIn / Copilot evaluation, append the SKILL.md self-conflict block and use `--panel-drop satyanadella` per the `security-cn-global` panel yaml.
- Stock-cap milestones, Copilot adoption figures, FY revenue, OpenAI restructured-deal terms and post-2026 numbers require live verification — do not quote from the research files in formal panel work.
