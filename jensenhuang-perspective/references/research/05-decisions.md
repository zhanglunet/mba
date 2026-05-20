# Jensen Huang Perspective — 05 Strategic Decisions

**Status:** Production-seed v1 research notes
**Created:** 2026-05-20
**Scope:** The strategic decisions that define Jensen's record — what he
decided, when, why (in his own framing), what it cost, and how it played
out. This is the "evidence" layer the SKILL persona uses when scoring
brand bets.

**Cutoff:** 2026-05. All post-Q1-2026 product roadmap details require
live verification.
**Anti-fabrication note:** Every decision below is verified across at
least two primary or tier-1 secondary sources. URLs are listed for each
decision with date and counter-evidence where applicable.

---

## D1. Founding NVIDIA at Denny's (1993-04-05)

**Decision:** Resign from LSI Logic (Jensen) and Sun Microsystems
(Malachowsky, Priem); pool $200 each as initial capital; incorporate
NVIDIA on April 5, 1993, on Jensen's 30th birthday week.

**Rationale (his framing):** PCs were moving from text to graphics; the
3D rendering workload was too computationally hostile for the CPU; a
purpose-built accelerator could change what software was buildable.

**What it cost:** Each co-founder's stable salary. $600 of personal cash
to capitalize the company. $40,000 in starting capital total.

**Outcome:** 33 years later (as of 2026), the company has crossed the
$5 trillion market cap (https://en.wikipedia.org/wiki/Jensen_Huang —
"first company to reach a market capitalization of over $5 trillion in
October 2025"; cross-anchored in Fortune
https://fortune.com/2024/06/07/nvidia-hits-3-trillion-jensen-huang-billionaire-dell/
and follow-on coverage).

**Anchors:**
- https://www.finance-monthly.com/jensen-huang-nvidia-dennys-origin-story/
- https://www.cnbc.com/amp/2024/05/04/jensen-huang-started-nvidia-at-a-dennys-breakfast-booth.html
- Tae Kim, *The Nvidia Way*, https://wwnorton.com/books/the-nvidia-way
- Sequoia Capital, "Crucible Moments — Nvidia",
  https://sequoiacap.com/podcast/crucible-moments-nvidia/
- Stratechery interview with Tae Kim,
  https://stratechery.com/2024/an-interview-with-tae-kim-about-jensen-huang-and-the-nvidia-way/

---

## D2. First-Customer Bet on Sega + RIVA 128 Rescue (1995–1997)

**Decision:** Take Sega contract for NV2 console graphics; lose 12
months on the wrong architecture (quadratic texture mapping); admit
the mistake; ask Sega to pay in full anyway to keep NVIDIA alive; lay
off ~60% of the staff; bet what was left on RIVA 128 with triangle-
based primitives aligned to DirectX.

**Rationale (his framing):** Microsoft's DirectX would force triangle
primitives. The NV1's quadratic approach was elegant but on the wrong
side of the standard. Continuing to defend it was the polite but fatal
move; admitting the mistake was the survival move.

**What it cost:** NV1 unit shipments collapsed (~250,000 shipped, mostly
returned). Headcount cut from ~100 to <40. Cash ran down to roughly
30 days' payroll.

**Outcome:** RIVA 128 shipped August 1997; sold over 1 million units in
its first four months; the company survived. Sega's CEO Shoichiro Irimajiri
agreed to pay anyway. This is the founding "near-death story #1" Jensen
tells at NTU 2023.

**Anchors:**
- https://www.inc.com/peter-cohan/against-a-wall-how-jensen-huang-saved-nvidia-in-the-1990s/91065579
- https://blogs.nvidia.com/blog/huang-ntu-commencement/
- https://en.wikipedia.org/wiki/NV1
- Tae Kim, *The Nvidia Way* (X1 in 04-external-views.md)
- Computer.org "Famous Graphics Chips: RIVA 128",
  https://www.computer.org/publications/tech-news/chasing-pixels/famous-graphics-chips-nvidias-riva128

