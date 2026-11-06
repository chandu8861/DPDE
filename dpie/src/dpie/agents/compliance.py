"""DPIE Compliance Agent

Maps findings to applicable regulations and guidelines.
Supports configurable jurisdiction-specific rules.
Includes evidence and explains the reasoning behind compliance mappings.
Never automatically declares legal violations based solely on AI predictions.
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


class ComplianceAgent(BaseAgent):
    """Maps findings to applicable regulations and guidelines.

    Supports configurable jurisdiction-specific rules.
    Includes evidence and explains the reasoning behind compliance mappings.
    Never automatically declares legal violations based solely on AI predictions.
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.COMPLIANCE

    async def analyze(self, input_data: AgentInput) -> AgentOutput:
        """Map findings to compliance regulations.

        Args:
            input_data: AgentInput with findings from previous agents

        Returns:
            AgentOutput with compliance mapping results
        """
        start_time = time.time()

        if not self.can_process(input_data):
            return self._generate_failed_output(start_time, "No input data provided")

        # Get previous findings
        previous_findings = input_data.previous_findings or []
        url = input_data.url or "unknown"

        # Get configuration for jurisdiction-specific rules
        configuration = input_data.configuration or {}
        jurisdiction = configuration.get("jurisdiction", "general")
        enabled_regulations = configuration.get("enabled_regulations", ["gdpr", "ccpa"])

        # Load compliance rules
        compliance_rules = self._load_compliance_rules(jurisdiction, enabled_regulations)

        findings: List[EvidenceRecord] = []

        # Map each finding to compliance regulations
        for finding in previous_findings:
            pattern = finding.get("detected_pattern", "") if isinstance(finding, dict) else getattr(finding, "detected_pattern", "")
            confidence = finding.get("confidence_score", 0) if isinstance(finding, dict) else getattr(finding, "confidence_score", 0)
            element_text = finding.get("element_text", "") if isinstance(finding, dict) else getattr(finding, "evidence_text", "")

            # Find matching compliance rules
            matching_rules = self._match_compliance_rules(pattern, confidence, element_text, compliance_rules)

            for rule_match in matching_rules:
                finding_result = EvidenceRecord(
                    source_agent=self.agent_type,
                    source_url=url,
                    element_text=element_text,
                    detected_pattern=pattern,
                    confidence_score=rule_match["confidence"],
                    evidence_text=f"Compliance mapping: {rule_match['description']}",
                    risk_score=rule_match["risk"],
                    tags=["compliance", rule_match["regulation"], pattern],
                    metadata={
                        "regulation": rule_match["regulation"],
                        "regulation_name": rule_match["regulation_name"],
                        "violation_type": rule_match["violation_type"],
                        "severity": rule_match["severity"],
                        "requires_legal_review": rule_match["requires_legal_review"],
                        "reasoning": rule_match["reasoning"],
                        "auto_declare_violation": False,  # Never auto-declare
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

        requires_followup = len(findings) > 0 and overall_confidence > 0.4
        next_agents = [AgentType.REPORTER] if findings else []

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
            f"Compliance agent completed: {len(findings)} compliance mappings, "
            f"confidence: {overall_confidence:.2f}"
        )

        return output

    def _load_compliance_rules(
        self,
        jurisdiction: str,
        enabled_regulations: List[str],
    ) -> List[Dict[str, Any]]:
        """Load compliance rules for the given jurisdiction."""
        all_rules = {
            "gdpr": {
                "regulation_name": "General Data Protection Regulation",
                "jurisdiction": "EU",
                "rules": {
                    "forced_action": {
                        "violation_type": "lack_of_free_consent",
                        "severity": "high",
                        "description": "Forced action may violate GDPR consent requirements",
                        "reasoning": "GDPR requires freely given, specific, informed consent",
                        "risk": 0.8,
                        "requires_legal_review": True,
                    },
                    "sneaking": {
                        "violation_type": "lack_of_transparency",
                        "severity": "high",
                        "description": "Sneaking patterns may violate GDPR transparency requirements",
                        "reasoning": "GDPR Article 12 requires transparent information",
                        "risk": 0.7,
                        "requires_legal_review": True,
                    },
                    "obstruction": {
                        "violation_type": "right_to_withdraw",
                        "severity": "medium",
                        "description": "Obstruction may violate right to withdraw consent",
                        "reasoning": "GDPR Article 7(3) right to withdraw consent",
                        "risk": 0.6,
                        "requires_legal_review": True,
                    },
                    "nagging": {
                        "violation_type": "excessive_processing",
                        "severity": "low",
                        "description": "Nagging may constitute excessive data processing",
                        "reasoning": "GDPR principle of data minimization",
                        "risk": 0.4,
                        "requires_legal_review": False,
                    },
                },
            },
            "ccpa": {
                "regulation_name": "California Consumer Privacy Act",
                "jurisdiction": "California, USA",
                "rules": {
                    "forced_action": {
                        "violation_type": "dark_pattern_consent",
                        "severity": "high",
                        "description": "Forced action may violate CCPA dark pattern prohibitions",
                        "reasoning": "CCPA regulations prohibit dark patterns that obstruct opt-out",
                        "risk": 0.75,
                        "requires_legal_review": True,
                    },
                    "sneaking": {
                        "violation_type": "deceptive_practices",
                        "severity": "high",
                        "description": "Sneaking may violate CCPA deceptive practices provisions",
                        "reasoning": "CCPA prohibits deceptive design patterns",
                        "risk": 0.7,
                        "requires_legal_review": True,
                    },
                    "obstruction": {
                        "violation_type": "obstructing_opt_out",
                        "severity": "medium",
                        "description": "Obstruction may violate CCPA opt-out rights",
                        "reasoning": "CCPA requires easy opt-out mechanisms",
                        "risk": 0.6,
                        "requires_legal_review": True,
                    },
                    "nagging": {
                        "violation_type": "excessive_notifications",
                        "severity": "low",
                        "description": "Nagging may constitute excessive notifications",
                        "reasoning": "CCPA limits excessive consumer notifications",
                        "risk": 0.35,
                        "requires_legal_review": False,
                    },
                },
            },
            "general": {
                "regulation_name": "General Consumer Protection",
                "jurisdiction": "General",
                "rules": {
                    "forced_action": {
                        "violation_type": "unfair_practice",
                        "severity": "medium",
                        "description": "Forced action may be an unfair consumer practice",
                        "reasoning": "General consumer protection against unfair practices",
                        "risk": 0.6,
                        "requires_legal_review": False,
                    },
                    "sneaking": {
                        "violation_type": "deceptive_design",
                        "severity": "medium",
                        "description": "Sneaking may be a deceptive design practice",
                        "reasoning": "Consumer protection against deceptive designs",
                        "risk": 0.55,
                        "requires_legal_review": False,
                    },
                    "obstruction": {
                        "violation_type": "unfair_practice",
                        "severity": "low",
                        "description": "Obstruction may be an unfair consumer practice",
                        "reasoning": "General consumer protection principles",
                        "risk": 0.5,
                        "requires_legal_review": False,
                    },
                    "nagging": {
                        "violation_type": "annoying_practice",
                        "severity": "low",
                        "description": "Nagging may be an annoying but not illegal practice",
                        "reasoning": "General consumer protection guidelines",
                        "risk": 0.3,
                        "requires_legal_review": False,
                    },
                },
            },
        }

        rules = []
        for reg in enabled_regulations:
            if reg in all_rules:
                reg_data = all_rules[reg]
                for pattern, rule_data in reg_data.get("rules", {}).items():
                    rules.append({
                        "regulation": reg,
                        "regulation_name": reg_data["regulation_name"],
                        "jurisdiction": reg_data["jurisdiction"],
                        "pattern": pattern,
                        **rule_data,
                    })

        return rules

    def _match_compliance_rules(
        self,
        pattern: str,
        confidence: float,
        element_text: str,
        compliance_rules: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Match findings against compliance rules."""
        matches = []

        if not pattern:
            return matches

        pattern_lower = pattern.lower()

        for rule in compliance_rules:
            if rule["pattern"] == pattern_lower:
                # Calculate adjusted confidence based on original confidence
                adjusted_confidence = min(max(confidence * rule.get("confidence_multiplier", 1.0), 0.0), 1.0)

                match = {
                    "regulation": rule["regulation"],
                    "regulation_name": rule["regulation_name"],
                    "jurisdiction": rule.get("jurisdiction", ""),
                    "violation_type": rule["violation_type"],
                    "severity": rule["severity"],
                    "description": rule["description"],
                    "reasoning": rule["reasoning"],
                    "risk": rule["risk"],
                    "requires_legal_review": rule["requires_legal_review"],
                    "confidence": adjusted_confidence,
                }
                matches.append(match)

        return matches

    def _generate_summary(self, findings: List[EvidenceRecord]) -> str:
        """Generate human-readable summary of compliance mappings."""
        if not findings:
            return "No compliance mappings found."

        regulations = set()
        for f in findings:
            if f.metadata:
                regulations.add(f.metadata.get("regulation", "unknown"))

        parts = [f"Mapped {len(findings)} findings to compliance regulations"]
        if regulations:
            parts.append(f"Regulations: {', '.join(sorted(regulations))}")

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
        """Check if compliance can process the given input."""
        has_content = bool(
            input_data.previous_findings or
            input_data.elements or
            input_data.url
        )
        return has_content


__all__ = ["ComplianceAgent"]