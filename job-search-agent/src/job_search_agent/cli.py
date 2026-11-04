"""Command-line entrypoint.

    job-search-agent run phase00     # market watcher (sourcing + scoring)
    job-search-agent run phase01     # proof factory (teardown drafter)
    job-search-agent run phase04     # application engine (tracker + follow-ups)
    job-search-agent score jd.txt    # deterministic JD scorer, standalone
"""

from __future__ import annotations

import argparse
import logging
import sys

PHASES = {
    "phase00": "Market watcher: source + score new PM postings into a review queue.",
    "phase01": "Proof factory: draft one LinkedIn teardown post per run.",
    "phase04": "Application engine: chase silent applications, update the funnel.",
}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    # `score` takes its own argparse-style flags (--text, --batch, ...) that
    # look exactly like top-level flags to argparse's subparser machinery,
    # so hand off to the scorer's own parser directly rather than nesting it
    # under this CLI's subparsers (nargs=REMAINDER doesn't play well with a
    # parent parser that also defines optional flags).
    if argv and argv[0] == "score":
        from . import scorer

        sys.argv = ["job-search-agent score", *argv[1:]]
        scorer.main()
        return 0

    parser = argparse.ArgumentParser(prog="job-search-agent", description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true", help="Log each tool call the agent makes")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run one phase agent")
    run_parser.add_argument("phase", choices=sorted(PHASES))

    sub.add_parser("score", help="Run the deterministic JD scorer directly, no agent (see: job-search-agent score --help)")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(message)s")

    if args.command == "run":
        module = __import__(f"job_search_agent.phases.{args.phase}_{_SUFFIX[args.phase]}", fromlist=["run"])
        print(module.run())
        return 0

    parser.print_help()
    return 1


_SUFFIX = {
    "phase00": "market_watcher",
    "phase01": "proof_factory",
    "phase04": "application_engine",
}


if __name__ == "__main__":
    sys.exit(main())
