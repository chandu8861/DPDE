"""DPIE MITRE Analyst Agent

Optional mapping to relevant cybersecurity techniques where appropriate.
Does not force unrelated dark patterns into MITRE ATT&CK categories.
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


class MitreAnalystAgent(BaseAgent):
    """Optional mapping to relevant cybersecurity techniques.

    Maps dark patterns to MITRE ATT&CK techniques where appropriate.
    Does not force unrelated dark patterns into MITRE ATT&CK categories.
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.MITRE_ANALYST

    async def analyze(self, input_data: AgentInput) -> AgentOutput:
        """Map findings to MITRE ATT&CK techniques where appropriate.

        Args:
            input_data: AgentInput with findings from previous agents

        Returns:
            AgentOutput with MITRE ATT&CK mappings
        """
        start_time = time.time()

        if not self.can_process(input_data):
            return self._generate_failed_output(start_time, "No input data provided")

        # Get previous findings
        previous_findings = input_data.previous_findings or []
        url = input_data.url or "unknown"

        # MITRE ATT&CK mapping database
        mitre_mappings = self._load_mitre_mappings()

        findings: List[EvidenceRecord] = []

        # Map each finding to MITRE techniques where appropriate
        for finding in previous_findings:
            pattern = finding.get("detected_pattern", "") if isinstance(finding, dict) else getattr(finding, "detected_pattern", "")
            confidence = finding.get("confidence_score", 0) if isinstance(finding, dict) else getattr(finding, "confidence_score", 0)
            element_text = finding.get("element_text", "") if isinstance(finding, dict) else getattr(finding, "evidence_text", "")

            # Find matching MITRE techniques
            mitre_match = self._map_to_mitre_technique(pattern, confidence, element_text, mitre_mappings)

            if mitre_match:
                finding_result = EvidenceRecord(
                    source_agent=self.agent_type,
                    source_url=url,
                    element_text=element_text,
                    detected_pattern=pattern,
                    confidence_score=mitre_match["confidence"],
                    evidence_text=f"MITRE mapping: {mitre_match['technique_name']} ({mitre_match['technique_id']}) - {mitre_match['description']}",
                    risk_score=mitre_match["risk"],
                    tags=["mitre", mitre_match["technique_id"], pattern],
                    metadata={
                        "technique_id": mitre_match["technique_id"],
                        "technique_name": mitre_match["technique_name"],
                        "tactic": mitre_match["tactic"],
                        "description": mitre_match["description"],
                        "mapping_confidence": mitre_match["mapping_confidence"],
                        "is_optional_mapping": True,
                        "reference": mitre_match.get("reference", ""),
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

        requires_followup = len(findings) > 0 and overall_confidence > 0.5
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
            f"MITRE Analyst agent completed: {len(findings)} MITRE mappings, "
            f"confidence: {overall_confidence:.2f}"
        )

        return output

    def _load_mitre_mappings(self) -> Dict[str, Any]:
        """Load MITRE ATT&CK technique mappings for dark patterns."""
        return {
            "forced_action": {
                "technique_id": "T1566",
                "technique_name": "Phishing",
                "tactic": "Initial Access",
                "description": "Forced action patterns resemble phishing techniques that trick users into unwanted actions",
                "risk": 0.7,
                "confidence": 0.6,
                "reference": "https://attack.mitre.org/techniques/T1566/",
            },
            "sneaking": {
                "technique_id": "T1566.001",
                "technique_name": "Spearphishing Attachment",
                "tactic": "Initial Access",
                "description": "Sneaking patterns hide information similar to spearphishing techniques",
                "risk": 0.65,
                "confidence": 0.55,
                "reference": "https://attack.mitre.org/techniques/T1566/001/",
            },
            "obstruction": {
                "technique_id": "T1497",
                "technique_name": "Virtualization/Sandbox Evasion",
                "tactic": "Defense Evasion",
                "description": "Obstruction patterns can evade user scrutiny similar to sandbox evasion",
                "risk": 0.6,
                "confidence": 0.5,
                "reference": "https://attack.mitre.org/techniques/T1497/",
            },
            "nagging": {
                "technique_id": "T1566.002",
                "technique_name": "Spearphishing Link",
                "tactic": "Initial Access",
                "description": "Repeated nagging can wear down user resistance similar to persistent phishing",
                "risk": 0.5,
                "confidence": 0.45,
                "reference": "https://attack.mitre.org/techniques/T1566/002/",
            },
            "interface_interference": {
                "technique_id": "T1496",
                "technique_name": "Resource Hijacking",
                "tactic": "Impact",
                "description": "Interface interference can hijack user attention similar to resource hijacking",
                "risk": 0.55,
                "confidence": 0.5,
                "reference": "https://attack.mitre.org/techniques/T1496/",
            },
            "confirmshaming": {
                "technique_id": "T1566.003",
                "technique_name": "Spearphishing via Service",
                "tactic": "Initial Access",
                "description": "Confirmshaming uses psychological manipulation similar to social engineering",
                "risk": 0.65,
                "confidence": 0.55,
                "reference": "https://attack.mitre.org/techniques/T1566/003/",
            },
        }

    def _map_to_mitre_technique(
        self,
        pattern: str,
        confidence: float,
        element_text: str,
        mitre_mappings: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Map a dark pattern to MITRE ATT&CK technique where appropriate."""
        if not pattern:
            return None

        pattern_lower = pattern.lower()

        # Direct match
        if pattern_lower in mitre_mappings:
            mapping = mitre_mappings[pattern_lower]
            # Only map if confidence is sufficient (optional mapping)
            if confidence > 0.4:
                return {
                    "technique_id": mapping["technique_id"],
                    "technique_name": mapping["technique_name"],
                    "tactic": mapping["tactic"],
                    "description": mapping["description"],
                    "risk": mapping["risk"],
                    "mapping_confidence": min(mapping["confidence"], confidence),
                    "reference": mapping["reference"],
                }

        return None

    def _generate_summary(self, findings: List[EvidenceRecord]) -> str:
        """Generate human-readable summary of MITRE mappings."""
        if not findings:
            return "No MITRE ATT&CK mappings found."

        techniques = set()
        for f in findings:
            if f.metadata:
                techniques.add(f.metadata.get("technique_id", "unknown"))

        parts = [f"Mapped {len(findings)} findings to MITRE ATT&CK techniques"]
        if techniques:
            parts.append(f"Techniques: {', '.join(sorted(techniques))}")

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
        """Check if MITRE analyst can process the given input."""
        has_content = bool(
            input_data.previous_findings or
            input_data.elements or
            input_data.url
        )
        return has_content


__all__ = ["MitreAnalystAgent"]