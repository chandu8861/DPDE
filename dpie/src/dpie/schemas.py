"""DPIE Shared Schemas Module

Pydantic models for shared intelligence, evidence, and agent communication.
All agents use these structured types for input/output without relying on
unstructured chat messages.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DetectionStatus(str, Enum):
    """Status of a dark pattern detection."""
    PASSED = "passed"          # No dark pattern detected
    DETECTED = "detected"      # Dark pattern detected
    UNCERTAIN = "uncertain"    # Inconclusive result


class AgentType(str, Enum):
    """Types of specialized agents in the framework."""
    TRIAGE = "triage"
    INVESTIGATOR = "investigator"
    THREAT_HUNTER = "threat_hunter"
    CORRELATOR = "correlator"
    FORENSICS = "forensics"
    THREAT_INTELLIGENCE = "threat_intelligence"
    COMPLIANCE = "compliance"
    REPORTER = "reporter"
    RESPONDER = "responder"
    AUTO_RESPONDER = "auto_responder"
    MITRE_ANALYST = "mitre_analyst"


class AgentStatus(str, Enum):
    """Status of agent execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class ReportFormat(str, Enum):
    """Supported report formats."""
    JSON = "json"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"
    HTML = "html"


class OrchestrationMode(str, Enum):
    """Execution modes for the agent orchestrator."""
    FAST = "fast"
    DEEP = "deep"
    FULL = "full"


# ---------------------------------------------------------------------------
# Evidence Models
# ---------------------------------------------------------------------------

class EvidenceRecord(BaseModel):
    """Structured evidence record from agent analysis."""
    
    # Unique identifier
    evidence_id: Optional[str] = Field(
        default=None, description="Unique identifier for this evidence record"
    )
    
    # Source identification
    source_agent: AgentType = Field(description="Agent that generated this evidence")
    source_element_id: Optional[str] = Field(
        default=None, description="Identifier of the DOM/UI element"
    )
    source_url: Optional[str] = Field(
        default=None, description="URL where the evidence was collected"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When evidence was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="When evidence was last updated")
    
    # Evidence content
    element_type: Optional[str] = Field(
        default=None, description="HTML element type (button, input, div, etc.)"
    )
    element_selector: Optional[str] = Field(
        default=None, description="CSS selector for the element"
    )
    element_text: Optional[str] = Field(
        default=None, description="Visible text content of the element"
    )
    element_attributes: Dict[str, Any] = Field(
        default_factory=dict, description="HTML attributes of the element"
    )
    
    # Detection data
    detected_pattern: Optional[str] = Field(
        default=None, description="Detected dark pattern category"
    )
    detected_subcategory: Optional[str] = Field(
        default=None, description="Detected dark pattern subcategory"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Confidence score (0-1)"
    )
    evidence_text: Optional[str] = Field(
        default=None, description="Supporting text explanation"
    )
    visual_properties: Optional[Dict[str, Any]] = Field(
        default=None, description="CSS/visual property observations"
    )
    interaction_context: Optional[Dict[str, Any]] = Field(
        default=None, description="User interaction context"
    )
    
    # Metadata
    risk_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Risk score (0-1)"
    )
    tags: List[str] = Field(
        default_factory=list, description="Classification tags"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    
    # Verification
    verified: bool = Field(default=False, description="Whether evidence was verified")
    verification_notes: Optional[str] = Field(
        default=None, description="Verification notes"
    )
    
    @validator("confidence_score")
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v
    
    @validator("risk_score")
    def validate_risk(cls, v):
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("Risk score must be between 0.0 and 1.0")
        return v


# ---------------------------------------------------------------------------
# Dark Pattern Taxonomy
# -------------------------------------------------------------------------


class DarkPatternCategory(BaseModel):
    """Category from established dark pattern research."""
    
    name: str = Field(description="Category name (e.g., 'Interface Interference')")
    code: Optional[str] = Field(
        default=None, description="Optional short code/identifier"
    )
    description: str = Field(description="Category description")
    subcategories: List[str] = Field(
        default_factory=list, description="Subcategory names"
    )
    severity_range: str = Field(
        default="medium", description="Typical severity range"
    )


class DarkPatternKnowledgeBase(BaseModel):
    """Structured dark pattern knowledge base entry."""
    
    category: DarkPatternCategory
    examples: List[Dict[str, Any]] = Field(
        default_factory=list, description="Known examples"
    )
    anti_examples: List[Dict[str, Any]] = Field(
        default_factory=list, description="Legitimate UI examples"
    )
    documentation: Optional[str] = Field(
        default=None, description="Link to documentation"
    )
    severity_weight: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Severity weight (0-1)"
    )


