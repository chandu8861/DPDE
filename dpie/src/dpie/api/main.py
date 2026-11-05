"""DPIE REST API Module

FastAPI-based REST endpoints for the DPIE framework.

Essential endpoints:
- POST /api/v1/analyze
- POST /api/v1/agents/triage
- POST /api/v1/agents/investigate
- POST /api/v1/agents/correlate
- POST /api/v1/agents/report
- GET /api/v1/agents
- GET /api/v1/health
- GET /dashboard (Interactive Developer Dashboard)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
import uvicorn

from dpie.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AgentInput,
    AgentOutput,
    OrchestrationMode,
    EvidenceRecord,
    DarkPatternCategory,
    AgentType,
    ReportFormat,
    DetectionStatus,
)
from dpie.orchestration import (
    OrchestrationEngine,
    run_fast_analysis,
    run_deep_analysis,
    run_full_analysis,
)
from dpie.knowledge_base import get_knowledge_base, SharedKnowledgeBase
from dpie.agents.registry import get_agent_registry, init_agent_registry, AgentRegistry
from dpie.config import settings, load_settings

logger = logging.getLogger(__name__)

# Initialize components
load_settings()
kb = get_knowledge_base()
registry = get_agent_registry()


def _register_default_agents():
    """Ensure all default agents are registered."""
    from dpie.agents.triage import TriageAgent
    from dpie.agents.investigator import InvestigatorAgent
    from dpie.agents.correlator import CorrelatorAgent
    from dpie.agents.reporter import ReporterAgent
    from dpie.agents.threat_hunter import ThreatHunterAgent
    from dpie.agents.forensics import ForensicsAgent
    from dpie.agents.threat_intelligence import ThreatIntelligenceAgent
    from dpie.agents.compliance import ComplianceAgent
    from dpie.agents.responder import ResponderAgent
    from dpie.agents.auto_responder import AutoResponderAgent
    from dpie.agents.mitre_analyst import MitreAnalystAgent

    default_agents = [
        (AgentType.TRIAGE, TriageAgent),
        (AgentType.INVESTIGATOR, InvestigatorAgent),
        (AgentType.CORRELATOR, CorrelatorAgent),
        (AgentType.REPORTER, ReporterAgent),
        (AgentType.THREAT_HUNTER, ThreatHunterAgent),
        (AgentType.FORENSICS, ForensicsAgent),
        (AgentType.THREAT_INTELLIGENCE, ThreatIntelligenceAgent),
        (AgentType.COMPLIANCE, ComplianceAgent),
        (AgentType.RESPONDER, ResponderAgent),
        (AgentType.AUTO_RESPONDER, AutoResponderAgent),
        (AgentType.MITRE_ANALYST, MitreAnalystAgent),
    ]

    for agent_type, agent_class in default_agents:
        if not registry.is_agent_enabled(agent_type):
            agent = agent_class(knowledge_base=kb)
            registry.register(agent)


# Register immediately so endpoints work without waiting for startup hooks
_register_default_agents()

# Create FastAPI app
app = FastAPI(
    title="DPIE - DarkPattern Intelligence Engine",
    description="""
    Multi-Agent AI Framework for detecting, investigating, correlating, 
    classifying, and reporting deceptive user-interface practices and dark patterns.
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create orchestration engine
orchestration_engine = OrchestrationEngine(orchestration_mode=settings.default_mode)


# ---------------------------------------------------------------------------
# Request/Response Models for API
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    """Request body for POST /api/v1/analyze."""
    url: Optional[str] = Field(default=None, description="Target URL")
    html: Optional[str] = Field(default=None, description="HTML content or DOM snapshot")
    dom_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Structured DOM data"
    )
    elements: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="List of UI elements to analyze"
    )
    mode: OrchestrationMode = Field(
        default=OrchestrationMode.FAST, description="Execution mode"
    )
    include_report: bool = Field(
        default=False, description="Whether to include report generation"
    )


class HealthCheck(BaseModel):
    """Response model for health check."""
    status: str = "ok"
    version: str = "0.1.0"
    agents_available: int
    knowledge_base_entities: int


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/v1/health", response_model=HealthCheck, tags=["health"])
async def health_check():
    """Health check endpoint."""
    return HealthCheck(
        status="ok",
        version="0.1.0",
        agents_available=len(registry.list_agents()),
        knowledge_base_entities=len(kb._memory.get("evidence", {})),
    )


