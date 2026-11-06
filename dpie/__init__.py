"""DPIE - DarkPattern Intelligence Engine

Root package that merges src/dpie/ submodules into this namespace.
"""
import sys
from pathlib import Path

# Prefer src/dpie version when available
try:
    from dpie._version import __version__  # type: ignore
except Exception:
    __version__ = "0.1.0"

# Extend __path__ so that `import dpie.schemas` etc. resolve from src/dpie/
_src_dpie = str(Path(__file__).parent / "src" / "dpie")
if _src_dpie not in __path__:  # noqa: F821  (__path__ is injected by Python for packages)
    __path__.append(_src_dpie)  # type: ignore[name-defined]  # noqa: F821

# Also make sure src/ itself is importable for any internal relative imports
_src = str(Path(__file__).parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)