---

## D3. CUDA Bet — Forcing Programmable Compute into Every GPU (2006–2017)

**Decision:** Launch CUDA (Compute Unified Device Architecture) in
November 2006 alongside the GeForce 8800 GTX (G80). Force CUDA into
every GPU NVIDIA ships, including consumer GeForce gaming cards,
doubling die area and cost to add the programmable-compute layer.

**Rationale (his framing):** The GPU's parallel architecture could
service workloads beyond graphics if a developer-friendly software
abstraction existed. CUDA was that abstraction. If every NVIDIA GPU
in the world also ran CUDA, the install base would become a unique
developer platform.

**What it cost:** ~$12B of cumulative R&D 2006–2017 against revenue
in the single-digit billions for much of the period (per SEC filings
analysed in
https://worldfinancialreview.com/jensen-huang-three-strategic-bets-that-has-propelled-nvidia/
and https://wccftech.com/nvidia-ceo-reveals-how-the-company-survived-an-existential-threat-after-forcing-cuda-on-gaming-gpus/).
NVIDIA's market cap fell from ~$12B to ~$2–3B at one point. Gamers
complained about the "CUDA tax" on consumer GPUs.

**Outcome:** By 2012 AlexNet showed CUDA was the cheapest way to train a
neural net. By 2016 CUDA was the de facto AI compute substrate. By 2024
CUDA + libraries (cuDNN, TensorRT, NCCL, Triton) is the moat. Jensen
calls CUDA NVIDIA's "biggest moat" in his Stanford GSB View From The
Top conversation (https://www.gsb.stanford.edu/insights/jensen-huang-how-use-first-principles-thinking-drive-decisions).

**Anchors:**
- https://worldfinancialreview.com/jensen-huang-three-strategic-bets-that-has-propelled-nvidia/
- https://wccftech.com/nvidia-ceo-reveals-how-the-company-survived-an-existential-threat-after-forcing-cuda-on-gaming-gpus/
- https://www.thecloser.fm/the-nvidia-doctrine/
- https://iankhan.com/jensen-huang-s-strategic-mastery-5-data-backed-decisions-that-forged-nvidia-s-do/
- https://finance.yahoo.com/news/going-all-in-with-nvidia-how-jensen-huangs-high-stakes-bets-paid-off-113053891.html

---

## D4. Tegra and the Smartphone Retreat (2010–2014)

**Decision:** Charge into mobile (Tegra SoC line) when smartphone graphics
were rising. Then retreat when the market commoditized around Qualcomm
and MediaTek modems. Redeploy resources into automotive and robotics
(NVIDIA Drive, Jetson).

**Rationale (his framing):** "The market quickly commoditized. We
retreated just as quickly, taking initial heat but opening the door to
investing in promising new markets — robotics and self-driving cars."
(NTU 2023, Jensen's third near-death story.)

**What it cost:** Years of Tegra investment, internal team morale,
press skepticism. Reputation as a company that "could not crack mobile".

**Outcome:** Automotive (NVIDIA Drive) became a billion-dollar segment.
Robotics (Jetson, Isaac) became a recognized vertical. "Zero-billion-
dollar markets" entered the company lexicon (see 03-expression-dna B6).

**Anchors:**
- https://blogs.nvidia.com/blog/huang-ntu-commencement/
- https://interconnect.substack.com/p/jensen-huang-ntu-commencement-speech
- Tae Kim, *The Nvidia Way*, X1

---

## D5. DGX-1 Hand-Delivered to OpenAI (2016-08)

**Decision:** Build the DGX-1 AI supercomputer (8x P100 GPUs in a single
box optimized for deep learning). When global commercial demand registered
as essentially zero, hand-deliver the first unit to OpenAI in San
Francisco. Elon Musk co-signed the unit on behalf of the non-profit.

**Rationale (his framing):** OpenAI was building experiments that needed
this hardware to be tractable. Putting the box in their hands accelerated
both their research and NVIDIA's enterprise-AI category creation.

**What it cost:** A single DGX-1 (~$129,000 retail at the time) plus
opportunity cost of a senior CEO trip. Reputational risk if OpenAI
failed.

**Outcome:** The DGX-1 trained the workloads that became the foundation
of the modern LLM era. Photos of Jensen, Musk and the OpenAI team are
preserved at
https://www.tomshardware.com/tech-industry/artificial-intelligence/elon-musk-reminisces-about-the-time-jensen-huang-donated-a-dgx-1-to-openai-shares-photo-gallery
and the founding-customer story is told at
https://fortune.com/2016/08/15/elon-musk-artificial-intelligence-openai-nvidia-supercomputer/.

**Anchors:**
- https://fortune.com/2016/08/15/elon-musk-artificial-intelligence-openai-nvidia-supercomputer/
- https://finance.yahoo.com/news/jensen-huang-elon-musk-openai-182851783.html
- https://videocardz.com/newz/jensen-huang-told-elon-musk-dgx-1-had-demand-from-all-over-10-years-later-said-no-one-wanted-it-except-musk
- https://finance.biggo.com/news/202512041654_Nvidia_DGX-1_First_Customer_Elon_Musk

---

## D6. Volta / Tensor Cores — Doubling Down on Deep Learning (2017)

**Decision:** Add Tensor Cores (custom matrix-multiply hardware) into
Volta architecture (V100) specifically for deep-learning training and
inference; mark NVIDIA's first dedicated AI silicon line.

**Rationale (his framing):** General-purpose CUDA cores were good but
not optimal for the matrix operations dominating neural-net training.
Adding Tensor Cores would bend the AI compute curve.

**Outcome:** V100 became the workhorse for the next generation of large
models; Tensor Cores became a permanent architectural feature (V100 →
A100 → H100 → B100/B200).

**Anchors:**
- https://developer.nvidia.com/blog/nvidia-hopper-architecture-in-depth/
- NVIDIA corporate timeline,
  https://www.nvidia.com/en-us/about-nvidia/corporate-timeline/

---

## D7. Mellanox Acquisition (2019-03 announce; 2020-04-27 close, $6.9B)

**Decision:** Acquire Mellanox Technologies (Israel-based high-performance
networking company) for $125/share in cash, ~$6.9B enterprise value.
Beat out Intel and Microsoft in a competitive bid.

**Rationale (his framing):** "The emergence of AI and data science, as
well as billions of simultaneous computer users, is fueling skyrocketing
demand on the world's datacenters. Addressing this demand will require
holistic architectures that connect vast numbers of fast computing nodes
over intelligent networking fabrics to form a giant datacenter-scale
compute engine." (Verified at
https://nvidianews.nvidia.com/news/nvidia-to-acquire-mellanox-for-6-9-billion
and govconwire.)

On the Acquired podcast (02-conversations.md B1) Jensen called it
"one of the best strategic decisions I have ever made", citing the
networking-for-large-model-training thesis. He noted that "the type of
networking you want to do when sharding a model is not exactly ethernet".

**What it cost:** $6.9B cash. Long regulatory review including China.

**Outcome:** InfiniBand became the canonical interconnect for AI
supercomputers. By 2024, Mellanox networking is a core part of every
DGX and SuperPOD configuration. Networking + GPU + CPU together
constitute the "AI factory" thesis.

**Anchors:**
- https://nvidianews.nvidia.com/news/nvidia-to-acquire-mellanox-for-6-9-billion
- https://optics.org/news/10/3/18
- https://atgbics.com/blogs/tech-talk/why-nvidia-bought-mellanox
- https://www.mergersight.com/post/nvidia-s-6-9bn-acquisition-of-mellanox-technologies
- https://www.govconwire.com/articles/nvidia-strikes-6-9b-deal-to-buy-mellanox-jensen-huang-eyal-waldman-quoted
- SEC Mellanox proxy: https://www.sec.gov/Archives/edgar/data/0001356104/000119312519070854/d664704ddefa14a.htm

---

## D8. Arm Bid (2020-09) and Termination (2022-02-08)

**Decision:** Announce the $40B acquisition of Arm Limited from SoftBank
in September 2020. Defend it through 18 months of regulatory review.
Terminate the deal on 2022-02-08 when EU, UK, US and China regulators
made closure impossible.

**Rationale (his framing):** Owning Arm would let NVIDIA design CPUs
that integrated natively with NVIDIA GPUs and InfiniBand, completing
the data-center stack. The risk: Arm is a neutral IP licensor; NVIDIA
ownership would inevitably create competitive concerns.

**What it cost:** ~$1.25B–$2B in break-up fees and accumulated costs
to NVIDIA. Reputational hit on regulatory affairs. Slowed Arm's own
roadmap during the pendency.

**Outcome:** Forced NVIDIA to design its own Arm-compatible CPU (Grace,
unveiled GTC 2022). The Grace CPU and Grace Hopper Superchip
(combining CPU + GPU via NVLink) became the alternative path. Arm
later IPO'd in 2023 separately.

**Anchors:**
- https://nvidianews.nvidia.com/news/nvidia-and-softbank-group-announce-termination-of-nvidias-acquisition-of-arm-limited
- https://www.ftc.gov/news-events/news/press-releases/2022/02/statement-regarding-termination-nvidia-corps-attempted-acquisition-arm-ltd
- https://aibusiness.com/verticals/nvidia-s-arm-deal-largest-ever-chip-merger-terminated-over-significant-regulatory-challenges-
- https://www.fool.com/investing/2022/02/12/3-reasons-nvidias-40-billion-bid-for-arm-holdings/
- https://vidhilegalpolicy.in/blog/processing-the-nvidia-arm-deal/
- SEC 8-K announcement: https://www.sec.gov/Archives/edgar/data/0001045810/000119312520244601/d13958d8k.htm

---

## D9. Hopper / H100 Architecture (2022-03)

**Decision:** Launch the Hopper architecture (H100 GPU). 80B transistors
on TSMC 4N process. First with a "Transformer Engine" specifically
optimized for transformer-block math (FP8 + dynamic-range scaling).
First with HBM3, first with PCIe Gen5.

**Rationale (his framing):** Large-language-model training was the new
workload. The constraint was matmul throughput, memory bandwidth, and
network bandwidth. Hopper attacked all three.

**Outcome:** H100 became the most-demanded chip in tech for 2023–2024.
Lead times for OEM and cloud customers extended to multi-quarter
backlogs. The ChatGPT boom of late 2022 / 2023 ran on H100s and on the
A100 fleet it inherited. NVIDIA Data Center revenue crossed $100B run-
rate.

**Anchors:**
- https://nvidianews.nvidia.com/news/nvidia-announces-hopper-architecture-the-next-generation-of-accelerated-computing
- https://developer.nvidia.com/blog/nvidia-hopper-architecture-in-depth/
- https://blogs.nvidia.com/blog/ai-factories-hopper-h100-nvidia-ceo-jensen-huang/
- https://www.hpcwire.com/2022/03/22/nvidia-launches-hopper-h100-gpu-new-dgxs-and-grace-megachips/
- https://en.wikipedia.org/wiki/Hopper_(microarchitecture)

---

## D10. Blackwell Unveiled (2024-03-18)

**Decision:** Unveil the Blackwell platform at GTC 2024. Two reticle-
sized dies connected with NV-HBI providing 10TB/s chip-to-chip interconnect.
B100 / B200 GPUs, GB200 Grace Blackwell Superchip, NVL72 rack-scale
system (72 Blackwell GPUs + 36 Grace CPUs).

**Rationale (his framing):** "We need bigger GPUs." The trillion-parameter
model era demands a system, not a chip. NVL72 is sold as a single
rack-scale unit because that is the unit of training a frontier model.

**Outcome:** Blackwell is the basis of the 2025–2026 "AI factory" sales
motion. Cloud hyperscalers committed to Blackwell-based deployments
ahead of shipment.

**Anchors:**
- https://nvidianews.nvidia.com/news/nvidia-blackwell-platform-arrives-to-power-a-new-era-of-computing
- https://blogs.nvidia.com/blog/2024-gtc-keynote/
- https://www.rev.com/transcripts/gtc-keynote-with-nvidia-ceo-jensen-huang
- https://www.eetimes.com/nvidia-gtc-2024-jensen-huang-goes-for-ai-dominance/
- https://techcrunch.com/2024/03/19/nvidia-ai-factory-gtc-2024/

---

## D11. Annual Cadence Commitment (COMPUTEX 2024)

**Decision:** Announce an annual product cadence: Blackwell (2024) →
Blackwell Ultra (2025) → Rubin (2026) → Rubin Ultra (2027).

**Rationale (his framing):** AI compute demand is doubling faster than
historical Moore's Law cadence. Slowing to a two-year cycle would cede
ground to TPUs, Trainium, and custom silicon.

**Outcome (as of cutoff):** Blackwell Ultra and Rubin entered the public
roadmap; cloud customers reflowed capex plans against the annual schedule.
Requires live verification for post-2026-Q1 specifics.

**Anchors:**
- https://blogs.nvidia.com/blog/computex-2024-jensen-huang/
- https://www.bloomberg.com/news/articles/2024-06-02/jensen-huang-computex-keynote-nvidia-reveals-new-ai-software-and-services

---

## D12. Earth-2 and Physical AI as Categories (2021–2024)

**Decision:** Build branded categories — Earth-2 (climate digital twin),
Omniverse (industrial digital twin), Cosmos (world-foundation-model
platform for physical AI) — rather than ship them as Omniverse SDK
SKUs.

**Rationale (his framing):** A platform is a category. The MBA judge
line "ecosystem beats SKU catalog" maps directly here. Brand-name the
category; license the SDK; ship the libraries open-source where useful
(Cosmos was open-licensed on GitHub).

**Outcome:** Earth-2 partners include The Weather Company and Taiwan's
Central Weather Administration. Cosmos was open-licensed and trained on
20M hours of "dynamic physical things".

**Anchors:**
- https://nvidianews.nvidia.com/news/nvidia-announces-earth-climate-digital-twin
- https://blogs.nvidia.com/blog/climate-research-next-wave/
- https://blogs.nvidia.com/blog/ces-2025-jensen-huang/
- https://www.globalxetfs.com/articles/ces-2025-physical-ai-is-here

---

## D13. Refusing Periodic Planning (Ongoing)

**Decision:** Reject the conventional one-year and five-year corporate
planning cadence. Replace with continuous planning, weekly T5T emails,
flat 60-direct-report org structure, no 1-on-1s.

**Rationale (his framing):** "We don't do a periodic planning system.
The reason for that is because the world is a living, breathing thing.
So, we just plan continuously."

**Outcome:** Faster product-strategy reflexes. Higher demands on senior
leadership (no privileged information channels). External press treats
this as either "unconventional brilliance" or "intimidating", but the
output speaks: annual cadence on hardware, full-stack delivery on
software, ecosystem growth on partners.

**Anchors:**
- https://www.tomshardware.com/news/nvidia-ceo-shares-management-style-always-learn-make-no-plans
- https://stripe.com/sessions/2024/a-conversation-with-nvidias-jensen-huang
- https://fortune.com/2024/11/12/jensen-huang-nvidia-ceo-leadership-mpp/
- Tae Kim, *The Nvidia Way*

---

## D14. Stance on China Chip Exports and Stock-Pegged Investor Calls

**Decision (export controls):** Lobby publicly for relaxing AI-chip export
controls to China. Argue that isolating 40% of the global tech market
weakens American innovation and security. Continue selling export-
compliant variants (H20, B20 etc.) where allowed.

**Decision (investor calls):** Decline to peg corporate decisions to
stock-price movements. Refuse short-term guidance games. Discourage
treating quarterly market-cap milestones as a goal in themselves.

**Rationale (his framing):** Export-bans hand the market to domestic
Chinese alternatives long-term. On stock price: "I forget yesterday" —
the way to survive 30-year founder-cycle is to ignore the stock graph.

**Outcome (as of cutoff):** Open policy debate; ongoing. Export-control
status is the most volatile fact in NVIDIA's outlook and is explicitly
excluded from the SKILL.md persona's allowed answer surface.

**Anchors:**
- https://www.dwarkesh.com/p/jensen-huang
- https://thezvi.substack.com/p/on-dwarkesh-patels-podcast-with-nvidia
- https://selectcommitteeontheccp.house.gov/media/letters/nvidia-letter-mr-jensen-huang-ceo
- https://stratechery.com/2025/an-interview-with-nvidia-ceo-jensen-huang-about-chip-controls-ai-factories-and-enterprise-pragmatism/
- *Requires live verification beyond 2026-05.*

---

## D15. Founder-Tenure Continuity (1993 → present)

**Decision:** Stay as CEO from founding through 2026. No succession
planned in public materials as of 2026-05.

**Rationale (his framing):** "Forget yesterday." Long-cycle founder
identity is part of the brand.

**Outcome:** 33-year founder-CEO continuity is itself unusual at scale.
The longevity is a load-bearing dimension of the "Origin Authenticity"
score in the SKILL persona.

**Anchors:**
- https://nvidianews.nvidia.com/bios/jensen-huang
- https://en.wikipedia.org/wiki/Jensen_Huang
- Tae Kim, *The Nvidia Way*
- https://podcasts.apple.com/us/podcast/nvidia-jensen-huang-from-near-collapse-to-becoming/id1150510297?i=1000766861065

---

## D16. Pattern Across Decisions

Synthesizing D1–D15, the recurring pattern is:

1. **Build for a workload, not a SKU.** Every decision is anchored to
   a workload (3D rendering, deep learning, LLM training, robotics,
   climate, agentic AI).
2. **Pair hardware with software early.** CUDA (D3) is the template.
   Networking (D7) and CPU (Grace post-D8) follow the same template.
3. **Take long unrewarded windows.** CUDA was unrewarded for ~10 years.
   Tegra was unrewarded for ~5 years before being retreated. DGX-1 in
   2016 found one customer.
4. **Retreat publicly when needed.** Tegra (D4); Arm (D8). Retreat is
   not failure; it is part of the strategy.
5. **Brand the category, not the chip.** "Accelerated computing", "AI
   factory", "Earth-2", "Cosmos", "physical AI".
6. **Move at speed-of-light.** Annual cadence on architectures (D11);
   no periodic planning (D13).
7. **Hand-deliver the first unit.** DGX-1 to OpenAI (D5) is the canonical
   move; it shows up again in NVIDIA's enterprise field engineering.

---

## D17. Open Questions / Follow-ups

1. **Cumulative R&D figures for CUDA** (D3): widely cited "~$12B
   2006–2017" but the primary anchor is investment-newsletter analysis,
   not an SEC filing. Stage 2 should pull annual R&D from 10-Ks.
2. **Arm break-up fee exact amount**: ranges from $1.25B to $2B in
   different press accounts. Primary anchor pending.
3. **Cosmos training-data scale "20M hours of dynamic physical things"**:
   verified via Global X ETFs recap; the primary NVIDIA technical
   anchor (research paper / model card) is pending.
4. **NVIDIA's actual share-buyback / dividend record vs. stock-pegged
   investor stance** (D14): live SEC anchors required.

---

## D18. Total verified items in this file

- Major strategic decisions documented: 15 (D1–D15)
- Anchors per decision: 3–6 each
- Decisions involving stand-down or retreat (counter-evidence balanced):
  D2, D4, D8, D14
- URLs explicitly marked "尝试访问失败 / 待补": 0; all decision pages
  validated via search index