@app.get("/api/v1/agents", tags=["agents"])
async def list_agents():
    """List available agents."""
    agents = registry.list_agents()
    result = []
    for agent in agents:
        info = agent.get_agent_info()
        info["enabled"] = registry.is_agent_enabled(agent.agent_type)
        result.append(info)
    return {"agents": result, "total": len(result)}


@app.post("/api/v1/agents/triage", tags=["agents"])
async def triage_agent(request: AnalyzeRequest):
    """Run the triage agent only."""
    agent = registry.get(AgentType.TRIAGE)
    if not agent:
        from dpie.agents.triage import TriageAgent
        agent = TriageAgent(knowledge_base=kb)
        registry.register(agent)

    input_data = AgentInput(
        url=request.url,
        html=request.html,
        dom_data=request.dom_data,
        elements=request.elements,
    )
    output = await agent.analyze(input_data)
    return {"agent_output": output.model_dump(), "agent_type": "triage"}


@app.post("/api/v1/agents/investigate", tags=["agents"])
async def investigate_agent(request: AnalyzeRequest):
    """Run the investigator agent only."""
    agent = registry.get(AgentType.INVESTIGATOR)
    if not agent:
        from dpie.agents.investigator import InvestigatorAgent
        agent = InvestigatorAgent(knowledge_base=kb)
        registry.register(agent)

    input_data = AgentInput(
        url=request.url,
        html=request.html,
        dom_data=request.dom_data,
        elements=request.elements,
    )
    output = await agent.analyze(input_data)
    return {"agent_output": output.model_dump(), "agent_type": "investigator"}


@app.post("/api/v1/agents/correlate", tags=["agents"])
async def correlate_agent(request: AnalyzeRequest):
    """Run the correlator agent only."""
    agent = registry.get(AgentType.CORRELATOR)
    if not agent:
        from dpie.agents.correlator import CorrelatorAgent
        agent = CorrelatorAgent(knowledge_base=kb)
        registry.register(agent)

    input_data = AgentInput(
        url=request.url,
        html=request.html,
        dom_data=request.dom_data,
        elements=request.elements,
    )
    output = await agent.analyze(input_data)
    return {"agent_output": output.model_dump(), "agent_type": "correlator"}


@app.post("/api/v1/agents/report", tags=["agents"])
async def reporter_agent(request: AnalyzeRequest):
    """Run the reporter agent to generate a report."""
    agent = registry.get(AgentType.REPORTER)
    if not agent:
        from dpie.agents.reporter import ReporterAgent
        agent = ReporterAgent(knowledge_base=kb)
        registry.register(agent)

    input_data = AgentInput(
        url=request.url,
        html=request.html,
        dom_data=request.dom_data,
        elements=request.elements,
    )
    output = await agent.analyze(input_data)

    report_content = {
        "format": "json",
        "pattern_name": "detected_patterns" if output.overall_confidence > 0.3 else "no_patterns_detected",
        "severity": "medium",
        "confidence": output.overall_confidence,
        "evidence_count": len(output.findings),
        "recommendations": [
            f.evidence_text for f in output.findings if f.evidence_text
        ][:3],
    }

    return {
        "agent_output": output.model_dump(),
        "report": report_content,
        "agent_type": "reporter",
    }


