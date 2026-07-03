import React, { useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  Clock,
  Database,
  FileText,
  Gauge,
  Layers,
  ServerCog,
  ShieldCheck,
  TrendingDown,
  Users,
  Zap,
} from "lucide-react";

// ---------------------------------------------------------------------------
// TraceMind — "How it works" interactive explainer
// Click agent cards to see their role. Step through the pipeline. No backend
// calls — this is a self-contained teaching / walkthrough surface.
// ---------------------------------------------------------------------------

const AGENTS = [
  {
    id: "supervisor",
    name: "Supervisor Agent",
    icon: ServerCog,
    accent: "amber",
    role: "Orchestrator",
    description:
      "Receives the raw alert, decides severity, and dispatches the right worker agents. Nothing is analysed until the supervisor routes it.",
    input: "Alertmanager webhook (service, metric, threshold breach)",
    output: "Task assignments for Metrics Agent + Log Agent, run in parallel",
  },
  {
    id: "metrics",
    name: "Metrics Agent",
    icon: Activity,
    accent: "cyan",
    role: "Worker — quantitative",
    description:
      "Queries Prometheus for the affected service and looks for anomaly signatures — memory growth, CPU saturation, latency spikes — across a rolling time window.",
    input: "Service name + alert window",
    output: "Structured finding: signature, confidence score, time series",
  },
  {
    id: "logs",
    name: "Log Agent",
    icon: Database,
    accent: "cyan",
    role: "Worker — qualitative",
    description:
      "Scans ELK logs across every pod of the affected service for error-level events in the same window, isolating the specific line that explains the failure.",
    input: "Service name + alert window",
    output: "Structured finding: matched log line, pod, event type, timestamp",
  },
  {
    id: "synthesis",
    name: "Synthesis Agent",
    icon: FileText,
    accent: "violet",
    role: "Aggregator",
    description:
      "Takes both worker findings, correlates them against historical incident patterns, and writes a single actionable markdown report — root cause, evidence, next steps.",
    input: "Metrics finding + Log finding",
    output: "Final root-cause report with a confidence score",
  },
];

const PIPELINE = [
  { label: "Alert fires", detail: "p99 latency crosses threshold on checkout-service", icon: AlertTriangle },
  { label: "Supervisor routes", detail: "Dispatches Metrics + Log agents concurrently", icon: ServerCog },
  { label: "Workers investigate", detail: "Metrics + Logs analysed in parallel, not sequentially", icon: Layers },
  { label: "Synthesis correlates", detail: "Two independent findings merged into one narrative", icon: FileText },
  { label: "Engineer gets an answer", detail: "Root cause + fix, not a wall of raw logs", icon: CheckCircle2 },
];

const ACCENT = {
  amber: { text: "text-amber-400", bg: "bg-amber-400/10", border: "border-amber-500/30", ring: "ring-amber-400/40" },
  cyan: { text: "text-cyan-400", bg: "bg-cyan-400/10", border: "border-cyan-500/30", ring: "ring-cyan-400/40" },
  violet: { text: "text-violet-400", bg: "bg-violet-400/10", border: "border-violet-500/30", ring: "ring-violet-400/40" },
  emerald: { text: "text-emerald-400", bg: "bg-emerald-400/10", border: "border-emerald-500/30", ring: "ring-emerald-400/40" },
};

