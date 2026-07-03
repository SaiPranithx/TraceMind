"""
Eval harness.

Runs the full pipeline against every scenario in the catalogue (optionally
multiple seeds each) and scores the resulting report against two things
that are actually checkable, not vibes:

  1. Structural consistency — does the report contain all four required
     sections? (This is where a claim like "100% data consistency" should
     come from — a real pass/fail check, not a guess.)
  2. Root-cause accuracy — does the report's Root Cause section mention
     enough of the scenario's expected keywords to count as correct?

Run:
    python -m eval.run_eval
    python -m eval.run_eval --seeds-per-scenario 3
"""

import argparse
import asyncio
import re
import time
from dataclasses import dataclass

from agents.base import Alert
from agents.supervisor import SupervisorAgent
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from telemetry.scenarios import SCENARIOS, Scenario

load_dotenv()
console = Console()

REQUIRED_SECTIONS = ("## Root cause", "## Evidence", "## Recommended actions", "## Confidence")
MIN_KEYWORD_MATCHES = 2  # a report is "correct" if it mentions at least this many expected keywords


@dataclass
class EvalRun:
    scenario_id: str
    seed: int
    mtti_seconds: float
    structurally_consistent: bool
    keyword_matches: int
    keywords_expected: int
    correct: bool


def check_structure(report: str) -> bool:
    return all(section in report for section in REQUIRED_SECTIONS)


def check_keywords(report: str, scenario: Scenario) -> int:
    report_lower = report.lower()
    return sum(1 for kw in scenario.root_cause_keywords if kw.lower() in report_lower)


async def run_one(scenario: Scenario, seed: int) -> EvalRun:
    alert = Alert(
        incident_id=f"EVAL-{scenario.id}-{seed}",
        service=scenario.service,
        reason=f"anomalous {scenario.metric_name} detected",
        severity="critical",
        scenario_id=scenario.id,
    )
    supervisor = SupervisorAgent()
    result = await supervisor.handle_alert(alert, scenario, seed=seed)

    structurally_consistent = check_structure(result.report_markdown)
    matches = check_keywords(result.report_markdown, scenario)
    correct = structurally_consistent and matches >= MIN_KEYWORD_MATCHES

    return EvalRun(
        scenario_id=scenario.id,
        seed=seed,
        mtti_seconds=result.mtti_seconds,
        structurally_consistent=structurally_consistent,
        keyword_matches=matches,
        keywords_expected=len(scenario.root_cause_keywords),
        correct=correct,
    )


async def run_eval(seeds_per_scenario: int) -> list[EvalRun]:
    runs: list[EvalRun] = []
    for scenario in SCENARIOS:
        for seed in range(seeds_per_scenario):
            run = await run_one(scenario, seed)
            runs.append(run)
    return runs


def print_report(runs: list[EvalRun]) -> None:
    table = Table(title="TraceMind eval results")
    table.add_column("Scenario")
    table.add_column("Seed")
    table.add_column("MTTI (s)")
    table.add_column("Structure OK")
    table.add_column("Keywords")
    table.add_column("Correct")

    for r in runs:
        table.add_row(
            r.scenario_id,
            str(r.seed),
            f"{r.mtti_seconds:.1f}",
            "✅" if r.structurally_consistent else "❌",
            f"{r.keyword_matches}/{r.keywords_expected}",
            "✅" if r.correct else "❌",
        )
    console.print(table)

    n = len(runs)
    structure_rate = sum(r.structurally_consistent for r in runs) / n
    accuracy = sum(r.correct for r in runs) / n
    max_mtti = max(r.mtti_seconds for r in runs)
    avg_mtti = sum(r.mtti_seconds for r in runs) / n

    console.print(f"\n[bold]Structural consistency:[/bold] {structure_rate:.0%} ({n} runs)")
    console.print(f"[bold]Root-cause accuracy:[/bold] {accuracy:.0%} ({n} runs, threshold={MIN_KEYWORD_MATCHES} keywords)")
    console.print(f"[bold]MTTI:[/bold] avg {avg_mtti:.1f}s, max {max_mtti:.1f}s (target <30s)")


def main():
    parser = argparse.ArgumentParser(description="Score TraceMind's Synthesis Agent against the scenario catalogue.")
    parser.add_argument("--seeds-per-scenario", type=int, default=1)
    args = parser.parse_args()

    runs = asyncio.run(run_eval(args.seeds_per_scenario))
    print_report(runs)


if __name__ == "__main__":
    main()
