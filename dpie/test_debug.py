#!/usr/bin/env python
"""Test script for DPIE Phase 2 agents - debug version."""
import sys
import importlib.util
import os

# Add src to path
sys.path.insert(0, r'D:\Project\Project-1\dpie\src')

# First, let's see what happens when we try to import schemas directly
print("Testing direct file import of schemas...")
spec = importlib.util.spec_from_file_location('schemas', r'D:\Project\Project-1\dpie\src\schemas.py')
schemas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schemas)
print('schemas OK')

# Now test if we can import the triage module
print('\nTesting triage module import...')
spec = importlib.util.spec_from_file_location('triage', r'D:\Project\Project-1\dpie\src\agents\triage.py')
try:
    triage_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(triage_mod)
    print('triage loaded OK')
    TriageAgent = triage_mod.TriageAgent
    print('TriageAgent loaded OK')
except Exception as e:
    print(f'triage FAILED: {e}')

# Test if we can create an instance
if 'TriageAgent' in dir():
    try:
        # Create a minimal mock kb
        class MockKB:
            def add_findings_to_kb(self, findings):
                pass
        kb = MockKB()
        agent = TriageAgent(knowledge_base=kb)
        print('TriageAgent instance created OK')
    except Exception as e:
        print(f'TriageAgent instance FAILED: {e}')