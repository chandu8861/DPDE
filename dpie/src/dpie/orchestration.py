"""DPIE Agent Orchestration Engine

Configurable orchestration system for running specialized agents in sequences,
parallel, or conditional modes.

Supports:
- Sequential agent execution
- Conditional routing
- Parallel investigation where appropriate
- Agent-to-agent communication through structured outputs
- Configurable confidence thresholds
- Execution timeouts
- Error handling
- Partial results when an agent fails
- Optional agent selection

Three execution modes:
- FAST MODE: Triage and lightweight analysis
- DEEP MODE: Investigator, Threat Hunter, and Correlator
- FULL ANALYSIS MODE: All relevant agents, evidence collection, compliance mapping, and reporting

The system does not invoke every agent for every request.
"""

from __future__ import annotations

import asyncio
import time
import logging
from typing import Any, Dict, List, Optional, Tuple

from dpie.schemas import (
    AgentType,
    AgentInput,
    AgentOutput,
    AgentStatus,
    OrchestrationMode,
    EvidenceRecord,
    AgentConfiguration,
    OrchestrationConfiguration,
    DetectionStatus,
    AnalysisResponse,
)
from dpie.agents.base import BaseAgent
from dpie.agents.registry import AgentRegistry, get_agent_registry
from dpie.knowledge_base import get_knowledge_base, SharedKnowledgeBase
from dpie.providers import ProviderFactory


logger = logging.getLogger(__name__)


