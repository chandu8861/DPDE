"""DPIE Python SDK Core

Core SDK module containing the DarkPatternEngine class and supporting types.

This is the main entry point for developers using the DPIE Python SDK.
"""

from __future__ import annotations

import json
import asyncio
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from dpie.schemas import (
    AgentInput,
    AgentOutput,
    AnalysisRequest,
    AnalysisResponse,
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
from dpie.providers import ProviderFactory, ProviderWrapper, OpenAIProvider
from dpie.knowledge_base import get_knowledge_base
from dpie.config import settings, load_settings
from dpie.agents import (
    TriageAgent,
    InvestigatorAgent,
    CorrelatorAgent,
    ReporterAgent,
    get_agent_registry,
    AgentRegistry,
)


# ---------------------------------------------------------------------------
# SDK Types
# -------------------------------------------------------------------------


class AnalysisConfig(BaseModel):
    """Configuration for an analysis run."""
    
    mode: OrchestrationMode = Field(
        default=OrchestrationMode.FAST, description="Execution mode"
    )
    include_report: bool = Field(
        default=False, description="Whether to generate report"
    )
    include_evidence: bool = Field(
        default=True, description="Whether to include evidence records"
    )
    agents: Optional[List[str]] = Field(
        default=None, description="Specific agent types to run (override mode)"
    )
    confidence_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum confidence threshold"
    )
    model: Optional[str] = Field(
        default=None, description="Specific LLM model to use"
    )
    fallback_provider: Optional[str] = Field(
        default=None, description="Fallback provider on primary failure"
    )


