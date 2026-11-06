#!/usr/bin/env python
"""Maintenance helper: ensure EvidenceRecord supports dict-like access.

Safe to run multiple times. Operates on the current package layout.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMA = ROOT / "src" / "dpie" / "schemas.py"


def main() -> int:
    text = SCHEMA.read_text(encoding="utf-8")
    if "def __getitem__(self, key: str)" in text and "def get(self, key: str, default" in text:
        print("EvidenceRecord access helpers already present.")
        return 0
    anchor = '    verified: bool = Field(default=False, description="Whether evidence was verified")'
    if anchor not in text:
        print("Anchor not found; no changes made.")
        return 1
    addition = anchor + '''

    # Backward-compatible dict-like access used by some tests/integrations
    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default
'''
    SCHEMA.write_text(text.replace(anchor, addition), encoding="utf-8")
    print("Added EvidenceRecord __getitem__/get helpers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
