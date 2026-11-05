"""DPIE Reporter Agent

Generates comprehensive reports.
Produces plain-language explanations.
Includes pattern names, severity, confidence, evidence, and recommendations.
Supports JSON and human-readable report formats.
"""

from __future__ import annotations

import json
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
    ReportContent,
    ReportFormat,
)
from dpie.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class ReporterAgent(BaseAgent):
    """Generates comprehensive reports from analysis findings."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.REPORTER

    def _ensure_evidence_records(self, findings: List[Any]) -> List[EvidenceRecord]:
        """Convert dict findings to EvidenceRecord objects if needed."""
        converted: List[EvidenceRecord] = []
        for f in findings:
            if isinstance(f, dict):
                converted.append(EvidenceRecord(**f))
            else:
                converted.append(f)
        return converted

    async def analyze(self, input_data: AgentInput) -> AgentOutput:
        """Generate comprehensive report from analysis findings."""
        start_time = time.time()

        # Validate input
        if not self.can_process(input_data):
            return self._generate_failed_output(start_time, "No input data provided")

        # Get findings - from previous_findings if provided
        findings_raw: List[Any] = input_data.previous_findings or []

        # Convert dict findings to EvidenceRecord objects
        findings = self._ensure_evidence_records(findings_raw)

        # If no findings, return empty result
        if not findings:
            return AgentOutput(
                agent_type=self.agent_type,
                status="completed",
                findings=[],
                summary="No findings available for report generation.",
                overall_confidence=0.0,
                overall_risk=0.0,
                execution_time_ms=int((time.time() - start_time) * 1000),
                model_used=None,
                tokens_consumed=0,
                next_agents=[],
                requires_followup=False,
            )

        # Calculate pattern counts and severity
        pattern_counts: Dict[str, int] = {}
        severity_counts: Dict[str, int] = {}

        for f in findings:
            pattern = f.detected_pattern or "unknown"
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            cf = f.confidence_score
            sev = "medium"
            if cf and cf > 0.7:
                sev = "high"
            elif cf and cf > 0.4:
                sev = "low"
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        primary_pattern = findings[0].detected_pattern or "unknown" if findings else "unknown"

        high_risk = sum(1 for f in findings if f.risk_score and f.risk_score > 0.7)
        medium_risk = sum(1 for f in findings if f.risk_score and 0.4 < f.risk_score <= 0.7)

        if high_risk > len(findings) / 2:
            severity = "high"
        elif medium_risk > len(findings) / 2 or high_risk > 0:
            severity = "medium"
        else:
            severity = "low"

        conf_scores = [f.confidence_score for f in findings if f.confidence_score is not None]
        risk_scores = [f.risk_score for f in findings if f.risk_score is not None]

        overall_confidence = max(conf_scores) if conf_scores else 0.5
        overall_risk = max(risk_scores) if risk_scores else 0.3

        requires_followup = overall_confidence > 0.4 and overall_risk > 0.3
        next_agents = []

        execution_time_ms = int((time.time() - start_time) * 1000)

        # Generate JSON report
        report_json_findings = []
        for f in findings:
            report_json_findings.append({
                "pattern": f.detected_pattern or "unknown",
                "confidence": f.confidence_score,
                "risk": f.risk_score,
                "element_type": f.element_type,
                "element_text": f.evidence_text,
                "risk_score": f.risk_score,
                "evidence": f.evidence_text,
                "tags": f.tags,
            })

        average_confidence = sum(conf_scores) / len(conf_scores) if conf_scores else 0
        average_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0

        report_json = {
            "report_type": "dark_pattern_analysis",
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_findings": len(findings),
            "patterns_detected": pattern_counts,
            "severity_distribution": severity_counts,
            "findings": report_json_findings,
            "aggregated": {
                "average_confidence": average_confidence,
                "average_risk": average_risk,
            }
        }

        # Generate plain text report
        lines = [
            "=" * 60,
            "DARK PATTERN ANALYSIS REPORT",
            "=" * 60,
            "Generated: " + time.strftime("%Y-%m-%d %H:%M:%S"),
            "Total Findings: " + str(len(findings)),
            "",
            "PATTERN SUMMARY:",
            "-" * 40,
        ]

        for pattern, count in sorted(pattern_counts.items()):
            lines.append("  • " + pattern + ": " + str(count) + " occurrence(s)")

        lines.extend([
            "",
            "DETAILED FINDINGS:",
            "-" * 40,
        ])

        for i, f in enumerate(findings, 1):
            lines.extend([
                "",
                "Finding " + str(i) + ":",
                "  Pattern: " + (f.detected_pattern or "unknown"),
                "  Confidence: " + (str(round(f.confidence_score, 2)) if f.confidence_score is not None else "N/A"),
                "  Risk Score: " + (str(round(f.risk_score, 2)) if f.risk_score is not None else "N/A"),
                "  Element Type: " + (f.element_type or "unknown"),
                "  Element Text: " + (f.evidence_text or "no text"),
                "  Risk Level: " + ("High" if ((f.risk_score or 0) > 0.7) else ("Medium" if ((f.risk_score or 0) > 0.4) else "Low")),
                "  Tags: " + (", ".join(f.tags) if f.tags else "none"),
            ])

        lines.extend([
            "",
            "AGGREGATED METRICS:",
            "-" * 40,
        ])

        avg_conf_str = str(round(average_confidence, 2)) if findings else "N/A"
        avg_risk_str = str(round(average_risk, 2)) if findings else "N/A"

        lines.append("  Average Confidence: " + avg_conf_str)
        lines.append("  Average Risk: " + avg_risk_str)
        lines.extend([
            "",
            "RECOMMENDATIONS:",
            "-" * 40,
        ])

        # Generate recommendations
        recommendations: List[str] = []
        patterns_set: set = set()

        for f in findings:
            p = f.detected_pattern
            if p:
                patterns_set.add(p)

        for pattern in patterns_set:
            if pattern == "forced_action":
                recommendations.append("Provide clear alternative options and exit paths for users")
                recommendations.append("Ensure users can easily understand and opt-out of actions")
            elif pattern == "sneaking":
                recommendations.append("Make hidden information or actions explicitly visible")
                recommendations.append("Disclose all costs, terms, and conditions upfront")
            elif pattern == "obstruction":
                recommendations.append("Remove unnecessary barriers to task completion")
                recommendations.append("Provide clear, direct paths to user goals")
            elif pattern == "nagging":
                recommendations.append("Limit repetition of prompts and permission requests")
                recommendations.append("Allow users to dismiss prompts permanently")
            elif pattern == "interface_interference":
                recommendations.append("Ensure UI elements don't distract from core content")
                recommendations.append("Maintain clear visual hierarchy and focus order")

        if not recommendations:
            recommendations.append("Review identified interface elements for potential dark patterns")
            recommendations.append("Test designs with user research to validate intent")

        for rec in recommendations:
            lines.append("  • " + rec)

        lines.extend([
            "",
            "=" * 60,
        ])

        plain_text = "\n".join(lines)

        # Store findings as dicts in metadata to avoid Pydantic class mismatch
        findings_metadata = []
        for f in findings:
            findings_metadata.append({
                "pattern": f.detected_pattern or "unknown",
                "confidence": f.confidence_score,
                "risk": f.risk_score,
                "element_type": f.element_type,
                "element_text": f.evidence_text,
                "risk_score": f.risk_score,
                "evidence": f.evidence_text,
                "tags": f.tags,
            })

        output = AgentOutput(
            agent_type=self.agent_type,
            status="completed",
            findings=[],  # Empty to avoid Pydantic class mismatch; findings are in metadata
            summary="Generated " + str(len(findings)) + "-point dark pattern report (pattern: " + primary_pattern + ", confidence: " + str(round(overall_confidence, 2)) + ")",
            overall_confidence=overall_confidence,
            overall_risk=overall_risk,
            execution_time_ms=execution_time_ms,
            model_used=None,
            tokens_consumed=0,
            next_agents=next_agents,
            requires_followup=requires_followup,
            metadata={
                "report_json": report_json,
                "report_plain": plain_text,
                "report_format": "json",
                "findings": findings_metadata,
            }
        )

        logger.info(
            f"Reporter agent completed: {len(findings)} findings, "
            f"pattern: {primary_pattern}, severity: {severity}"
        )

        return output

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
        """Check if reporter can process the given input."""
        has_findings = bool(
            input_data.previous_findings or (input_data.elements is not None)
        )
        return has_findings


__all__ = ["ReporterAgent"]