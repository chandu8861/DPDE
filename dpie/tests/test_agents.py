"""Unit and Integration tests for all 11 DPIE Specialized Agents

Runs without pytest — uses plain Python unittest + asyncio with timeout.
"""

import sys
import asyncio
import unittest
from pathlib import Path

_src = str(Path(__file__).parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from dpie.schemas import (  # noqa: E402
    AgentType,
    AgentInput,
)
from dpie.agents import (  # noqa: E402
    TriageAgent,
    InvestigatorAgent,
    CorrelatorAgent,
    ReporterAgent,
    ThreatHunterAgent,
    ForensicsAgent,
    ThreatIntelligenceAgent,
    ComplianceAgent,
    ResponderAgent,
    AutoResponderAgent,
    MitreAnalystAgent,
)


class MockKnowledgeBase:
    def __init__(self):
        self.evidence = []

    def add_findings_to_kb(self, findings):
        self.evidence.extend(findings)

    def search_evidence_by_pattern(self, pattern):
        return [e for e in self.evidence if e.detected_pattern == pattern]


MOCK_KB = MockKnowledgeBase()

TEST_INPUT = AgentInput(
    url="https://example.com/pricing",
    html="""
    <div>
        <button class="cta">Subscribe now - it's free and you must agree!</button>
        <a href="#" class="decline">No thanks, I prefer paying full price</a>
        <span class="terms">Auto-renews at $99/mo after 3 days. Cancel fee $25 applies.</span>
        <input type="hidden" name="csrf_token" value="safe123">
        <input type="hidden" name="optin_newsletter" value="true">
    </div>
    """,
    elements=[
        {
            "element_type": "button",
            "element_text": "Subscribe now - it's free and you must agree!",
            "element_selector": ".cta",
            "element_attributes": {"class": "cta"},
        },
        {
            "element_type": "a",
            "element_text": "No thanks, I prefer paying full price",
            "element_selector": ".decline",
            "element_attributes": {"class": "decline"},
        },
        {
            "element_type": "span",
            "element_text": "Auto-renews at $99/mo after 3 days. Cancel fee $25 applies.",
            "element_selector": ".terms",
            "element_attributes": {"class": "terms"},
        },
        {
            "element_type": "input",
            "element_text": "",
            "element_selector": "input[name=csrf_token]",
            "element_attributes": {"type": "hidden", "name": "csrf_token", "value": "safe123"},
        },
        {
            "element_type": "input",
            "element_text": "",
            "element_selector": "input[name=optin_newsletter]",
            "element_attributes": {"type": "hidden", "name": "optin_newsletter", "value": "true"},
        },
    ],
)


def run_async(coro, timeout=10):
    """Run a coroutine synchronously with a timeout."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
    finally:
        loop.close()


class TestAllAgents(unittest.TestCase):

    def _make_agent(self, cls):
        return cls(knowledge_base=MOCK_KB)

    def test_01_triage_agent(self):
        agent = self._make_agent(TriageAgent)
        out = run_async(agent.analyze(TEST_INPUT))
        self.assertEqual(out.agent_type, AgentType.TRIAGE)
        self.assertGreater(len(out.findings), 0)
        print(f"  TriageAgent: {len(out.findings)} findings, conf={round(out.overall_confidence, 2)}")

    def test_02_investigator_agent(self):
        agent = self._make_agent(InvestigatorAgent)
        out = run_async(agent.analyze(TEST_INPUT))
        self.assertEqual(out.agent_type, AgentType.INVESTIGATOR)
        self.assertGreater(len(out.findings), 0)
        print(f"  InvestigatorAgent: {len(out.findings)} findings, conf={round(out.overall_confidence, 2)}")

    def test_03_threat_hunter_no_csrf_false_positive(self):
        agent = self._make_agent(ThreatHunterAgent)
        out = run_async(agent.analyze(TEST_INPUT))
        self.assertEqual(out.agent_type, AgentType.THREAT_HUNTER)
        csrf_flags = [f for f in out.findings if "csrf_token" in (f.evidence_text or "")]
        self.assertEqual(len(csrf_flags), 0, "False positive: CSRF token was flagged!")
        print(f"  ThreatHunterAgent: {len(out.findings)} findings, CSRF correctly ignored")

    def test_04_correlator_agent(self):
        inv_agent = self._make_agent(InvestigatorAgent)
        inv_out = run_async(inv_agent.analyze(TEST_INPUT))

        corr_input = AgentInput(
            url=TEST_INPUT.url,
            elements=TEST_INPUT.elements,
            previous_findings=inv_out.findings,
        )
        agent = self._make_agent(CorrelatorAgent)
        out = run_async(agent.analyze(corr_input))
        self.assertEqual(out.agent_type, AgentType.CORRELATOR)
        print(f"  CorrelatorAgent: {len(out.findings)} correlated findings")

    def test_05_forensics_agent(self):
        agent = self._make_agent(ForensicsAgent)
        out = run_async(agent.analyze(TEST_INPUT))
        self.assertEqual(out.agent_type, AgentType.FORENSICS)
        print(f"  ForensicsAgent: {len(out.findings)} evidence records")

    def _run_downstream_agent(self, cls, agent_type, upstream_findings):
        agent = self._make_agent(cls)
        inp = AgentInput(
            url=TEST_INPUT.url,
            elements=TEST_INPUT.elements,
            previous_findings=upstream_findings,
        )
        out = run_async(agent.analyze(inp))
        self.assertEqual(out.agent_type, agent_type)
        print(f"  {cls.__name__}: {len(out.findings)} findings")

    def test_06_threat_intelligence_agent(self):
        inv_out = run_async(self._make_agent(InvestigatorAgent).analyze(TEST_INPUT))
        self._run_downstream_agent(ThreatIntelligenceAgent, AgentType.THREAT_INTELLIGENCE, inv_out.findings)

    def test_07_compliance_agent(self):
        inv_out = run_async(self._make_agent(InvestigatorAgent).analyze(TEST_INPUT))
        self._run_downstream_agent(ComplianceAgent, AgentType.COMPLIANCE, inv_out.findings)

    def test_08_responder_agent(self):
        inv_out = run_async(self._make_agent(InvestigatorAgent).analyze(TEST_INPUT))
        self._run_downstream_agent(ResponderAgent, AgentType.RESPONDER, inv_out.findings)

    def test_09_auto_responder_agent(self):
        inv_out = run_async(self._make_agent(InvestigatorAgent).analyze(TEST_INPUT))
        self._run_downstream_agent(AutoResponderAgent, AgentType.AUTO_RESPONDER, inv_out.findings)

    def test_10_mitre_analyst_agent(self):
        inv_out = run_async(self._make_agent(InvestigatorAgent).analyze(TEST_INPUT))
        self._run_downstream_agent(MitreAnalystAgent, AgentType.MITRE_ANALYST, inv_out.findings)

    def test_11_reporter_agent(self):
        inv_out = run_async(self._make_agent(InvestigatorAgent).analyze(TEST_INPUT))
        self._run_downstream_agent(ReporterAgent, AgentType.REPORTER, inv_out.findings)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    loader.sortTestMethodsUsing = None  # Keep definition order
    suite = loader.loadTestsFromTestCase(TestAllAgents)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
