#!/usr/bin/env python
"""Test script for DPIE Phase 3 agents."""
import sys
import importlib.util

# Add src to path
sys.path.insert(0, r'D:\Project\Project-1\dpie\src')

# Import schemas
_schemas_spec = importlib.util.spec_from_file_location("dpie_schemas", r"D:\Project\Project-1\dpie\src\schemas.py")
_schemas_mod = importlib.util.module_from_spec(_schemas_spec)
_schemas_spec.loader.exec_module(_schemas_mod)

AgentType = _schemas_mod.AgentType
AgentInput = _schemas_mod.AgentInput
EvidenceRecord = _schemas_mod.EvidenceRecord

print('schemas OK')

# Import agents
agents = {}
for name in ['triage', 'investigator', 'correlator', 'reporter', 'threat_hunter', 'forensics', 'threat_intelligence', 'compliance', 'responder', 'auto_responder', 'mitre_analyst']:
    try:
        spec = importlib.util.spec_from_file_location(name, r'D:\Project\Project-1\dpie\src\agents\\' + name + '.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        agents[name] = getattr(mod, name.capitalize() + 'Agent')
        print(name + ' loaded OK')
    except Exception as e:
        print(name + ' FAILED: ' + str(e))

mock_kb = type('MockKB', (), {'add_findings_to_kb': lambda self, x: None})()

agent_instances = {}
for name, cls in agents.items():
    try:
        agent_instances[name] = cls(knowledge_base=mock_kb)
    except Exception as e:
        print('  ' + name + ' instance FAILED: ' + str(e))

test_elements = [
    {'element_type': 'button', 'element_text': 'Subscribe now - it\'s free and you must agree!', 'element_selector': '.subscribe-btn', 'element_attributes': {'class': 'subscribe-btn'}},
    {'element_type': 'input', 'element_text': 'Email required', 'element_selector': '.email-field', 'element_attributes': {'type': 'email'}},
]
test_html = '<html><button style="visibility: hidden">Hidden</button><script>eval("x")</script><meta http-equiv="refresh" content="0;url=evil.com"></html>'
sr = EvidenceRecord(source_agent=AgentType.INVESTIGATOR, detected_pattern='forced_action', confidence_score=0.8, risk_score=0.7, evidence_text='Must agree', element_type='button', element_selector='.btn', tags=['forced_action', 'investigator-flagged'])

import asyncio

async def test_all():
    results = {}
    
    # Triage
    print('\nTriage:')
    input_data = AgentInput(url='https://example.com', elements=test_elements[:1], html=test_html)
    r = await agent_instances['triage'].analyze(input_data)
    print('  ' + str(len(r.findings)) + ' findings, conf=' + str(round(r.overall_confidence, 2)) + ', risk=' + str(round(r.overall_risk, 2)))
    results['triage'] = {'findings': len(r.findings), 'confidence': r.overall_confidence, 'risk': r.overall_risk}
    
    # Investigator
    print('\nInvestigator:')
    input_data = AgentInput(url='https://example.com', elements=test_elements[:1], html=test_html)
    r = await agent_instances['investigator'].analyze(input_data)
    print('  ' + str(len(r.findings)) + ' findings, conf=' + str(round(r.overall_confidence, 2)) + ', risk=' + str(round(r.overall_risk, 2)))
    results['investigator'] = {'findings': len(r.findings), 'confidence': r.overall_confidence, 'risk': r.overall_risk}
    
    # Correlator
    print('\nCorrelator:')
    input_data = AgentInput(url='https://example.com', elements=test_elements)
    r = asyncio.run(agent_instances['correlator'].analyze(input_data))
    print('  ' + str(len(r.findings)) + ' findings, conf=' + str(round(r.overall_confidence, 2)) + ', risk=' + str(round(r.overall_risk, 2)))
    results['correlator'] = {'findings': len(r.findings), 'confidence': r.overall_confidence, 'risk': r.overall_risk}
    
    # Reporter
    print('\nReporter:')
    sr = EvidenceRecord(source_agent=AgentType.INVESTIGATOR, detected_pattern='forced_action', confidence_score=0.8, risk_score=0.7, evidence_text='Must agree', element_type='button', element_selector='.btn', tags=['forced_action', 'investigator-flagged'])
    input_data = AgentInput(url='https://example.com', previous_findings=[sr])
    r = asyncio.run(agent_instances['reporter'].analyze(input_data))
    print('  ' + str(len(r.findings)) + ' findings, ' + r.summary)
    print('  conf=' + str(round(r.overall_confidence, 2)) + ', risk=' + str(round(r.overall_risk, 2)))
    results['reporter'] = {'findings': len(r.findings), 'confidence': r.overall_confidence, 'risk': r.overall_risk}
    
    # ThreatHunter
    print('\nThreatHunter:')
    input_data = AgentInput(url='https://example.com', html=test_html, elements=test_elements)
    r = asyncio.run(agent_instances['threat_hunter'].analyze(input_data))
    print('  ' + str(len(r.findings)) + ' findings')
    results['threat_hunter'] = {'findings': len(r.findings), 'confidence': r.overall_confidence, 'risk': r.overall_risk}
    
    # Forensics
    print('\nForensics:')
    input_data = AgentInput(url='https://example.com', html=test_html, elements=test_elements)
    r = asyncio.run(agent_instances['forensics'].analyze(input_data))
    print('  ' + str(len(r.findings)) + ' findings')
    results['forensics'] = {'findings': len(r.findings), 'confidence': r.overall_confidence, 'risk': r.overall_risk}
    
    # ThreatIntelligence
    print('\nThreatIntelligence:')
    sr2 = EvidenceRecord(source_agent=AgentType.INVESTIGATOR, detected_pattern='forced_action', confidence_score=0.8, risk_score=0.7, evidence_text='Must agree', element_type='button', element_selector='.btn', tags=['forced_action', 'investigator-flagged'])
    input_data = AgentInput(url='https://example.com', previous_findings=[sr], elements=test_elements)
    r = asyncio.run(agent_instances['threat_intelligence'].analyze(input_data))
    print('  ' + str(len(r.findings)) + ' findings')
    results['threat_intelligence'] = {'findings': len(r.findings), 'confidence': r.overall_confidence, 'risk': r.overall_risk}
    
    # Compliance
    print('\nCompliance:')
    input_data = AgentInput(url='https://example.com', previous_findings=[sr], configuration={'jurisdiction': 'EU', 'enabled_regulations': ['gdpr', 'ccpa']})
    r = asyncio.run(agent_instances['compliance'].analyze(input_data))
    print('  ' + str(len(r.findings)) + ' findings')
    results['compliance'] = {'findings': len(r.findings), 'confidence': r.overall_confidence, 'risk': r.overall_risk}
    
    # Responder
    print('\nResponder:')
    input_data = AgentInput(url='https://example.com', previous_findings=[sr])
    r = asyncio.run(agent_instances['responder'].analyze(input_data))
    print('  ' + str(len(r.findings)) + ' findings, ' + r.summary)
    results['responder'] = {'findings': len(r.findings), 'confidence': r.overall_confidence, 'risk': r.overall_risk}
    
    # AutoResponder
    print('\nAutoResponder:')
    input_data = AgentInput(url='https://example.com', previous_findings=[sr], configuration={'safety_policy': 'conservative', 'permission_policy': 'manual_approval'})
    r = asyncio.run(agent_instances['auto_responder'].analyze(input_data))
    print('  ' + str(len(r.findings)) + ' findings, ' + r.summary)
    results['auto_responder'] = {'findings': len(r.findings), 'confidence': r.overall_confidence, 'risk': r.overall_risk}
    
    # MitreAnalyst
    print('\nMitreAnalyst:')
    sr3 = EvidenceRecord(source_agent=AgentType.INVESTIGATOR, detected_pattern='forced_action', confidence_score=0.8, risk_score=0.7, evidence_text='Must agree', element_type='button', element_selector='.btn', tags=['forced_action', 'investigator-flagged'])
    input_data = AgentInput(url='https://example.com', previous_findings=[sr3])
    r = asyncio.run(agent_instances['mitre_analyst'].analyze(input_data))
    print('  ' + str(len(r.findings)) + ' findings')
    results['mitre_analyst'] = {'findings': len(r.findings), 'confidence': r.overall_confidence, 'risk': r.overall_risk}
    
    print('\n' + '='*50)
    print('PHASE 3 TEST COMPLETE')
    print('Total agents: 11')
    passed = sum(1 for r in results.values() if r is not None)
    print('Agents with results: ' + str(passed))
    print('='*50)

asyncio.run(test_all())