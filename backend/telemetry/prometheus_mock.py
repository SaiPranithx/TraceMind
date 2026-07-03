"""
Mock Prometheus client.

Generates a synthetic time series for a scenario's metric, and provides a
deterministic (non-LLM) anomaly classifier that mirrors what a real Metrics
Agent tool would do: look at the shape of the curve, not just its endpoint.

Keeping this deterministic means the Metrics Agent's output is reproducible
and unit-testable — no LLM call needed to notice "this went up 7x in 14
minutes."
"""

import random
from dataclasses import dataclass

from telemetry.scenarios import Scenario


@dataclass
class MetricPoint:
    t_minus_seconds: int   # seconds before the alert fired (0 = alert time)
    value: float


@dataclass
class MetricsFinding:
    service: str
    metric_name: str
    unit: str
    window_minutes: int
    start_value: float
    end_value: float
    signature: str
    confidence: float
    series: list[MetricPoint]


def generate_metric_series(
    scenario: Scenario,
    window_minutes: int = 14,
    resolution_seconds: int = 30,
    seed: int | None = None,
) -> list[MetricPoint]:
    """Synthesize a noisy time series that ramps from baseline -> peak."""
    rng = random.Random(seed)
    total_points = int((window_minutes * 60) / resolution_seconds)
    noise_amplitude = max(scenario.baseline, 1) * 0.04

    points: list[MetricPoint] = []
    for i in range(total_points + 1):
        progress = i / total_points  # 0.0 (window start) -> 1.0 (alert time)
        t_minus = int((total_points - i) * resolution_seconds)

        if scenario.trend == "linear_climb":
            base = scenario.baseline + (scenario.peak - scenario.baseline) * progress
        elif scenario.trend == "step_spike":
            # flat baseline for the first 70% of the window, then a sharp step
            base = scenario.baseline if progress < 0.7 else scenario.peak
        else:  # sawtooth fallback
            base = scenario.baseline + (scenario.peak - scenario.baseline) * abs(
                (progress * 2) % 2 - 1
            )

        value = max(0.0, base + rng.uniform(-noise_amplitude, noise_amplitude))
        points.append(MetricPoint(t_minus_seconds=t_minus, value=round(value, 2)))

    return points


def classify_signature(scenario: Scenario, series: list[MetricPoint]) -> tuple[str, float]:
    """
    Deterministic shape-based classifier. In production this is the kind of
    logic a Metrics Agent tool would run (rate-of-change, step detection,
    z-score against baseline) before ever involving an LLM.
    """
    start_value = series[0].value
    end_value = series[-1].value
    delta_ratio = (end_value - start_value) / max(start_value, 1e-6)

    # crude step-vs-climb detection: compare the back half's slope to the front half's
    midpoint = len(series) // 2
    front_delta = series[midpoint].value - series[0].value
    back_delta = series[-1].value - series[midpoint].value
    is_step = abs(back_delta) > abs(front_delta) * 2.5

    if delta_ratio > 0.3 and is_step:
        signature = "step_spike_signature"
    elif delta_ratio > 0.3:
        signature = "linear_climb_signature"
    elif delta_ratio < -0.3:
        signature = "sharp_drop_signature"
    else:
        signature = "no_significant_anomaly"

    # confidence scales with how extreme the swing was, capped at 0.97
    confidence = min(0.97, 0.55 + min(abs(delta_ratio), 1.2) * 0.35)
    return signature, round(confidence, 2)


async def fetch_metrics(scenario: Scenario, seed: int | None = None) -> MetricsFinding:
    """Simulates the network + query latency of a real Prometheus call."""
    import asyncio

    await asyncio.sleep(0.4)  # stand-in for real query latency
    series = generate_metric_series(scenario, seed=seed)
    signature, confidence = classify_signature(scenario, series)

    return MetricsFinding(
        service=scenario.service,
        metric_name=scenario.metric_name,
        unit=scenario.unit,
        window_minutes=14,
        start_value=series[0].value,
        end_value=series[-1].value,
        signature=signature,
        confidence=confidence,
        series=series,
    )
