#!/usr/bin/env python
"""Test script for DPIE schemas."""
import sys
import importlib.util

# Add src to path
sys.path.insert(0, r'D:\Project\Project-1\dpie\src')

# Load schemas directly
spec = importlib.util.spec_from_file_location('schemas', r'D:\Project\Project-1\dpie\src\schemas.py')
schemas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schemas)
print('schemas OK')

# Now test creating an EvidenceRecord
er = schemas.EvidenceRecord(
    source_agent=schemas.AgentType.TRIAGE,
    confidence_score=0.85,
    detected_pattern='interface_interference'
)
print(f'EvidenceRecord created: {er}')
print(f'  confidence_score: {er.confidence_score}')
print(f'  detected_pattern: {er.detected_pattern}')

# Test DarkPatternCategory
dpc = schemas.DarkPatternCategory(
    name='Interface Interference',
    code='ii',
    description='Test description',
    subcategories=['misleading_navigation', 'hidden_conditions'],
    severity_range='medium'
)
print(f'DarkPatternCategory created: {dpc.name}')

# Test AgentType
print(f'AgentType.TRIAGE: {schemas.AgentType.TRIAGE.value}')

# Test OrchestrationMode
print(f'OrchestrationMode.FAST: {schemas.OrchestrationMode.FAST.value}')

# Test DetectionStatus
print(f'DetectionStatus.DETECTED: {schemas.DetectionStatus.DETECTED.value}')

# Test AgentInput
ai = schemas.AgentInput(
    url='https://example.com',
    html='<html><body>Test</body></html>'
)
print(f'AgentInput created successfully')

# Test AgentOutput
ao = schemas.AgentOutput(
    agent_type=schemas.AgentType.TRIAGE,
    status=schemas.AgentStatus.COMPLETED,
    overall_confidence=0.9
)
print(f'AgentOutput created: confidence={ao.overall_confidence}')

# Test AnalysisRequest
ar = schemas.AnalysisRequest(
    url='https://example.com',
    mode=schemas.OrchestrationMode.DEEP
)
print(f'AnalysisRequest created successfully')

# Test AnalysisResponse
ar_resp = schemas.AnalysisResponse(
    request_id='test-123',
    status='completed'
)
print(f'AnalysisResponse created: request_id={ar_resp.request_id}')

# Test ReportContent
rc = schemas.ReportContent(
    format=schemas.ReportFormat.JSON,
    pattern_name='Interface Interference',
    severity='high',
    confidence=0.9,
    explanation='Test explanation',
    recommendations=['Fix the issue']
)
print(f'ReportContent created successfully')

# Test AgentConfiguration
ac = schemas.AgentConfiguration(
    agent_type=schemas.AgentType.INVESTIGATOR,
    confidence_threshold=0.7
)
print(f'AgentConfiguration created: threshold={ac.confidence_threshold}')

# Test OrchestrationConfiguration
oc = schemas.OrchestrationConfiguration(
    mode=schemas.OrchestrationMode.FULL,
    max_parallel_agents=3
)
print(f'OrchestrationConfiguration created: mode={oc.mode}')

print('\n=== ALL SCHEMA TESTS PASSED ===')