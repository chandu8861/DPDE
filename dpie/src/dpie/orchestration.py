"""DPIE Agent Orchestration Engine

Configurable orchestration for running specialized agents.

Supports:
- Sequential execution and conditional *agent routing* (`next_agents` emitted by an agent can enqueue that agent once per run).
- Optional parallel execution for independent (producer) agents via `OrchestrationConfiguration.parallel_execution` / `max_parallel_agents`. Dependent agents that consume `previous_findings` run after producers with accumulated findings.
- Agent-to-agent communication through structured `previous_findings` propagation.
- Timeouts, error handling, and partial results when an agent fails.

Modes (default agent sets):
- FAST: triage
- DEEP: triage, investigator, correlator
- FULL: triage, investigator, threat_hunter, correlator, forensics, compliance, reporter
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
    OrchestrationConfiguration,
    AnalysisResponse,
)
from dpie.agents.registry import AgentRegistry, get_agent_registry
from dpie.knowledge_base import get_knowledge_base, SharedKnowledgeBase


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
        self._ensure_default_agents()

    def _ensure_default_agents(self) -> None:
        """Register default agent implementations when missing."""
        try:
            from dpie.agents.triage import TriageAgent
            from dpie.agents.investigator import InvestigatorAgent
            from dpie.agents.correlator import CorrelatorAgent
            from dpie.agents.reporter import ReporterAgent
            from dpie.agents.threat_hunter import ThreatHunterAgent
            from dpie.agents.forensics import ForensicsAgent
            from dpie.agents.threat_intelligence import ThreatIntelligenceAgent
            from dpie.agents.compliance import ComplianceAgent
            from dpie.agents.responder import ResponderAgent
            from dpie.agents.auto_responder import AutoResponderAgent
            from dpie.agents.mitre_analyst import MitreAnalystAgent
        except Exception as e:
            logger.debug("Could not import default agents: %s", e)
            return

        defaults = [
            (AgentType.TRIAGE, TriageAgent),
            (AgentType.INVESTIGATOR, InvestigatorAgent),
            (AgentType.CORRELATOR, CorrelatorAgent),
            (AgentType.REPORTER, ReporterAgent),
            (AgentType.THREAT_HUNTER, ThreatHunterAgent),
            (AgentType.FORENSICS, ForensicsAgent),
            (AgentType.THREAT_INTELLIGENCE, ThreatIntelligenceAgent),
            (AgentType.COMPLIANCE, ComplianceAgent),
            (AgentType.RESPONDER, ResponderAgent),
            (AgentType.AUTO_RESPONDER, AutoResponderAgent),
            (AgentType.MITRE_ANALYST, MitreAnalystAgent),
        ]
        for agent_type, cls in defaults:
            try:
                if self.agent_registry.get_agent(agent_type) is None:
                    self.agent_registry.register(cls(knowledge_base=self.knowledge_base))
            except Exception as e:
                logger.debug("Could not register %s: %s", agent_type, e)
    
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
            self._ensure_default_agents()
            agents_to_run = selected_agents or self.get_agents_for_mode(self.orchestration_mode)
            agents_to_run = [a for a in agents_to_run if self.agent_registry.is_agent_enabled(a)]
        if not agents_to_run:
            return AnalysisResponse(
                request_id=self._generate_request_id(),
                status="no_agents_available",
                all_findings=[],
                aggregated_confidence=0.0,
                aggregated_risk=1.0,
                execution_summary="No agents available for the selected mode",
                total_execution_time_ms=int((time.time() - start_time) * 1000),
            )
        
        # Execute agents with timeout/error handling.
        # Findings are propagated as previous_findings to downstream agents.
        all_findings: List[EvidenceRecord] = list(input_data.previous_findings or [])
        agent_results: Dict[AgentType, AgentOutput] = {}
        overall_confidence = 0.5
        overall_risk = 1.0
        execution_errors: List[str] = []

        run_queue: List[AgentType] = list(agents_to_run)
        run_set = set(run_queue)
        parallel = bool(getattr(self.configuration, "parallel_execution", False))
        max_parallel = int(getattr(self.configuration, "max_parallel_agents", 3) or 3)
        max_parallel = max(1, min(max_parallel, 16))
        routed_budget = 20

        async def _run_agent(agent_type: AgentType, inp: AgentInput) -> Tuple[AgentType, AgentOutput, int]:
            agent = self.agent_registry.get_agent(agent_type)
            if agent is None:
                logger.warning(f"Agent {agent_type} not registered, skipping")
                return agent_type, AgentOutput(
                    agent_type=agent_type, status=AgentStatus.FAILED, findings=[],
                    overall_confidence=0.0, overall_risk=1.0, execution_time_ms=0,
                    model_used=None, tokens_consumed=0, requires_followup=False,
                ), 0
            if not agent.can_process(inp):
                logger.info(f"Agent {agent_type} cannot process input, skipping")
                return agent_type, AgentOutput(
                    agent_type=agent_type, status=AgentStatus.SKIPPED, findings=[],
                    overall_confidence=1.0, overall_risk=0.0, execution_time_ms=0,
                    model_used=None, tokens_consumed=0, requires_followup=False,
                ), 0
            agent_start = time.time()
            try:
                output: AgentOutput = await asyncio.wait_for(
                    agent.analyze(inp), timeout=self._get_agent_timeout(agent_type)
                )
                agent.log_execution(agent_start, output)
                return agent_type, output, int((time.time() - agent_start) * 1000)
            except asyncio.TimeoutError:
                logger.error(f"Agent {agent_type} execution timed out")
                return agent_type, AgentOutput(
                    agent_type=agent_type, status=AgentStatus.FAILED, findings=[],
                    overall_confidence=0.0, overall_risk=1.0,
                    execution_time_ms=self._get_agent_timeout(agent_type) * 1000,
                    model_used=None, tokens_consumed=0, requires_followup=False,
                ), self._get_agent_timeout(agent_type) * 1000
            except Exception as e:
                logger.error(f"Agent {agent_type} failed: {e}", exc_info=True)
                return agent_type, AgentOutput(
                    agent_type=agent_type, status=AgentStatus.FAILED, findings=[],
                    overall_confidence=0.0, overall_risk=1.0,
                    execution_time_ms=int((time.time() - agent_start) * 1000),
                    model_used=None, tokens_consumed=0, requires_followup=False,
                ), int((time.time() - agent_start) * 1000)

        def _needs_previous(agent_type: AgentType) -> bool:
            # Agents that primarily consume previous findings; keep after producers.
            return agent_type in {
                AgentType.CORRELATOR, AgentType.REPORTER, AgentType.COMPLIANCE,
                AgentType.THREAT_INTELLIGENCE, AgentType.RESPONDER,
                AgentType.AUTO_RESPONDER, AgentType.MITRE_ANALYST,
            }

        def _store_and_merge(output: AgentOutput) -> None:
            nonlocal overall_confidence, overall_risk
            if output.findings:
                if hasattr(self.knowledge_base, "add_findings_to_kb"):
                    self.knowledge_base.add_findings_to_kb(output.findings)
                elif hasattr(self.knowledge_base, "store_evidence"):
                    for f in output.findings:
                        try:
                            self.knowledge_base.store_evidence(f)
                        except Exception:
                            pass
                all_findings.extend(output.findings)
            if getattr(output, "overall_confidence", None) is not None and output.overall_confidence > overall_confidence:
                overall_confidence = output.overall_confidence
            if getattr(output, "overall_risk", None) is not None and output.overall_risk > overall_risk:
                overall_risk = output.overall_risk
            for nxt in (output.next_agents or []):
                if routed_budget <= 0:
                    break
                try:
                    nt = nxt if isinstance(nxt, AgentType) else AgentType(nxt)
                except Exception:
                    continue
                if nt not in run_set and self.agent_registry.is_agent_enabled(nt):
                    run_queue.append(nt)
                    run_set.add(nt)

        # Phase 1: producers (independent of previous findings). Can run in parallel.
        i = 0
        while i < len(run_queue):
            batch: List[AgentType] = []
            while i < len(run_queue):
                at = run_queue[i]
                if at in agent_results:
                    i += 1
                    continue
                if _needs_previous(at):
                    break
                batch.append(at)
                i += 1
            if not batch and i < len(run_queue):
                # next is a dependent; handle in phase 2
                pass
            if batch:
                inp0 = input_data.model_copy(update={"previous_findings": list(all_findings)})
                if parallel and len(batch) > 1:
                    sem = asyncio.Semaphore(max_parallel)
                    async def _bounded(at: AgentType):
                        async with sem:
                            return await _run_agent(at, inp0)
                    results = await asyncio.gather(*[_bounded(at) for at in batch])
                else:
                    results = [await _run_agent(at, inp0) for at in batch]
                for at, out, _ms in results:
                    agent_results[at] = out
                    _store_and_merge(out)
                    if out.status == AgentStatus.FAILED:
                        execution_errors.append(f"Agent {at.value if hasattr(at,'value') else at} failed")
            # Phase 2: consume any dependent agents now ready (sequential, with accumulated findings)
            while i < len(run_queue):
                at = run_queue[i]
                if at in agent_results:
                    i += 1
                    continue
                if not _needs_previous(at):
                    break
                inp = input_data.model_copy(update={"previous_findings": list(all_findings)})
                at2, out2, _ms2 = await _run_agent(at, inp)
                agent_results[at2] = out2
                _store_and_merge(out2)
                if out2.status == AgentStatus.FAILED:
                    execution_errors.append(f"Agent {at2.value if hasattr(at2,'value') else at2} failed")
                i += 1
                # routed agents appended to queue; loop will handle
            if i < len(run_queue) and run_queue[i] in agent_results:
                i += 1
            elif not batch and i < len(run_queue) and _needs_previous(run_queue[i]):
                # safety: force progress
                at = run_queue[i]
                i += 1
                if at not in agent_results:
                    inp = input_data.model_copy(update={"previous_findings": list(all_findings)})
                    at2, out2, _ = await _run_agent(at, inp)
                    agent_results[at2] = out2
                    _store_and_merge(out2)
        
        # Deduplicate findings
        all_findings = self._deduplicate_findings(all_findings)

        # Normalize risk/confidence semantics across agents
        all_findings = self._normalize_findings(all_findings)

        # Calculate aggregated confidence and risk
        if all_findings:
            confidences = [float(f.confidence_score) for f in all_findings if getattr(f, "confidence_score", None) is not None]
            risks = [float(f.risk_score) for f in all_findings if getattr(f, "risk_score", None) is not None]
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5
            overall_risk = sum(risks) / len(risks) if risks else max((c for c in confidences), default=0.5)
        else:
            overall_confidence = 0.0
            overall_risk = 0.0
        
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
        def _dump(out: Optional[AgentOutput]) -> Any:
            if out is None:
                return None
            return out.model_dump() if hasattr(out, "model_dump") else out

        response = AnalysisResponse(
            request_id=self._generate_request_id(),
            status=status,
            triage=_dump(agent_results.get(AgentType.TRIAGE)),
            investigator=_dump(agent_results.get(AgentType.INVESTIGATOR)),
            correlator=_dump(agent_results.get(AgentType.CORRELATOR)),
            reporter=_dump(agent_results.get(AgentType.REPORTER)),
            threat_hunter=_dump(agent_results.get(AgentType.THREAT_HUNTER)),
            forensics=_dump(agent_results.get(AgentType.FORENSICS)),
            compliance=_dump(agent_results.get(AgentType.COMPLIANCE)),
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

    @staticmethod
    def _clamp01(value: Any, default: float) -> float:
        try:
            v = float(value)
        except Exception:
            v = default
        if v != v:  # NaN
            v = default
        return max(0.0, min(1.0, v))

    def _normalize_findings(self, findings: List[EvidenceRecord]) -> List[EvidenceRecord]:
        """Normalize confidence/risk across agent outputs.

        - confidence_score: required, clamped to [0,1] (default 0.5)
        - risk_score: clamped to [0,1]; if missing, derived from confidence
        """
        out: List[EvidenceRecord] = []
        for f in findings:
            conf = self._clamp01(getattr(f, "confidence_score", 0.5), 0.5)
            risk_raw = getattr(f, "risk_score", None)
            risk = self._clamp01(risk_raw, conf) if risk_raw is not None else conf
            try:
                if conf != getattr(f, "confidence_score", conf) or risk != getattr(f, "risk_score", risk):
                    if hasattr(f, "model_copy"):
                        f = f.model_copy(update={"confidence_score": conf, "risk_score": risk})
                    else:
                        f.confidence_score = conf
                        f.risk_score = risk
            except Exception:
                pass
            out.append(f)
        return out
    
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


    async def execute_fast_mode(self, input_data: AgentInput) -> AnalysisResponse:
        self.configure_mode(OrchestrationMode.FAST)
        return await self.execute(input_data)

    async def execute_deep_mode(self, input_data: AgentInput) -> AnalysisResponse:
        self.configure_mode(OrchestrationMode.DEEP)
        return await self.execute(input_data)

    async def execute_full_mode(self, input_data: AgentInput) -> AnalysisResponse:
        self.configure_mode(OrchestrationMode.FULL)
        return await self.execute(input_data)


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
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        raise RuntimeError("run_fast_analysis cannot be used inside a running event loop; await engine.execute_fast_mode(...)")
    return asyncio.run(engine.execute_fast_mode(input_data))


def run_deep_analysis(
    input_data: AgentInput,
    orchestration_engine: Optional[OrchestrationEngine] = None,
) -> AnalysisResponse:
    """Run deep analysis (investigator + correlator)."""
    engine = orchestration_engine or OrchestrationEngine(mode=OrchestrationMode.DEEP)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        raise RuntimeError("run_deep_analysis cannot be used inside a running event loop; await engine.execute_deep_mode(...)")
    return asyncio.run(engine.execute_deep_mode(input_data))


def run_full_analysis(
    input_data: AgentInput,
    orchestration_engine: Optional[OrchestrationEngine] = None,
) -> AnalysisResponse:
    """Run full analysis (all agents)."""
    engine = orchestration_engine or OrchestrationEngine(mode=OrchestrationMode.FULL)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        raise RuntimeError("run_full_analysis cannot be used inside a running event loop; await engine.execute_full_mode(...)")
    return asyncio.run(engine.execute_full_mode(input_data))


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