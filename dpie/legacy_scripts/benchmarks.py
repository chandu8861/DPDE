#!/usr/bin/env python
"""DPIE Performance & Benchmarking Suite (Phase 7)

Measures and validates:
- Execution latency across FAST, DEEP, and FULL modes
- Throughput (analyses/sec)
- Peak memory footprint using tracemalloc
- Multi-agent orchestration overhead
"""

import asyncio
import json
import os
import sys
import time
import tracemalloc
from pathlib import Path

# Add src to sys.path
_src = str(Path(__file__).parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from dpie.schemas import AgentInput, OrchestrationMode
from dpie.orchestration import OrchestrationEngine


SAMPLE_PAYLOAD = {
    "url": "https://example.com/checkout",
    "html": """
    <html>
        <body>
            <button class="cta">Subscribe now - it's free and you must agree!</button>
            <a href="#" class="skip-btn">No thanks, I prefer paying full price</a>
            <input type="hidden" name="csrf_token" value="abc123xyz">
            <span class="terms">Auto-renews at $99/mo after 3-day trial. Cancel fee $25 applies.</span>
        </body>
    </html>
    """,
    "elements": [
        {
            "element_type": "button",
            "element_text": "Subscribe now - it's free and you must agree!",
            "element_selector": ".cta",
            "element_attributes": {"class": "cta"}
        },
        {
            "element_type": "a",
            "element_text": "No thanks, I prefer paying full price",
            "element_selector": ".skip-btn",
            "element_attributes": {"class": "skip-btn"}
        },
        {
            "element_type": "input",
            "element_text": "",
            "element_selector": "input[name=csrf_token]",
            "element_attributes": {"type": "hidden", "name": "csrf_token", "value": "abc123xyz"}
        },
        {
            "element_type": "span",
            "element_text": "Auto-renews at $99/mo after 3-day trial. Cancel fee $25 applies.",
            "element_selector": ".terms",
            "element_attributes": {"class": "terms"}
        }
    ]
}


async def benchmark_mode(mode: OrchestrationMode, iterations: int = 5):
    engine = OrchestrationEngine(orchestration_mode=mode)
    input_data = AgentInput(
        url=SAMPLE_PAYLOAD["url"],
        html=SAMPLE_PAYLOAD["html"],
        elements=SAMPLE_PAYLOAD["elements"],
    )

    latencies = []
    findings_count = 0

    tracemalloc.start()
    start_wall = time.perf_counter()

    for _ in range(iterations):
        t0 = time.perf_counter()
        resp = await engine.execute(input_data)
        elapsed = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed)
        findings_count = len(resp.all_findings)

    total_wall = time.perf_counter() - start_wall
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    avg_latency = sum(latencies) / len(latencies)
    throughput = (iterations / total_wall) if total_wall > 0 else 0

    return {
        "mode": mode.value,
        "iterations": iterations,
        "avg_latency_ms": round(avg_latency, 2),
        "min_latency_ms": round(min(latencies), 2),
        "max_latency_ms": round(max(latencies), 2),
        "throughput_ops_sec": round(throughput, 2),
        "peak_memory_kb": round(peak_mem / 1024, 2),
        "findings_detected": findings_count,
    }


async def run_all_benchmarks():
    print("=" * 65)
    print("  DPIE Phase 7 Performance Benchmark Suite")
    print("=" * 65)
    print(f"Python: {sys.version.split()[0]} | Platform: {sys.platform}\n")

    results = []
    for mode in [OrchestrationMode.FAST, OrchestrationMode.DEEP, OrchestrationMode.FULL]:
        print(f"[*] Benchmarking [{mode.value.upper()}] mode (5 runs)...", end=" ", flush=True)
        res = await benchmark_mode(mode, iterations=5)
        results.append(res)
        print("Done.")

    print("\n" + "-" * 75)
    print(f"{'Mode':<8} | {'Avg Latency':<14} | {'Throughput':<15} | {'Peak RAM':<12} | {'Findings':<8}")
    print("-" * 75)
    for r in results:
        print(f"{r['mode'].upper():<8} | {r['avg_latency_ms']:>8.2f} ms     | {r['throughput_ops_sec']:>7.2f} ops/s    | {r['peak_memory_kb']:>7.2f} KB   | {r['findings_detected']:<8}")
    print("-" * 75)

    # Export benchmark report
    report_path = Path(__file__).parent / "benchmark_report.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Full benchmark report saved to: {report_path.name}")


if __name__ == "__main__":
    asyncio.run(run_all_benchmarks())

