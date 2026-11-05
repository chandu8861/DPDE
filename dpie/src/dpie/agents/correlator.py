"""DPIE Correlator Agent

Combines findings from different agents.
Detects relationships between suspicious elements.
Identifies larger deceptive interaction flows.
Removes duplicate findings.
Calculates evidence-based confidence and risk scores.
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


class CorrelatorAgent(BaseAgent):
    """Combines findings from different agents.

    Detects relationships between suspicious elements.
    Identifies larger deceptive interaction flows.
    Removes duplicate findings.
    Calculates evidence-based confidence and risk scores.
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.CORRELATOR

    async def analyze(self, input_data: AgentInput) -> AgentOutput:
        """Combine findings from different agents and detect patterns.

        Args:
            input_data: AgentInput with findings from previous agents

        Returns:
            AgentOutput with correlated findings and risk scores
        """
        start_time = time.time()

        # Validate input
        if not self.can_process(input_data):
            return self._generate_failed_output(start_time, "No input data provided")

        # Extract data from input_data object
        elements = input_data.elements or []
        url = input_data.url or ""

        new_findings: List[EvidenceRecord] = []
        for element in elements:
            elem_finding = EvidenceRecord(
                source_agent=self.agent_type,
                source_element_id=element.get("element_selector"),
                source_url=url,
                element_type=element.get("element_type"),
                element_selector=element.get("element_selector"),
                element_text=element.get("element_text"),
                element_attributes=element.get("element_attributes", {}),
                detected_pattern=self._detect_pattern(element),
                confidence_score=self._calculate_element_confidence(element),
                risk_score=self._calculate_element_risk(element),
                tags=["correlated", "correlator-flagged"],
            )
            new_findings.append(elem_finding)

        # Deduplicate and merge findings
        correlated_findings = self._deduplicate_and_correlate(new_findings)

        # Calculate aggregated confidence and risk
        overall_confidence = 0.5
        overall_risk = 0.3

        if correlated_findings:
            confidences = [f.confidence_score for f in correlated_findings if f.confidence_score]
            risks = [f.risk_score for f in correlated_findings if f.risk_score is not None]
            if confidences:
                overall_confidence = sum(confidences) / len(confidences)
            if risks:
                overall_risk = sum(risks) / len(risks)

        # Detect larger interaction flows
        interaction_flows = self._detect_interaction_flows(correlated_findings)

        # Determine requires followup and next agents
        requires_followup = len(correlated_findings) > 0 and overall_confidence > 0.4
        next_agents = [AgentType.REPORTER] if correlated_findings else []

        execution_time_ms = int((time.time() - start_time) * 1000)

        output = AgentOutput(
            agent_type=self.agent_type,
            status="completed",
            findings=correlated_findings,
            summary=self._generate_correlation_summary(correlated_findings, interaction_flows),
            overall_confidence=overall_confidence,
            overall_risk=overall_risk,
            execution_time_ms=execution_time_ms,
            model_used=None,
            tokens_consumed=0,
            next_agents=next_agents,
            requires_followup=requires_followup,
        )

        logger.info(
            f"Correlator agent completed: {len(correlated_findings)} correlated findings, "
            f"flows detected: {len(interaction_flows)}, "
            f"confidence: {overall_confidence:.2f}"
        )

        return output

    def _detect_pattern(self, element: Dict[str, Any]) -> Optional[str]:
        """Detect dark pattern pattern from element data."""
        element_text = element.get("element_text", "").lower()
        element_type = element.get("element_type", "")

        # Check for various pattern indicators
        if any(kw in element_text for kw in ["must", "required", "need"]):
            return "forced_action"
        if any(kw in element_text for kw in ["hidden", "conceal", "mask"]):
            return "sneaking"
        if any(kw in element_text for kw in ["confirmshaming", "shame"]):
            return "obstruction"
        if any(kw in element_text for kw in ["reminder", "remind"]):
            return "nagging"
        if any(kw in element_text for kw in ["limited", "urgent", "expires"]):
            return "sneaking"

        # Based on element type
        if element_type in ("button", "input"):
            return "forced_action" if len(element_text) > 0 else None

        return None

    def _calculate_element_confidence(self, element: Dict[str, Any]) -> float:
        """Calculate confidence score for an element."""
        element_text = element.get("element_text", "").lower()
        confidence = 0.3  # Base

        # Boost confidence for specific patterns
        if any(kw in element_text for kw in ["must", "required"]):
            confidence = 0.7
        elif any(kw in element_text for kw in ["hidden", "conceal"]):
            confidence = 0.6
        elif any(kw in element_text for kw in ["limited", "urgent"]):
            confidence = 0.55
        elif len(element.get("element_text", "")) > 50:
            confidence = 0.4

        return min(confidence, 1.0)

    def _calculate_element_risk(self, element: Dict[str, Any]) -> Optional[float]:
        """Calculate risk score for an element."""
        element_type = element.get("element_type", "")
        element_text = element.get("element_text", "").lower()

        # Risk based on pattern and element type
        if any(kw in element_text for kw in ["must", "required"]):
            return 0.8 if element_type in ("button", "input") else 0.6
        elif any(kw in element_text for kw in ["hidden", "conceal"]):
            return 0.7
        elif any(kw in element_text for kw in ["limited", "urgent"]):
            return 0.5
        elif len(element.get("element_text", "")) > 100:
            return 0.3

        return None

    def _deduplicate_and_correlate(self, findings: List[EvidenceRecord]) -> List[EvidenceRecord]:
        """Deduplicate findings and detect correlations between them."""
        if not findings:
            return []

        # Group findings by detected pattern
        pattern_groups: Dict[str, List[EvidenceRecord]] = {}
        for finding in findings:
            pattern = finding.detected_pattern or "unknown"
            if pattern not in pattern_groups:
                pattern_groups[pattern] = []
            pattern_groups[pattern].append(finding)

        # Correlate findings across patterns
        correlated: List[EvidenceRecord] = []

        for finding in findings:
            related_count = 0
            for other in findings:
                if other is finding:
                    continue
                if (finding.detected_pattern == other.detected_pattern or
                    self._patterns_related(finding.detected_pattern, other.detected_pattern)):
                    related_count += 1

            # If finding has relationships, keep it with adjusted confidence
            finding.confidence_score = min(finding.confidence_score * (1 + related_count * 0.1), 1.0)
            correlated.append(finding)

        return correlated

    def _patterns_related(self, pattern1: Optional[str], pattern2: Optional[str]) -> bool:
        """Check if two pattern categories are related."""
        if not pattern1 or not pattern2:
            return False

        related_pairs = [
            ("forced_action", "obstruction"),
            ("sneaking", "interface_interference"),
            ("nagging", "obstruction"),
            ("forced_action", "sneaking"),
        ]

        p1, p2 = pattern1.lower(), pattern2.lower()
        for p1_rel, p2_rel in related_pairs:
            if (p1 == p1_rel and p2 == p2_rel) or (p1 == p2_rel and p2 == p1_rel):
                return True

        return False

    def _detect_interaction_flows(self, findings: List[EvidenceRecord]) -> List[Dict[str, Any]]:
        """Detect larger deceptive interaction flows from findings."""
        flows: List[Dict[str, Any]] = []

        if len(findings) < 2:
            return flows

        pattern_sequence = [f.detected_pattern for f in findings if f.detected_pattern]

        if len(set(pattern_sequence)) > 1:
            flow = {
                "type": "multi_pattern_flow",
                "patterns_detected": list(set(pattern_sequence)),
                "element_count": len(findings),
                "description": "Multiple different dark pattern types detected in sequence",
            }
            flows.append(flow)

        element_ids = [f.source_element_id for f in findings if f.source_element_id]
        if len(element_ids) != len(set(element_ids)):
            flow = {
                "type": "element_concentration",
                "repeated_elements": [eid for eid in set(element_ids) if element_ids.count(eid) > 1],
                "element_count": len(findings),
                "description": "Same elements appear in multiple pattern detections",
            }
            flows.append(flow)

        return flows

    def _generate_correlation_summary(
        self,
        findings: List[EvidenceRecord],
        interaction_flows: List[Dict[str, Any]]
    ) -> str:
        """Generate summary of correlated findings."""
        if not findings:
            return "No correlated findings."

        summary_parts = ["Correlated " + str(len(findings)) + " findings"]

        pattern_counts: Dict[str, int] = {}
        for f in findings:
            p = f.detected_pattern or "unknown"
            pattern_counts[p] = pattern_counts.get(p, 0) + 1

        for pattern, count in pattern_counts.items():
            summary_parts.append(str(count) + " " + pattern)

        if interaction_flows:
            flow_types = [f["type"] for f in interaction_flows]
            summary_parts.append("Flows: " + ", ".join(set(flow_types)))

        return ". ".join(summary_parts) + "."

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
        """Check if correlator can process the given input."""
        has_content = bool(
            input_data.elements or
            input_data.previous_findings or
            input_data.url
        )
        return has_content


__all__ = ["CorrelatorAgent"]