"""DPIE Agent Modules

Package containing all specialized agents for the DPIE framework.
"""

from dpie.agents.base import BaseAgent
from dpie.agents.registry import (
    AgentRegistry,
    get_agent_registry,
    init_agent_registry,
    register_agent,
)
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

__all__ = [
    "BaseAgent",
    "AgentRegistry",
    "get_agent_registry",
    "init_agent_registry",
    "register_agent",
    "TriageAgent",
    "InvestigatorAgent",
    "CorrelatorAgent",
    "ReporterAgent",
    "ThreatHunterAgent",
    "ForensicsAgent",
    "ThreatIntelligenceAgent",
    "ComplianceAgent",
    "ResponderAgent",
    "AutoResponderAgent",
    "MitreAnalystAgent",
]
