#!/usr/bin/env python3
"""
scorer.py
=========
The one genuinely deterministic piece of the sourcing pipeline (phase00).

Scores a job description on a "Builder PM" <-> "Integrator PM" spectrum by
matching weighted signal phrases -- no model call, no network, same output
every time for the same input. That matters: the market-watcher agent (see
`phases/phase00_market_watcher.py`) uses this as a tool so that *triage* is
a deterministic function the agent calls, not a judgment the model re-makes
(and could re-make differently) every run. The model is only in the loop for
genuinely non-deterministic work: finding the postings in the first place.

USAGE
-----
Score one JD from a file:
    python3 -m job_search_agent.scorer jd.txt

Score one JD from stdin:
    cat jd.txt | python3 -m job_search_agent.scorer

Score every .txt file in a folder and write a summary CSV:
    python3 -m job_search_agent.scorer --batch ./jds/ --out scored_jds.csv

Score inline text:
    python3 -m job_search_agent.scorer --text "Own the roadmap, ship prototypes..."
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Signal dictionary
# ---------------------------------------------------------------------------
# Builder-PM phrases: shipping/prototyping, evals, model/agent fluency,
# technical hands-on signals. Integrator-PM phrases: stakeholder governance,
# enterprise rollout, program management. Calibrated against real 2026 JD
# language; edit freely for your own market.

BUILDER_SIGNALS: dict[str, float] = {
    r"\bship(ped|ping)?\b.{0,20}\b(prototype|feature|surface|product)": 3,
    r"\b(working|clickable|functional)\s+prototype": 3,
    r"\bhands[- ]?on\b": 2,
    r"\bbuild\s+(and\s+)?ship\b": 2.5,
    r"\b0\s*(to|→|-)\s*1\b|\bzero[- ]to[- ]one\b": 2,
    r"\bfounding\s+pm\b|\bfirst\s+pm\s+hire\b": 2.5,
    r"\bno[- ]?code\b|\blow[- ]?code\b": 1,
    r"\b(cursor|v0\.dev|bolt\.new|replit|lovable)\b": 3,
    r"\bevals?\b|\bevaluation\s+(framework|pipeline|harness)\b": 2.5,
    r"\boffline\s+(test|eval)s?\b": 2,
    r"\ba/?b\s*test(s|ing)?\b": 1.5,
    r"\bllm[- ]as[- ]a?[- ]?judge\b": 2.5,
    r"\bpass/fail\b|\brubric\b": 2,
    r"\bmodel\s+lifecycle\b": 2,
    r"\bfine[- ]?tun(e|ing)\b": 2,
    r"\brag\b|\bretrieval[- ]augmented\b": 2.5,
    r"\bagentic?\b|\bagent\s+orchestration\b|\bagent\s+workflows?\b": 2.5,
    r"\bprompt\s+(design|engineering)\b": 2,
    r"\btoken(s|ization)?\b.{0,15}\blatency\b|\blatency\b.{0,15}\btoken": 2,
    r"\bhallucinat(e|ion)\b": 1.5,
    r"\bcost\s*/\s*latency\s*/\s*quality\b|\bper[- ]request\b": 2,
    r"\bsql\b": 1,
    r"\bpython\b": 1.5,
    r"\bapi(s)?\b": 1,
    r"\bml\s+toolkit(s)?\b": 1.5,
    r"\bdeployment\s+(and\s+)?monitoring\b": 1.5,
}

INTEGRATOR_SIGNALS: dict[str, float] = {
    r"\bstakeholder\s+(management|alignment)\b": 2.5,
    r"\bcross[- ]functional\s+alignment\b": 2,
    r"\broadmap\s+governance\b": 2.5,
    r"\bprogram\s+management\b": 2,
    r"\brequirements?\s+gathering\b": 2,
    r"\bwrite\s+(a\s+)?prd(s)?\b|\bproduct\s+requirements?\s+document\b": 2,
    r"\benterprise\s+(rollout|deployment|customers?)\b": 2,
    r"\bchange\s+management\b": 2.5,
    r"\bcompliance\b|\blegal\s+review\b|\bprocurement\b": 2,
    r"\bscope\s*/\s*timeline\s*/\s*headcount\b|\bresource\s+allocation\b": 2,
    r"\bsteering\s+committee\b": 2.5,
    r"\bvendor\s+management\b|\brfp\b|\bsla\s+negotiation\b": 2,
    r"\bquarterly\s+business\s+review\b|\bqbr\b": 1.5,
    r"\bmulti[- ]?year\s+strategy\b": 1.5,
}


@dataclass
class ScoreResult:
    builder_score: float = 0.0
    integrator_score: float = 0.0
    builder_hits: list[str] = field(default_factory=list)
    integrator_hits: list[str] = field(default_factory=list)

    @property
    def lean(self) -> str:
        total = self.builder_score + self.integrator_score
        if total == 0:
            return "Unclear (too little signal -- read manually)"
        net = (self.builder_score - self.integrator_score) / total
        if net >= 0.35:
            return "Builder PM"
        if net <= -0.35:
            return "Integrator PM"
        return "Hybrid"

    @property
    def confidence(self) -> str:
        total = self.builder_score + self.integrator_score
        if total >= 12:
            return "High"
        if total >= 5:
            return "Medium"
        return "Low"

    def to_dict(self) -> dict:
        return {
            "builder_score": round(self.builder_score, 1),
            "integrator_score": round(self.integrator_score, 1),
            "lean": self.lean,
            "confidence": self.confidence,
            "builder_hits": self.builder_hits,
            "integrator_hits": self.integrator_hits,
        }


def score_jd(text: str) -> ScoreResult:
    """Keyword-heuristic scorer. No API key, no network, fully deterministic."""
    lowered = text.lower()
    result = ScoreResult()
    for pattern, weight in BUILDER_SIGNALS.items():
        matches = re.findall(pattern, lowered)
        if matches:
            result.builder_score += weight * len(matches)
            result.builder_hits.append(pattern)
    for pattern, weight in INTEGRATOR_SIGNALS.items():
        matches = re.findall(pattern, lowered)
        if matches:
            result.integrator_score += weight * len(matches)
            result.integrator_hits.append(pattern)
    return result


def print_report(result: ScoreResult, label: str = "") -> None:
    header = f"JD: {label}" if label else "JD"
    print(f"\n{'=' * 60}\n{header}\n{'=' * 60}")
    print(f"Builder signal score:    {result.builder_score:.1f}")
    print(f"Integrator signal score: {result.integrator_score:.1f}")
    print(f"Lean:                    {result.lean}")
    print(f"Confidence:              {result.confidence}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", nargs="?", help="Path to a JD text file")
    parser.add_argument("--text", help="Score inline text instead of a file")
    parser.add_argument("--batch", metavar="DIR", help="Score every .txt file in DIR")
    parser.add_argument("--out", metavar="CSV", default="scored_jds.csv", help="Output CSV for --batch")
    args = parser.parse_args()

    if args.batch:
        folder = Path(args.batch)
        files = sorted(folder.glob("*.txt"))
        if not files:
            print(f"No .txt files found in {folder}", file=sys.stderr)
            sys.exit(1)
        rows = []
        for f in files:
            text = f.read_text(encoding="utf-8", errors="ignore")
            result = score_jd(text)
            print_report(result, label=f.name)
            rows.append({"file": f.name, **{k: v for k, v in result.to_dict().items() if k != "builder_hits" and k != "integrator_hits"}})
        with open(args.out, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["file", "builder_score", "integrator_score", "lean", "confidence"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n\nWrote summary for {len(rows)} JDs to {args.out}")
        return

    if args.text:
        text = args.text
    elif args.file:
        text = Path(args.file).read_text(encoding="utf-8", errors="ignore")
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        parser.print_help()
        sys.exit(1)

    print_report(score_jd(text))


if __name__ == "__main__":
    main()
