# Wuying Cloud Browser — How to Use It in This Skill

The Wuying (无影) cloud browser is provisioned via Alibaba Cloud's AgentBay service. The
project ships with a one-shot helper at `~/mba/wuying_open.py` that creates a session and
prints `SESSION_ID` + `RESOURCE_URL`.

This skill uses Wuying for things `WebFetch` can't do well:
- X / Twitter search results (rate-limited / blocked for unauth fetch)
- 小红书 (RedNote), 抖音, Bilibili, 知乎 — Chinese sites with anti-bot
- App store listings with dynamic comment loading
- Login-walled press archives
- Anything requiring a JS render to extract content

## One-shot session lifecycle

### 1. Create

```bash
ssh <MAC_USER>@<MAC_HOST> 'cd ~/mba && python3 wuying_open.py'
```

Output:
```
===
SESSION_ID=<id>
RESOURCE_URL=<wss-url>
===
Session left ALIVE. To delete later, run:
  python3 -c "..."
```

Capture both `SESSION_ID` and `RESOURCE_URL`.

### 2. Drive via agent-browser CLI

`agent-browser` 0.27.0 is installed on John (`/opt/homebrew/bin/agent-browser`).
**Important:** PATH on non-login SSH does not include `/opt/homebrew/bin` — use a login shell
or the absolute path:

```bash
ssh <MAC_USER>@<MAC_HOST> 'bash -lc "agent-browser <command>"'
```

The agent-browser SKILL.md stub is at `~/.claude/skills/agent-browser/SKILL.md` on John —
read it for the exact subcommand surface (navigate, click, type, screenshot, extract).

If agent-browser does not natively support attaching to an external CDP/WSS endpoint
(check `agent-browser --help`), fall back to:
- Driving via Playwright/Puppeteer scripts that connect to `RESOURCE_URL`
- Or having the user open `RESOURCE_URL` in their local browser and walk through manually
  while you observe (only acceptable as a last resort — note this in the wuying_browse.md log)

### 3. Tear down (REQUIRED — sessions cost money)

After the cloud-browser leg finishes, delete the session:

```bash
ssh <MAC_USER>@<MAC_HOST> "cd ~/mba && python3 -c \"
from agentbay import AgentBay
import os
api_key = open('.env').read().split('WUYING_API_KEY=')[1].split('\\n')[0].strip()
c = AgentBay(api_key=api_key)
if hasattr(c, 'delete_by_id'):
    c.delete_by_id('${SESSION_ID}')
    print('deleted ${SESSION_ID}')
\""
```

Log the teardown (or its failure) in `wuying_browse.md`. Never silently leave a session alive.

## What to capture per platform

### X / Twitter
- 10 latest posts mentioning the brand or founder handle
- For each: text, post URL, timestamp, like/repost/reply count
- Sentiment skew (favorable / mixed / hostile)

### RedNote (小红书)
- Top 10 posts (by engagement) for the brand keyword
- Author profile cohort (KOL / 素人 / 品牌官号)
- Comment top-3 sentiments per post

### Bilibili
- Top 5 videos by views — title, uploader, view count, like-rate, comment top-3
- Note distinct angles (评测 / 教程 / 吐槽 / 二次创作)

### Chinese tech press (36kr / 虎嗅 / 钛媒体)
- 3 most recent articles — headline, author, date, slant (founder-driven / outsider /
  re-published PR)

### Brand's own surfaces
- Hero copy (screenshot + transcribed)
- Footer / about page (founding story version)
- Pricing page if any
- Top-of-funnel CTA wording

## Output format — `wuying_browse.md`

```markdown
# Wuying browse — {BRAND}

**Session:** SESSION_ID=...
**Created:** {ISO timestamp}
**Torn down:** {ISO timestamp} ({status})

## X / Twitter
{table or bullets}

## RedNote
{...}

## Bilibili
{...}

## Press
{...}

## Brand-owned surfaces
{...}

## Surprises (vs open-web findings)
{bullets — what only this leg surfaced}

## Screenshots
{paths — keep all under /tmp/mba-screenshots/{brand-slug}/}
```

## Failure modes

- **Wuying API key missing** — the `.env` file on John must have `WUYING_API_KEY=...`. If
  it's still `your_api_key_here`, abort the cloud-browser leg and tell the user.
- **`agentbay` Python pkg missing** — `pip install --user agentbay-sdk` (or whatever the
  exact package name is per the team's convention; `wuying_open.py` imports `agentbay`).
- **Session create succeeds but RESOURCE_URL is empty** — the SDK version may not surface
  it. Re-check by calling the AgentBay describe-session API directly. Don't proceed with an
  unknown URL.
- **agent-browser can't attach** — degrade to "manual open" and ask the user to navigate;
  document the screenshots they take. Do NOT silently skip the leg.

## Cost discipline

Sessions accrue per-minute cost. Two rules:
1. One session per skill invocation. If you finish a list of platforms and need more later,
   create a new session — don't leave one parked.
2. Always confirm teardown in `wuying_browse.md`. The Lead reads this section in Phase 3
   and will block the report if teardown is missing.
