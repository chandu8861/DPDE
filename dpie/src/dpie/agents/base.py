"""DPIE Agent Base Interface

Defines the contract that all specialized agents must follow.
Enables structured agent-to-agent communication and orchestration.

All agents must implement:
- analyze(): Main analysis method
- get_config(): Get agent configuration
- get_agent_type(): Return agent type enum
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from dpie.schemas import (
    AgentType,
    AgentOutput,
    EvidenceRecord,
    AgentInput,
    OrchestrationMode,
    DetectionStatus,
)


# ---------------------------------------------------------------------------
# BaseAgent Class
# ---------------------------------------------------------------------------


class BaseAgent:
    """Base class for all DPIE specialized agents.

    Provides common functionality and enforces the agent interface contract.
    Agents are designed to be interchangeable and composable through
    structured outputs (EvidenceRecord) rather than unstructured messages.
    """

    def __init__(self, knowledge_base=None, configuration=None, llm_provider=None):
        self.knowledge_base = knowledge_base or {}
        self.configuration = configuration or {}
        self.llm_provider = llm_provider
        self._execution_count = 0
        self._total_tokens = 0
        self._total_time_ms = 0

    @property
    def agent_type(self) -> AgentType:
        """Return the type of this agent. Must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement agent_type property")

    async def analyze(self, input_data: AgentInput) -> AgentOutput:
        """Perform the agent's analysis.

        This is the main entry point for all agent analysis.
        Must return an AgentOutput containing findings, confidence, etc.

        Args:
            input_data: AgentInput containing source material and context

        Returns:
            AgentOutput with analysis results
        """
        raise NotImplementedError("Subclasses must implement analyze method")

    def get_configuration(self) -> dict:
        """Get this agent's configuration."""
        return self.configuration

    def can_process(self, input_data: AgentInput) -> bool:
        """Check if this agent can process the given input."""
        return bool(input_data and (input_data.html or input_data.dom_data or input_data.elements or input_data.url))

    def generate_common_output(self, **kwargs: Any) -> dict:
        """Generate a common AgentOutput structure.

        Args:
            status: Execution status string
            findings: List of finding dicts
            **kwargs: Additional fields for AgentOutput

        Returns:
            dict with common structure
        """
        return {
            "agent_type": self.agent_type,
            "status": "completed",
            "findings": kwargs.get("findings", []),
            "overall_confidence": kwargs.get("overall_confidence", 0.5),
            "overall_risk": kwargs.get("overall_risk"),
            "execution_time_ms": kwargs.get("execution_time_ms"),
            "model_used": kwargs.get("model_used"),
            "tokens_consumed": kwargs.get("tokens_consumed"),
            "next_agents": kwargs.get("next_agents"),
            "requires_followup": kwargs.get("requires_followup", False),
        }

    def get_agent_info(self) -> dict:
        """Get agent information for dashboard/debugging."""
        return {
            "agent_type": self.agent_type,
            "execution_count": self._execution_count,
            "total_time_ms": self._total_time_ms,
            "total_tokens": self._total_tokens,
            "configuration": self.configuration,
        }

    def log_execution(self, start_time: float, output: Any = None) -> None:
        """Record execution metrics."""
        self._execution_count += 1
        elapsed_ms = int((time.time() - start_time) * 1000)
        self._total_time_ms += elapsed_ms
        if output and hasattr(output, "tokens_consumed") and output.tokens_consumed:
            self._total_tokens += output.tokens_consumed

    async def execute_with_timeout(self, coroutine, timeout_seconds: int = 30) -> dict:
        """Execute an analysis coroutine with timeout.

        Args:
            coroutine: Async coroutine that returns dict
            timeout_seconds: Maximum execution time in seconds

        Returns:
            dict from the coroutine

        Raises:
            TimeoutError: If execution exceeds timeout
        """
        try:
            return await asyncio.wait_for(coroutine, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger = __import__("logging").getLogger(__name__)
            logger.error(f"Agent {self.agent_type} execution timed out after {timeout_seconds}s")
            return {
                "agent_type": self.agent_type,
                "status": "failed",
                "findings": [],
                "overall_confidence": 0.0,
                "overall_risk": 1.0,
                "execution_time_ms": timeout_seconds * 1000,
                "model_used": None,
                "tokens_consumed": 0,
                "requires_followup": False,
            }


# ---------------------------------------------------------------------------
# Agent Registry
# ---------------------------------------------------------------------------

from dpie.agents.registry import (
    AgentRegistry,
    get_agent_registry,
    init_agent_registry,
    register_agent,
)

# ---------------------------------------------------------------------------
# Export useful types
# ---------------------------------------------------------------------------

__all__ = [
    "BaseAgent",
    "AgentType",
    "AgentStatus",
    "OrchestrationMode",
    "DetectionStatus",
    "AgentRegistry",
    "get_agent_registry",
    "init_agent_registry",
    "register_agent",
]