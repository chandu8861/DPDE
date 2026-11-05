"""DPIE Forensics Agent

Preserves relevant detection evidence.
Maintains element identifiers and contextual information.
Generates structured evidence records.
Maintains an auditable analysis history.
"""

from __future__ import annotations

import asyncio
import time
import logging
import importlib.util
import os
import json
import hashlib
from typing import Any, Dict, List, Optional

from dpie.schemas import (
    AgentType,
    AgentInput,
    AgentOutput,
    EvidenceRecord,
)
from dpie.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class ForensicsAgent(BaseAgent):
    """Preserves relevant detection evidence.

    Maintains element identifiers and contextual information.
    Generates structured evidence records.
    Maintains an auditable analysis history.
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.FORENSICS

    async def analyze(self, input_data: AgentInput) -> AgentOutput:
        """Perform forensics evidence preservation.

        Args:
            input_data: AgentInput with HTML/DOM data and elements

        Returns:
            AgentOutput with forensics evidence records
        """
        start_time = time.time()

        if not self.can_process(input_data):
            return self._generate_failed_output(start_time, "No input data provided")

        elements = input_data.elements or []
        html = input_data.html or ""
        dom_data = input_data.dom_data or {}
        url = input_data.url or "unknown"

        findings: List[EvidenceRecord] = []

        # Preserve evidence for each element
        for element in elements:
            element_type = element.get("element_type", "")
            element_text = element.get("element_text", "") or ""
            element_selector = element.get("element_selector", "")
            attrs = element.get("element_attributes", {})

            # Generate evidence hash for this element
            evidence_hash = self._generate_evidence_hash(
                element_type, element_text, element_selector, attrs, url
            )

            finding = EvidenceRecord(
                source_agent=self.agent_type,
                source_element_id=element_selector,
                source_url=url,
                element_type=element_type,
                element_selector=element_selector,
                element_text=element_text,
                element_attributes=attrs,
                detected_pattern="evidence_preserved",
                confidence_score=1.0,  # Evidence preservation is deterministic
                evidence_text=self._generate_evidence_description(
                    element_type, element_text, element_selector, attrs
                ),
                risk_score=0.0,  # Evidence preservation is not a risk itself
                tags=["forensics", "evidence_preserved", "auditable"],
                metadata={
                    "evidence_hash": evidence_hash,
                    "preserved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "source": "forensics_agent",
                },
            )
            findings.append(finding)

        # Preserve HTML snapshot evidence
        if html:
            html_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()[:16]
            finding = EvidenceRecord(
                source_agent=self.agent_type,
                source_url=url,
                element_text="html_snapshot",
                detected_pattern="evidence_preserved",
                confidence_score=1.0,
                evidence_text=f"HTML snapshot preserved (hash: {html_hash})",
                risk_score=0.0,
                tags=["forensics", "evidence_preserved", "html_snapshot"],
                metadata={
                    "evidence_hash": html_hash,
                    "preserved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "source": "forensics_agent",
                    "snapshot_type": "html",
                },
            )
            findings.append(finding)

        # Preserve DOM data evidence
        if dom_data:
            dom_json = json.dumps(dom_data, sort_keys=True)
            dom_hash = hashlib.sha256(dom_json.encode("utf-8")).hexdigest()[:16]
            finding = EvidenceRecord(
                source_agent=self.agent_type,
                source_url=url,
                element_text="dom_data_snapshot",
                detected_pattern="evidence_preserved",
                confidence_score=1.0,
                evidence_text=f"DOM data snapshot preserved (hash: {dom_hash})",
                risk_score=0.0,
                tags=["forensics", "evidence_preserved", "dom_snapshot"],
                metadata={
                    "evidence_hash": dom_hash,
                    "preserved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "source": "forensics_agent",
                    "snapshot_type": "dom",
                },
            )
            findings.append(finding)

        # Calculate overall confidence and risk
        overall_confidence = 1.0  # Forensics is deterministic
        overall_risk = 0.0  # Evidence preservation has no risk

        requires_followup = False  # Forensics doesn't require followup
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
            f"Forensics agent completed: {len(findings)} evidence records preserved, "
            f"confidence: {overall_confidence:.2f}"
        )

        return output

    def _generate_evidence_hash(
        self,
        element_type: str,
        element_text: str,
        element_selector: str,
        attrs: Dict[str, Any],
        url: str,
    ) -> str:
        """Generate a unique hash for an evidence record."""
        data = f"{url}|{element_type}|{element_selector}|{element_text}|{json.dumps(attrs, sort_keys=True)}"
        return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]

    def _generate_evidence_description(
        self,
        element_type: str,
        element_text: str,
        element_selector: str,
        attrs: Dict[str, Any],
    ) -> str:
        """Generate a human-readable description of preserved evidence."""
        parts = [
            f"Element: {element_type}",
            f"Selector: {element_selector or 'none'}",
            f"Text: {element_text[:100] if element_text else 'none'}",
        ]

        if attrs:
            attr_items = [f"{k}={v}" for k, v in attrs.items() if k not in ("style", "class")]
            if attr_items:
                parts.append(f"Attributes: {', '.join(attr_items[:5])}")

        return " | ".join(parts)

    def _generate_summary(self, findings: List[EvidenceRecord]) -> str:
        """Generate human-readable summary of findings."""
        if not findings:
            return "No evidence preserved."

        element_count = sum(1 for f in findings if f.tags and "evidence_preserved" in f.tags and f.element_type)
        html_count = sum(1 for f in findings if f.tags and "html_snapshot" in f.tags)
        dom_count = sum(1 for f in findings if f.tags and "dom_snapshot" in f.tags)

        parts = [f"Preserved {len(findings)} evidence records"]
        if element_count:
            parts.append(f"{element_count} elements")
        if html_count:
            parts.append(f"{html_count} HTML snapshot(s)")
        if dom_count:
            parts.append(f"{dom_count} DOM snapshot(s)")

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
        """Check if forensics can process the given input."""
        has_content = bool(
            input_data.html or
            input_data.dom_data or
            input_data.elements or
            input_data.url
        )
        return has_content


__all__ = ["ForensicsAgent"]