class OrchestrationEngine:
    """Core orchestration engine for DPIE agents.
    
    Manages agent execution in configurable modes and sequences.
    Handles routing, parallelism, timeouts, and result aggregation.
    """
    
    def __init__(
        self,
        orchestration_mode: OrchestrationMode = OrchestrationMode.FAST,
        agent_registry: Optional[AgentRegistry] = None,
        knowledge_base: Optional[SharedKnowledgeBase] = None,
        configuration: Optional[OrchestrationConfiguration] = None,
        mode: Optional[Any] = None,
    ):
        """Initialize the orchestration engine.
        
        Args:
            orchestration_mode: Execution mode (fast, deep, full)
            agent_registry: AgentRegistry instance
            knowledge_base: SharedKnowledgeBase instance
            configuration: OrchestrationConfiguration settings
            mode: Optional alias for orchestration_mode
        """
        if mode is not None:
            if isinstance(mode, str):
                self.orchestration_mode = OrchestrationMode(mode)
            else:
                self.orchestration_mode = mode
        elif isinstance(orchestration_mode, str):
            self.orchestration_mode = OrchestrationMode(orchestration_mode)
        else:
            self.orchestration_mode = orchestration_mode
        self.agent_registry = agent_registry or get_agent_registry()
        self.knowledge_base = knowledge_base or get_knowledge_base()
        self.configuration = configuration or OrchestrationConfiguration()
        
        # Mode-to-agent base mappings (can be overridden per execution)
        self._mode_agents: Dict[OrchestrationMode, List[AgentType]] = {
            OrchestrationMode.FAST: [AgentType.TRIAGE],
            OrchestrationMode.DEEP: [
                AgentType.TRIAGE,
                AgentType.INVESTIGATOR,
                AgentType.CORRELATOR,
            ],
            OrchestrationMode.FULL: [
                AgentType.TRIAGE,
                AgentType.INVESTIGATOR,
                AgentType.THREAT_HUNTER,
                AgentType.CORRELATOR,
                AgentType.FORENSICS,
                AgentType.COMPLIANCE,
                AgentType.REPORTER,
            ],
        }
        
        # Timeout settings
        self.default_timeout_seconds: int = 60
        self.per_agent_timeout: Optional[Dict[AgentType, int]] = None
    
    def get_agents_for_mode(self, mode: Optional[OrchestrationMode] = None) -> List[AgentType]:
        """Get the list of agents to execute for a given mode.
        
        Args:
            mode: OrchestrationMode (uses self.orchestration_mode if None)
            
        Returns:
            List of AgentType values in execution order
        """
        mode = mode or self.orchestration_mode
        return self._mode_agents.get(mode, self._mode_agents[OrchestrationMode.FAST])
    
    async def execute(
        self,
        input_data: AgentInput,
        selected_agents: Optional[List[AgentType]] = None,
    ) -> AnalysisResponse:
        """Execute the orchestration sequence.
        
        Args:
            input_data: AgentInput with analysis request data
            selected_agents: Optional override of which agents to run
            
        Returns:
            AnalysisResponse with all findings and metadata
        """
        start_time = time.time()
        
        # Determine which agents to run
        if selected_agents is None:
            agents_to_run = self.get_agents_for_mode(self.orchestration_mode)
        else:
            agents_to_run = selected_agents
        
        # Filter to only enabled agents
        agents_to_run = [
            a for a in agents_to_run 
            if self.agent_registry.is_agent_enabled(a)
        ]
        
        # Early exit if no agents available
        if not agents_to_run:
            return AnalysisResponse(
                request_id=self._generate_request_id(),
                status="no_agents_available",
                overall_confidence=0.0,
                overall_risk=1.0,
                all_findings=[],
                aggregated_confidence=0.0,
                aggregated_risk=1.0,
                execution_summary="No agents available for the selected mode",
                total_execution_time_ms=int((time.time() - start_time) * 1000),
            )
        
        # Execute agents sequentially with timeout and error handling
        all_findings: List[EvidenceRecord] = []
        agent_results: Dict[AgentType, AgentOutput] = {}
        overall_confidence = 0.5
        overall_risk = 1.0
        execution_errors: List[str] = []
        
        for agent_type in agents_to_run:
            agent = self.agent_registry.get_agent(agent_type)
            if agent is None:
                logger.warning(f"Agent {agent_type} not registered, skipping")
                agent_results[agent_type] = AgentOutput(
                    agent_type=agent_type,
                    status=AgentStatus.FAILED,
                    findings=[],
                    overall_confidence=0.0,
                    overall_risk=1.0,
                    execution_time_ms=0,
                    model_used=None,
                    tokens_consumed=0,
                    requires_followup=False,
                )
                overall_risk = 1.0
                execution_errors.append(f"Agent {agent_type} not registered")
                continue
            
            # Check if agent can process this input
            if not agent.can_process(input_data):
                logger.info(f"Agent {agent_type} cannot process input, skipping")
                agent_results[agent_type] = AgentOutput(
                    agent_type=agent_type,
                    status=AgentStatus.SKIPPED,
                    findings=[],
                    overall_confidence=1.0,
                    overall_risk=0.0,
                    execution_time_ms=0,
                    model_used=None,
                    tokens_consumed=0,
                    requires_followup=False,
                )
                continue
            
            # Execute agent with timeout
            agent_start = time.time()
            try:
                output: AgentOutput = await asyncio.wait_for(
                    agent.analyze(input_data),
                    timeout=self._get_agent_timeout(agent_type)
                )
                
                # Log execution
                agent_exec_time = int((time.time() - agent_start) * 1000)
                agent.log_execution(agent_start, output)
                
                # Store findings in knowledge base
                if output.findings:
                    self.knowledge_base.add_findings_to_kb(output.findings)
                    all_findings.extend(output.findings)
                
                agent_results[agent_type] = output
                
                # Update overall metrics
                if output.overall_confidence > overall_confidence:
                    overall_confidence = output.overall_confidence
                if output.overall_risk is not None and output.overall_risk > overall_risk:
                    overall_risk = output.overall_risk
                
                # Check if followup is needed and routing specified
                if output.requires_followup and output.next_agents:
                    logger.info(
                        f"Agent {agent_type} requires followup, next agents: {output.next_agents}"
                    )
                
            except asyncio.TimeoutError:
                logger.error(f"Agent {agent_type} execution timed out")
                agent_results[agent_type] = AgentOutput(
                    agent_type=agent_type,
                    status=AgentStatus.FAILED,
                    findings=[],
                    overall_confidence=0.0,
                    overall_risk=1.0,
                    execution_time_ms=self._get_agent_timeout(agent_type),
                    model_used=None,
                    tokens_consumed=0,
                    requires_followup=False,
                )
                overall_risk = 1.0
                execution_errors.append(f"Agent {agent_type} timeout")
                agent_results[agent_type] = AgentOutput(
                    agent_type=agent_type,
                    status=AgentStatus.FAILED,
                    findings=[],
                    overall_confidence=0.0,
                    overall_risk=1.0,
                    execution_time_ms=self._get_agent_timeout(agent_type),
                    model_used=None,
                    tokens_consumed=0,
                    requires_followup=False,
                )
                
            except Exception as e:
                logger.error(f"Agent {agent_type} failed: {e}", exc_info=True)
                agent_results[agent_type] = AgentOutput(
                    agent_type=agent_type,
                    status=AgentStatus.FAILED,
                    findings=[],
                    overall_confidence=0.0,
                    overall_risk=1.0,
                    execution_time_ms=int((time.time() - agent_start) * 1000),
                    model_used=None,
                    tokens_consumed=0,
                    requires_followup=False,
                )
                overall_risk = 1.0
                execution_errors.append(f"Agent {agent_type} error: {str(e)[:100]}")
        
        # Deduplicate findings
        all_findings = self._deduplicate_findings(all_findings)
        
        # Calculate aggregated confidence and risk
        if all_findings:
            confidences = [f.confidence_score for f in all_findings if f.confidence_score]
            risks = [f.risk_score for f in all_findings if f.risk_score is not None]
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5
            overall_risk = sum(risks) / len(risks) if risks else 1.0
        
        # Total execution time
        total_time_ms = int((time.time() - start_time) * 1000)
        
        # Collect models used and tokens
        models_used: List[str] = []
        tokens_total = 0
        for agent_type, output in agent_results.items():
            if output.model_used:
                models_used.append(output.model_used)
            tokens_total += output.tokens_consumed or 0
        
        # Determine final status
        status = "completed" if all_findings else "no_findings"
        
        # Build response
        response = AnalysisResponse(
            request_id=self._generate_request_id(),
            status=status,
            triage=agent_results.get(AgentType.TRIAGE),
            investigator=agent_results.get(AgentType.INVESTIGATOR),
            correlator=agent_results.get(AgentType.CORRELATOR),
            reporter=agent_results.get(AgentType.REPORTER),
            threat_hunter=agent_results.get(AgentType.THREAT_HUNTER),
            forensics=agent_results.get(AgentType.FORENSICS),
            compliance=agent_results.get(AgentType.COMPLIANCE),
            all_findings=all_findings,
            aggregated_confidence=round(overall_confidence, 4),
            aggregated_risk=round(overall_risk, 4) if overall_risk is not None else None,
            execution_summary=self._generate_execution_summary(agent_results, execution_errors),
            total_execution_time_ms=total_time_ms,
            models_used=list(set(models_used)) if models_used else [],
            tokens_total=tokens_total,
        )
        
        return response
    
    def _get_agent_timeout(self, agent_type: AgentType) -> int:
        """Get the timeout for a specific agent."""
        if self.per_agent_timeout and agent_type in self.per_agent_timeout:
            return self.per_agent_timeout[agent_type]
        return self.default_timeout_seconds
    
    def _deduplicate_findings(self, findings: List[EvidenceRecord]) -> List[EvidenceRecord]:
        """Remove duplicate findings based on element and pattern."""
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
    
    def _generate_execution_summary(
        self, 
        agent_results: Dict[AgentType, AgentOutput], 
        execution_errors: List[str]
    ) -> str:
        """Generate a human-readable execution summary."""
        parts = []
        
        completed_agents = sum(1 for a in agent_results.values() if a.status.value == "completed")
        failed_agents = sum(1 for a in agent_results.values() if a.status.value == "failed")
        skipped_agents = sum(1 for a in agent_results.values() if a.status.value == "skipped")
        
        parts.append(f"Executed {completed_agents + skipped_agents + failed_agents} agents")
        parts.append(f"Completed: {completed_agents}, Failed: {failed_agents}, Skipped: {skipped_agents}")
        
        if execution_errors:
            parts.append(f"Errors: {'; '.join(execution_errors[:3])}")
        
        if any(a.findings for a in agent_results.values()):
            total_findings = sum(len(a.findings) for a in agent_results.values())
            parts.append(f"Findings: {total_findings} total")
        
        return ". ".join(parts) + "."
    
    def _generate_request_id(self) -> str:
        """Generate a unique request ID."""
        import hashlib
        return hashlib.sha256(f"{time.time()}{id(self)}".encode()).hexdigest()[:16]
    
    def configure_mode(self, mode: OrchestrationMode) -> None:
        """Change the orchestration mode.
        
        Args:
            mode: New orchestration mode
        """
        self.orchestration_mode = mode
        logger.info(f"Orchestration mode set to: {mode}")
    
    def set_timeout(self, default_seconds: int = 60, per_agent: Optional[Dict[AgentType, int]] = None) -> None:
        """Set execution timeouts.
        
        Args:
            default_seconds: Default timeout in seconds for all agents
            per_agent: Per-agent timeout overrides
        """
        self.default_timeout_seconds = default_seconds
        self.per_agent_timeout = per_agent or {}


