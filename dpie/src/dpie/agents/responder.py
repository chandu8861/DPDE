"""DPIE Responder Agent

Recommends corrective actions.
Suggests improvements to problematic interface designs.
Supports configurable remediation workflows.
Requires explicit authorization before making changes.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List

from dpie.schemas import (
    AgentType,
    AgentInput,
    AgentOutput,
    EvidenceRecord,
)
from dpie.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class ResponderAgent(BaseAgent):
    """Recommends corrective actions for dark patterns.

    Suggests improvements to problematic interface designs.
    Supports configurable remediation workflows.
    Requires explicit authorization before making changes.
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.RESPONDER

    async def analyze(self, input_data: AgentInput) -> AgentOutput:
        """Generate remediation recommendations for detected dark patterns.

        Args:
            input_data: AgentInput with findings from previous agents

        Returns:
            AgentOutput with remediation recommendations
        """
        start_time = time.time()

        if not self.can_process(input_data):
            return self._generate_failed_output(start_time, "No input data provided")

        # Get previous findings
        previous_findings = input_data.previous_findings or []
        url = input_data.url or "unknown"
        configuration = input_data.configuration or {}
        require_authorization = configuration.get("require_authorization", True)

        findings: List[EvidenceRecord] = []

        # Generate recommendations for each finding
        for finding in previous_findings:
            pattern = finding.get("detected_pattern", "") if isinstance(finding, dict) else getattr(finding, "detected_pattern", "")
            confidence = finding.get("confidence_score", 0) if isinstance(finding, dict) else getattr(finding, "confidence_score", 0)
            element_text = finding.get("element_text", "") if isinstance(finding, dict) else getattr(finding, "evidence_text", "")

            recommendations = self._generate_recommendations(pattern, confidence, element_text)

            finding_result = EvidenceRecord(
                source_agent=self.agent_type,
                source_url=url,
                element_text=element_text,
                detected_pattern=pattern,
                confidence_score=confidence,
                evidence_text=f"Remediation recommendations for {pattern}: {recommendations['summary']}",
                risk_score=min(confidence + 0.1, 1.0),
                tags=["responder", "remediation", pattern],
                metadata={
                    "recommendations": recommendations["actions"],
                    "implementation_priority": recommendations["priority"],
                    "requires_authorization": require_authorization,
                    "auto_apply": False,  # Never auto-apply changes
                    "estimated_effort": recommendations["effort"],
                },
            )
            findings.append(finding_result)

        # Calculate overall confidence and risk
        overall_confidence = 0.5
        overall_risk = 0.3

        if findings:
            confidences = [f.confidence_score for f in findings if f.confidence_score]
            risks = [f.risk_score for f in findings if f.risk_score is not None]
            if confidences:
                overall_confidence = sum(confidences) / len(confidences)
            if risks:
                overall_risk = sum(risks) / len(risks)

        requires_followup = len(findings) > 0
        next_agents = []

        execution_time_ms = int((time.time() - start_time) * 1000)

        output = AgentOutput(
            agent_type=self.agent_type,
            status="completed",
            findings=findings,
            summary=self._generate_summary(findings),
            overall_confidence=overall_confidence,
            overall_risk=overall_risk,
            execution_time_ms=execution_time_ms,
            model_used=None,
            tokens_consumed=0,
            next_agents=next_agents,
            requires_followup=requires_followup,
        )

        logger.info(
            f"Responder agent completed: {len(findings)} recommendations, "
            f"confidence: {overall_confidence:.2f}"
        )

        return output

    def _generate_recommendations(
        self,
        pattern: str,
        confidence: float,
        element_text: str,
    ) -> Dict[str, Any]:
        """Generate remediation recommendations for a specific pattern."""
        recommendation_map = {
            "forced_action": {
                "actions": [
                    "Add clear opt-out or cancel button",
                    "Provide alternative options to users",
                    "Ensure users understand what they are agreeing to",
                    "Make exit paths prominent and accessible",
                ],
                "priority": "high",
                "effort": "medium",
                "summary": "Provide clear alternatives and exit paths",
            },
            "sneaking": {
                "actions": [
                    "Make hidden information explicitly visible",
                    "Disclose all costs and terms upfront",
                    "Remove hidden fields or obscured elements",
                    "Ensure transparency in all user communications",
                ],
                "priority": "high",
                "effort": "medium",
                "summary": "Increase transparency and disclosure",
            },
            "obstruction": {
                "actions": [
                    "Remove unnecessary barriers to task completion",
                    "Simplify cancellation and opt-out processes",
                    "Provide direct paths to user goals",
                    "Reduce steps required to complete actions",
                ],
                "priority": "high",
                "effort": "high",
                "summary": "Remove barriers and simplify processes",
            },
            "nagging": {
                "actions": [
                    "Limit repetition of prompts and notifications",
                    "Allow users to dismiss prompts permanently",
                    "Implement reasonable frequency limits",
                    "Provide clear opt-out from notifications",
                ],
                "priority": "medium",
                "effort": "low",
                "summary": "Reduce prompt frequency and allow dismissal",
            },
            "interface_interference": {
                "actions": [
                    "Ensure UI elements don't distract from core content",
                    "Maintain clear visual hierarchy",
                    "Remove unnecessary visual elements",
                    "Improve focus order and accessibility",
                ],
                "priority": "medium",
                "effort": "medium",
                "summary": "Reduce visual interference and improve clarity",
            },
        }

        pattern_lower = pattern.lower()
        if pattern_lower in recommendation_map:
            return recommendation_map[pattern_lower]

        # Default recommendations for unknown patterns
        return {
            "actions": [
                "Review the element for potential dark pattern characteristics",
                "Consider user testing to validate intent",
                "Document the design decision rationale",
            ],
            "priority": "low",
            "effort": "low",
            "summary": "Manual review recommended",
        }

    def _generate_summary(self, findings: List[EvidenceRecord]) -> str:
        """Generate human-readable summary of findings."""
        if not findings:
            return "No remediation recommendations generated."

        priorities = {}
        for f in findings:
            if f.metadata:
                priority = f.metadata.get("implementation_priority", "unknown")
                priorities[priority] = priorities.get(priority, 0) + 1

        parts = [f"Generated {len(findings)} remediation recommendations"]
        if priorities:
            priority_str = ", ".join([f"{k}: {v}" for k, v in sorted(priorities.items())])
            parts.append(f"Priorities: {priority_str}")

        return ". ".join(parts) + "."

    def _generate_failed_output(self, start_time: float, error_msg: str) -> AgentOutput:
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
        """Check if responder can process the given input."""
        has_content = bool(
            input_data.previous_findings or
            input_data.elements or
            input_data.url
        )
        return has_content


__all__ = ["ResponderAgent"]