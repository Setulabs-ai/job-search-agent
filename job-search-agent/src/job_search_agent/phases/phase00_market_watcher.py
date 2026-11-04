"""Phase 00 -- market-watcher agent.

Automate tier of "Read the Market & Pick Your Lane": watches a configured
list of target companies and job boards, skips anything already logged,
scores new postings Builder PM / Integrator PM / Hybrid with the
deterministic scorer tool, and appends everything new to a draft-to-approve
review queue. Nothing here applies to anything or messages anyone -- it
only ever proposes what's worth your attention.

Run with: `job-search-agent run phase00`
"""

from __future__ import annotations

import yaml

from ..config import get_paths, ensure_state_files
from ..mcp_tools import scoring_server
from ..runner import run_agent

SYSTEM_PROMPT = """\
You are the Phase 00 market-watcher agent for a PM job search automation
system. Your ONLY job this run: find new, genuinely open product-manager
job postings from the configured target list, score each one, and log
what's new to the review queue. You never apply to anything, never message
anyone, and never mark anything as applied -- that's a human action logged
separately.

Rules:
1. Read `seen_postings.md` first. Anything already listed there (by URL) is
   already logged -- skip it, don't re-fetch it, don't re-score it.
2. Read `config/targets.yaml` for the companies and boards to check.
3. For each target, search for current PM openings (WebSearch / WebFetch).
   If a direct fetch is blocked, note that and move on -- don't retry the
   same source more than once.
4. For every genuinely new posting, call the `score_job_description` tool
   with the posting's text/snippet -- do not score it yourself by eye, the
   tool is deterministic and the whole point is that triage is reproducible.
5. Append new postings to `new_matches.md` as one new dated run block at the
   top (keep the "NEWEST RUN AT TOP" convention already in the file), with
   company, title, link, lean, and a one-line reason.
6. Append the same postings' dedupe keys (date | company | title | url) to
   `seen_postings.md` so they're never re-logged.
7. End with a one-line run summary: sources checked, new postings found, by
   lean category.

Never auto-apply, never claim you applied, never contact anyone. This is a
draft-to-approve queue only -- a human reviews `new_matches.md` themselves.
"""


def run() -> str:
    paths = get_paths()
    ensure_state_files(paths)

    targets_path = paths.targets_yaml
    if targets_path.exists():
        targets = yaml.safe_load(targets_path.read_text(encoding="utf-8")) or {}
    else:
        targets = {}
    n_companies = len(targets.get("companies", []))
    n_boards = len(targets.get("boards", []))

    prompt = (
        f"Run today's market-watcher sweep. Config has {n_companies} target "
        f"companies and {n_boards} job boards (see config/targets.yaml). "
        f"State files to use: {paths.seen_postings_md.name}, {paths.new_matches_md.name}."
    )

    return run_agent(
        prompt,
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=["WebSearch", "WebFetch", "Read", "Write", "mcp__job-search-scoring__score_job_description"],
        cwd=paths.state_dir,
        mcp_servers={"job-search-scoring": scoring_server()},
    )


if __name__ == "__main__":
    run()
