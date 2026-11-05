#!/usr/bin/env python
import importlib.util
import os
import sys

sys.path.insert(0, r'D:\Project\Project-1\dpie\src')

print("=" * 60)
print("DPIE Code Verification")
print("=" * 60)

# 1. Check that all .py files in src/ are syntactically valid
src_dir = r'D:\Project\Project-1\dpie\src'
syntax_ok = True
py_files = [f for f in os.listdir(src_dir) if f.endswith('.py')]
print(f"\nChecking {len(py_files)} Python source files in src/:")
for f in py_files:
    fpath = os.path.join(src_dir, f)
    try:
        with open(fpath, 'rb') as fh:
            code = fh.read()
        compile(code, fpath, 'exec')
        print(f"  OK: {f}")
    except SyntaxError as e:
        print(f"  ❌ {f}: {e}")
        syntax_ok = False

# 2. Load key modules using importlib
print("\n" + "=" * 50)
print("Loading key modules using importlib:")
print("=" * 50)

modules_to_load = [
    ('schemas', r'D:\Project\Project-1\dpie\src\schemas.py'),
    ('config', r'D:\Project\Project-1\dpie\src\config.py'),
    ('providers', r'D:\Project\Project-1\dpie\src\providers.py'),
    ('knowledge_base', r'D:\Project\Project-1\dpie\src\knowledge_base.py'),
    ('orchestration', r'D:\Project\Project-1\dpie\src\orchestration.py'),
]

loaded_modules = {}
for name, path in modules_to_load:
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        loaded_modules[name] = mod
        print(f"  ✅ {name}")
    except Exception as e:
        print(f"  ❌ {name}: {str(e)[:50]}")

# 3. Test that key classes can be instantiated
print("\n" + "="*50)
print("Testing key class instantiation:")
print("=" * 50)

# Test schemas
schemas_mod = loaded_modules.get('schemas')
if schemas_mod:
    try:
        er = schemas_mod.EvidenceRecord(
            source_agent=schemas_mod.AgentType.TRIAGE,
            confidence_score=0.85,
            detected_pattern='interface_interference'
        )
        print(f"  ✅ EvidenceRecord: confidence={er.confidence_score}, pattern={er.detected_pattern}")
    except Exception as e:
        print(f"  ❌ EvidenceRecord creation failed: {e}")

    # Test DarkPatternCategory
    dpc = schemas_mod.DarkPatternCategory(
        name='Test Category',
        code='test',
        description='A test category',
        subcategories=['sub1'],
        severity_range='medium'
    )
    print(f"  ✅ DarkPatternCategory: {dpc.name}")

    # Test AgentType
    print(f"  ✅ AgentType.TRIAGE: {schemas_mod.AgentType.TRIAGE.value}")

# Test config
config_mod = loaded_modules.get('config')
if schemas_mod and config_mod:
    print(f"  ✅ config module loaded")

# Test knowledge_base
kb_mod = loaded_modules.get('knowledge_base')
if kb_mod:
    print(f"  ✅ knowledge_base module loaded")

# Test providers
providers_mod = loaded_modules.get('providers')
if providers_mod:
    print(f"  ✅ providers module loaded")

# Test orchestration
orchestration_mod = loaded_modules.get('orchestration')
if orchestration_mod:
    print(f"  ✅ orchestration module loaded")

print("\n" + "="*50)
print("VERIFICATION COMPLETE")
print("=" * 50)