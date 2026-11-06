"""DPIE - DarkPattern Intelligence Engine

A modular, reusable Multi-Agent AI Framework for detecting, investigating,
correlating, classifying, and reporting deceptive user-interface practices
and dark patterns.
"""

from dpie._version import __version__

from dpie.schemas import (
    AgentType,
    AgentStatus,
    AgentInput,
    AgentOutput,
    EvidenceRecord,
    DarkPatternCategory,
    OrchestrationMode,
    DetectionStatus,
    ReportFormat,
    AnalysisRequest,
    AnalysisResponse,
)
from dpie.config import settings, load_settings
from dpie.knowledge_base import get_knowledge_base, SharedKnowledgeBase
from dpie.agents.registry import get_agent_registry, init_agent_registry, AgentRegistry
from dpie.orchestration import (
    OrchestrationEngine,
    run_fast_analysis,
    run_deep_analysis,
    run_full_analysis,
)
from dpie.sdk.sdk_core import DarkPatternEngine, AnalysisConfig, AnalysisResult
from dpie.providers import ProviderFactory, BaseLLMProvider

__all__ = [
    "__version__",
    "AgentType",
    "AgentStatus",
    "AgentInput",
    "AgentOutput",
    "EvidenceRecord",
    "DarkPatternCategory",
    "OrchestrationMode",
    "DetectionStatus",
    "ReportFormat",
    "AnalysisRequest",
    "AnalysisResponse",
    "settings",
    "load_settings",
    "get_knowledge_base",
    "SharedKnowledgeBase",
    "get_agent_registry",
    "init_agent_registry",
    "AgentRegistry",
    "OrchestrationEngine",
    "run_fast_analysis",
    "run_deep_analysis",
    "run_full_analysis",
    "DarkPatternEngine",
    "AnalysisConfig",
    "AnalysisResult",
    "ProviderFactory",
    "BaseLLMProvider",
]

