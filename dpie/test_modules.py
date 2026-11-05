#!/usr/bin/env python
import sys
import importlib.util
import os

path = r'D:\Project\Project-1\dpie'

# List key files
key_files = [
    'pyproject.toml',
    '__init__.py',
    'src/__init__.py',
    'src/config.py',
    'src/schemas.py',
    'src/providers.py',
    'src/knowledge_base.py',
    'src/orchestration.py',
]

print('=== DPIE Project Structure ===')
print()

for f in key_files:
    full_path = os.path.join(path, f)
    exists = os.path.exists(full_path)
    if exists:
        print(f'{f}: EXISTS')
    else:
        print(f'{f}: MISSING')

print()
print('=== Module Loading Tests ===')

# Test schemas
spec = importlib.util.spec_from_file_location('schemas', r'D:\Project\Project-1\dpie\src\schemas.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('schemas: OK')

# Test config
spec = importlib.util.spec_from_file_location('config', r'D:\Project\Project-1\dpie\src\config.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('config: OK')

# Test knowledge_base
spec = importlib.util.spec_from_file_location('knowledge_base', r'D:\Project\Project-1\dpie\src\knowledge_base.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('knowledge_base: OK')

# Test orchestration
spec = importlib.util.spec_from_file_location('orchestration', r'D:\Project\Project-1\dpie\src\orchestration.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('orchestration: OK')

# Test agents
for agent_name in ['triage', 'investigator', 'correlator', 'reporter']:
    try:
        spec = importlib.util.spec_from_file_location(agent_name, f'D:\\Project\\Project-1\\dpie\\src\\agents\\{agent_name}.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        print(f'agents/{agent_name}: OK')
    except Exception as e:
        print(f'agents/{agent_name}: ERROR - {str(e)[:50]}')

print('\nAll module tests complete.')