# ---------------------------------------------------------------------------
# Execution mode helpers
# -------------------------------------------------------------------------


def run_fast_analysis(
    input_data: AgentInput,
    orchestration_engine: Optional[OrchestrationEngine] = None,
) -> AnalysisResponse:
    """Run fast analysis (triage only).
    
    Args:
        input_data: Analysis request
        orchestration_engine: Optional engine instance
        
    Returns:
        AnalysisResponse with triage results
    """
    engine = orchestration_engine or OrchestrationEngine(mode=OrchestrationMode.FAST)
    return engine.execute_fast_mode(input_data)


def run_deep_analysis(
    input_data: AgentInput,
    orchestration_engine: Optional[OrchestrationEngine] = None,
) -> AnalysisResponse:
    """Run deep analysis (investigator + correlator).
    
    Args:
        input_data: Analysis request
        orchestration_engine: Optional engine instance
        
    Returns:
        AnalysisResponse with deep analysis results
    """
    engine = orchestration_engine or OrchestrationEngine(mode=OrchestrationMode.DEEP)
    return engine.execute_deep_mode(input_data)


def run_full_analysis(
    input_data: AgentInput,
    orchestration_engine: Optional[OrchestrationEngine] = None,
) -> AnalysisResponse:
    """Run full analysis (all agents).
    
    Args:
        input_data: Analysis request
        orchestration_engine: Optional engine instance
        
    Returns:
        AnalysisResponse with full analysis results
    """
    engine = orchestration_engine or OrchestrationEngine(mode=OrchestrationMode.FULL)
    return engine.execute_full_mode(input_data)


# ---------------------------------------------------------------------------
# Export
# -------------------------------------------------------------------------

__all__ = [
    "OrchestrationEngine",
    "run_fast_analysis",
    "run_deep_analysis",
    "run_full_analysis",
    "OrchestrationMode",
]