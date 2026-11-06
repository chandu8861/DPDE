#!/usr/bin/env python
"""DPIE verification script.

Performs lightweight, import-safe checks against the current package layout.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def check_syntax() -> bool:
    print("== Syntax check: src/dpie ==")
    ok = True
    for path in (SRC / "dpie").rglob("*.py"):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
            rel = path.relative_to(ROOT)
            print(f"  OK  {rel}")
        except Exception as e:
            ok = False
            rel = path.relative_to(ROOT)
            print(f"  FAIL {rel}: {e}")
    return ok


def check_imports() -> bool:
    print("\n== Import check ==")
    try:
        import dpie
        from dpie import DarkPatternEngine, OrchestrationEngine, schemas
        from dpie.providers import ProviderFactory
        print(f"  OK  dpie v{getattr(dpie, '__version__', '?')} imports")
        return True
    except Exception as e:
        print(f"  FAIL imports: {e}")
        return False


def check_basic_behavior() -> bool:
    print("\n== Basic behavior check ==")
    try:
        from dpie.schemas import EvidenceRecord, AgentType
        er = EvidenceRecord(source_agent=AgentType.TRIAGE, confidence_score=0.5, detected_pattern="sneaking")
        assert er.detected_pattern == "sneaking"
        print("  OK  schema instantiation")
        return True
    except Exception as e:
        print(f"  FAIL behavior: {e}")
        return False


def main() -> int:
    print("DPIE Verification")
    print("=" * 60)
    ok = check_syntax() and check_imports() and check_basic_behavior()
    print("\n" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
