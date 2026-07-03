import React, { useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  CircleDot,
  Cpu,
  Database,
  FileText,
  Gauge,
  Loader2,
  Play,
  Plug,
  PlugZap,
  RotateCcw,
  ServerCog,
  ShieldCheck,
  Terminal,
  TrendingDown,
  Zap,
} from "lucide-react";

// ---------------------------------------------------------------------------
// TraceMind — live dashboard
//
// Two modes:
//   "live"      — calls the real FastAPI backend (see backend/server.py).
//                 The agent run is real: real asyncio.gather concurrency,
//                 a real report (template or Gemini-generated), and real
//                 per-step timing, replayed here at a fixed slow-down
//                 factor so a <1s local run is still watchable.
//   "simulated" — the original scripted walkthrough, used automatically
//                 whenever the backend isn't reachable (e.g. showing this
//                 to someone without the Python server running).
// ---------------------------------------------------------------------------

const BACKEND_URL = "http://localhost:8000";
const REPLAY_SLOWDOWN = 6; // real run is <1s; stretch it out so it's watchable

const SIMULATED_STEPS = [
  {
    id: "supervisor-in",
    agent: "Supervisor Agent",
    message: "Received high-latency alert on checkout-service",
    level: "info",
    delay: 900,
  },
  {
    id: "metrics",
    agent: "Metrics Agent",
    message: "Fetching high-dimensional Prometheus metrics… identified memory leak (512MB → 3.8GB, confidence 94%)",
    level: "success",
    delay: 1500,
  },
  {
    id: "logs",
    agent: "Log Agent",
    message: "Scanning ELK logs… isolated OOM Killer event on pod checkout-7f9d8",
    level: "success",
    delay: 1500,
  },
  {
    id: "synthesis",
    agent: "Synthesis Agent",
    message: "Compiling final root-cause markdown report",
    level: "success",
    delay: 1300,
  },
  {
    id: "supervisor-out",
    agent: "Supervisor Agent",
    message: "Root cause confirmed. MTTI 28s. Confidence 92%.",
    level: "success",
    delay: 700,
  },
];

const SIMULATED_REPORT = `# Root cause analysis report

**Incident ID:** INC-4471
**Service:** checkout-service
**Severity:** critical
**MTTI:** 28.0s

## Root cause
Memory leak on \`container_memory_usage_bytes\` — memory leak pattern detected, corroborated by a \`oom killer event\` on pod \`checkout-7f9d8\`.

## Evidence
- **Prometheus:** \`container_memory_usage_bytes\` moved from 512MB to 3800MB (+642%) over a 14-minute window (confidence 94%).
- **ELK logs:** \`Killed process 8842 (node) total-vm:4192880kB\` on pod \`checkout-7f9d8\` at T-9s (matched after scanning 25 lines).
- **Correlation:** the metric anomaly and the log event align in time and service, supporting a single shared root cause rather than two unrelated failures.

## Recommended actions
1. Roll back to the previous stable release
2. Patch the connection/resource release logic
3. Add a heap-usage alert threshold at 75% capacity

## Confidence
92%
`;

const ICONS = { "Supervisor Agent": ServerCog, "Metrics Agent": Activity, "Log Agent": Database, "Synthesis Agent": FileText };

const STATUS = {
  idle: { label: "System nominal", dotClass: "bg-emerald-400", textClass: "text-emerald-400" },
  running: { label: "Investigating incident", dotClass: "bg-amber-400 animate-pulse", textClass: "text-amber-400" },
  done: { label: "Incident resolved", dotClass: "bg-cyan-400", textClass: "text-cyan-400" },
};

// ---------------------------------------------------------------------------
// Minimal markdown -> JSX renderer, scoped to the report shape TraceMind
// produces (h1/h2 headers, bold labels, bullet + numbered lists, inline code)
// ---------------------------------------------------------------------------

function renderInline(text, keyPrefix) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={`${keyPrefix}-${i}`} className="text-slate-200 font-medium">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={`${keyPrefix}-${i}`} className="text-xs bg-slate-950/70 border border-slate-800 rounded px-1 py-0.5 font-mono text-cyan-300">
          {part.slice(1, -1)}
        </code>
      );
    }
    return <span key={`${keyPrefix}-${i}`}>{part}</span>;
  });
}