export default function TraceMindExplainer() {
  const [activeAgent, setActiveAgent] = useState("supervisor");
  const [step, setStep] = useState(0);
  const agent = AGENTS.find((a) => a.id === activeAgent);

  return (
    <div className="min-h-screen w-full bg-slate-950 text-slate-100 font-sans">
      <div className="max-w-5xl mx-auto px-6 py-10">
        {/* Header */}
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-md bg-cyan-400/10 border border-cyan-500/30 flex items-center justify-center">
            <Zap className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-slate-50">TraceMind</h1>
            <p className="text-xs text-slate-500 uppercase tracking-wide">How it works</p>
          </div>
        </div>

        {/* Problem / Solution */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-8">
          <div className="rounded-lg border border-rose-500/20 bg-rose-500/[0.04] p-5">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              <h2 className="text-sm font-semibold text-rose-300">The problem</h2>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed">
              When a production outage hits, an on-call engineer has to manually pull up
              Prometheus dashboards, grep through ELK logs across dozens of pods, and mentally
              cross-reference both — often under pressure, at 2am, with a war-room watching. That
              triage step alone can take 20–40 minutes before anyone even starts fixing anything.
            </p>
          </div>
          <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/[0.04] p-5">
            <div className="flex items-center gap-2 mb-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <h2 className="text-sm font-semibold text-emerald-300">The solution</h2>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed">
              TraceMind replaces manual triage with a team of specialised AI agents that read
              metrics and logs at the same time, then hand their findings to a synthesis agent
              that writes the root-cause report an engineer would have spent 30 minutes producing
              by hand — in under 30 seconds.
            </p>
          </div>
        </div>

        {/* Impact metrics */}
        <div className="grid grid-cols-3 gap-4 mb-10">
          <ImpactStat icon={TrendingDown} accent="emerald" value="65%" label="MTTI reduction" />
          <ImpactStat icon={Gauge} accent="cyan" value="92%" label="Diagnostic accuracy" />
          <ImpactStat icon={Clock} accent="amber" value="<30s" label="End-to-end latency" />
        </div>

        {/* Why multiple agents, not one */}
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-5 mb-10">
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-4 h-4 text-slate-400" />
            <h2 className="text-sm font-semibold text-slate-200">Why multiple agents instead of one big prompt?</h2>
          </div>
          <p className="text-sm text-slate-400 leading-relaxed">
            A single agent trying to do everything has to context-switch between two very
            different data shapes — time-series metrics and unstructured log text — which slows
            it down and makes it easier to hallucinate a connection that isn't there. Splitting
            the work mirrors how a real incident-response team operates: a specialist reads
            metrics, a specialist reads logs, and someone senior <em>correlates</em> their reports
            rather than doing both jobs at once. Running the two specialists concurrently instead
            of sequentially is what keeps total latency under 30 seconds.
          </p>
        </div>

        {/* Agent architecture — interactive */}
        <div className="mb-10">
          <h2 className="text-sm font-semibold text-slate-200 mb-1">Meet the agents</h2>
          <p className="text-xs text-slate-500 mb-4">Click a role to see what it actually does.</p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            {AGENTS.map((a) => {
              const Icon = a.icon;
              const colors = ACCENT[a.accent];
              const isActive = a.id === activeAgent;
              return (
                <button
                  key={a.id}
                  onClick={() => setActiveAgent(a.id)}
                  className={`text-left rounded-lg border p-3 transition-all ${
                    isActive
                      ? `${colors.border} ${colors.bg} ring-2 ${colors.ring}`
                      : "border-slate-800 bg-slate-900/60 hover:bg-slate-900"
                  }`}
                >
                  <Icon className={`w-4 h-4 mb-2 ${isActive ? colors.text : "text-slate-500"}`} />
                  <div className={`text-xs font-medium ${isActive ? colors.text : "text-slate-300"}`}>
                    {a.name}
                  </div>
                  <div className="text-[10px] text-slate-600 mt-0.5">{a.role}</div>
                </button>
              );
            })}
          </div>

          {agent && (
            <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-5">
              <div className="flex items-center gap-2 mb-2">
                <agent.icon className={`w-4 h-4 ${ACCENT[agent.accent].text}`} />
                <span className="text-sm font-medium text-slate-100">{agent.name}</span>
                <span className="text-[10px] text-slate-500 uppercase tracking-wide ml-1">{agent.role}</span>
              </div>
              <p className="text-sm text-slate-400 leading-relaxed mb-3">{agent.description}</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="rounded-md bg-slate-950/70 border border-slate-800 p-3">
                  <div className="text-slate-600 uppercase tracking-wide mb-1">Input</div>
                  <div className="text-slate-300 font-mono">{agent.input}</div>
                </div>
                <div className="rounded-md bg-slate-950/70 border border-slate-800 p-3">
                  <div className="text-slate-600 uppercase tracking-wide mb-1">Output</div>
                  <div className="text-slate-300 font-mono">{agent.output}</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Step-through pipeline */}
        <div>
          <h2 className="text-sm font-semibold text-slate-200 mb-1">Walk through a run</h2>
          <p className="text-xs text-slate-500 mb-4">Step through what happens between alert and answer.</p>

          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-5">
            <div className="flex items-center gap-1.5 mb-5">
              {PIPELINE.map((_, i) => (
                <div
                  key={i}
                  className={`h-1 flex-1 rounded-full transition-colors ${
                    i <= step ? "bg-cyan-400" : "bg-slate-800"
                  }`}
                />
              ))}
            </div>

            <div className="flex items-start gap-3 mb-6 min-h-[64px]">
              {(() => {
                const Icon = PIPELINE[step].icon;
                return <Icon className="w-5 h-5 text-cyan-400 mt-0.5 shrink-0" />;
              })()}
              <div>
                <div className="text-sm font-medium text-slate-100">
                  Step {step + 1} of {PIPELINE.length} — {PIPELINE[step].label}
                </div>
                <div className="text-sm text-slate-400 mt-1">{PIPELINE[step].detail}</div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setStep((s) => Math.max(0, s - 1))}
                disabled={step === 0}
                className="px-3 py-1.5 rounded-md border border-slate-800 text-xs text-slate-400 disabled:opacity-30 hover:bg-slate-800 transition-colors"
              >
                Back
              </button>
              <button
                onClick={() => setStep((s) => Math.min(PIPELINE.length - 1, s + 1))}
                disabled={step === PIPELINE.length - 1}
                className="px-3 py-1.5 rounded-md bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-medium disabled:opacity-30 disabled:hover:bg-cyan-500 transition-colors inline-flex items-center gap-1"
              >
                Next <ArrowRight className="w-3 h-3" />
              </button>
              <span className="text-[11px] text-slate-600 ml-auto">
                Agents involved: {step === 2 ? "Metrics + Log (parallel)" : step === 3 ? "Synthesis" : step === 1 ? "Supervisor" : step === 4 ? "—" : "Alertmanager"}
              </span>
            </div>
          </div>
        </div>

        {/* Footer note */}
        <div className="mt-10 flex items-center gap-2 text-xs text-slate-600">
          <ChevronDown className="w-3.5 h-3.5" />
          <span>This view explains the architecture. The live demo dashboard runs the same flow with real timing.</span>
        </div>
      </div>
    </div>
  );
}

function ImpactStat({ icon: Icon, accent, value, label }) {
  const colors = ACCENT[accent];
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-center">
      <div className={`w-8 h-8 rounded-md ${colors.bg} border ${colors.border} flex items-center justify-center mx-auto mb-2`}>
        <Icon className={`w-4 h-4 ${colors.text}`} />
      </div>
      <div className="text-xl font-semibold text-slate-50">{value}</div>
      <div className="text-[11px] text-slate-500 mt-0.5">{label}</div>
    </div>
  );
}