@app.post("/api/v1/analyze", response_model=AnalysisResponse, tags=["analysis"])
async def analyze_endpoint(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Main analysis endpoint - runs selected agents in the specified mode."""
    input_data = AgentInput(
        url=request.url,
        html=request.html,
        dom_data=request.dom_data,
        elements=request.elements,
    )
    engine = OrchestrationEngine(orchestration_mode=request.mode)
    response = await engine.execute(input_data)
    return response


@app.get("/dashboard", response_class=HTMLResponse, tags=["dashboard"])
async def dashboard_view():
    """Interactive Developer Dashboard."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DPIE - DarkPattern Intelligence Engine Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #0f172a; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; }
        .card { background: #1e293b; border: 1px solid #334155; color: #f8fafc; }
        .badge-dp { font-size: 0.85rem; padding: 0.35rem 0.65rem; border-radius: 9999px; }
        pre { background: #090d16; padding: 1rem; border-radius: 0.5rem; color: #38bdf8; max-height: 400px; overflow-y: auto; }
    </style>
</head>
<body class="p-4">
    <div class="container-fluid">
        <header class="d-flex justify-content-between align-items-center mb-4 pb-2 border-bottom border-secondary">
            <h2>🛡️ DPIE Dashboard <span class="badge bg-primary fs-6">v0.1.0</span></h2>
            <a href="/docs" target="_blank" class="btn btn-outline-info btn-sm">Interactive Swagger Docs</a>
        </header>

        <div class="row g-4">
            <div class="col-md-5">
                <div class="card p-3 shadow">
                    <h5 class="card-title text-info mb-3">Inspect & Analyze UI</h5>
                    <div class="mb-3">
                        <label class="form-label">Target URL</label>
                        <input type="text" id="targetUrl" class="form-control bg-dark text-white border-secondary" value="https://example.com/checkout">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Analysis Mode</label>
                        <select id="analysisMode" class="form-select bg-dark text-white border-secondary">
                            <option value="fast">FAST (Triage)</option>
                            <option value="deep" selected>DEEP (Triage + Investigator + Correlator)</option>
                            <option value="full">FULL (All 11 Specialized Agents)</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">HTML / DOM Snippet</label>
                        <textarea id="htmlSnippet" class="form-control bg-dark text-white border-secondary" rows="5"><button class="cta">Subscribe now - it's free and you must agree!</button>
<a href="#" class="decline-link">No thanks, I prefer paying full price</a>
<span class="fine-print">Auto-renews at $99/mo after 3 days trial. Cancel anytime with $25 fee.</span></textarea>
                    </div>
                    <button class="btn btn-primary w-100 py-2 fw-semibold" onclick="runAnalysis()">Run Intelligence Engine</button>
                </div>
            </div>

            <div class="col-md-7">
                <div class="card p-3 shadow">
                    <h5 class="card-title text-success mb-3">Detection Results & Findings</h5>
                    <div id="resultsSummary" class="mb-3 text-muted">Run analysis to see detected dark patterns, confidence scores, and compliance analysis.</div>
                    <pre id="resultsOutput">Ready.</pre>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function runAnalysis() {
            const url = document.getElementById('targetUrl').value;
            const mode = document.getElementById('analysisMode').value;
            const html = document.getElementById('htmlSnippet').value;
            const out = document.getElementById('resultsOutput');
            const summary = document.getElementById('resultsSummary');

            out.textContent = 'Running analysis...';
            try {
                const res = await fetch('/api/v1/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        url: url,
                        html: html,
                        mode: mode,
                        elements: [
                            { element_type: 'button', element_text: "Subscribe now - it's free and you must agree!", element_selector: '.cta' },
                            { element_type: 'a', element_text: "No thanks, I prefer paying full price", element_selector: '.decline-link' },
                            { element_type: 'span', element_text: "Auto-renews at $99/mo after 3 days trial. Cancel anytime with $25 fee.", element_selector: '.fine-print' }
                        ]
                    })
                });
                const data = await res.json();
                out.textContent = JSON.stringify(data, null, 2);
                summary.innerHTML = `<span class="badge bg-danger badge-dp">${data.all_findings ? data.all_findings.length : 0} Findings</span> Confidence: <strong>${Math.round((data.aggregated_confidence || 0) * 100)}%</strong> | Risk: <strong>${Math.round((data.aggregated_risk || 0) * 100)}%</strong>`;
            } catch (err) {
                out.textContent = 'Error: ' + err.message;
            }
        }
    </script>
</body>
</html>"""


@app.on_event("startup")
async def startup_event():
    """Initialize the API on startup."""
    _register_default_agents()
    logger.info(f"DPIE API started successfully with {len(registry.list_agents())} registered agents")


def run_api(host: str = settings.api_host, port: int = settings.api_port):
    """Run the FastAPI development server."""
    uvicorn.run("dpie.api:app", host=host, port=port, reload=True, access_log=True)


__all__ = [
    "app",
    "health_check",
    "list_agents",
    "triage_agent",
    "investigate_agent",
    "correlate_agent",
    "reporter_agent",
    "analyze_endpoint",
    "dashboard_view",
    "run_api",
]
