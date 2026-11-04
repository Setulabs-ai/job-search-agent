"""Pure, deterministic logic for the application engine (phase04).

Deciding *which* tracker rows are due for a follow-up, and *when* a row
stops being chased, is bookkeeping -- it should give the same answer every
time for the same tracker + date, and it should be unit-testable without an
API key or a model call. Only the follow-up *message text* is generative;
that part lives in `phases/phase04_application_engine.py` and calls Claude
for exactly that one step.

This mirrors the automation contract the whole system is built on:
deterministic bookkeeping needs no approval and no model; anything that
reads like a claim or a message gets drafted, then a human sends it.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .config import CLOSED_STAGES, FIRST_FOLLOWUP_WINDOW, SECOND_FOLLOWUP_WINDOW

TRACKER_FIELDS = [
    "Company",
    "Tier",
    "Role",
    "Source/Recruiter",
    "Contacts",
    "Applied Date",
    "Last Touch",
    "Follow-ups Drafted",
    "Stage",
    "Notes",
]


@dataclass
class DueRow:
    index: int  # row position in the CSV (0-based, excluding header)
    company: str
    role: str
    days_silent: int
    which: str  # "first" or "second"
    window: tuple[int, int]


def read_tracker(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        return []
    with csv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_tracker(csv_path: Path, rows: list[dict]) -> None:
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TRACKER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def days_since_touch(row: dict, today: date) -> int | None:
    last_touch = _parse_date(row.get("Last Touch", ""))
    reference = last_touch or _parse_date(row.get("Applied Date", ""))
    if reference is None:
        return None
    return (today - reference).days


def compute_due_rows(rows: list[dict], today: date | None = None) -> list[DueRow]:
    """The only decision logic in the whole application engine. Given the
    tracker and today's date, return exactly the rows that are newly due for
    a first or second follow-up -- skipping anything past Applied/Screening,
    anything outside both windows, and anything already drafted for the
    window it's currently in.
    """
    today = today or date.today()
    due: list[DueRow] = []
    for i, row in enumerate(rows):
        stage = (row.get("Stage") or "").strip()
        if stage in CLOSED_STAGES:
            continue
        silent = days_since_touch(row, today)
        if silent is None:
            continue
        drafted = {d.strip() for d in (row.get("Follow-ups Drafted") or "").split(",") if d.strip()}

        lo1, hi1 = FIRST_FOLLOWUP_WINDOW
        lo2, hi2 = SECOND_FOLLOWUP_WINDOW
        if lo1 <= silent <= hi1 and "1" not in drafted:
            due.append(DueRow(i, row.get("Company", ""), row.get("Role", ""), silent, "first", FIRST_FOLLOWUP_WINDOW))
        elif lo2 <= silent <= hi2 and "2" not in drafted:
            due.append(DueRow(i, row.get("Company", ""), row.get("Role", ""), silent, "second", SECOND_FOLLOWUP_WINDOW))
    return due


def mark_drafted(rows: list[dict], due_rows: list[DueRow]) -> list[dict]:
    """Bookkeeping only -- never a platform-facing action, so it needs no
    human approval. Marking happens *after* a draft is actually written to
    the review queue, so a crash mid-run never marks a row that has no
    drafted message to show for it."""
    marker = {"first": "1", "second": "2"}
    for due in due_rows:
        row = rows[due.index]
        existing = {d.strip() for d in (row.get("Follow-ups Drafted") or "").split(",") if d.strip()}
        existing.add(marker[due.which])
        row["Follow-ups Drafted"] = ",".join(sorted(existing))
    return rows


def funnel_snapshot(rows: list[dict], today: date | None = None) -> dict:
    """Deterministic funnel counts -- no model call needed for arithmetic."""
    today = today or date.today()
    by_stage: dict[str, int] = {}
    applied_last_7_days = 0
    open_count = 0
    closed_count = 0
    for row in rows:
        stage = (row.get("Stage") or "Unknown").strip() or "Unknown"
        by_stage[stage] = by_stage.get(stage, 0) + 1
        if stage in CLOSED_STAGES:
            closed_count += 1
        else:
            open_count += 1
        applied = _parse_date(row.get("Applied Date", ""))
        if applied and (today - applied).days <= 7:
            applied_last_7_days += 1
    return {
        "total": len(rows),
        "by_stage": by_stage,
        "applied_last_7_days": applied_last_7_days,
        "open_count": open_count,
        "closed_count": closed_count,
    }
