"""
Log Agent — plain async Python, no LLM.

Fetches (mock) ELK logs for the incident's service and pattern-matches for
a known error signature. Pure worker logic: scenario in, LogFinding out.
"""

from agents.base import EmitFn, TraceEvent, emit
from telemetry.elk_mock import LogFinding, fetch_logs
from telemetry.scenarios import Scenario


class LogAgent:
    name = "Log Agent"

    async def analyze(
        self,
        scenario: Scenario,
        events: list[TraceEvent],
        run_start: float,
        on_event: EmitFn = None,
        seed: int | None = None,
    ) -> LogFinding:
        await emit(events, run_start, on_event, self.name, f"Scanning ELK logs across pods of {scenario.service}…")

        finding = await fetch_logs(scenario, seed=seed)

        await emit(
            events,
            run_start,
            on_event,
            self.name,
            f"Isolated {finding.event} on pod {finding.pod} "
            f"(scanned {finding.lines_scanned} lines, matched at {finding.timestamp})",
            level="success",
        )
        return finding
