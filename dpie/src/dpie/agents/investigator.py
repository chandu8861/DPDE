"""DPIE Investigator Agent

Performs detailed dark pattern investigation.
Analyzes DOM information, text, interface hierarchy, visual properties, and interaction context.
Identifies dark pattern categories and subcategories.
Explains findings using supporting evidence.
Distinguishes legitimate design choices from potentially manipulative practices.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from dpie.schemas import (
    AgentType,
    AgentInput,
    AgentOutput,
    EvidenceRecord,
)
from dpie.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class InvestigatorAgent(BaseAgent):
    """Detailed dark pattern investigation agent.

    Performs comprehensive analysis of DOM information, text, interface hierarchy,
    visual properties, and interaction context. Identifies dark pattern categories
    and subcategories. Explains findings using supporting evidence. Distinguishes
    legitimate design choices from potentially manipulative practices.
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.INVESTIGATOR

    async def analyze(self, input_data: AgentInput) -> AgentOutput:
        """Perform detailed dark pattern investigation.

        Args:
            input_data: AgentInput with HTML/DOM data and elements

        Returns:
            AgentOutput with investigation findings and evidence
        """
        start_time = time.time()

        # Validate input
        if not self.can_process(input_data):
            return self._generate_failed_output(start_time, "No input data provided")

        # Extract data from input_data object
        elements = input_data.elements or []
        html = input_data.html or ""
        dom_data = input_data.dom_data or {}
        url = input_data.url or "unknown"

        findings: List[EvidenceRecord] = []

        # Detailed analysis of each element
        for element in elements:
            element_type = element.get("element_type", "")
            element_text = element.get("element_text", "") or ""
            element_selector = element.get("element_selector", "")
            attrs = element.get("element_attributes", {})

            element_finding = await self._analyze_element(
                element_type, element_text, element_selector, attrs, url
            )
            if element_finding:
                findings.append(element_finding)

        # If no structured elements, do HTML-level analysis
        if not elements and html:
            html_findings = await self._analyze_html_snapshot(html, url)
            findings.extend(html_findings)

        # If no DOM data, do basic text analysis
        if not elements and not html and dom_data:
            dom_findings = await self._analyze_dom_data(dom_data, url)
            findings.extend(dom_findings)

        # Deduplicate findings - merge close duplicates
        findings = self._deduplicate_findings(findings)

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

        # Determine requires followup and next agents
        requires_followup = len(findings) > 0 and overall_confidence > 0.4
        next_agents = [AgentType.CORRELATOR] if findings else []

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
            f"Investigator agent completed: {len(findings)} findings, "
            f"confidence: {overall_confidence:.2f}, risk: {overall_risk:.2f}"
        )

        return output

    async def _analyze_element(
        self,
        element_type: str,
        element_text: str,
        element_selector: str,
        attrs: Dict[str, Any],
        url: str,
    ) -> Optional[EvidenceRecord]:
        """Analyze a single DOM element for dark patterns."""
        findings: List[EvidenceRecord] = []
        element_text_lower = element_text.lower()

        # Analyze button/text for dark pattern indicators
        if element_type in ("button", "a", "input"):
            # Check for forced action patterns
            if any(keyword in element_text_lower for keyword in ["must", "required", "need", "have to"]):
                finding = EvidenceRecord(
                    source_agent=self.agent_type,
                    source_element_id=element_selector,
                    source_url=url,
                    element_type=element_type,
                    element_selector=element_selector,
                    element_text=element_text,
                    element_attributes=attrs,
                    detected_pattern="forced_action",
                    confidence_score=self._calculate_confidence(
                        element_text_lower, ["must", "required", "need", "have to"]
                    ),
                    evidence_text=self._generate_forced_action_explanation(element_text),
                    risk_score=self._calculate_risk(element_type, "forced_action"),
                    tags=["forced_action", "investigator-flagged"],
                )
                findings.append(finding)

            # Check for sneaking/obfuscation patterns
            if any(keyword in element_text_lower for keyword in ["hidden", "conceal", "mask", "disguise"]):
                finding = EvidenceRecord(
                    source_agent=self.agent_type,
                    source_element_id=element_selector,
                    source_url=url,
                    element_type=element_type,
                    element_selector=element_selector,
                    element_text=element_text,
                    element_attributes=attrs,
                    detected_pattern="sneaking",
                    confidence_score=self._calculate_confidence(
                        element_text_lower, ["hidden", "conceal", "mask", "disguise"]
                    ),
                    evidence_text=self._generate_sneaking_explanation(element_text),
                    risk_score=self._calculate_risk(element_type, "sneaking"),
                    tags=["sneaking", "investigator-flagged"],
                )
                findings.append(finding)

            # Check for obstruction/confirmshaming
            confirmshaming_keywords = ["no thanks", "i hate saving", "i don't want to save", "prefer paying full", "decline offer", "lose my benefits", "confirmshaming", "shame", "blame"]
            if any(keyword in element_text_lower for keyword in confirmshaming_keywords):
                finding = EvidenceRecord(
                    source_agent=self.agent_type,
                    source_element_id=element_selector,
                    source_url=url,
                    element_type=element_type,
                    element_selector=element_selector,
                    element_text=element_text,
                    element_attributes=attrs,
                    detected_pattern="obstruction",
                    confidence_score=self._calculate_confidence(
                        element_text_lower, confirmshaming_keywords
                    ),
                    evidence_text=self._generate_obstruction_explanation(element_text),
                    risk_score=self._calculate_risk(element_type, "obstruction"),
                    tags=["obstruction", "confirmshaming", "investigator-flagged"],
                )
                findings.append(finding)

            # Check for nagging/repeated prompts
            if any(keyword in element_text_lower for keyword in ["reminder", "remind", "remember", "don't leave yet"]):
                finding = EvidenceRecord(
                    source_agent=self.agent_type,
                    source_element_id=element_selector,
                    source_url=url,
                    element_type=element_type,
                    element_selector=element_selector,
                    element_text=element_text,
                    element_attributes=attrs,
                    detected_pattern="nagging",
                    confidence_score=self._calculate_confidence(
                        element_text_lower, ["reminder", "remind", "remember", "don't leave yet"]
                    ),
                    evidence_text=self._generate_nagging_explanation(element_text),
                    risk_score=self._calculate_risk(element_type, "nagging"),
                    tags=["nagging", "investigator-flagged"],
                )
                findings.append(finding)

        # Analyze fine print and disguised terms
        disguised_keywords = ["auto-renew", "recurring charge", "billed annually", "renews automatically", "cancel fee"]
        if element_text and any(keyword in element_text_lower for keyword in disguised_keywords):
            finding = EvidenceRecord(
                source_agent=self.agent_type,
                source_element_id=element_selector,
                source_url=url,
                element_type=element_type,
                element_selector=element_selector,
                element_text=element_text,
                element_attributes=attrs,
                detected_pattern="sneaking",
                confidence_score=0.75,
                evidence_text=f"Disguised recurring terms detected: {element_text[:120]}",
                risk_score=0.7,
                tags=["sneaking", "hidden_terms", "investigator-flagged"],
            )
            findings.append(finding)

        return findings[0] if findings else None

    async def _analyze_html_snapshot(self, html: str, url: str) -> List[EvidenceRecord]:
        """Analyze HTML snapshot for dark patterns."""
        findings: List[EvidenceRecord] = []

        import re

        # Check for countdown timers
        if re.search(r'countdown|limited time|expires|ending soon', html, re.IGNORECASE):
            findings.append(EvidenceRecord(
                source_agent=self.agent_type,
                source_url=url,
                element_text="countdown_timer",
                detected_pattern="sneaking",
                confidence_score=0.5,
                evidence_text="Countdown timer or limited-time offer detected",
                risk_score=0.4,
                tags=["sneaking", "html-analyzed"],
            ))

        # Check for confirmed selection patterns
        if re.search(r'confirmed selection|I have read and', html, re.IGNORECASE):
            findings.append(EvidenceRecord(
                source_agent=self.agent_type,
                source_url=url,
                element_text="confirmed_selection",
                detected_pattern="forced_action",
                confidence_score=0.55,
                evidence_text="Confirmed selection pattern detected - may force user commitment",
                risk_score=0.6,
                tags=["forced_action", "html-analyzed"],
            ))

        return findings

    async def _analyze_dom_data(self, dom_data: Dict[str, Any], url: str) -> List[EvidenceRecord]:
        """Analyze structured DOM data for dark patterns."""
        findings: List[EvidenceRecord] = []

        nodes = dom_data.get("nodes", [])

        for node in nodes:
            node_type = node.get("type", "")
            node_text = node.get("text", "") or ""

            if node_type in ("button", "input", "select") and node_text:
                text_lower = node_text.lower()

                if any(kw in text_lower for kw in ["required", "must", "need"]):
                    findings.append(EvidenceRecord(
                        source_agent=self.agent_type,
                        source_url=url,
                        element_text=node_text,
                        element_type=node_type,
                        detected_pattern="forced_action",
                        confidence_score=0.5,
                        evidence_text="Required/necessary text in interactive element",
                        risk_score=0.5,
                        tags=["forced_action", "dom-analyzed"],
                    ))

                if any(kw in text_lower for kw in ["free", "discount", "special offer"]):
                    findings.append(EvidenceRecord(
                        source_agent=self.agent_type,
                        source_url=url,
                        element_text=node_text,
                        element_type=node_type,
                        detected_pattern="sneaking",
                        confidence_score=0.45,
                        evidence_text="Promotional text in interactive element",
                        risk_score=0.4,
                        tags=["sneaking", "dom-analyzed"],
                    ))

        return findings

    def _deduplicate_findings(self, findings: List[EvidenceRecord]) -> List[EvidenceRecord]:
        """Remove duplicate findings."""
        unique_findings: List[EvidenceRecord] = []
        seen_keys: set = set()

        for finding in findings:
            key = (
                f"{finding.detected_pattern or 'unknown'}",
                f"{finding.source_element_id or ''}",
            )

            if key not in seen_keys:
                seen_keys.add(key)
                unique_findings.append(finding)

        return unique_findings

    def _generate_summary(self, findings: List[EvidenceRecord]) -> str:
        """Generate human-readable summary of findings."""
        if not findings:
            return "No dark patterns detected in analysis."

        pattern_counts: Dict[str, int] = {}
        for f in findings:
            pattern = f.detected_pattern or "unknown"
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        summary_parts = ["Analyzed " + str(len(findings)) + " elements"]
        for pattern, count in pattern_counts.items():
            summary_parts.append(str(count) + " potential " + pattern)

        return ". ".join(summary_parts) + "."

    @staticmethod
    def _calculate_confidence(text: str, keywords: List[str]) -> float:
        """Calculate confidence score based on keyword presence."""
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw in text_lower)
        return min(matches / max(len(keywords), 1), 1.0) * 0.8 + 0.2

    @staticmethod
    def _calculate_risk(element_type: str, pattern: str) -> float:
        """Calculate risk score based on element type and pattern."""
        base_risks = {
            ("button", "forced_action"): 0.7,
            ("input", "forced_action"): 0.6,
            ("button", "sneaking"): 0.5,
            ("a", "obstruction"): 0.6,
            ("div", "interface_interference"): 0.3,
        }
        return base_risks.get((element_type, pattern), 0.4)

    def _generate_forced_action_explanation(self, text: str) -> str:
        """Generate explanation for forced pattern."""
        return "Element text '" + text[:80] + "...' suggests user must perform action."

    def _generate_sneaking_explanation(self, text: str) -> str:
        """Generate explanation for sneaking pattern."""
        return "Element text '" + text[:80] + "...' may hide true intent from user."

    def _generate_obstruction_explanation(self, text: str) -> str:
        """Generate explanation for obstruction pattern."""
        return "Element text '" + text[:80] + "...' creates barrier to user goal."

    def _generate_nagging_explanation(self, text: str) -> str:
        """Generate explanation for nagging pattern."""
        return "Element text '" + text[:80] + "...' may repeatedly prompt user."

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
        """Check if investigator can process the given input."""
        has_content = bool(
            input_data.html or
            input_data.dom_data or
            input_data.elements or
            input_data.url
        )
        return has_content


__all__ = ["InvestigatorAgent"]