
import os

from agents.base import Alert, EmitFn, TraceEvent, emit
from telemetry.elk_mock import LogFinding
from telemetry.prometheus_mock import MetricsFinding
from telemetry.scenarios import Scenario

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


class SynthesisAgent:
    name = "Synthesis Agent"

    async def synthesize(
        self,
        alert: Alert,
        scenario: Scenario,
        metrics_finding: MetricsFinding,
        log_finding: LogFinding,
        mtti_seconds: float,
        confidence: float,
        events: list[TraceEvent],
        run_start: float,
        on_event: EmitFn = None,
    ) -> str:
        await emit(events, run_start, on_event, self.name, "Correlating metrics + log evidence…")

        if GEMINI_API_KEY:
            report = await self._synthesize_with_gemini(alert, scenario, metrics_finding, log_finding, mtti_seconds, confidence)
            source = f"Gemini ({GEMINI_MODEL})"
        else:
            report = self._synthesize_template(alert, scenario, metrics_finding, log_finding, mtti_seconds, confidence)
            source = "template"

        await emit(
            events, run_start, on_event, self.name,
            f"Report ready via {source} — confidence {confidence:.0%}",
            level="success",
        )
        return report

    # -- Week 2: deterministic fallback, always available offline ----------

    def _synthesize_template(self, alert, scenario, metrics_finding, log_finding, mtti_seconds, confidence) -> str:
        delta_pct = round(
            ((metrics_finding.end_value - metrics_finding.start_value) / max(abs(metrics_finding.start_value), 1.0)) * 100
        )
        actions = "\n".join(f"{i}. {a}" for i, a in enumerate(scenario.recommended_actions, start=1))
        return f"""# Root cause analysis report

**Incident ID:** {alert.incident_id}
**Service:** {alert.service}
**Severity:** {alert.severity}
**MTTI:** {mtti_seconds:.1f}s

## Root cause
{scenario.display_name} on `{metrics_finding.metric_name}` — {scenario.root_cause_keywords[0]} pattern
detected, corroborated by a `{log_finding.event.replace('_', ' ')}` on pod `{log_finding.pod}`.

## Evidence
- **Prometheus:** `{metrics_finding.metric_name}` moved from {metrics_finding.start_value:.0f}{metrics_finding.unit}
  to {metrics_finding.end_value:.0f}{metrics_finding.unit} ({delta_pct:+d}%) over a {metrics_finding.window_minutes}-minute window
  (confidence {metrics_finding.confidence:.0%}).
- **ELK logs:** `{log_finding.matched_line}` on pod `{log_finding.pod}` at {log_finding.timestamp}
  (matched after scanning {log_finding.lines_scanned} lines).
- **Correlation:** the metric anomaly and the log event align in time and service, supporting
  a single shared root cause rather than two unrelated failures.

## Recommended actions
{actions}

## Confidence
{confidence:.0%}
"""

    # -- Week 3: Gemini-backed narrative, same structured inputs -----------

    async def _synthesize_with_gemini(self, alert, scenario, metrics_finding, log_finding, mtti_seconds, confidence) -> str:
        import asyncio

        from google import genai

        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""You are the Synthesis Agent in TraceMind, an incident root-cause system.
You are given two structured findings from independent worker agents — do not invent
any facts beyond what's listed below. Write a concise root-cause markdown report with
exactly these sections: "## Root cause", "## Evidence", "## Recommended actions", "## Confidence".
Keep it under 200 words. State the confidence exactly as given, do not change it.
In the Root cause section, name the failure mode in plain language (e.g. "memory leak",
"connection pool exhaustion") — don't just repeat the raw signature slug.

Incident: {alert.incident_id} | service: {alert.service} | severity: {alert.severity} | MTTI: {mtti_seconds:.1f}s

Metrics finding:
- metric: {metrics_finding.metric_name}
- moved from {metrics_finding.start_value:.0f}{metrics_finding.unit} to {metrics_finding.end_value:.0f}{metrics_finding.unit}
  over {metrics_finding.window_minutes} minutes
- detected signature: {metrics_finding.signature}
- detection confidence: {metrics_finding.confidence:.0%}

Log finding:
- event: {log_finding.event}
- matched line: {log_finding.matched_line}
- pod: {log_finding.pod}
- timestamp: {log_finding.timestamp}
- lines scanned: {log_finding.lines_scanned}

Overall confidence to report: {confidence:.0%}
"""
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=GEMINI_MODEL,
            contents=prompt,
        )
        return response.text
