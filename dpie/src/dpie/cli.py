"""DPIE Command Line Interface

Entrypoint for `dpie` CLI commands.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Optional

from dpie import __version__
from dpie.schemas import AgentInput, OrchestrationMode
from dpie.orchestration import OrchestrationEngine
from dpie.agents.registry import get_agent_registry


def print_banner():
    banner = f"""
===========================================================
  DPIE - DarkPattern Intelligence Engine (v{__version__})
  Multi-Agent AI Framework for Deceptive UI Practice Detection
===========================================================
"""
    print(banner)


async def run_analysis(url: str, mode: str, html: Optional[str] = None):
    try:
        orch_mode = OrchestrationMode(mode.lower())
    except ValueError:
        print(f"Error: Unknown mode '{mode}'. Choose from: fast, deep, full")
        sys.exit(1)

    print(f"[*] Initializing DPIE Engine in [{orch_mode.value.upper()}] mode...")
    engine = OrchestrationEngine(orchestration_mode=orch_mode)

    input_data = AgentInput(
        url=url,
        html=html or f"<html><body><a href='{url}'>Target Element</a></body></html>",
        elements=[{
            "element_type": "button",
            "element_text": "Subscribe now - it's free and you must agree!",
            "element_selector": ".cta"
        }] if not html else None,
    )

    print(f"[*] Running multi-agent analysis for {url}...")
    response = await engine.execute(input_data)

    print("\n" + "=" * 50)
    print("ANALYSIS RESULTS")
    print("=" * 50)
    print(f"Status: {response.status}")
    print(f"Aggregated Confidence: {round((response.aggregated_confidence or 0) * 100, 1)}%")
    print(f"Aggregated Risk Score: {round((response.aggregated_risk or 0) * 100, 1)}%")
    print(f"Total Findings: {len(response.all_findings)}")
    print(f"Execution Time: {response.total_execution_time_ms} ms")

    if response.all_findings:
        print("\nFindings:")
        for idx, f in enumerate(response.all_findings, 1):
            pattern = f.detected_pattern or "unknown"
            conf = round((f.confidence_score or 0) * 100, 1)
            risk = round((f.risk_score or 0) * 100, 1)
            print(f"  {idx}. [{pattern.upper()}] Conf: {conf}% | Risk: {risk}%")
            if f.evidence_text:
                print(f"     Explanation: {f.evidence_text}")


def main():
    parser = argparse.ArgumentParser(
        prog="dpie",
        description="DPIE - DarkPattern Intelligence Engine CLI",
    )
    parser.add_argument("-v", "--version", action="version", version=f"DPIE {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a URL or HTML snippet for dark patterns")
    analyze_parser.add_argument("url", help="Target URL to inspect")
    analyze_parser.add_argument("--mode", default="deep", choices=["fast", "deep", "full"], help="Analysis mode")
    analyze_parser.add_argument("--html", default=None, help="Optional raw HTML to analyze")

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Run the DPIE REST API & Dashboard")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")

    # agents command
    subparsers.add_parser("agents", help="List registered intelligence agents")

    args = parser.parse_args()

    if not args.command:
        print_banner()
        parser.print_help()
        sys.exit(0)

    if args.command == "analyze":
        print_banner()
        asyncio.run(run_analysis(args.url, args.mode, args.html))

    elif args.command == "serve":
        print_banner()
        from dpie.api.main import run_api
        print(f"[*] Starting API & Developer Dashboard on http://{args.host}:{args.port}")
        print(f"[*] Dashboard: http://localhost:{args.port}/dashboard")
        print(f"[*] Swagger Docs: http://localhost:{args.port}/docs")
        run_api(host=args.host, port=args.port)

    elif args.command == "agents":
        print_banner()
        registry = get_agent_registry()
        # Ensure default agents loaded
        from dpie.api.main import _register_default_agents
        _register_default_agents()
        agents = registry.list_agents()
        print(f"Registered Agents ({len(agents)} total):")
        for a in agents:
            enabled = registry.is_agent_enabled(a.agent_type)
            status_str = "ENABLED" if enabled else "DISABLED"
            print(f"  • {a.agent_type.value if hasattr(a.agent_type, 'value') else a.agent_type:<22} [{status_str}]")


if __name__ == "__main__":
    main()