class AnalysisResult(BaseModel):
    """Result from an analysis run."""
    
    request_id: str = Field(description="Unique request identifier")
    status: str = Field(description="Overall analysis status")
    
    # Agent outputs (individual agent results)
    triage: Optional[Dict[str, Any]] = Field(
        default=None, description="Triage agent output"
    )
    investigator: Optional[Dict[str, Any]] = Field(
        default=None, description="Investigator agent output"
    )
    correlator: Optional[Dict[str, Any]] = Field(
        default=None, description="Correlator agent output"
    )
    reporter: Optional[Dict[str, Any]] = Field(
        default=None, description="Reporter output"
    )
    threat_hunter: Optional[Dict[str, Any]] = Field(
        default=None, description="Threat Hunter output"
    )
    forensics: Optional[Dict[str, Any]] = Field(
        default=None, description="Forensics output"
    )
    compliance: Optional[Dict[str, Any]] = Field(
        default=None, description="Compliance output"
    )
    
    # Aggregated findings
    all_findings: List[Dict[str, Any]] = Field(
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
        default=None, description="Total execution time in ms"
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
    
    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True


# ---------------------------------------------------------------------------
# Main DarkPatternEngine Class
# -------------------------------------------------------------------------


class DarkPatternEngine:
    """Main entry point for the DPIE Python SDK.
    
    A modular, reusable Multi-Agent AI Framework for detecting, investigating,
    correlating, classifying, and reporting deceptive user-interface practices
    and dark patterns.
    
    This is an independent software product, not built specifically for any
    existing browser extension or website.
    
    Example:
        >>> from dpie import DarkPatternEngine
        >>> 
        >>> engine = DarkPatternEngine(mode="deep")
        >>> result = engine.analyze({
        >>>     "url": "https://example.com",
        >>>     "elements": [...]
        >>> })
        >>> print(result.findings)
    """
    
    def __init__(
        self,
        mode: str = "fast",
        api_key: Optional[str] = None,
        provider: str = "openai",
        model: Optional[str] = None,
        knowledge_base: Optional[Any] = None,
    ):
        """Initialize the DarkPatternEngine.
        
        Args:
            mode: Execution mode ("fast", "deep", "full")
            api_key: API key for the LLM provider
            provider: LLM provider ("openai", "anthropic", "google_gemini", "ollama")
            model: Specific model name (defaults to provider default)
            knowledge_base: Optional knowledge base instance
        """
        load_settings()
        
        # Set up API key if provided
        if api_key:
            from dpie.sdk.sdk_providers import set_api_key
            set_api_key(provider, api_key)
        
        # Initialize orchestration engine
        self.mode = OrchestrationMode(mode.lower()) if mode.lower() in [
            "fast", "deep", "full"
        ] else OrchestrationMode.FAST
        
        self.engine = OrchestrationEngine(mode=self.mode)
        
        # Set up LLM provider
        self._provider = self._initialize_provider(
            provider, model or settings.default_provider
        )
        
        # Set up knowledge base
        self.kb = knowledge_base or get_knowledge_base()
        
        # Initialize agent registry
        from dpie.agents.registry import init_agent_registry, get_agent_registry
        init_agent_registry()
        self.registry = get_agent_registry()
        
        # Ensure default agents are registered
        self._ensure_agents_initialized()
    
    def _initialize_provider(
        self, provider: str, model: Optional[str] = None
    ) -> ProviderWrapper:
        """Initialize the LLM provider.
        
        Args:
            provider: Provider name
            model: Specific model name
            
        Returns:
            ProviderWrapper instance
        """
        from dpie.providers import ProviderFactory
        
        # Create base provider
        try:
            base_provider = ProviderFactory.create_provider(provider)
        except ValueError:
            # Fall back to openai
            base_provider = ProviderFactory.create_provider("openai")
        
        # Wrap with fallback and monitoring
        wrapper = ProviderWrapper(primary=base_provider)
        
        # Set model if specified
        if model:
            wrapper.primary.model_info  # Just to validate
        
        return wrapper
    
    def _ensure_agents_initialized(self):
        """Ensure default agents are registered in the registry."""
        from dpie.agents.triage import TriageAgent
        from dpie.agents.investigator import InvestigatorAgent
        from dpie.agents.correlator import CorrelatorAgent
        from dpie.agents.reporter import ReporterAgent
        
        default_agents = [
            (AgentType.TRIAGE, TriageAgent),
            (AgentType.INVESTIGATOR, InvestigatorAgent),
            (AgentType.CORRELATOR, CorrelatorAgent),
            (AgentType.REPORTER, ReporterAgent),
        ]
        
        for agent_type, agent_class in default_agents:
            if not self.registry.is_agent_enabled(agent_type):
                agent = agent_class(knowledge_base=self.kb)
                self.registry.register(agent)
    
    async def _analyze_single(
        self,
        input_data: AgentInput,
    ) -> AnalysisResult:
        """Run analysis with the current engine configuration.
        
        Args:
            input_data: AgentInput with analysis request data
            
        Returns:
            AnalysisResult with all findings and metadata
        """
        # Execute analysis based on mode
        if self.mode == OrchestrationMode.FAST:
            response = await run_fast_analysis(input_data, self.engine)
        elif self.mode == OrchestrationMode.DEEP:
            response = await run_deep_analysis(input_data, self.engine)
        else:
            response = await run_full_analysis(input_data, self.engine)
        
        # Convert to AnalysisResult
        result = AnalysisResult(
            request_id=response.request_id,
            status=response.status,
            triage=response.triage.model_dump() if response.triage else None,
            investigator=response.investigator.model_dump() if response.investigator else None,
            correlator=response.correlator.model_dump() if response.correlator else None,
            reporter=response.reporter.model_dump() if response.reporter else None,
            threat_hunter=getattr(response, 'threat_hunter', None),
            forensics=getattr(response, 'forensics', None),
            compliance=getattr(response, 'compliance', None),
            all_findings=[f.model_dump() for f in response.all_findings],
            aggregated_confidence=response.aggregated_confidence,
            aggregated_risk=response.aggregated_risk,
            execution_summary=response.execution_summary,
            total_execution_time_ms=response.total_execution_time_ms,
            models_used=response.models_used or [],
            tokens_total=response.tokens_total,
        )
        
        # Generate report if needed
        if hasattr(response, 'reporter') and response.reporter:
            # Simple report generation
            result.report = {
                "format": "summary",
                "pattern_name": "detected_patterns" if response.aggregated_confidence > 0.3 else "no_patterns_detected",
                "severity": "medium" if response.aggregated_confidence > 0.3 else "low",
                "confidence": response.aggregated_confidence,
                "risk": response.aggregated_risk,
                "evidence_count": len(response.all_findings),
                "findings_summary": [
                    {
                        "pattern": f.detected_pattern or "unknown",
                        "confidence": f.confidence_score,
                        "description": f.evidence_text[:100] if f.evidence_text else ""
                    }
                    for f in response.all_findings[:5]  # Top 5
                ],
            }
        
        return result
    
    def analyze(
        self,
        input_data: Union[Dict[str, Any], AgentInput],
        config: Optional[AnalysisConfig] = None,
    ) -> AnalysisResult:
        """Analyze HTML/DOM content for dark patterns.
        
        This is the main method developers use to analyze webpages or UI
        for dark pattern elements.
        
        Args:
            input_data: Dict or AgentInput containing:
                - url: Target URL (optional)
                - html: HTML content or DOM snapshot (optional)
                - dom_data: Structured DOM data (optional)
                - elements: List of UI elements to analyze (optional)
            config: Optional AnalysisConfig overriding defaults
            
        Returns:
            AnalysisResult with all findings and metadata
            
        Example:
            >>> from dpie import DarkPatternEngine
            >>> engine = DarkPatternEngine(mode="deep")
            >>> result = engine.analyze({
            >>>     "url": "https://example.com",
            >>>     "elements": [
            >>>         {"tag": "button", "text": "Subscribe now!", "selector": ".cta-btn"}
            >>>     ]
            >>> })
            >>> print(result.aggregated_confidence)
            >>> print([f['pattern'] for f in result.all_findings])
        """
        # Convert dict to AgentInput if needed
        if isinstance(input_data, dict):
            # Build AgentInput from dict
            agent_input = AgentInput(
                url=input_data.get("url"),
                html=input_data.get("html"),
                dom_data=input_data.get("dom_data"),
                elements=input_data.get("elements"),
                mode=config.mode if config else self.mode,
            )
        else:
            agent_input = input_data
        
        # Run analysis
        result = asyncio.get_event_loop().run_until_complete(
            self._analyze_single(agent_input)
        )
        
        return result
    
    def set_mode(self, mode: str) -> None:
        """Change the execution mode.
        
        Args:
            mode: New mode ("fast", "deep", "full")
        """
        self.mode = OrchestrationMode(mode.lower()) if mode.lower() in [
            "fast", "deep", "full"
        ] else OrchestrationMode.FAST
        self.engine = OrchestrationEngine(mode=self.mode)
    
    def get_status(self) -> Dict[str, Any]:
        """Get engine status and statistics.
        
        Returns:
            Dictionary with engine information
        """
        return {
            "mode": self.mode.value,
            "agents_registered": len(self.registry.get_all_agents()),
            "agents_enabled": len(self.registry.get_enabled_agents()),
            "knowledge_base_entities": len(self.kb._memory["evidence"]),
            "total_execution_count": self.engine._execution_count if hasattr(self.engine, '_execution_count') else 0,
        }
    
    def get_findings_summary(self, result: AnalysisResult) -> Dict[str, Any]:
        """Get a summary of the analysis findings.
        
        Args:
            result: AnalysisResult from engine.analyze()
            
        Returns:
            Summary dictionary
        """
        patterns = {}
        for finding in result.all_findings:
            pattern = finding.get("detected_pattern", "unknown")
            if pattern not in patterns:
                patterns[pattern] = {
                    "count": 0,
                    "confidences": [],
                    "risk_scores": [],
                }
            patterns[pattern]["count"] += 1
            patterns[pattern]["confidences"].append(finding.get("confidence_score", 0))
            patterns[pattern]["risk_scores"].append(finding.get("risk_score") or 0)
        
        # Calculate summaries
        summary = {
            "total_findings": len(result.all_findings),
            "patterns_detected": list(patterns.keys()),
            "aggregated_confidence": result.aggregated_confidence,
            "aggregated_risk": result.aggregated_risk,
            "pattern_details": {},
        }
        
        for pattern, data in patterns.items():
            avg_confidence = sum(data["confidences"]) / len(data["confidences"]) if data["confidences"] else 0
            avg_risk = sum(data["risk_scores"]) / len(data["risk_scores"]) if data["risk_scores"] else 0
            summary["pattern_details"][pattern] = {
                "count": data["count"],
                "average_confidence": round(avg_confidence, 3),
                "average_risk": round(avg_risk, 3),
            }
        
        return summary


# ---------------------------------------------------------------------------
# SDK Provider Management
# -------------------------------------------------------------------------


def set_api_key(provider: str, api_key: str) -> None:
    """Set an API key for a specific provider.
    
    Args:
        provider: Provider name ("openai", "anthropic", "google_gemini", "ollama")
        api_key: The API key value
    """
    from dpie.providers import ProviderWrapper
    
    # Create provider and store in settings
    if provider == "openai":
        settings.openai_api_key = api_key
    elif provider == "anthropic":
        settings.anthropic_api_key = api_key
    elif provider == "google_gemini":
        settings.google_api_key = api_key
    elif provider == "ollama":
        settings.ollama_base_url = api_key  # For ollama, this might be a base URL
    
    logger = __import__("logging").getLogger(__name__)
    logger.info(f"API key set for provider: {provider}")


def get_provider(provider: Optional[str] = None) -> ProviderWrapper:
    """Get the current LLM provider wrapper.
    
    Args:
        provider: Provider name (uses default if None)
        
    Returns:
        ProviderWrapper instance
    """
    from dpie.providers import ProviderFactory, ProviderWrapper
    
    provider_name = provider or settings.default_provider
    base_provider = ProviderFactory.create_provider(provider_name)
    return ProviderWrapper(primary=base_provider)


def list_providers() -> Dict[str, bool]:
    """Check which LLM providers are configured.
    
    Returns:
        Dict mapping provider names to availability status
    """
    from dpie.providers import ProviderFactory
    
    return ProviderFactory.get_provider_names_with_keys(
        openai_key=settings.openai_api_key,
        anthropic_key=settings.anthropic_api_key,
        google_key=settings.google_api_key,
    )


# ---------------------------------------------------------------------------
# Module logger
# -------------------------------------------------------------------------

import logging
logger = logging.getLogger(__name__)

# Console handler for SDK
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s - DPIE-SDK - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logger.setLevel(logging.INFO)
logger.addHandler(handler)


# ---------------------------------------------------------------------------
# Export
# -------------------------------------------------------------------------

__all__ = [
    "DarkPatternEngine",
    "AnalysisConfig",
    "AnalysisResult",
    "set_api_key",
    "get_provider",
    "list_providers",
    "DetectionStatus",
    "AgentType",
    "OrchestrationMode",
    "EvidenceRecord",
    "ReportFormat",
]