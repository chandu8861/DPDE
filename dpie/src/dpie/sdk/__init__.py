"""DPIE Python SDK

Software Development Kit for the DPIE (DarkPattern Intelligence Engine) framework.
"""

from __future__ import annotations

from .sdk_core import DarkPatternEngine, AnalysisConfig, AnalysisResult
from .sdk_providers import set_api_key, get_api_key, list_providers_status
from dpie.schemas import (
    DetectionStatus,
    AgentType,
    OrchestrationMode,
    EvidenceRecord,
    ReportFormat,
)

__all__ = [
    "DarkPatternEngine",
    "AnalysisConfig",
    "AnalysisResult",
    "set_api_key",
    "get_api_key",
    "list_providers_status",
    "DetectionStatus",
    "AgentType",
    "OrchestrationMode",
    "EvidenceRecord",
    "ReportFormat",
]
