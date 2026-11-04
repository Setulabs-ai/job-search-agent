# job-search-agent

A small multi-agent system, built on the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python),
that runs the unglamorous parts of a job search: finding new postings worth
a look, keeping a weekly proof-of-work habit going, and chasing applications
that have gone quiet -- with a hard, enforced line between what the agent is
allowed to do on its own and what always stops for a human.

It's a port of a system I actually ran on myself for a Builder-PM job
search in India (2026): first as three scheduled Claude-powered automations
reading/writing shared docs, running daily/weekly for weeks against real
job boards and a real application tracker. This repo rebuilds that same
design as a standalone, open-source codebase anyone can run against their
own search, with their own API key, on their own schedule.

## Why this exists, and why it's built this way

Most "AI agent for X" demos either do everything through one model call
(no real structure) or automate the one step that should never be
automated (anything that reads, to a stranger, like it came from a human
who meant to send it). The actual hard part of agentic automation isn't
getting a model to do a task -- it's deciding *which* steps get full
autonomy, which get a human glance, and which never touch an agent at all.

This repo encodes that decision explicitly, as a reusable contract, not a
one-off judgment call per feature:

1. **Escalate on stakes, not task type.** Only externally irreversible
   actions (sent, published, applied-to, said on someone's behalf) or
   claims about you need a human. Everything else can run.
2. **Queues, not gates.** No agent here ever blocks waiting for approval of
   its last output -- it writes to a review queue and moves on. You clear
   the queue on your own schedule.
3. **Batch the interruptions.** One review file per phase, read whenever
   you want, not a notification per item.
4. **Deterministic logic stays deterministic.** Anything that should give
   the same answer every time for the same input -- is this JD a Builder or
   Integrator role, which tracker rows are overdue for a follow-up, what
   are the current funnel counts -- is plain Python, unit-tested, and never
   re-derived by a model call. The model is only invoked for the one thing
   it's actually needed for in each phase: finding things, and writing
   prose. See `scorer.py` and `followups.py`.

That last point also shows up in the code as an access-control boundary,
not just a convention: the phase04 agent that drafts follow-up messages
gets read access to a fact base and write access to a review queue --
and *no* access to the tracker file that's the actual system of record.
Only this repo's own (non-agentic) code updates that file, and only after
a draft has actually been written.

## The three agents

| Phase | What it does | Tools it gets | What it never does |
|---|---|---|---|
| `phase00` market watcher | Reads your target company/board list, finds new PM postings, scores each one Builder PM / Integrator PM / Hybrid with a deterministic keyword tool, logs what's new | WebSearch, WebFetch, Read, Write, `score_job_description` | Apply to anything, message anyone |
| `phase01` proof factory | Finds one recent, real AI product decision, drafts a sourced 150-250 word critique grounded only in your `[VERIFIED]` facts | WebSearch, WebFetch, Read, Write | Publish anything |
| `phase04` application engine | Computes (in plain Python) which tracked applications are silent 7-10 or 21-28 days, drafts a follow-up message for each one that's newly due, recomputes the funnel snapshot | Read, Write (queue only -- not the tracker) | Send anything, touch the tracker file itself, re-decide which rows are due |

Everything these agents produce lands in a markdown "review queue" file --
`new_matches.md`, `teardown_queue.md`, `followups_queue.md` -- that you read
and act on yourself. Nothing is ever posted, sent, or submitted by the
agent. The one real-world action every phase assumes stays yours: applying,
posting, and hitting send.

## Architecture

```
config/targets.yaml          <- companies & boards phase00 watches (yours, not committed real data)
state/                       <- your real, gitignored working files (seeded from examples/ on first run)
  application_tracker.csv       system of record -- only non-agent code writes this
  seen_postings.md               dedupe log for phase00
  new_matches.md                  phase00's review queue
  teardown_queue.md                phase01's review queue
  followups_queue.md                phase04's review queue
  funnel_dashboard.md                phase04's deterministic snapshot (overwritten each run)
  fact_base.md                        your own [VERIFIED]/[NEEDS INPUT]/[RECONSTRUCTED] facts
examples/                    <- sanitized, fictional starter versions of everything above
src/job_search_agent/
  scorer.py                  <- deterministic JD scorer (no model, no network)
  followups.py               <- deterministic due-date + funnel logic (no model, no network)
  mcp_tools.py                <- exposes scorer.py to the agent as an in-process tool call
  runner.py                    <- the one module that actually calls claude_agent_sdk.query()
  phases/
    phase00_market_watcher.py
    phase01_proof_factory.py
    phase04_application_engine.py
  cli.py                      <- `job-search-agent run <phase>` / `job-search-agent score`
tests/                        <- unit tests for the deterministic pieces, no API key required
```

## Setup

```bash
git clone <this repo>
cd job-search-agent
pip install -e .
cp .env.example .env   # fill in ANTHROPIC_API_KEY
```

Replace the placeholders before pointing this at a real search:

- `config/targets.yaml` -- your own target companies/boards.
- `state/fact_base.md` -- your own facts (created from `examples/fact_base.example.md`
  on first run; edit it in place). **Keep this file truthful and tagged** --
  phase01 and phase04 are instructed to only draft from lines marked
  `[VERIFIED]`.
- `state/application_tracker.csv` -- log a real application yourself; it's
  never written to by anything except you and this repo's own bookkeeping
  code.

`state/` is gitignored on purpose -- it holds your real applications and
your real resume facts. The sanitized `examples/` versions are what's
checked into git and what new users see first.

## Running it

```bash
job-search-agent run phase00     # sourcing + scoring
job-search-agent run phase01     # weekly proof-of-work draft
job-search-agent run phase04     # follow-ups + funnel snapshot
job-search-agent score jd.txt    # just the deterministic scorer, no agent, no API key needed
```

`phase04` is worth noting on its own: if nothing is due for a follow-up, it
never calls the model at all -- the due-row computation is plain Python and
answers that question for free. Try it right now, with no API key:

```bash
job-search-agent run phase04
# -> "No rows due for a follow-up today. Funnel: 1 open, 0 closed, 1 total. No model call made."
```

### Scheduling

`.github/workflows/scheduled_runs.yml` runs `phase00`/`phase04` daily and
`phase01` weekly via GitHub Actions, committing state changes back to the
repo (needs an `ANTHROPIC_API_KEY` repo secret). That's a drop-in
replacement for however the original version of this system was scheduled
day to day -- any cron runner works the same way:

```cron
30 2 * * *  cd /path/to/job-search-agent && job-search-agent run phase00 && job-search-agent run phase04
30 3 * * 1  cd /path/to/job-search-agent && job-search-agent run phase01
```

## Testing

```bash
pip install -e ".[dev]"
pytest
```

All 12 tests run with no API key and no network call -- they only exercise
`scorer.py` and `followups.py`, the two modules deliberately kept free of
any model dependency.

## What's deliberately *not* automated

The original system this was ported from also designed a Phase 03
(networking/referrals) automation, then explicitly chose not to build its
highest-autonomy version: identifying a named hiring manager or recruiter
from public profiles is a bad fit for available tooling without scraping
LinkedIn, which its own terms of service prohibit at any real volume. The
honest scope for that phase is a per-company research brief plus a drafted
outreach message, leaving contact-finding and the actual send fully human
-- and it's left out of this repo rather than faked. Interview prep and
negotiation support (phases 05/06 in the original design) were deferred for
the same reason: they only matter once there's a real screen or a real
offer to prep for, and building them speculatively would just be scope for
its own sake.

## License

MIT -- see `LICENSE`.
