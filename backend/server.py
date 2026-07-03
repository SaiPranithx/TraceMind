"""
TraceMind API server.

Exposes the real agent pipeline over HTTP so the frontend can trigger an
actual Supervisor -> Metrics/Log -> Synthesis run instead of only playing
back a scripted animation.

Run:
    uvicorn server:app --reload --port 8000

Endpoints:
    GET  /scenarios                        -> list available incidents
    POST /incidents/simulate {scenario_id}  -> run the real pipeline once,
                                                returns the report + a
                                                timestamped trace the
                                                frontend can replay with
                                                real per-step timing
"""

import random

from agents.base import Alert
from agents.supervisor import SupervisorAgent
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from telemetry.scenarios import SCENARIOS, get_scenario

load_dotenv()

app = FastAPI(title="TraceMind API")

# Local dev: Vite's default port. Adjust/add your deployed frontend origin
# when you deploy (see README "Deployment").
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulateRequest(BaseModel):
    scenario_id: str | None = None
    seed: int | None = None


@app.get("/scenarios")
def list_scenarios():
    return [
        {"id": s.id, "display_name": s.display_name, "service": s.service, "fault_type": s.fault_type}
        for s in SCENARIOS
    ]


@app.post("/incidents/simulate")
async def simulate_incident(req: SimulateRequest):
    try:
        scenario = get_scenario(req.scenario_id) if req.scenario_id else random.choice(SCENARIOS)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown scenario_id: {req.scenario_id}")

    alert = Alert(
        incident_id=f"INC-{random.randint(1000, 9999)}",
        service=scenario.service,
        reason=f"anomalous {scenario.metric_name} detected",
        severity="critical",
        scenario_id=scenario.id,
    )

    supervisor = SupervisorAgent()
    result = await supervisor.handle_alert(alert, scenario, seed=req.seed)

    return {
        "incident_id": alert.incident_id,
        "service": alert.service,
        "scenario_id": scenario.id,
        "mtti_seconds": round(result.mtti_seconds, 2),
        "confidence": result.confidence,
        "report_markdown": result.report_markdown,
        "trace": [
            {"agent": e.agent, "message": e.message, "t_offset_ms": e.t_offset_ms, "level": e.level}
            for e in result.trace
        ],
    }


@app.get("/health")
def health():
    return {"status": "ok"}
