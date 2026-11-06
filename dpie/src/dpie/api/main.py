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
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn

from dpie.schemas import (
    AnalysisResponse,
    AgentInput,
    OrchestrationMode,
    AgentType,
)
from dpie.orchestration import (
    OrchestrationEngine,
)
from dpie.knowledge_base import get_knowledge_base
from dpie.agents.registry import get_agent_registry
from dpie.config import settings, load_settings
from dpie._version import __version__

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize/cleanup around app lifecycle (preferred over on_event)."""
    _register_default_agents()
    logger.info(f"DPIE API started successfully with {len(registry.list_agents())} registered agents")
    yield


# Create FastAPI app
app = FastAPI(
    title="DPIE - DarkPattern Intelligence Engine",
    description="""
    Multi-Agent AI Framework for detecting, investigating, correlating, 
    classifying, and reporting deceptive user-interface practices and dark patterns.
    """,
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
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
    version: str = __version__
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
        version=__version__,
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
    try:
        from dpie.dashboard_ui import get_dashboard_html
        return get_dashboard_html()
    except Exception:
        return "<html><body><h3>DPIE Dashboard</h3><p>Dashboard UI module unavailable. Use <a href='/docs'>/docs</a>.</p></body></html>"


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
