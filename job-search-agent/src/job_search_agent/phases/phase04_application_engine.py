"""Phase 04 -- application engine (tracker + follow-up drafter).

This phase is split deliberately: deciding *which* rows are due for a
follow-up, marking them drafted, and recomputing the funnel snapshot are
all pure Python (see `followups.py`) -- no model call, same answer every
time, fully unit-tested. The model is invoked for exactly one thing: writing
the follow-up message text for rows that are newly due. It gets read access
to the fact base (for one optional proof point) and write access only to
the review queue -- never to `application_tracker.csv`, which stays a
deterministic system of record that only this module's own code updates.

Run with: `job-search-agent run phase04`
"""

from __future__ import annotations

from datetime import date

from ..config import get_paths, ensure_state_files
from ..followups import (
    compute_due_rows,
    funnel_snapshot,
    mark_drafted,
    read_tracker,
    write_tracker,
)
from ..runner import run_agent

SYSTEM_PROMPT = """\
You are the Phase 04 follow-up drafter. You have been handed an exact list
of applications that are newly due for a follow-up -- that decision has
already been made deterministically outside of you; do not re-derive it or
second-guess the list.

For each row in the list, draft a short, specific follow-up message (3-5
sentences): reference the real company and role, restate genuine interest,
ask one light, specific question about status or timeline. If this is a
SECOND follow-up, say plainly this is likely the last check-in on this one
and that you won't chase further after it.

You may read `fact_base.md` and, if one fits naturally, use exactly one
line tagged [VERIFIED] as a proof point -- never a [NEEDS INPUT] or
[RECONSTRUCTED] line, and never force a proof point in if none fits.

Prepend one dated block per row to `followups_queue.md`, immediately after
the "NEWEST AT TOP" marker, in the existing format of that file. Keep every
earlier entry unchanged. You do not have write access to the tracker file
and should not try to edit it -- that bookkeeping happens outside this
conversation. End with a one-line list of which companies you drafted for.
"""


def _format_due_list(due_rows) -> str:
    lines = []
    for d in due_rows:
        lines.append(
            f"- {d.company} — {d.role} — {d.which} follow-up (day {d.window[0]}-{d.window[1]}, "
            f"{d.days_silent} days silent)"
        )
    return "\n".join(lines)


def run() -> str:
    paths = get_paths()
    ensure_state_files(paths)

    rows = read_tracker(paths.tracker_csv)
    today = date.today()
    due_rows = compute_due_rows(rows, today)

    if not due_rows:
        snapshot = funnel_snapshot(rows, today)
        _write_dashboard(paths, snapshot, today, drafted_for=[])
        return (
            f"No rows due for a follow-up today. Funnel: {snapshot['open_count']} open, "
            f"{snapshot['closed_count']} closed, {snapshot['total']} total. No model call made."
        )

    prompt = (
        "Draft follow-ups for exactly these newly-due rows, and only these:\n\n"
        + _format_due_list(due_rows)
        + f"\n\nWrite each draft into {paths.followups_queue_md.name}."
    )

    transcript = run_agent(
        prompt,
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=["Read", "Write"],
        cwd=paths.state_dir,
    )

    # Deterministic bookkeeping happens after the drafts are written, by
    # code -- not by the model, and not before the drafts exist.
    rows = mark_drafted(rows, due_rows)
    write_tracker(paths.tracker_csv, rows)

    snapshot = funnel_snapshot(rows, today)
    drafted_for = [f"{d.company} ({d.which})" for d in due_rows]
    _write_dashboard(paths, snapshot, today, drafted_for=drafted_for)

    return (
        transcript
        + f"\n\n[bookkeeping] Drafted for: {', '.join(drafted_for)}. "
        f"Funnel: {snapshot['open_count']} open, {snapshot['closed_count']} closed."
    )


def _write_dashboard(paths, snapshot: dict, today: date, drafted_for: list[str]) -> None:
    stage_lines = "\n".join(f"- {stage}: {count}" for stage, count in sorted(snapshot["by_stage"].items()))
    denom = snapshot["total"] or 1
    response_rate = round(100 * (snapshot["total"] - snapshot["by_stage"].get("Ghosted", 0)) / denom, 1)
    drafted_line = ", ".join(drafted_for) if drafted_for else "none"
    content = f"""\
# Application Funnel Dashboard

_Last updated: {today.isoformat()}_ (deterministic snapshot -- regenerated
every run from `application_tracker.csv`, not a log; this file always holds
only the current counts.)

**Totals:** {snapshot['total']} applications tracked -- {snapshot['open_count']} open
(Applied/Screening), {snapshot['closed_count']} closed out.

**By stage:**
{stage_lines or '- (no rows yet)'}

**Applied in the last 7 days:** {snapshot['applied_last_7_days']}

**Rough non-ghosted rate:** {response_rate}% of tracked applications are not marked Ghosted.

**Follow-ups drafted this run:** {drafted_line}
"""
    paths.funnel_dashboard_md.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    run()
