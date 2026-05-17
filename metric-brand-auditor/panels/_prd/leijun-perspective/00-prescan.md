# Lei Jun Perspective — Prescan

**Status:** P1 source inventory, not a usable perspective skill yet
**Created:** 2026-05-17
**Target slug:** `leijun`
**Target panel:** `auto` first; later reusable by `vc-cn`
**Cutoff intent:** build from public material through the 2024 SU7 launch / 2024 annual speech first. Add 2025+ only after a deliberate refresh pass.

This file starts the `leijun-perspective` build without creating
`leijun-perspective/SKILL.md` yet. That is intentional: once a real
`<slug>-perspective/SKILL.md` exists, MBA's panel resolver treats the judge as
available. We should only create it after the six research files and the draft
persona pass quality checks.

## Build Goal

Create a Lei Jun perspective skill that can judge auto brands from an
operator-founder point of view:

- software-to-hardware migration
- consumer electronics supply chain
- "good product + honest price" brand contract
- founder-as-super-IP distribution
- long-cycle manufacturing risk
- ecosystem closure: phone / OS / car / home

The first dogfood target should be:

```text
/mba xiaomi --industry auto --quick --panel-drop leijun
```

Use `--panel-drop leijun` when judging Xiaomi itself unless we explicitly add a
conflict disclaimer. For non-Xiaomi auto brands, `leijun` can run normally.

## Why Lei Jun First

The auto-panel PRD recommends Path A: build one judge before batch-building all
five. Lei Jun is the best first judge because his source density is unusually
high and his perspective bridges the existing MBA default panel with the new
auto panel:

- annual speeches from 2020-2024 create a time series of self-narration
- the 2024 SU7 launch and annual speech expose a complete automotive go-to-market
  argument
- annual speeches and launch / Q&A material already provide enough public method
  backbone for v1; `Xiaomi Entrepreneurship Thinking` is a future refresh source
  unless legitimate chapter notes are added
- his public voice is distinctive enough to test whether an "auto operator"
  perspective can stay separate from Fusheng / Jobs / Zhang Yiming

## Source Inventory

Legend:

- **P0**: must read before drafting SKILL.md
- **P1**: useful supporting evidence
- **Primary**: Lei Jun / Xiaomi first-person or official material
- **Secondary**: press / third-party interpretation

| Priority | Type | Source | Use |
|---|---|---|---|
| P0 | Primary mirror | `2024 雷军年度演讲全文：小米造车，勇气从何而来，又如何冲出重围？` — Digitaling mirror, says author Lei Jun and first published by Xiaomi. URL: https://www.digitaling.com/articles/1241022.html | Core SU7 origin story, "勇气" frame, 1000-day auto journey, founder risk posture |
| P0 | Primary mirror | `小米汽车发布会文字完整版：人车合一，我心澎湃` — Digitaling mirror, says author account Lei Jun. URL: https://www.digitaling.com/articles/1056740.html | SU7 launch pitch, pricing, R&D spend, testing scale, smart-driving claims, ecosystem closure |
| P0 | Primary mirror | `2023 雷军年度演讲全文：成长的经历和感悟` — Digitaling mirror, says author Lei Jun and first published by Xiaomi. URL: https://www.digitaling.com/articles/962891.html | Technology strategy upgrade, `(software x hardware)^AI`, long-term R&D, growth narrative |
| P0 | Primary / transcript PDF | `2022 年度演讲：穿越人生低谷的感悟` PDF. URL: https://csrc.xmu.edu.cn/index_cn/article_pdf/202208131.pdf | Failure / low-point handling, Xiaomi method, book launch, R&D escalation |
| P0 | Primary mirror | `2021 雷军年度演讲：我的梦想，我的选择` — Sina mirror. URL: https://finance.sina.cn/tech/2021-08-10/detail-ikqcfncc2102383.d.html | Early self-narrative and "choice" frame; compare with 2024 "courage" frame |
| P0 | Primary mirror | `2023 武汉大学毕业典礼演讲：相信自己，每个人的人生都有无限可能` — IT之家 mirror. URL: https://www.ithome.com/0/701/013.htm | Personal origin story, confidence / choice rhetoric, non-product public voice |
| P1 | Official / JS-heavy | `Lei Jun Annual Speech 2024` — Xiaomi Global. URL: https://www.mi.com/global/event/lei-jun-annual-speech-2024/ | Official landing page confirms global framing, but content is JS-light in fetch; use as source pointer, not main transcript |
| P1 | Secondary / state media | Xinhua: `小米首款新能源汽车正式发布`. URL: https://www.news.cn/20240328/7ba29784a82b429c9f175366bf07d750/c.html | External factual check for SU7 launch date, price range, delivery plan, factory scale |
| P1 | Secondary / press | 证券时报 / IT之家 / 第一财经 coverage around 2022-2024 speeches | Cross-check numerical claims and public reception; do not use as voice source |
| P2 | Primary / book | `小米创业思考` | Future refresh only. Do not cite in production v1 unless legitimate chapter notes or reliable short excerpts are added |

## Research File Plan

Create the six standard perspective research files only after source extraction:

```text
leijun-perspective/
├── SKILL.md                         # create only after 01-06 are drafted
└── references/research/
    ├── 00-prescan.md                # copy/adapt this file
    ├── 01-writings.md               # annual speeches + launch scripts; book excerpts only in future refresh
    ├── 02-conversations.md          # interviews, launch Q&A, CCTV/long-form if available
    ├── 03-expression-dna.md         # sentence patterns, repeated words, launch rhetoric
    ├── 04-external-views.md         # press / market / criticism, clearly separated
    ├── 05-decisions.md              # Kingsoft, Joyo, Xiaomi phone, high-end, car, chip
    └── 06-timeline.md               # 1969-2024/2025 public timeline
```

## Hypotheses To Test

Do not bake these into SKILL.md until the sources support them.

1. **Engineer + marketer + value believer**: Lei Jun's public voice fuses engineering specificity, mass-market pricing morality, and founder IP warmth.
2. **"Honest premium" rather than cheapness**: The Xiaomi contract is not lowest price; it is high perceived value under a trustable price ceiling.
3. **Founder risk as distribution**: His personal credibility becomes a launch channel, especially for SU7, but also creates conflict-of-interest risk when judging Xiaomi.
4. **Ecosystem closure**: Phone, OS, home, and car are not separate categories in his frame; they are one user life surface.
5. **Long-cycle humility**: In auto, he speaks less like "move fast" internet founder and more like an operator asking for time, testing, and manufacturing respect.

## Anti-Fabrication Boundaries To Design

The eventual SKILL.md must explicitly prohibit:

- claiming private conversations with Xiaomi / auto founders unless directly sourced
- inventing 2025+ sales, delivery, accident, or chip numbers from memory
- using political or personal-life speculation
- judging Xiaomi without a visible conflict disclaimer, or skipping `leijun` for Xiaomi when the panel supports dropping judges
- using third-party praise / criticism as Lei Jun's own position
- turning Lei Jun into a generic "性价比" caricature; source notes must preserve the shift toward premium / tech / automotive risk

## Immediate Next Tasks

1. Extract notes from the six P0 sources into `01-writings.md`, preserving source URLs and dates.
2. Search for long-form interviews / Q&A where Lei Jun answers rather than performs a keynote; put those in `02-conversations.md`.
3. Build `03-expression-dna.md` from direct language samples only.
4. Draft the SKILL only after `01`, `03`, `05`, and `06` have enough material to pass quality checks.
5. Add a panel-level conflict rule before enabling `leijun` in `auto.yaml` for Xiaomi audits.
