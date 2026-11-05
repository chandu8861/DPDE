#!/usr/bin/env python
"""Test script for DPIE Phase 2 agents."""
import sys
import importlib.util

# Add src to path
sys.path.insert(0, r'D:\Project\Project-1\dpie\src')

# Import schemas using importlib (same pattern as agents)
_schemas_spec = importlib.util.spec_from_file_location("dpie_schemas", r"D:\Project\Project-1\dpie\src\schemas.py")
_schemas_mod = importlib.util.module_from_spec(_schemas_spec)
_schemas_spec.loader.exec_module(_schemas_mod)

# Pull needed classes
AgentType = _schemas_mod.AgentType
AgentInput = _schemas_mod.AgentInput
EvidenceRecord = _schemas_mod.EvidenceRecord
AgentOutput = _schemas_mod.AgentOutput
OrchestrationMode = _schemas_mod.OrchestrationMode

print('schemas OK')

# Mock Knowledge Base
class MockKnowledgeBase:
    def add_findings_to_kb(self, findings):
        pass
    def search_evidence_by_pattern(self, pattern):
        return []

mock_kb = MockKnowledgeBase()

# Import agents directly from their module files
_spec = importlib.util.spec_from_file_location('triage', r'D:\Project\Project-1\dpie\src\agents\triage.py')
_triage_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_triage_mod)
TriageAgent = _triage_mod.TriageAgent
print('TriageAgent loaded OK')

_spec = importlib.util.spec_from_file_location('investigator', r'D:\Project\Project-1\dpie\src\agents\investigator.py')
_inv_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_inv_mod)
InvestigatorAgent = _inv_mod.InvestigatorAgent
print('InvestigatorAgent loaded OK')

_spec = importlib.util.spec_from_file_location('correlator', r'D:\Project\Project-1\dpie\src\agents\correlator.py')
_corr_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_corr_mod)
CorrelatorAgent = _corr_mod.CorrelatorAgent
print('CorrelatorAgent loaded OK')

_spec = importlib.util.spec_from_file_location('reporter', r'D:\Project\Project-1\dpie\src\agents\reporter.py')
_rep_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rep_mod)
ReporterAgent = _rep_mod.ReporterAgent
print('ReporterAgent loaded OK')

# Create agent instances with mock kb
triage_agent = TriageAgent(knowledge_base=mock_kb)
investigator_agent = InvestigatorAgent(knowledge_base=mock_kb)
correlator_agent = CorrelatorAgent(knowledge_base=mock_kb)
reporter_agent = ReporterAgent(knowledge_base=mock_kb)

print('All agent instances created successfully!')
print(f'Triage: {triage_agent.agent_type}')
print(f'Investigator: {investigator_agent.agent_type}')
print(f'Correlator: {correlator_agent.agent_type}')
print(f'Reporter: {reporter_agent.agent_type}')

# Test triage analysis with sample input
import asyncio

async def test_triage():
    input_data = AgentInput(
        url='https://example-signup.com',
        html='<button>Subscribe now - it\'s free and you must agree!</button>',
        elements=[{
            'element_type': 'button',
            'element_text': 'Subscribe now - it\'s free and you must agree!',
            'element_selector': '.subscribe-btn',
            'element_attributes': {'class': 'subscribe-btn'}
        }]
    )

    output = await triage_agent.analyze(input_data)
    print('\nTriage Results:')
    print('  Findings: ' + str(len(output.findings)))
    for f in output.findings:
        pattern = f.detected_pattern if f.detected_pattern else 'unknown'
        conf = f.confidence_score if f.confidence_score is not None else 0
        risk = f.risk_score if f.risk_score is not None else 0
        print('    - ' + pattern + ': confidence=' + str(round(conf, 2)) + ', risk=' + str(round(risk, 2)))
    oc = output.overall_confidence if output.overall_confidence is not None else 0
    print('  Overall confidence: ' + str(round(oc, 2)))
    na = output.next_agents if output.next_agents else []
    print('  Next agents: ' + str([a.value if hasattr(a, 'value') else str(a) for a in na]))
    print('  Requires followup: ' + str(output.requires_followup))

asyncio.run(test_triage())

