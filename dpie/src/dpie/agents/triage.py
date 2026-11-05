"""DPIE Triage Agent

Fast initial analysis agent that screens webpage elements and detection signals.
Identifies suspicious elements and assigns investigation priority.
Routes relevant findings to other agents.
Minimizes unnecessary LLM calls.
"""

from __future__ import annotations

import asyncio
import time
import logging
import importlib.util
import os
from typing import Any, Dict, List, Optional

from dpie.schemas import (
    AgentType,
    AgentInput,
    AgentOutput,
    EvidenceRecord,
    DarkPatternCategory,
    OrchestrationMode,
    DetectionStatus,
)
from dpie.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class TriageAgent(BaseAgent):
    """Fast initial analysis agent.

    Screens webpage elements and detection signals.
    Identifies suspicious elements.
    Assigns investigation priority.
    Routes relevant findings to other agents.
    Minimizes unnecessary LLM calls.
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.TRIAGE

    async def analyze(self, input_data: AgentInput) -> AgentOutput:
        """Perform fast triage analysis of webpage/UI elements.

        Args:
            input_data: AgentInput with HTML/DOM data and elements

        Returns:
            AgentOutput with triage findings and priority routing
        """
        start_time = time.time()

        # Validate input
        if not self.can_process(input_data):
            return self._generate_failed_output(start_time, "No input data provided")

        # Extract data from input_data object
        elements = input_data.elements or []
        html = input_data.html or ""
        dom_data = input_data.dom_data or {}
        url = input_data.url or ""

        findings: List[EvidenceRecord] = []
        suspicious_elements: List[Dict[str, Any]] = []
        priority_routing: List[AgentType] = []

        # Quick heuristic-based detection without LLM calls for speed
        for element in elements:
            element_type = element.get("element_type", "")
            element_text = element.get("element_text", "").lower()
            attrs = element.get("element_attributes", {})

            # Fast pattern detection using rule-based checks
            is_suspicious = False
            detected_pattern = None
            confidence = 0.3  # Base confidence for triage

            # Check for known dark pattern indicators
            if element_type in ("button", "a") and any(
                keyword in element_text for keyword in ["free", "discount", "limited", "offer", "urgent"]
            ):
                is_suspicious = True
                detected_pattern = "sneaking"
                confidence = 0.5

            if element_text in ("accept", "accept all", "i agree") and any(
                keyword in element_text for keyword in ["cookies", "tracking", "privacy"]
            ):
                is_suspicious = True
                detected_pattern = "obstruction"
                confidence = 0.45

            if any(keyword in element_text for keyword in ["continue", "skip", "close"]) and len(element_text) > 0:
                # Could be hidden close button or forced action indicator
                pass  # Low priority, investigate deeper

            if is_suspicious:
                # Create evidence record for this suspicious element
                finding = EvidenceRecord(
                    source_agent=self.agent_type,
                    source_element_id=element.get("element_selector"),
                    source_url=url,
                    element_type=element_type,
                    element_selector=element.get("element_selector"),
                    element_text=element.get("element_text"),
                    element_attributes=attrs,
                    detected_pattern=detected_pattern,
                    confidence_score=confidence,
                    evidence_text=f"Triage detected {detected_pattern} pattern indicator: {element_text[:100]}",
                    risk_score=min(confidence + 0.1, 1.0),
                    tags=[detected_pattern, "triage-flagged"],
                )
                findings.append(finding)
                suspicious_elements.append({
                    "element": element,
                    "pattern": detected_pattern,
                    "confidence": confidence,
                })

        # If we have suspicious elements, route to investigator and correlator
        if suspicious_elements:
            priority_routing = [AgentType.INVESTIGATOR, AgentType.CORRELATOR]

        # Calculate overall confidence
        overall_confidence = max([f.confidence_score for f in findings], default=0.3)

        # Determine requires followup
        requires_followup = len(findings) > 0 and overall_confidence > 0.4

        execution_time_ms = int((time.time() - start_time) * 1000)

        output = AgentOutput(
            agent_type=self.agent_type,
            status="completed",
            findings=findings,
            summary=f"Triage analyzed {len(elements) if elements else 0} elements, "
                    f"found {len(findings)} suspicious patterns, "
                    f"confidence: {overall_confidence:.2f}",
            overall_confidence=overall_confidence,
            overall_risk=max([f.risk_score for f in findings], default=0.3) if findings else 0.3,
            execution_time_ms=execution_time_ms,
            model_used=None,  # Rule-based, no LLM
            tokens_consumed=0,  # No LLM calls
            next_agents=priority_routing,
            requires_followup=requires_followup,
        )

        logger.info(
            f"Triage agent completed: {len(findings)} findings, "
            f"routing to {priority_routing}, "
            f"confidence: {overall_confidence:.2f}"
        )

        return output

    def _generate_failed_output(self, start_time: float, error_msg: str) -> AgentOutput:
        """Generate a failed output when input validation fails."""
        execution_time_ms = int((time.time() - start_time) * 1000)

        return AgentOutput(
            agent_type=self.agent_type,
            status="failed",
            findings=[],
            overall_confidence=0.0,
            overall_risk=1.0,
            execution_time_ms=execution_time_ms,
            model_used=None,
            tokens_consumed=0,
            requires_followup=False,
        )

    def can_process(self, input_data: AgentInput) -> bool:
        """Check if triage can process the given input."""
        # Triage can process if there's some input material
        has_content = bool(
            input_data.html or
            input_data.dom_data or
            input_data.elements or
            input_data.url
        )
        return has_content


__all__ = ["TriageAgent"]