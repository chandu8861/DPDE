"""DPIE Threat Hunter Agent

Identifies subtle and less obvious deceptive design signals.
Finds combinations of suspicious interface behaviors.
Identifies potentially hidden manipulation techniques.
"""

from __future__ import annotations

import asyncio
import time
import logging
import importlib.util
import os
import re
from typing import Any, Dict, List, Optional

from dpie.schemas import (
    AgentType,
    AgentInput,
    AgentOutput,
    EvidenceRecord,
)
from dpie.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class ThreatHunterAgent(BaseAgent):
    """Identifies subtle and less obvious deceptive design signals.

    Finds combinations of suspicious interface behaviors.
    Identifies potentially hidden manipulation techniques.
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.THREAT_HUNTER

    async def analyze(self, input_data: AgentInput) -> AgentOutput:
        """Perform threat hunting analysis for subtle dark patterns.

        Args:
            input_data: AgentInput with HTML/DOM data and elements

        Returns:
            AgentOutput with threat hunting findings
        """
        start_time = time.time()

        if not self.can_process(input_data):
            return self._generate_failed_output(start_time, "No input data provided")

        elements = input_data.elements or []
        html = input_data.html or ""
        dom_data = input_data.dom_data or {}
        url = input_data.url or "unknown"

        findings: List[EvidenceRecord] = []

        # Hunt for subtle patterns in elements
        for element in elements:
            element_type = element.get("element_type", "")
            element_text = element.get("element_text", "") or ""
            element_selector = element.get("element_selector", "")
            attrs = element.get("element_attributes", {})

            element_findings = await self._hunt_element(
                element_type, element_text, element_selector, attrs, url
            )
            findings.extend(element_findings)

        # HTML-level hunting for hidden manipulation
        if html:
            html_findings = await self._hunt_html(html, url)
            findings.extend(html_findings)

        # DOM-level hunting
        if dom_data:
            dom_findings = await self._hunt_dom(dom_data, url)
            findings.extend(dom_findings)

        # Deduplicate findings
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

        requires_followup = len(findings) > 0 and overall_confidence > 0.3
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
            f"Threat Hunter agent completed: {len(findings)} findings, "
            f"confidence: {overall_confidence:.2f}, risk: {overall_risk:.2f}"
        )

        return output

    async def _hunt_element(
        self,
        element_type: str,
        element_text: str,
        element_selector: str,
        attrs: Dict[str, Any],
        url: str,
    ) -> List[EvidenceRecord]:
        """Hunt for subtle threats in a single element."""
        findings: List[EvidenceRecord] = []
        element_text_lower = element_text.lower()

        # Check for color-based deception (low contrast text for important info)
        if attrs.get("style") and "color" in attrs.get("style", "").lower():
            style = attrs.get("style", "").lower()
            if "#ccc" in style or "#ddd" in style or "#eee" in style:
                if element_type in ("span", "div", "p") and len(element_text) > 10:
                    findings.append(EvidenceRecord(
                        source_agent=self.agent_type,
                        source_element_id=element_selector,
                        source_url=url,
                        element_type=element_type,
                        element_selector=element_selector,
                        element_text=element_text,
                        element_attributes=attrs,
                        detected_pattern="interface_interference",
                        confidence_score=0.6,
                        evidence_text="Low contrast text detected - may hide important information",
                        risk_score=0.5,
                        tags=["threat_hunter", "subtle", "low_contrast"],
                    ))

        # Check for misleading button placement or size
        if element_type in ("button", "a"):
            if element_text and len(element_text) > 0:
                # Check for unusually small or large buttons
                style = attrs.get("style", "")
                if "font-size" in style.lower():
                    try:
                        size_match = re.search(r"font-size:\s*(\d+)", style.lower())
                        if size_match:
                            size = int(size_match.group(1))
                            if size <= 10 and element_text:
                                findings.append(EvidenceRecord(
                                    source_agent=self.agent_type,
                                    source_element_id=element_selector,
                                    source_url=url,
                                    element_type=element_type,
                                    element_selector=element_selector,
                                    element_text=element_text,
                                    element_attributes=attrs,
                                    detected_pattern="sneaking",
                                    confidence_score=0.55,
                                    evidence_text="Very small font size on interactive element - may hide intent",
                                    risk_score=0.45,
                                    tags=["threat_hunter", "subtle", "tiny_text"],
                                ))
                    except (ValueError, AttributeError):
                        pass

        # Check for pre-checked options
        if element_type == "input" and attrs.get("type") in ("checkbox", "radio"):
            if attrs.get("checked") == "checked" or attrs.get("checked") == "true":
                findings.append(EvidenceRecord(
                    source_agent=self.agent_type,
                    source_element_id=element_selector,
                    source_url=url,
                    element_type=element_type,
                    element_selector=element_selector,
                    element_text=element_text,
                    element_attributes=attrs,
                    detected_pattern="forced_action",
                    confidence_score=0.7,
                    evidence_text="Pre-checked option detected - may force user commitment",
                    risk_score=0.65,
                    tags=["threat_hunter", "subtle", "pre_checked"],
                ))

        # Check for hidden fields with manipulative defaults (skip standard CSRF/auth tokens)
        if element_type == "input" and attrs.get("type") == "hidden":
            field_name = (attrs.get("name") or attrs.get("id") or "").lower()
            safe_tokens = ["csrf", "token", "auth", "state", "nonce", "utf8", "viewstate", "session", "method"]
            is_safe = any(token in field_name for token in safe_tokens)
            suspicious_names = ["optin", "subscribe", "newsletter", "marketing", "auto_add", "addon"]
            is_suspicious = any(name in field_name for name in suspicious_names)
            if not is_safe and is_suspicious and attrs.get("value"):
                findings.append(EvidenceRecord(
                    source_agent=self.agent_type,
                    source_element_id=element_selector,
                    source_url=url,
                    element_type=element_type,
                    element_selector=element_selector,
                    element_text=element_text,
                    element_attributes=attrs,
                    detected_pattern="sneaking",
                    confidence_score=0.7,
                    evidence_text=f"Hidden form field auto-submitting consent or add-on: {field_name}",
                    risk_score=0.65,
                    tags=["threat_hunter", "subtle", "hidden_field"],
                ))

        return findings

    async def _hunt_html(self, html: str, url: str) -> List[EvidenceRecord]:
        """Hunt for subtle threats in HTML."""
        findings: List[EvidenceRecord] = []

        # Check for zero-font cloaking or tiny font deception
        if re.search(r"font-size\s*:\s*0(\.0+)?(px|pt|em|rem)?\b", html.lower()):
            findings.append(EvidenceRecord(
                source_agent=self.agent_type,
                source_url=url,
                element_text="zero_font_cloaking",
                detected_pattern="sneaking",
                confidence_score=0.75,
                evidence_text="Zero-font cloaked text detected - content hidden from user view",
                risk_score=0.7,
                tags=["threat_hunter", "subtle", "cloaked_text"],
            ))

        # Check for JavaScript obfuscation
        if re.search(r"eval\s*\(", html.lower()):
            findings.append(EvidenceRecord(
                source_agent=self.agent_type,
                source_url=url,
                element_text="javascript_obfuscation",
                detected_pattern="sneaking",
                confidence_score=0.7,
                evidence_text="JavaScript eval detected - may execute hidden code",
                risk_score=0.8,
                tags=["threat_hunter", "subtle", "js_obfuscation"],
            ))

        # Check for meta refresh redirects
        if re.search(r"meta.*refresh", html.lower()):
            findings.append(EvidenceRecord(
                source_agent=self.agent_type,
                source_url=url,
                element_text="meta_refresh",
                detected_pattern="interface_interference",
                confidence_score=0.6,
                evidence_text="Meta refresh redirect detected - may redirect users unexpectedly",
                risk_score=0.55,
                tags=["threat_hunter", "subtle", "auto_redirect"],
            ))

        return findings

    async def _hunt_dom(self, dom_data: Dict[str, Any], url: str) -> List[EvidenceRecord]:
        """Hunt for subtle threats in DOM data."""
        findings: List[EvidenceRecord] = []

        nodes = dom_data.get("nodes", [])

        for node in nodes:
            node_type = node.get("type", "")
            node_text = node.get("text", "") or ""

            # Check for nested iframes (potential clickjacking)
            if node_type == "iframe":
                findings.append(EvidenceRecord(
                    source_agent=self.agent_type,
                    source_url=url,
                    element_text="iframe_element",
                    detected_pattern="interface_interference",
                    confidence_score=0.65,
                    evidence_text="IFrame detected - potential clickjacking vector",
                    risk_score=0.7,
                    tags=["threat_hunter", "subtle", "iframe"],
                ))

            # Check for elements with unusual z-index (layering attacks)
            if node_type in ("div", "span"):
                style = node.get("style", "") or ""
                if "z-index" in style.lower():
                    try:
                        z_match = re.search(r"z-index:\s*(\d+)", style.lower())
                        if z_match:
                            z = int(z_match.group(1))
                            if z > 9999:
                                findings.append(EvidenceRecord(
                                    source_agent=self.agent_type,
                                    source_url=url,
                                    element_text=node_text,
                                    element_type=node_type,
                                    detected_pattern="interface_interference",
                                    confidence_score=0.55,
                                    evidence_text="Very high z-index detected - potential layering attack",
                                    risk_score=0.6,
                                    tags=["threat_hunter", "subtle", "z_index"],
                                ))
                    except (ValueError, AttributeError):
                        pass

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
            return "No subtle threats detected."

        pattern_counts: Dict[str, int] = {}
        for f in findings:
            pattern = f.detected_pattern or "unknown"
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        summary_parts = [f"Analyzed {len(findings)} elements for subtle threats"]
        for pattern, count in pattern_counts.items():
            summary_parts.append(f"{count} potential {pattern}")

        return ". ".join(summary_parts) + "."

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
        """Check if threat hunter can process the given input."""
        has_content = bool(
            input_data.html or
            input_data.dom_data or
            input_data.elements or
            input_data.url
        )
        return has_content


__all__ = ["ThreatHunterAgent"]