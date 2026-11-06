# DPIE Documentation

This directory contains the canonical documentation for **DPIE (DarkPattern Intelligence Engine)** v0.1.0.

## Contents

1. [**Architecture**](architecture.md) — components, package layout, execution/data flow.
2. [**Agents & Orchestration**](agents-and-orchestration.md) — agent contract, registry, FAST/DEEP/FULL modes, routing, parallelism, aggregation.
3. [**Data Models**](data-models.md) — core enums and Pydantic schemas (`EvidenceRecord`, `AgentInput/Output`, `AnalysisRequest/Response`).
4. [**REST API Reference**](api-reference.md) — endpoints, request/response shapes, dashboard, Swagger.
5. [**Python SDK**](sdk.md) — `DarkPatternEngine`, `AnalysisConfig/Result`, sync/async usage.
6. [**Configuration**](configuration.md) — `Settings`, environment variables (`DPIE_` prefix), KB/provider/runtime knobs.
7. [**Deployment**](deployment.md) — local serving, Docker/Compose, production guidance.
8. [**Development**](development.md) — setup, tests, linting, CI, verification, coding notes.
9. [**Troubleshooting & Caveats**](troubleshooting.md) — known limitations and common issues.

## Source of truth

- Runtime behavior: `src/dpie/` (especially `orchestration.py`, `schemas.py`, `api/main.py`, `sdk/sdk_core.py`, `agents/*`, `config.py`, `knowledge_base.py`, `providers.py`).
- Packaging/commands: `pyproject.toml` (`[project.scripts] dpie = dpie.cli:main`).
- Maintained tests: `tests/`. Legacy ad-hoc scripts: `legacy_scripts/` (not maintained).

## Conventions

- Commands below assume execution from `D:\Project\Project-1\dpie` (package root) unless noted.
- Python: **3.11+**. Package layout: **`src/dpie`**.
- Claims in docs should match implemented behavior; where behavior is heuristic/experimental, docs call that out explicitly.
