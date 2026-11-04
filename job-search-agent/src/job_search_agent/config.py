"""Shared configuration for every phase agent.

Nothing here talks to the network or the model -- it just resolves paths and
a couple of env-overridable knobs, so the phase modules and the tests can
both import it cheaply.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Paths:
    """Where each phase reads/writes its state.

    Real, personal state lives under `state/` and is gitignored -- it is
    created on first run (see `ensure_state_files`). `examples/` ships
    sanitized, fictional sample data so the repo is useful (and safe to look
    at) before you've pointed it at your own job search.
    """

    root: Path
    state_dir: Path
    config_dir: Path
    examples_dir: Path

    @property
    def tracker_csv(self) -> Path:
        return self.state_dir / "application_tracker.csv"

    @property
    def seen_postings_md(self) -> Path:
        return self.state_dir / "seen_postings.md"

    @property
    def new_matches_md(self) -> Path:
        return self.state_dir / "new_matches.md"

    @property
    def teardown_queue_md(self) -> Path:
        return self.state_dir / "teardown_queue.md"

    @property
    def followups_queue_md(self) -> Path:
        return self.state_dir / "followups_queue.md"

    @property
    def funnel_dashboard_md(self) -> Path:
        return self.state_dir / "funnel_dashboard.md"

    @property
    def fact_base_md(self) -> Path:
        return self.state_dir / "fact_base.md"

    @property
    def targets_yaml(self) -> Path:
        return self.config_dir / "targets.yaml"


def get_paths() -> Paths:
    root = Path(os.environ.get("JOB_SEARCH_AGENT_ROOT", REPO_ROOT))
    state_dir = Path(os.environ.get("JOB_SEARCH_AGENT_STATE_DIR", root / "state"))
    return Paths(
        root=root,
        state_dir=state_dir,
        config_dir=root / "config",
        examples_dir=root / "examples",
    )


# Model + run knobs. None means "let the Claude Agent SDK / CLI pick its
# current default" -- deliberately not hardcoded to one model string so this
# doesn't go stale.
DEFAULT_MODEL = os.environ.get("JOB_SEARCH_AGENT_MODEL") or None
DEFAULT_MAX_TURNS = int(os.environ.get("JOB_SEARCH_AGENT_MAX_TURNS", "40"))

# Follow-up cadence (days of silence). Matches the system this was built
# for: one nudge at day 7-10, one more at day 21-28, then stop.
FIRST_FOLLOWUP_WINDOW = (7, 10)
SECOND_FOLLOWUP_WINDOW = (21, 28)

# Stages past which the application engine stops chasing a row.
CLOSED_STAGES = {"Interviewing", "Offer", "Rejected", "Ghosted", "Withdrawn"}


def ensure_state_files(paths: Paths) -> None:
    """Seed `state/` from `examples/` on first run, without ever overwriting
    real state that already exists."""
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    seeds = {
        paths.tracker_csv: paths.examples_dir / "application_tracker.example.csv",
        paths.seen_postings_md: paths.examples_dir / "seen_postings.example.md",
        paths.new_matches_md: paths.examples_dir / "new_matches.example.md",
        paths.teardown_queue_md: paths.examples_dir / "teardown_queue.example.md",
        paths.followups_queue_md: paths.examples_dir / "followups_queue.example.md",
        paths.funnel_dashboard_md: paths.examples_dir / "funnel_dashboard.example.md",
        paths.fact_base_md: paths.examples_dir / "fact_base.example.md",
    }
    for dest, seed in seeds.items():
        if not dest.exists() and seed.exists():
            dest.write_text(seed.read_text(encoding="utf-8"), encoding="utf-8")
