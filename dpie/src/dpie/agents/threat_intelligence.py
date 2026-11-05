"""DPIE Threat Intelligence Agent

Maintains references to known deceptive patterns.
Supports external intelligence integrations.
Compares findings with documented examples.
Distinguishes verified intelligence from model-generated hypotheses.
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


class ThreatIntelligenceAgent(BaseAgent):
    """Maintains references to known deceptive patterns.

    Supports external intelligence integrations.
    Compares findings with documented examples.
    Distinguishes verified intelligence from model-generated hypotheses.
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.THREAT_INTELLIGENCE

    async def analyze(self, input_data: AgentInput) -> AgentOutput:
        """Compare findings with known threat intelligence.

        Args:
            input_data: AgentInput with findings from previous agents

        Returns:
            AgentOutput with threat intelligence comparison results
        """
        start_time = time.time()

        if not self.can_process(input_data):
            return self._generate_failed_output(start_time, "No input data provided")

        # Get previous findings
        previous_findings = input_data.previous_findings or []
        elements = input_data.elements or []
        url = input_data.url or "unknown"

        # Known dark pattern intelligence database
        known_patterns = self._load_known_patterns()

        findings: List[EvidenceRecord] = []

        # Compare previous findings with known intelligence
        for finding in previous_findings:
            pattern = finding.get("detected_pattern", "") if isinstance(finding, dict) else getattr(finding, "detected_pattern", "")
            confidence = finding.get("confidence_score", 0) if isinstance(finding, dict) else getattr(finding, "confidence_score", 0)

            # Check if this pattern matches known intelligence
            known_match = self._match_known_pattern(pattern, confidence, known_patterns)

            if known_match:
                finding_result = EvidenceRecord(
                    source_agent=self.agent_type,
                    source_url=url,
                    element_text=finding.get("element_text", "") if isinstance(finding, dict) else getattr(finding, "evidence_text", ""),
                    detected_pattern=pattern,
                    confidence_score=known_match["confidence"],
                    evidence_text=f"Verified intelligence: {known_match['description']}",
                    risk_score=known_match["risk"],
                    tags=["threat_intelligence", "verified", pattern],
                    metadata={
                        "is_verified": True,
                        "source": known_match.get("source", "dpie_internal"),
                        "pattern_category": known_match.get("category", ""),
                        "reference": known_match.get("reference", ""),
                    },
                )
                findings.append(finding_result)
            else:
                # Model-generated hypothesis - lower confidence
                finding_result = EvidenceRecord(
                    source_agent=self.agent_type,
                    source_url=url,
                    element_text=finding.get("element_text", "") if isinstance(finding, dict) else getattr(finding, "evidence_text", ""),
                    detected_pattern=pattern,
                    confidence_score=min(confidence * 0.8, 1.0),
                    evidence_text=f"Model-generated hypothesis: {pattern} pattern detected",
                    risk_score=min(confidence * 0.9, 1.0),
                    tags=["threat_intelligence", "hypothesis", pattern],
                    metadata={
                        "is_verified": False,
                        "source": "dpie_model",
                        "pattern_category": pattern,
                        "reference": None,
                    },
                )
                findings.append(finding_result)

        # Also analyze current elements for known patterns
        for element in elements:
            element_text = element.get("element_text", "") or ""
            element_type = element.get("element_type", "")
            element_selector = element.get("element_selector", "")

            pattern_match = self._analyze_element_for_known_pattern(
                element_text, element_type, element_selector
            )

            if pattern_match:
                finding = EvidenceRecord(
                    source_agent=self.agent_type,
                    source_element_id=element_selector,
                    source_url=url,
                    element_type=element_type,
                    element_selector=element_selector,
                    element_text=element_text,
                    element_attributes=element.get("element_attributes", {}),
                    detected_pattern=pattern_match["pattern"],
                    confidence_score=pattern_match["confidence"],
                    evidence_text=f"Known pattern match: {pattern_match['description']}",
                    risk_score=pattern_match["risk"],
                    tags=["threat_intelligence", "verified", pattern_match["pattern"]],
                    metadata={
                        "is_verified": True,
                        "source": pattern_match.get("source", "dpie_internal"),
                        "pattern_category": pattern_match.get("category", ""),
                        "reference": pattern_match.get("reference", ""),
                    },
                )
                findings.append(finding)

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

        requires_followup = len(findings) > 0 and overall_confidence > 0.5
        next_agents = [AgentType.COMPLIANCE] if findings else []

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
            f"Threat Intelligence agent completed: {len(findings)} findings, "
            f"confidence: {overall_confidence:.2f}"
        )

        return output

    def _load_known_patterns(self) -> Dict[str, Any]:
        """Load known dark pattern intelligence database."""
        return {
            "interface_interference": {
                "category": "Interface Interference",
                "description": "Elements that distract or mislead users by modifying the UI",
                "risk": 0.6,
                "source": "dark_pattern_research",
                "reference": "https://www.darkpatterns.org",
            },
            "obstruction": {
                "category": "Obstruction",
                "description": "Barriers that make it difficult for users to accomplish goals",
                "risk": 0.7,
                "source": "dark_pattern_research",
                "reference": "https://www.darkpatterns.org",
            },
            "sneaking": {
                "category": "Sneaking",
                "description": "Deceptive designs that hide, delay, or confuse information",
                "risk": 0.65,
                "source": "dark_pattern_research",
                "reference": "https://www.darkpatterns.org",
            },
            "forced_action": {
                "category": "Forced Action",
                "description": "Actions forced on users without reasonable alternatives",
                "risk": 0.8,
                "source": "dark_pattern_research",
                "reference": "https://www.darkpatterns.org",
            },
            "nagging": {
                "category": "Nagging",
                "description": "Excessive repeated prompts that annoy or wear down users",
                "risk": 0.5,
                "source": "dark_pattern_research",
                "reference": "https://www.darkpatterns.org",
            },
            "confirmshaming": {
                "category": "Obstruction",
                "description": "Using shame or guilt to manipulate user decisions",
                "risk": 0.7,
                "source": "dark_pattern_research",
                "reference": "https://www.darkpatterns.org",
            },
            "bait_and_switch": {
                "category": "Sneaking",
                "description": "Advertising one thing but delivering another",
                "risk": 0.8,
                "source": "dark_pattern_research",
                "reference": "https://www.darkpatterns.org",
            },
            "hidden_costs": {
                "category": "Sneaking",
                "description": "Revealing additional costs late in the process",
                "risk": 0.75,
                "source": "dark_pattern_research",
                "reference": "https://www.darkpatterns.org",
            },
        }

    def _match_known_pattern(
        self,
        pattern: str,
        confidence: float,
        known_patterns: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Match a pattern against known intelligence."""
        if not pattern:
            return None

        pattern_lower = pattern.lower()

        # Direct match
        if pattern_lower in known_patterns:
            match = known_patterns[pattern_lower]
            return {
                "pattern": pattern,
                "confidence": min(max(confidence, 0.7), 0.95),
                "description": match["description"],
                "risk": match["risk"],
                "source": match["source"],
                "category": match["category"],
                "reference": match["reference"],
            }

        # Partial match
        for known_pattern, info in known_patterns.items():
            if known_pattern in pattern_lower or pattern_lower in known_pattern:
                return {
                    "pattern": pattern,
                    "confidence": min(max(confidence * 0.9, 0.6), 0.9),
                    "description": info["description"],
                    "risk": info["risk"],
                    "source": info["source"],
                    "category": info["category"],
                    "reference": info["reference"],
                }

        return None

    def _analyze_element_for_known_pattern(
        self,
        element_text: str,
        element_type: str,
        element_selector: str,
    ) -> Optional[Dict[str, Any]]:
        """Analyze an element for known dark pattern indicators."""
        element_text_lower = element_text.lower()

        known_patterns = self._load_known_patterns()

        # Check for forced action indicators
        if any(kw in element_text_lower for kw in ["must", "required", "need", "have to"]):
            if element_type in ("button", "input"):
                return {
                    "pattern": "forced_action",
                    "confidence": 0.8,
                    "description": "Forced action: element requires user commitment",
                    "risk": 0.8,
                    "source": "dpie_internal",
                    "category": "Forced Action",
                    "reference": "https://www.darkpatterns.org",
                }

        # Check for sneaking indicators
        if any(kw in element_text_lower for kw in ["hidden", "conceal", "mask", "disguise"]):
            return {
                "pattern": "sneaking",
                "confidence": 0.75,
                "description": "Sneaking pattern: element may hide true intent",
                "risk": 0.65,
                "source": "dpie_internal",
                "category": "Sneaking",
                "reference": "https://www.darkpatterns.org",
            }

        # Check for obstruction indicators
        if any(kw in element_text_lower for kw in ["confirmshaming", "shame", "blame"]):
            return {
                "pattern": "obstruction",
                "confidence": 0.8,
                "description": "Obstruction pattern: element creates barrier to user goal",
                "risk": 0.7,
                "source": "dpie_internal",
                "category": "Obstruction",
                "reference": "https://www.darkpatterns.org",
            }

        # Check for nagging indicators
        if any(kw in element_text_lower for kw in ["reminder", "remind", "remember"]):
            return {
                "pattern": "nagging",
                "confidence": 0.7,
                "description": "Nagging pattern: element may repeatedly prompt user",
                "risk": 0.5,
                "source": "dpie_internal",
                "category": "Nagging",
                "reference": "https://www.darkpatterns.org",
            }

        return None

    def _generate_summary(self, findings: List[EvidenceRecord]) -> str:
        """Generate human-readable summary of findings."""
        if not findings:
            return "No threat intelligence matches found."

        verified_count = sum(1 for f in findings if f.metadata and f.metadata.get("is_verified"))
        hypothesis_count = len(findings) - verified_count

        parts = [f"Compared findings against threat intelligence database"]
        if verified_count:
            parts.append(f"{verified_count} verified intelligence match(es)")
        if hypothesis_count:
            parts.append(f"{hypothesis_count} model-generated hypothesis(es)")

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
        """Check if threat intelligence can process the given input."""
        has_content = bool(
            input_data.previous_findings or
            input_data.elements or
            input_data.url
        )
        return has_content


__all__ = ["ThreatIntelligenceAgent"]