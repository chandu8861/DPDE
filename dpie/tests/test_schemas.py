import sys
from pathlib import Path

_src = str(Path(__file__).resolve().parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

try:
    import pytest  # type: ignore
except Exception:  # pragma: no cover
    class _PytestShim:
        class _Raises:
            def __init__(self, exc):
                self.exc = exc
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return exc_type is not None and issubclass(exc_type, self.exc)
        @staticmethod
        def raises(exc):
            return _PytestShim._Raises(exc)
    pytest = _PytestShim()  # type: ignore

from dpie.schemas import (  # noqa: E402
    AgentType,
    AgentStatus,
    OrchestrationMode,
    EvidenceRecord,
    AgentInput,
    AgentOutput,
)


def test_evidence_record_creation():
    rec = EvidenceRecord(
        source_agent=AgentType.TRIAGE,
        detected_pattern="sneaking",
        confidence_score=0.85,
        risk_score=0.6,
        evidence_text="Hidden fee detected",
        element_type="button",
        element_selector=".cta",
    )
    assert rec.detected_pattern == "sneaking"
    assert rec.confidence_score == 0.85
    assert rec.risk_score == 0.6
    assert rec.source_agent == AgentType.TRIAGE


def test_confidence_validation():
    with pytest.raises(Exception):
        EvidenceRecord(
            source_agent=AgentType.TRIAGE,
            confidence_score=1.5,
        )


def test_agent_input_output():
    inp = AgentInput(url="https://example.com", elements=[{"text": "click here"}])
    assert inp.url == "https://example.com"
    assert len(inp.elements) == 1

    out = AgentOutput(
        agent_type=AgentType.TRIAGE,
        status=AgentStatus.COMPLETED,
        findings=[],
        overall_confidence=0.9,
    )
    assert out.status == AgentStatus.COMPLETED
    assert out.overall_confidence == 0.9


def test_orchestration_modes():
    assert OrchestrationMode.FAST.value == "fast"
    assert OrchestrationMode.DEEP.value == "deep"
    assert OrchestrationMode.FULL.value == "full"


if __name__ == "__main__":
    test_evidence_record_creation()
    test_agent_input_output()
    test_orchestration_modes()
    # Test validation error
    try:
        EvidenceRecord(source_agent=AgentType.TRIAGE, confidence_score=1.5)
        print("ERROR: Should have raised validation error")
    except Exception:
        print("confidence_score>1.0 validation works OK")
    print("All schema tests passed successfully!")

