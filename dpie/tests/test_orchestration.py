"""Integration tests for DPIE Orchestration Engine"""

import asyncio
import sys
from pathlib import Path

_src = str(Path(__file__).parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from dpie.schemas import AgentInput, OrchestrationMode  # noqa: E402
from dpie.orchestration import (  # noqa: E402
    OrchestrationEngine,
)


TEST_INPUT = AgentInput(
    url="https://example.com/subscribe",
    html="<button class='cta'>Subscribe now - it's free and you must agree!</button>",
    elements=[
        {
            "element_type": "button",
            "element_text": "Subscribe now - it's free and you must agree!",
            "element_selector": ".cta",
            "element_attributes": {"class": "cta"}
        }
    ]
)


async def test_fast_mode():
    engine = OrchestrationEngine(orchestration_mode=OrchestrationMode.FAST)
    resp = await engine.execute(TEST_INPUT)
    assert resp.status in ("completed", "triage_only")
    assert resp.aggregated_confidence is not None
    print(f"[OK] Fast Mode: findings={len(resp.all_findings)}, time={resp.total_execution_time_ms}ms")


async def test_deep_mode():
    engine = OrchestrationEngine(orchestration_mode=OrchestrationMode.DEEP)
    resp = await engine.execute(TEST_INPUT)
    assert resp.status == "completed"
    assert len(resp.all_findings) > 0
    print(f"[OK] Deep Mode: findings={len(resp.all_findings)}, time={resp.total_execution_time_ms}ms")


async def test_full_mode():
    engine = OrchestrationEngine(orchestration_mode=OrchestrationMode.FULL)
    resp = await engine.execute(TEST_INPUT)
    assert resp.status == "completed"
    print(f"[OK] Full Mode: findings={len(resp.all_findings)}, time={resp.total_execution_time_ms}ms")


async def run_all():
    print("=" * 60)
    print("Testing DPIE Orchestration Engine Modes")
    print("=" * 60)
    await test_fast_mode()
    await test_deep_mode()
    await test_full_mode()
    print("All orchestration tests passed!")


if __name__ == "__main__":
    asyncio.run(run_all())

