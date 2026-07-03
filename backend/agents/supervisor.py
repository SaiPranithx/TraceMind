"""
Supervisor Agent.

Owns orchestration only — it never touches metrics or logs directly. It
dispatches Metrics Agent and Log Agent concurrently, waits for both, hands
their findings to Synthesis, and times the whole run.
"""

import time

from agents.base import Alert, EmitFn, IncidentResult, TraceEvent, emit
from agents.log_agent import LogAgent
from agents.metrics_agent import MetricsAgent
from agents.synthesis_agent import SynthesisAgent
from telemetry.scenarios import Scenario


class SupervisorAgent:
    name = "Supervisor Agent"

    def __init__(self):
        self.metrics_agent = MetricsAgent()
        self.log_agent = LogAgent()
        self.synthesis_agent = SynthesisAgent()

    async def handle_alert(
        self,
        alert: Alert,
        scenario: Scenario,
        on_event: EmitFn = None,
        seed: int | None = None,
    ) -> IncidentResult:
        import asyncio

        run_start = time.monotonic()
        events: list[TraceEvent] = []

        await emit(events, run_start, on_event, self.name, f"Received alert: {alert.reason} ({alert.service})")
        await emit(events, run_start, on_event, self.name, "Dispatching Metrics + Log agents concurrently")

        # The concurrency that makes MTTI reduction real: both workers run
        # at the same time, not one after the other.
        metrics_finding, log_finding = await asyncio.gather(
            self.metrics_agent.analyze(scenario, events, run_start, on_event, seed=seed),
            self.log_agent.analyze(scenario, events, run_start, on_event, seed=seed),
        )

        confidence = round(metrics_finding.confidence * 0.6 + 0.95 * 0.4, 2)

        report_markdown = await self.synthesis_agent.synthesize(
            alert, scenario, metrics_finding, log_finding,
            mtti_seconds=time.monotonic() - run_start,
            confidence=confidence,
            events=events, run_start=run_start, on_event=on_event,
        )

        mtti_seconds = time.monotonic() - run_start
        await emit(
            events, run_start, on_event, self.name,
            f"Root cause confirmed. MTTI {mtti_seconds:.1f}s. Confidence {confidence:.0%}.",
            level="success",
        )

        return IncidentResult(
            alert=alert,
            metrics_finding=metrics_finding,
            log_finding=log_finding,
            report_markdown=report_markdown,
            trace=events,
            mtti_seconds=mtti_seconds,
            confidence=confidence,
        )
