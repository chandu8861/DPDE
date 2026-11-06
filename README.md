# DPIE — DarkPattern Intelligence Engine

DPIE is a **modular multi-agent Python framework** for detecting, investigating, correlating, classifying, and reporting deceptive user-interface practices (“dark patterns”). It is designed as an **independent, reusable software product/library** (CLI, REST API, Python SDK, dashboard), not as a browser-extension-specific implementation.

> **Status:** v0.1.0 (early). Core orchestration, schemas, and a maintained test suite are in place; detection is primarily **heuristic/rule-based** today. LLM provider integrations exist but should be treated as optional/experimental and require keys/config where applicable.

## Key capabilities

- **11 specialized agents** (triage, investigator, threat hunter, correlator, forensics, threat intelligence, compliance, reporter, responder, auto responder, MITRE analyst) registered via an `AgentRegistry`.
- **Orchestration modes**: `fast`, `deep`, `full` with dependency-aware execution, `previous_findings` propagation, bounded `next_agents` routing (once per run), optional bounded parallelism for independent producer agents, timeouts/error handling/partial results, deduplication, and confidence/risk normalization.
- **Structured evidence**: Pydantic v2 models (`EvidenceRecord`, `AgentInput/Output`, `AnalysisResponse`, etc.) for agent communication (no unstructured chat dependency).
- **Shared knowledge base**: in-memory + optional SQLite persistence (`SharedKnowledgeBase`) for evidence, taxonomy, investigation history, and execution logs; includes bounded in-memory retention and batched commit support for bulk writes.
- **Interfaces**: CLI (`dpie`), FastAPI REST API + Swagger, Python SDK (`DarkPatternEngine`), developer dashboard (`/dashboard`).
- **Packaging/CI**: `src/dpie` layout, `pyproject.toml` (`dpie` script), GitHub Actions workflow for `ruff` + tests.

## Quick start

### Requirements
- Python **3.11+**

### Install (from `dpie/`)

```powershell
python -m pip install -e .
# dev tools (pytest, pytest-asyncio, ruff)
python -m pip install -e ".[dev]"
# optional dashboard extras (jinja2)
python -m pip install -e ".[dashboard]"
```

### Verify

```powershell
python verify.py
python -m ruff check src tests
python -m pytest -q tests
```

### CLI

```powershell
dpie --help
dpie agents
dpie analyze https://example.com --mode deep
dpie serve --host 0.0.0.0 --port 8000
```

### REST API / Dashboard

```powershell
dpie serve --port 8000
# Swagger:   http://localhost:8000/docs
# Dashboard: http://localhost:8000/dashboard
# Health:    http://localhost:8000/api/v1/health
```

### Python SDK

```python
from dpie import DarkPatternEngine

engine = DarkPatternEngine(mode="deep")
result = engine.analyze({
    "url": "https://example.com",
    "elements": [{
        "element_type": "button",
        "element_text": "Subscribe now - free, you must agree",
        "element_selector": ".cta",
    }],
})

print(result.status, len(result.all_findings), result.aggregated_confidence)
# result.all_findings / result.triage / result.investigator / ... / result.report
```

> `analyze()` is a synchronous wrapper around the async engine. Do not call it from a running event loop (use async engine methods such as `execute_deep_mode` / `execute_*` in async contexts).

## Documentation

| Document | Description |
|---|---|
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/architecture.md](docs/architecture.md) | System architecture, data flow, components |
| [docs/agents-and-orchestration.md](docs/agents-and-orchestration.md) | Agent contract, registry, modes, routing, parallelism |
| [docs/api-reference.md](docs/api-reference.md) | REST endpoints, request/response models |
| [docs/sdk.md](docs/sdk.md) | Python SDK (`DarkPatternEngine`, config, results) |
| [docs/configuration.md](docs/configuration.md) | Settings, environment variables, KB/provider knobs |
| [docs/development.md](docs/development.md) | Dev setup, tests, linting, CI, contributing notes |
| [docs/deployment.md](docs/deployment.md) | Docker, Compose, production considerations |
| [docs/data-models.md](docs/data-models.md) | Core Pydantic schemas and evidence model |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common issues and caveats |
| [SUMMARY.md](SUMMARY.md) | Implementation summary / status snapshot |

## Project layout

```text
dpie/
├── pyproject.toml
├── README.md
├── SUMMARY.md
├── verify.py
├── dashboard.py
├── docker-compose.yml
├── Dockerfile
├── .github/workflows/dpie-ci.yml
├── docs/
├── src/dpie/
│   ├── _version.py
│   ├── cli.py
│   ├── config.py
│   ├── schemas.py
│   ├── orchestration.py
│   ├── knowledge_base.py
│   ├── providers.py
│   ├── dashboard_ui.py
│   ├── agents/           # base, registry, 11 agent implementations
│   ├── api/              # FastAPI app
│   └── sdk/              # SDK core/providers helpers
├── tests/                # maintained pytest suite
└── legacy_scripts/       # archived ad-hoc scripts (not maintained)
```

## Caveats / limitations

- **Detection accuracy is not calibrated**; many agents are heuristic-first. Validate outputs before relying on them for enforcement/compliance decisions.
- **LLM providers** are abstracted (`providers.py`) but not fully end-to-end contract-tested across all providers; configure keys via environment/settings and expect heuristic-only fallback in some SDK paths when providers/keys are unavailable.
- **Global singletons** (registry/KB/settings patterns in parts of the system) can limit multi-tenant isolation; treat as single-tenant/process-local unless you add explicit isolation.
- **Security hardening is partial**: API CORS is permissive by default for development convenience; do not expose publicly without auth/rate limiting/CORS restrictions.
- **Version metadata**: runtime uses `src/dpie/_version.py`; keep `pyproject.toml` version in sync for build metadata.

## License

See repository/project licensing terms (not specified in this package snapshot).
