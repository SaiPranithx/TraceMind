"""
Mock ELK client.

Generates a realistic slice of log lines around the incident window —
mostly noise (INFO/WARN chatter from unrelated pods) plus one smoking-gun
line — and provides a deterministic scanner that filters and matches it.

This mirrors what a real Log Agent tool does: query a window, filter to
ERROR+ severity, and pattern-match against known signatures. No LLM
required to notice a line contains "Killed process" or "Connection is not
available."
"""

import random
from dataclasses import dataclass

from telemetry.scenarios import Scenario

_NOISE_LINES = [
    ("INFO", "healthcheck: /ready 200 OK"),
    ("INFO", "gc: minor collection completed in 12ms"),
    ("INFO", "request served: GET /api/v1/status 200 4ms"),
    ("WARN", "cache miss for key session:99213, fetching from origin"),
    ("INFO", "heartbeat sent to service registry"),
    ("DEBUG", "connection pool stats: active=6 idle=14"),
    ("INFO", "request served: POST /api/v1/ping 200 2ms"),
]


@dataclass
class LogLine:
    t_minus_seconds: int
    level: str
    pod: str
    message: str


@dataclass
class LogFinding:
    service: str
    pod: str
    event: str
    matched_line: str
    timestamp: str
    lines_scanned: int
    lines: list[LogLine]


def generate_log_lines(
    scenario: Scenario,
    window_minutes: int = 14,
    noise_count: int = 24,
    seed: int | None = None,
) -> list[LogLine]:
    rng = random.Random(seed)
    pod_suffix = f"{rng.randint(1000, 9999):x}"
    incident_pod = f"{scenario.service}-{pod_suffix}"

    lines: list[LogLine] = []
    for _ in range(noise_count):
        level, message = rng.choice(_NOISE_LINES)
        t_minus = rng.randint(0, window_minutes * 60)
        pod = f"{scenario.service}-{rng.randint(1000, 9999):x}"
        lines.append(LogLine(t_minus_seconds=t_minus, level=level, pod=pod, message=message))

    # the smoking gun, near the end of the window (close to alert time)
    lines.append(
        LogLine(
            t_minus_seconds=rng.randint(0, 20),
            level="ERROR",
            pod=incident_pod,
            message=scenario.log_line,
        )
    )

    lines.sort(key=lambda l: l.t_minus_seconds, reverse=True)
    return lines


def scan_for_signature(scenario: Scenario, lines: list[LogLine]) -> LogFinding:
    """Deterministic filter+match — the Log Agent's actual "analysis"."""
    error_lines = [l for l in lines if l.level in ("ERROR", "CRITICAL")]
    match = next((l for l in error_lines if l.message == scenario.log_line), None)

    if match is None:
        # defensive fallback — shouldn't happen since we always inject it
        match = error_lines[-1] if error_lines else lines[-1]

    return LogFinding(
        service=scenario.service,
        pod=match.pod,
        event=scenario.log_event,
        matched_line=match.message,
        timestamp=f"T-{match.t_minus_seconds}s",
        lines_scanned=len(lines),
        lines=lines,
    )


async def fetch_logs(scenario: Scenario, seed: int | None = None) -> LogFinding:
    """Simulates the network + query latency of a real ELK/Elasticsearch call."""
    import asyncio

    await asyncio.sleep(0.5)  # stand-in for real query latency
    lines = generate_log_lines(scenario, seed=seed)
    return scan_for_signature(scenario, lines)