# ---------------------------------------------------------------------------
# Agent Communication Models
# -------------------------------------------------------------------------


class AgentInput(BaseModel):
    """Base input model for all agents."""
    
    # Source material
    url: Optional[str] = Field(default=None, description="Target URL")
    html: Optional[str] = Field(
        default=None, description="HTML content or DOM snapshot"
    )
    dom_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Structured DOM data"
    )
    elements: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="List of UI elements to analyze"
    )
    screenshot_metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Metadata from screenshot analysis"
    )
    
    # Context
    investigation_id: Optional[str] = Field(
        default=None, description="Related investigation ID"
    )
    previous_findings: Optional[List[EvidenceRecord]] = Field(
        default=None, description="Findings from previous agent runs"
    )
    configuration: Dict[str, Any] = Field(
        default_factory=dict, description="Agent-specific configuration"
    )
    
    # Metadata
    timestamp: Optional[datetime] = Field(
        default_factory=datetime.utcnow, description="Analysis timestamp"
    )


class AgentOutput(BaseModel):
    """Base output model for all agents."""
    
    agent_type: AgentType = Field(description="Type of agent that produced this output")
    status: AgentStatus = Field(description="Execution status")
    
    # Findings
    findings: List[EvidenceRecord] = Field(
        default_factory=list, description="Detected findings/evidence"
    )
    summary: Optional[str] = Field(
        default=None, description="Human-readable summary"
    )
    
    # Confidence and risk
    overall_confidence: float = Field(
        ge=0.0, le=1.0, default=0.5, description="Overall confidence"
    )
    overall_risk: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Overall risk"
    )
    
    # Agent-specific
    execution_time_ms: Optional[int] = Field(
        default=None, description="Execution time in milliseconds"
    )
    model_used: Optional[str] = Field(
        default=None, description="LLM model used for analysis"
    )
    tokens_consumed: Optional[int] = Field(
        default=None, description="Number of tokens consumed"
    )
    
    # Routing
    next_agents: Optional[List[AgentType]] = Field(
        default=None, description="Agents to route findings to next"
    )
    requires_followup: bool = Field(
        default=False, description="Whether follow-up investigation is needed"
    )
    
    @validator("overall_confidence")
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Overall confidence must be between 0.0 and 1.0")
        return v
    
    @validator("overall_risk")
    def validate_risk(cls, v):
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("Overall risk must be between 0.0 and 1.0")
        return v


# ---------------------------------------------------------------------------
# Analysis Request/Response
# -------------------------------------------------------------------------


class AnalysisRequest(AgentInput):
    """Request model for analysis operations."""
    
    mode: OrchestrationMode = Field(
        default=OrchestrationMode.FAST, description="Execution mode"
    )
    include_report: bool = Field(
        default=False, description="Whether to include report generation"
    )
    include_evidence: bool = Field(
        default=True, description="Whether to include evidence records"
    )


class AnalysisResponse(BaseModel):
    """Response model for analysis operations."""
    
    request_id: str = Field(description="Unique request identifier")
    status: str = Field(description="Overall analysis status")
    
    # Results
    triage: Optional[AgentOutput] = Field(
        default=None, description="Triage agent output"
    )
    investigator: Optional[AgentOutput] = Field(
        default=None, description="Investigator agent output"
    )
    correlator: Optional[AgentOutput] = Field(
        default=None, description="Correlator agent output"
    )
    reporter: Optional[Dict[str, Any]] = Field(
        default=None, description="Report generation output"
    )
    
    # Aggregated findings
    all_findings: List[EvidenceRecord] = Field(
        default_factory=list, description="All findings from all agents"
    )
    aggregated_confidence: float = Field(
        ge=0.0, le=1.0, default=0.5, description="Aggregated confidence"
    )
    aggregated_risk: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Aggregated risk score"
    )
    
    # Metadata
    execution_summary: Optional[str] = Field(
        default=None, description="Summary of execution"
    )
    total_execution_time_ms: Optional[int] = Field(
        default=None, description="Total execution time"
    )
    
    # Model info
    models_used: List[str] = Field(
        default_factory=list, description="Models used by agents"
    )
    tokens_total: Optional[int] = Field(
        default=None, description="Total tokens consumed"
    )
    
    # Report
    report: Optional[Dict[str, Any]] = Field(
        default=None, description="Generated report (if include_report=True)"
    )
    
    @validator("aggregated_confidence")
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Aggregated confidence must be between 0.0 and 1.0")
        return v
    
    @validator("aggregated_risk")
    def validate_risk(cls, v):
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("Aggregated risk must be between 0.0 and 1.0")
        return v


