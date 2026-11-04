from datetime import date

from job_search_agent.followups import (
    compute_due_rows,
    funnel_snapshot,
    mark_drafted,
)


def _row(**kwargs):
    base = {
        "Company": "Acme",
        "Tier": "Stretch",
        "Role": "Senior PM",
        "Source/Recruiter": "",
        "Contacts": "",
        "Applied Date": "2026-01-01",
        "Last Touch": "2026-01-01",
        "Follow-ups Drafted": "",
        "Stage": "Applied",
        "Notes": "",
    }
    base.update(kwargs)
    return base


def test_row_due_for_first_followup_at_day_8():
    today = date(2026, 1, 9)  # 8 days after 2026-01-01
    rows = [_row()]
    due = compute_due_rows(rows, today)
    assert len(due) == 1
    assert due[0].which == "first"


def test_row_not_due_before_window():
    today = date(2026, 1, 5)  # 4 days silent
    rows = [_row()]
    assert compute_due_rows(rows, today) == []


def test_row_not_redrafted_once_marked():
    today = date(2026, 1, 9)
    rows = [_row(**{"Follow-ups Drafted": "1"})]
    assert compute_due_rows(rows, today) == []


def test_second_followup_window():
    today = date(2026, 1, 25)  # 24 days silent
    rows = [_row(**{"Follow-ups Drafted": "1"})]
    due = compute_due_rows(rows, today)
    assert len(due) == 1
    assert due[0].which == "second"


def test_closed_stage_is_never_chased():
    today = date(2026, 1, 9)
    for stage in ["Interviewing", "Offer", "Rejected", "Ghosted", "Withdrawn"]:
        rows = [_row(Stage=stage)]
        assert compute_due_rows(rows, today) == [], f"{stage} should not be chased"


def test_mark_drafted_appends_without_duplicating():
    today = date(2026, 1, 9)
    rows = [_row()]
    due = compute_due_rows(rows, today)
    rows = mark_drafted(rows, due)
    assert rows[0]["Follow-ups Drafted"] == "1"
    # Running it again for an already-marked window should not duplicate.
    due_again = compute_due_rows(rows, today)
    assert due_again == []


def test_funnel_snapshot_counts_open_vs_closed():
    rows = [
        _row(Stage="Applied"),
        _row(Stage="Screening"),
        _row(Stage="Rejected"),
        _row(Stage="Offer"),
    ]
    snap = funnel_snapshot(rows, date(2026, 1, 9))
    assert snap["total"] == 4
    assert snap["open_count"] == 2
    assert snap["closed_count"] == 2
    assert snap["by_stage"]["Applied"] == 1


def test_days_since_touch_falls_back_to_applied_date():
    rows = [_row(**{"Last Touch": "", "Applied Date": "2026-01-01"})]
    due = compute_due_rows(rows, date(2026, 1, 9))
    assert len(due) == 1
