"""
Shared data contracts used across all agents.

Defined once here so Supervisor/Metrics/Log/Synthesis all agree on the same
shapes — this is the "what each agent receives and returns" contract from
the architecture doc, made concrete in code.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from telemetry.elk_mock import LogFinding
from telemetry.prometheus_mock import MetricsFinding

EmitFn = Optional[Callable[["TraceEvent"], Awaitable[None]]]


@dataclass
class Alert:
    incident_id: str
    service: str
    reason: str
    severity: str
    scenario_id: str
    received_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class TraceEvent:
    """One line of the agent thought loop — what the frontend renders live."""

    agent: str
    message: str
    t_offset_ms: int          # milliseconds since the run started
    level: str = "info"        # info | success | error


@dataclass
class IncidentResult:
    alert: Alert
    metrics_finding: MetricsFinding
    log_finding: LogFinding
    report_markdown: str
    trace: list[TraceEvent]
    mtti_seconds: float
    confidence: float = 0.92


async def emit(events: list[TraceEvent], run_start: float, cb: EmitFn, agent: str, message: str, level: str = "info"):
    """Record a trace event and, if a live callback is attached, stream it."""
    event = TraceEvent(agent=agent, message=message, t_offset_ms=int((time.monotonic() - run_start) * 1000), level=level)
    events.append(event)
    if cb is not None:
        await cb(event)
    return event
