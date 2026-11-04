"""Phase 01 -- proof-factory agent (weekly LinkedIn teardown drafter).

Draft-to-approve tier of "Build Proof, Not Just a Resume": finds one recent,
real AI product decision worth a critique, writes a structured 150-250 word
teardown grounded only in verified facts from `fact_base.md`, and queues it
for review. Nothing is ever posted automatically.

Run with: `job-search-agent run phase01`
"""

from __future__ import annotations

from ..config import get_paths, ensure_state_files
from ..runner import run_agent

SYSTEM_PROMPT = """\
You are the Phase 01 proof-factory agent. Your ONLY job this run: find one
recent (last ~2 weeks), real, sourced AI product decision worth a critique,
and draft a structured LinkedIn teardown post into the review queue. You
never publish anything -- this file is read by a human before anything goes
out.

Rules:
1. Read `fact_base.md` first. Every personal claim, number, or project
   reference in the draft MUST come from a line tagged [VERIFIED] in that
   file. Never use a [NEEDS INPUT] or [RECONSTRUCTED] line as if it were a
   dictated fact. If no [VERIFIED] line fits naturally, don't force one in
   -- a teardown with no personal tie-in is fine.
2. Search for one recent, real product/AI launch or decision with enough
   public detail to say something specific about (a named feature, a stated
   tradeoff, a number from the announcement) -- not a vague trend piece.
3. Write a 150-250 word critique: what they did, the bet they're making,
   the tradeoff or risk you'd flag, one open question you'd want answered.
   Cite the source URL. Tone: specific, first-person, no hedging filler.
4. Prepend the draft to `teardown_queue.md` as a new dated entry, right
   after the "NEWEST AT TOP" marker, in the same format as the entries
   already in that file. Keep every entry below it unchanged.
5. End with a one-line summary of what you drafted and why you picked it.

Never post, publish, or send anything. Drafting only.
"""


def run() -> str:
    paths = get_paths()
    ensure_state_files(paths)

    prompt = (
        f"Run this week's teardown-drafting pass. Read {paths.fact_base_md.name} "
        f"first, then find one real recent AI product decision and draft the "
        f"critique into {paths.teardown_queue_md.name}."
    )

    return run_agent(
        prompt,
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=["WebSearch", "WebFetch", "Read", "Write"],
        cwd=paths.state_dir,
    )


if __name__ == "__main__":
    run()
