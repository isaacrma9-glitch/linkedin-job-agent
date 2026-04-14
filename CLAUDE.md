# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the agent

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill in credentials
cp .env.example .env

# Run locally
python src/main.py
```

## Required environment variables

| Variable | Description |
|---|---|
| `DISCORD_BOT_TOKEN` | Discord bot token (stored in `~/.claude/channels/discord/.env`) |
| `DISCORD_CHANNEL_ID` | Isaac's DM channel ID: `1485389933807013932` |
| `GMAIL_USER` | `isaac.rma9@gmail.com` |
| `GMAIL_APP_PASSWORD` | 16-char Google App Password |

All four are also stored as GitHub Actions secrets in the repo.

## Architecture

```
src/
  profile.py       — Search queries and skill keywords (edit this to tune results)
  job_searcher.py  — Scrapes LinkedIn guest API (no auth required)
  scorer.py        — Scores each job 0-100 based on skill/role keyword matches
  deduplicator.py  — Persists seen job IDs to data/seen_jobs.json
  notifier.py      — Sends top 10 as Discord embeds + all 30 as Gmail HTML report
  main.py          — Orchestrator: fetch → score → dedup → cap 30 → notify
```

## How scoring works

`scorer.py` assigns points per keyword match: title matches score 6 pts each, snippet matches 2 pts, role matches up to 30 pts, and location bonus 10 pts. Max 100. Jobs below `PROFILE["min_score"]` (default 20) are dropped before the 30-job cap is applied.

## Tuning search results

All customization is in `src/profile.py`:
- `PROFILE["skills"]` — keywords scored against title/snippet
- `PROFILE["target_roles"]` — high-weight role matches
- `PROFILE["min_score"]` — raise to get fewer but higher-quality results
- `SEARCH_QUERIES` — list of `{keywords, location}` dicts passed to LinkedIn

## LinkedIn scraping

Uses the public guest endpoint `/jobs-guest/jobs/api/seeMoreJobPostings/search` — no login needed. Includes a 1.5–3s random delay between paginated requests to avoid rate limiting. If LinkedIn changes their HTML card structure, update `_parse_job_cards()` in `job_searcher.py`. The `f_TPR=r86400` param filters to last 24 hours.

## Schedule

GitHub Actions runs **Tuesday, Thursday and Sunday at 9:00 AM Costa Rica time** (UTC-6 → `0 15 * * 0,2,4`). After each run, `data/seen_jobs.json` is committed back to the repo to persist deduplication state across runs.