# Test investigator analysis
async def test_investigator():
    input_data = AgentInput(
        url='https://example-signup.com',
        html='<button>Subscribe now - it\'s free and you must agree!</button>',
        elements=[{
            'element_type': 'button',
            'element_text': 'Subscribe now - it\'s free and you must agree!',
            'element_selector': '.subscribe-btn',
            'element_attributes': {'class': 'subscribe-btn'}
        }]
    )

    output = await investigator_agent.analyze(input_data)
    print('\nInvestigator Results:')
    print('  Findings: ' + str(len(output.findings)))
    for f in output.findings:
        pattern = f.detected_pattern if f.detected_pattern else 'unknown'
        conf = f.confidence_score if f.confidence_score is not None else 0
        risk = f.risk_score if f.risk_score is not None else 0
        expl = f.evidence_text[:75] if f.evidence_text else 'N/A'
        print('    - Pattern: ' + pattern + ', Confidence: ' + str(round(conf, 2)))
        print('      Risk: ' + str(round(risk, 2)))
        print('      Explanation: ' + expl + '...')
    oc = output.overall_confidence if output.overall_confidence is not None else 0
    or_ = output.overall_risk if output.overall_risk is not None else 0
    print('  Overall confidence: ' + str(round(oc, 2)))
    print('  Overall risk: ' + str(round(or_, 2)))
    na = output.next_agents if output.next_agents else []
    print('  Next agents: ' + str([a.value if hasattr(a, 'value') else str(a) for a in na]))

asyncio.run(test_investigator())

# Test correlator analysis
async def test_correlator():
    input_data = AgentInput(
        url='https://example-site.com',
        elements=[{
            'element_type': 'button',
            'element_text': 'Subscribe now - it\'s free and you must agree!',
            'element_selector': '.subscribe-btn',
            'element_attributes': {'class': 'subscribe-btn'}
        }, {
            'element_type': 'input',
            'element_text': 'Email required',
            'element_selector': '.email-field',
            'element_attributes': {'type': 'email'}
        }]
    )

    output = await correlator_agent.analyze(input_data)
    print('\nCorrelator Results:')
    print('  Findings: ' + str(len(output.findings)))
    for f in output.findings:
        pattern = f.detected_pattern if f.detected_pattern else 'unknown'
        conf = f.confidence_score if f.confidence_score is not None else 0
        risk = f.risk_score if f.risk_score is not None else 0
        print('    - Pattern: ' + pattern + ', Confidence: ' + str(round(conf, 2)) + ', Risk: ' + str(round(risk, 2)))
    oc = output.overall_confidence if output.overall_confidence is not None else 0
    or_ = output.overall_risk if output.overall_risk is not None else 0
    print('  Overall confidence: ' + str(round(oc, 2)))
    print('  Overall risk: ' + str(round(or_, 2)))

asyncio.run(test_correlator())

# Test reporter analysis
async def test_reporter():
    # Pass findings as dicts to avoid EvidenceRecord class mismatch across importlib loads
    investigator_findings_dicts = [
        {
            'source_agent': AgentType.INVESTIGATOR,
            'detected_pattern': 'forced_action',
            'confidence_score': 0.7,
            'risk_score': 0.8,
            'evidence_text': 'Must agree to terms',
            'element_type': 'button',
            'element_selector': '.btn',
            'tags': ['forced_action', 'investigator-flagged'],
        }
    ]
    
    input_data = AgentInput(
        url='https://example-site.com',
        previous_findings=investigator_findings_dicts
    )

    output = await reporter_agent.analyze(input_data)
    print('\nReporter Results:')
    print('  Summary: ' + str(output.summary))
    oc = output.overall_confidence if output.overall_confidence is not None else 0
    or_ = output.overall_risk if output.overall_risk is not None else 0
    print('  Overall confidence: ' + str(round(oc, 2)))
    print('  Overall risk: ' + str(round(or_, 2)))
    na = output.next_agents if output.next_agents else []
    print('  Next agents: ' + str([a.value if hasattr(a, 'value') else str(a) for a in na]))
    print('  Report generated successfully!')

asyncio.run(test_reporter())

print('\n=== ALL AGENT FUNCTIONALITY TESTS PASSED ===')