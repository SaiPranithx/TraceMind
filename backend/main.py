"""
TraceMind CLI.

Week 2 deliverable: a full Supervisor -> Metrics/Log -> Synthesis run that
produces a correct report end-to-end with zero external dependencies.

Week 3 adds: set GEMINI_API_KEY (see synthesis_agent.py) and the same
command uses live LLM synthesis instead of the template — no code changes
needed here.

Usage:
    python main.py                          # random scenario
    python main.py --scenario memory-leak-checkout
    python main.py --list                   # show available scenarios
"""

import argparse
import asyncio
import random
import sys
import time

from agents.base import Alert
from agents.supervisor import SupervisorAgent
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from telemetry.scenarios import SCENARIOS, get_scenario

load_dotenv()
console = Console()


async def run(scenario_id: str | None, seed: int | None) -> None:
    scenario = get_scenario(scenario_id) if scenario_id else random.choice(SCENARIOS)

    console.print(Panel.fit(f"[bold]TraceMind[/bold] — simulating outage on {scenario.service}", border_style="yellow"))

    alert = Alert(
        incident_id=f"INC-{random.randint(1000, 9999)}",
        service=scenario.service,
        reason=f"anomalous {scenario.metric_name} detected",
        severity="critical",
        scenario_id=scenario.id,
    )

    async def on_event(event):
        color = {"info": "white", "success": "green", "error": "red"}[event.level]
        console.log(f"[{color}][{event.agent}][/{color}] {event.message}")

    supervisor = SupervisorAgent()
    result = await supervisor.handle_alert(alert, scenario, on_event=on_event, seed=seed)

    console.print()
    console.print(Panel(Markdown(result.report_markdown), title="Root-cause report", border_style="green"))

    with open("report.md", "w") as f:
        f.write(result.report_markdown)
    console.print(f"\n[dim]Report written to report.md — MTTI {result.mtti_seconds:.1f}s[/dim]")


def main():
    parser = argparse.ArgumentParser(description="TraceMind — simulate an incident and generate a root-cause report.")
    parser.add_argument("--scenario", help="scenario id to run (see --list)", default=None)
    parser.add_argument("--seed", type=int, default=None, help="random seed for reproducible mock data")
    parser.add_argument("--list", action="store_true", help="list available scenario ids and exit")
    args = parser.parse_args()

    if args.list:
        for s in SCENARIOS:
            console.print(f"[cyan]{s.id}[/cyan] — {s.display_name} ({s.service})")
        sys.exit(0)

    asyncio.run(run(args.scenario, args.seed))


if __name__ == "__main__":
    main()
