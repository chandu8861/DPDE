#!/usr/bin/env python
"""Debug test for triage agent import."""
import sys
import importlib.util

# Add src to path
sys.path.insert(0, r'D:\Project\Project-1\dpie\src')

# Test the exact import pattern used in triage.py
spec = importlib.util.spec_from_file_location("dpie_schemas", r"D:\Project\Project-1\dpie\src\schemas.py")
print(f"spec: {spec}")
print(f"spec.loader: {spec.loader}")

_schemas_mod = importlib.util.module_from_spec(_schemas_spec)
try:
    _schemas_spec.loader.exec_module(_schemas_mod)
    print('schemas loaded OK')
    print('Has AgentType:', hasattr(_schemas_mod, 'AgentType'))
except Exception as e:
    print(f'Error loading schemas: {e}')

# Now try the triage module
spec2 = importlib.util.spec_from_file_location('triage', r'D:\Project\Project-1\dpie\src\agents\triage.py')
print(f'\ntriSpec: {spec2}')
try:
    triage_mod = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(triage_mod)
    print('triage loaded OK')
    print(f'triage_mod has TriageAgent: {hasattr(triage_mod, "TriageAgent")}')
except Exception as e:
    print(f'triage FAILED: {e}')
    import traceback
    traceback.print_exc()