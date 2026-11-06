"""Unit tests for DPIE Shared Knowledge Base"""

import sys
import tempfile
from pathlib import Path

_src = str(Path(__file__).parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from dpie.schemas import AgentType, EvidenceRecord  # noqa: E402
from dpie.knowledge_base import SharedKnowledgeBase  # noqa: E402


def test_in_memory_kb():
    kb = SharedKnowledgeBase()
    rec = EvidenceRecord(
        source_agent=AgentType.TRIAGE,
        detected_pattern="forced_action",
        confidence_score=0.9,
        element_text="Must accept terms",
    )
    ev_id = kb.store_evidence(rec)
    assert ev_id is not None

    retrieved = kb.get_evidence(ev_id)
    assert retrieved is not None
    pattern = retrieved.get("detected_pattern") if hasattr(retrieved, "get") else retrieved["detected_pattern"]
    assert pattern == "forced_action"


def test_sqlite_persistence():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name

    try:
        kb = SharedKnowledgeBase(db_path=db_path)
        rec = EvidenceRecord(
            source_agent=AgentType.INVESTIGATOR,
            detected_pattern="sneaking",
            confidence_score=0.8,
            risk_score=0.7,
            element_text="Hidden fee",
        )
        ev_id = kb.store_evidence(rec)
        assert ev_id is not None

        # Reopen from disk
        kb2 = SharedKnowledgeBase(db_path=db_path)
        retrieved = kb2.get_evidence(ev_id)
        assert retrieved is not None
        pattern = retrieved.get("detected_pattern") if hasattr(retrieved, "get") else retrieved["detected_pattern"]
        assert pattern == "sneaking"
        print("OK: SQLite Persistence test passed!")
    finally:
        import os
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass


if __name__ == "__main__":
    test_in_memory_kb()
    test_sqlite_persistence()
    print("All KnowledgeBase tests passed!")

