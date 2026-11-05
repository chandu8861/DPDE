"""DPIE Auto Responder Agent

Coordinates approved workflows.
Handles routing and escalation.
Operates under configurable safety and permission policies.
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
)
from dpie.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class AutoResponderAgent(BaseAgent):
    """Coordinates approved workflows and handles routing/escalation.

    Operates under configurable safety and permission policies.
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.AUTO_RESPONDER

    async def analyze(self, input_data: AgentInput) -> AgentOutput:
        """Coordinate workflows based on previous findings.

        Args:
            input_data: AgentInput with findings from previous agents

        Returns:
            AgentOutput with workflow coordination results
        """
        start_time = time.time()

        if not self.can_process(input_data):
            return self._generate_failed_output(start_time, "No input data provided")

        # Get previous findings and configuration
        previous_findings = input_data.previous_findings or []
        url = input_data.url or "unknown"
        configuration = input_data.configuration or {}

        safety_policy = configuration.get("safety_policy", "conservative")
        permission_policy = configuration.get("permission_policy", "manual_approval")
        auto_escalation = configuration.get("auto_escalation", False)

        findings: List[EvidenceRecord] = []

        # Coordinate workflow based on findings
        for finding in previous_findings:
            pattern = finding.get("detected_pattern", "") if isinstance(finding, dict) else getattr(finding, "detected_pattern", "")
            confidence = finding.get("confidence_score", 0) if isinstance(finding, dict) else getattr(finding, "confidence_score", 0)
            risk = finding.get("risk_score", 0) if isinstance(finding, dict) else getattr(finding, "risk_score", 0)

            # Determine workflow action based on safety policy
            workflow_action = self._determine_workflow_action(
                pattern, confidence, risk, safety_policy, permission_policy
            )

            finding_result = EvidenceRecord(
                source_agent=self.agent_type,
                source_url=url,
                element_text=finding.get("element_text", "") if isinstance(finding, dict) else getattr(finding, "evidence_text", ""),
                detected_pattern=pattern,
                confidence_score=confidence,
                evidence_text=f"Workflow action: {workflow_action['description']}",
                risk_score=risk,
                tags=["auto_responder", "workflow", pattern],
                metadata={
                    "workflow_action": workflow_action["action"],
                    "escalation_required": workflow_action["escalation_required"],
                    "auto_execute": workflow_action["auto_execute"],
                    "permission_required": workflow_action["permission_required"],
                    "safety_policy": safety_policy,
                    "routing_target": workflow_action.get("routing_target", ""),
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
            f"Auto Responder agent completed: {len(findings)} workflow actions, "
            f"confidence: {overall_confidence:.2f}"
        )

        return output

    def _determine_workflow_action(
        self,
        pattern: str,
        confidence: float,
        risk: float,
        safety_policy: str,
        permission_policy: str,
    ) -> Dict[str, Any]:
        """Determine the appropriate workflow action based on policy."""
        # Determine action based on risk level and safety policy
        if risk >= 0.8:
            action = "escalate_immediately"
            escalation_required = True
            auto_execute = False
            permission_required = True
            routing_target = "security_team"
        elif risk >= 0.6:
            action = "escalate_for_review"
            escalation_required = True
            auto_execute = False
            permission_required = True
            routing_target = "compliance_team"
        elif risk >= 0.4:
            if safety_policy == "conservative":
                action = "queue_for_manual_review"
                escalation_required = False
                auto_execute = False
                permission_required = True
                routing_target = "product_team"
            else:
                action = "suggest_remediation"
                escalation_required = False
                auto_execute = False
                permission_required = True
                routing_target = "design_team"
        else:
            action = "log_and_monitor"
            escalation_required = False
            auto_execute = False
            permission_required = False
            routing_target = "none"

        # Apply permission policy overrides
        if permission_policy == "manual_approval":
            auto_execute = False
            permission_required = True
        elif permission_policy == "semi_automatic":
            if risk < 0.4:
                auto_execute = True
                permission_required = False
            else:
                auto_execute = False
                permission_required = True

        # Generate description
        descriptions = {
            "escalate_immediately": "Escalate immediately to security team",
            "escalate_for_review": "Escalate for compliance team review",
            "queue_for_manual_review": "Queue for manual review by product team",
            "suggest_remediation": "Suggest remediation to design team",
            "log_and_monitor": "Log finding and monitor for changes",
        }

        return {
            "action": action,
            "description": descriptions.get(action, "Unknown action"),
            "escalation_required": escalation_required,
            "auto_execute": auto_execute,
            "permission_required": permission_required,
            "routing_target": routing_target,
        }

    def _generate_summary(self, findings: List[EvidenceRecord]) -> str:
        """Generate human-readable summary of findings."""
        if not findings:
            return "No workflow actions determined."

        escalate_count = sum(
            1 for f in findings
            if f.metadata and f.metadata.get("escalation_required")
        )
        auto_execute_count = sum(
            1 for f in findings
            if f.metadata and f.metadata.get("auto_execute")
        )

        parts = [f"Coordinated {len(findings)} workflow actions"]
        if escalate_count:
            parts.append(f"{escalate_count} require escalation")
        if auto_execute_count:
            parts.append(f"{auto_execute_count} can auto-execute")

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
        """Check if auto responder can process the given input."""
        has_content = bool(
            input_data.previous_findings or
            input_data.elements or
            input_data.url
        )
        return has_content


__all__ = ["AutoResponderAgent"]