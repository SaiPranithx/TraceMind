"""
Metrics Agent — plain async Python, no LLM.

Fetches (mock) Prometheus data for the incident's service and classifies
the anomaly shape. This is pure worker logic: it receives a scenario and
returns a MetricsFinding, nothing else.
"""

import time

from agents.base import EmitFn, TraceEvent, emit
from telemetry.prometheus_mock import MetricsFinding, fetch_metrics
from telemetry.scenarios import Scenario


class MetricsAgent:
    name = "Metrics Agent"

    async def analyze(
        self,
        scenario: Scenario,
        events: list[TraceEvent],
        run_start: float,
        on_event: EmitFn = None,
        seed: int | None = None,
    ) -> MetricsFinding:
        await emit(events, run_start, on_event, self.name, "Fetching high-dimensional Prometheus metrics…")

        finding = await fetch_metrics(scenario, seed=seed)

        delta_pct = round(((finding.end_value - finding.start_value) / max(finding.start_value, 1e-6)) * 100)
        await emit(
            events,
            run_start,
            on_event,
            self.name,
            f"Identified {finding.signature} on {finding.metric_name} "
            f"({finding.start_value:.0f}{finding.unit} -> {finding.end_value:.0f}{finding.unit}, "
            f"{delta_pct:+d}%, confidence {finding.confidence:.0%})",
            level="success",
        )
        return finding