# ---------------------------------------------------------------------------
# Report Models
# -------------------------------------------------------------------------


class ReportRequest(BaseModel):
    """Request model for report generation."""
    
    format: ReportFormat = Field(default=ReportFormat.JSON, description="Report format")
    include_evidence: bool = Field(
        default=True, description="Include evidence records"
    )
    include_recommendations: bool = Field(
        default=True, description="Include recommendations"
    )
    custom_sections: Optional[List[str]] = Field(
        default=None, description="Custom report sections"
    )


class ReportContent(BaseModel):
    """Structured report content."""
    
    format: ReportFormat
    pattern_name: str = Field(description="Detected dark pattern name")
    severity: str = Field(description="Severity level")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    risk: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Risk score"
    )
    evidence: List[EvidenceRecord] = Field(
        default_factory=list, description="Supporting evidence"
    )
    explanation: str = Field(description="Plain-language explanation")
    recommendations: List[str] = Field(
        default_factory=list, description="Recommended actions"
    )
    compliance_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Compliance mapping information"
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Configuration References
# -------------------------------------------------------------------------


class AgentConfiguration(BaseModel):
    """Configuration for a specific agent."""
    
    agent_type: AgentType
    enabled: bool = Field(default=True, description="Whether agent is enabled")
    confidence_threshold: float = Field(
        ge=0.0, le=1.0, default=0.5, description="Confidence threshold"
    )
    timeout_seconds: int = Field(
        default=30, description="Maximum execution time"
    )
    model_preference: Optional[str] = Field(
        default=None, description="Preferred LLM model"
    )
    custom_parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Agent-specific parameters"
    )


class OrchestrationConfiguration(BaseModel):
    """Configuration for the agent orchestrator."""
    
    mode: OrchestrationMode = Field(default=OrchestrationMode.FAST)
    enabled_agents: List[AgentType] = Field(
        default_factory=lambda: [
            AgentType.TRIAGE,
            AgentType.INVESTIGATOR,
            AgentType.CORRELATOR,
        ]
    )
    parallel_execution: bool = Field(
        default=False, description="Whether to run agents in parallel"
    )
    max_parallel_agents: int = Field(
        default=3, description="Maximum number of parallel agents"
    )
    confidence_threshold: float = Field(
        ge=0.0, le=1.0, default=0.5, description="Global confidence threshold"
    )
    timeout_seconds: int = Field(
        default=60, description="Maximum orchestration timeout"
    )


# ---------------------------------------------------------------------------
# Rebuild Pydantic models to resolve forward references
# ---------------------------------------------------------------------------

# Call model_rebuild on all models that have cross-references
# This is required for Pydantic v2 when models reference each other
EvidenceRecord.model_rebuild()
DarkPatternCategory.model_rebuild()
DarkPatternKnowledgeBase.model_rebuild()
AgentInput.model_rebuild()
AgentOutput.model_rebuild()
AnalysisRequest.model_rebuild()
AnalysisResponse.model_rebuild()
ReportRequest.model_rebuild()
ReportContent.model_rebuild()
AgentConfiguration.model_rebuild()
OrchestrationConfiguration.model_rebuild()


# ---------------------------------------------------------------------------
# Export useful types
# -------------------------------------------------------------------------

__all__ = [
    "DetectionStatus",
    "AgentType",
    "AgentStatus",
    "ReportFormat",
    "OrchestrationMode",
    "EvidenceRecord",
    "DarkPatternCategory",
    "DarkPatternKnowledgeBase",
    "AgentInput",
    "AgentOutput",
    "AnalysisRequest",
    "AnalysisResponse",
    "ReportRequest",
    "ReportContent",
    "AgentConfiguration",
    "OrchestrationConfiguration",
]