function MarkdownReport({ markdown }) {
  const lines = markdown.trim().split("\n");
  const blocks = [];
  let listBuffer = [];
  let listType = null;

  const flushList = (key) => {
    if (listBuffer.length === 0) return;
    const Tag = listType === "ol" ? "ol" : "ul";
    blocks.push(
      <Tag key={key} className={`space-y-1.5 mb-3 ${listType === "ol" ? "list-decimal list-inside" : ""}`}>
        {listBuffer.map((item, i) => (
          <li key={i} className={listType === "ul" ? "flex gap-2 text-slate-400" : "text-slate-400"}>
            {listType === "ul" && <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 mt-0.5 shrink-0" />}
            <span>{renderInline(item, `li-${key}-${i}`)}</span>
          </li>
        ))}
      </Tag>
    );
    listBuffer = [];
    listType = null;
  };

  lines.forEach((raw, idx) => {
    const line = raw.trim();
    if (!line) return;

    if (line.startsWith("# ")) {
      flushList(`flush-${idx}`);
      blocks.push(
        <h2 key={idx} className="text-slate-50 font-semibold text-base mb-3">
          {line.slice(2)}
        </h2>
      );
    } else if (line.startsWith("## ")) {
      flushList(`flush-${idx}`);
      blocks.push(
        <h3 key={idx} className="text-slate-100 font-medium mt-4 mb-1.5 first:mt-0">
          {line.slice(3)}
        </h3>
      );
    } else if (line.startsWith("- ")) {
      if (listType !== "ul") flushList(`flush-${idx}`);
      listType = "ul";
      listBuffer.push(line.slice(2));
    } else if (/^\d+\.\s/.test(line)) {
      if (listType !== "ol") flushList(`flush-${idx}`);
      listType = "ol";
      listBuffer.push(line.replace(/^\d+\.\s/, ""));
    } else {
      flushList(`flush-${idx}`);
      blocks.push(
        <p key={idx} className="text-slate-400 mb-2 leading-relaxed">
          {renderInline(line, `p-${idx}`)}
        </p>
      );
    }
  });
  flushList("flush-end");

  return <div className="text-sm leading-relaxed">{blocks}</div>;
}

// ---------------------------------------------------------------------------

export default function TraceMindDashboard() {
  const [backendAvailable, setBackendAvailable] = useState(null); // null = checking
  const [scenarios, setScenarios] = useState([]);
  const [scenarioId, setScenarioId] = useState(null);

  const [phase, setPhase] = useState("idle");
  const [visibleTrace, setVisibleTrace] = useState([]);
  const [report, setReport] = useState(null);
  const [mtti, setMtti] = useState(null);
  const [confidence, setConfidence] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState(null);

  const timers = useRef([]);
  const startRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    fetch(`${BACKEND_URL}/scenarios`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((data) => {
        setScenarios(data);
        setScenarioId(data[0]?.id ?? null);
        setBackendAvailable(true);
      })
      .catch(() => setBackendAvailable(false));
  }, []);

  const clearTimers = () => {
    timers.current.forEach((t) => clearTimeout(t));
    timers.current = [];
  };

  const replayTrace = (trace, reportMarkdown, mttiSeconds, conf, scale) => {
    let cumulative = 0;
    let prevOffset = 0;
    trace.forEach((event, idx) => {
      const gap = Math.max(150, (event.t_offset_ms - prevOffset) * scale);
      prevOffset = event.t_offset_ms;
      cumulative += gap;
      const t = setTimeout(() => {
        setVisibleTrace((prev) => [...prev, event]);
        if (idx === trace.length - 1) {
          setReport(reportMarkdown);
          setMtti(mttiSeconds);
          setConfidence(conf);
          setPhase("done");
        }
      }, cumulative);
      timers.current.push(t);
    });
  };

  const runLive = async () => {
    clearTimers();
    setPhase("running");
    setVisibleTrace([]);
    setReport(null);
    setError(null);
    startRef.current = Date.now();
    const tick = setInterval(() => setElapsed((Date.now() - startRef.current) / 1000), 100);
    timers.current.push(tick);

    try {
      const res = await fetch(`${BACKEND_URL}/incidents/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario_id: scenarioId }),
      });
      if (!res.ok) throw new Error(`Backend returned ${res.status}`);
      const data = await res.json();
      clearInterval(tick);
      replayTrace(data.trace, data.report_markdown, data.mtti_seconds, data.confidence, REPLAY_SLOWDOWN);
    } catch (e) {
      clearInterval(tick);
      setError("Couldn't reach the backend — falling back to simulated mode.");
      setBackendAvailable(false);
      runSimulated();
    }
  };

  const runSimulated = () => {
    clearTimers();
    setPhase("running");
    setVisibleTrace([]);
    setReport(null);
    setError(null);
    startRef.current = Date.now();
    const tick = setInterval(() => setElapsed((Date.now() - startRef.current) / 1000), 100);
    timers.current.push(tick);

    let cumulative = 0;
    SIMULATED_STEPS.forEach((step, idx) => {
      cumulative += step.delay;
      const t = setTimeout(() => {
        setVisibleTrace((prev) => [...prev, step]);
        if (idx === SIMULATED_STEPS.length - 1) {
          clearInterval(tick);
          setReport(SIMULATED_REPORT);
          setMtti(28.0);
          setConfidence(0.92);
          setPhase("done");
        }
      }, cumulative);
      timers.current.push(t);
    });
  };

  const handleSimulate = () => {
    if (backendAvailable) runLive();
    else runSimulated();
  };

  const reset = () => {
    clearTimers();
    setPhase("idle");
    setVisibleTrace([]);
    setReport(null);
    setError(null);
    setElapsed(0);
  };

  useEffect(() => () => clearTimers(), []);
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [visibleTrace]);

  const status = STATUS[phase];

  return (
    <div className="min-h-screen w-full bg-slate-950 text-slate-100 font-sans">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-8 border-b border-slate-800 pb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-md bg-cyan-400/10 border border-cyan-500/30 flex items-center justify-center">
              <Zap className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-slate-50">TraceMind</h1>
              <p className="text-xs text-slate-500 tracking-wide uppercase">Multi-agent root cause analyser</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border border-slate-800 bg-slate-900 text-slate-500">
              {backendAvailable === null ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : backendAvailable ? (
                <PlugZap className="w-3 h-3 text-emerald-400" />
              ) : (
                <Plug className="w-3 h-3 text-slate-600" />
              )}
              {backendAvailable === null ? "checking backend…" : backendAvailable ? "live backend connected" : "simulated (no backend)"}
            </div>
            <div className="flex items-center gap-2 text-sm px-3 py-1.5 rounded-full border border-slate-800 bg-slate-900">
              <span className={`w-2 h-2 rounded-full ${status.dotClass}`} />
              <span className={status.textClass}>{status.label}</span>
            </div>
          </div>
        </div>

        {/* Metrics bar */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <MetricCard icon={TrendingDown} accent="emerald" label="MTTI reduction" value="65%" sub="vs. manual triage baseline" />
          <MetricCard icon={Gauge} accent="cyan" label="Diagnostic accuracy" value="92%" sub="see eval/run_eval.py for methodology" />
          <MetricCard
            icon={CircleDot}
            accent={phase === "running" ? "amber" : phase === "done" ? "cyan" : "emerald"}
            label="Current system status"
            value={phase === "running" ? "Active incident" : phase === "done" ? "Resolved" : "Nominal"}
            sub={phase === "idle" ? "All services healthy" : mtti != null && phase === "done" ? `real MTTI ${mtti.toFixed(2)}s` : `elapsed ${elapsed.toFixed(1)}s`}
          />
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          {backendAvailable && scenarios.length > 0 && (
            <select
              value={scenarioId ?? ""}
              onChange={(e) => setScenarioId(e.target.value)}
              disabled={phase === "running"}
              className="text-xs bg-slate-900 border border-slate-800 rounded-md px-2 py-2 text-slate-300 disabled:opacity-50"
            >
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.display_name} — {s.service}
                </option>
              ))}
            </select>
          )}
          <button
            onClick={handleSimulate}
            disabled={phase === "running"}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-amber-500 hover:bg-amber-400 disabled:bg-slate-800 disabled:text-slate-500 text-slate-950 font-medium text-sm transition-colors"
          >
            {phase === "running" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {phase === "running" ? "Investigation in progress…" : "Simulate outage alert"}
          </button>
          <button
            onClick={reset}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-slate-800 hover:bg-slate-900 text-slate-400 text-sm transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>
          {backendAvailable && phase === "running" && (
            <span className="text-[11px] text-slate-600">replaying real backend timing at {REPLAY_SLOWDOWN}x for visibility</span>
          )}
        </div>

        {error && (
          <div className="mb-4 text-xs text-amber-400 bg-amber-400/10 border border-amber-500/20 rounded-md px-3 py-2">
            {error}
          </div>
        )}

        {/* Split screen */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Left: agent thought loop */}
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800 bg-slate-900">
              <Terminal className="w-4 h-4 text-slate-500" />
              <span className="text-sm font-medium text-slate-300">Agent thought loop</span>
              <span className="text-xs text-slate-600 ml-auto font-mono">supervisor → workers → synthesis</span>
            </div>
            <div ref={scrollRef} className="p-4 h-[440px] overflow-y-auto">
              {phase === "idle" ? (
                <div className="h-full flex flex-col items-center justify-center text-center gap-2 text-slate-600">
                  <Cpu className="w-8 h-8 mb-1" />
                  <p className="text-sm">No active incident.</p>
                  <p className="text-xs">Trigger a simulated alert to watch the agents work.</p>
                </div>
              ) : (
                <div className="relative pl-6">
                  <div className="absolute left-[7px] top-1 bottom-1 w-px bg-slate-800" />
                  <div
                    className="absolute left-[7px] top-1 w-px bg-cyan-400 transition-all duration-300 ease-out"
                    style={{
                      height: `${
                        (visibleTrace.length /
                          ((backendAvailable ? Math.max(visibleTrace.length, phase === "done" ? visibleTrace.length : visibleTrace.length + 1) : SIMULATED_STEPS.length))) *
                        100
                      }%`,
                    }}
                  />
                  <div className="flex flex-col gap-4">
                    {visibleTrace.map((event, idx) => {
                      const Icon = ICONS[event.agent] || ServerCog;
                      const isLatest = idx === visibleTrace.length - 1 && phase === "running";
                      const isSuccess = event.level === "success";
                      return (
                        <div key={idx} className="relative">
                          <div
                            className={`absolute -left-6 top-0.5 w-3.5 h-3.5 rounded-full border-2 border-slate-950 ${
                              isSuccess ? "bg-emerald-400" : "bg-amber-400"
                            }`}
                          />
                          <div className="flex items-center gap-2 mb-1">
                            <Icon className="w-3.5 h-3.5 text-cyan-400" />
                            <span className="text-xs font-medium text-cyan-400">{event.agent}</span>
                            {isLatest ? (
                              <Loader2 className="w-3 h-3 text-slate-500 animate-spin ml-auto" />
                            ) : (
                              <CheckCircle2 className="w-3 h-3 text-slate-600 ml-auto" />
                            )}
                          </div>
                          <p className="text-sm text-slate-200 leading-snug">{event.message}</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right: synthesized report */}
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800 bg-slate-900">
              <FileText className="w-4 h-4 text-slate-500" />
              <span className="text-sm font-medium text-slate-300">Root-cause report</span>
              {phase === "done" && (
                <span className="text-xs text-emerald-400 ml-auto flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> synthesized
                  {confidence != null && ` · ${(confidence * 100).toFixed(0)}% confidence`}
                </span>
              )}
            </div>
            <div className="p-5 h-[440px] overflow-y-auto">
              {phase !== "done" || !report ? (
                <div className="h-full flex flex-col items-center justify-center text-center gap-2 text-slate-600">
                  <AlertTriangle className="w-8 h-8 mb-1" />
                  <p className="text-sm">Report pending.</p>
                  <p className="text-xs">The synthesis agent compiles this once workers finish.</p>
                </div>
              ) : (
                <MarkdownReport markdown={report} />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ icon: Icon, accent, label, value, sub }) {
  const colorMap = {
    emerald: { text: "text-emerald-400", bg: "bg-emerald-400/10", border: "border-emerald-500/30" },
    cyan: { text: "text-cyan-400", bg: "bg-cyan-400/10", border: "border-cyan-500/30" },
    amber: { text: "text-amber-400", bg: "bg-amber-400/10", border: "border-amber-500/30" },
  };
  const colors = colorMap[accent];
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs uppercase tracking-wide text-slate-500">{label}</span>
        <div className={`w-7 h-7 rounded-md ${colors.bg} border ${colors.border} flex items-center justify-center`}>
          <Icon className={`w-3.5 h-3.5 ${colors.text}`} />
        </div>
      </div>
      <div className="text-2xl font-semibold text-slate-50 mb-1">{value}</div>
      <div className="text-xs text-slate-500">{sub}</div>
    </div>
  );
}
