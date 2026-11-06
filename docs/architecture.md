# Architecture

## Overview

DPIE is organized as a Python package (`src/dpie`) with four primary interfaces over a shared core:

- **CLI** (`dpie.cli:main`, script `dpie`) — analyze a URL/HTML snippet, list agents, start the API/dashboard.
- **REST API** (`dpie.api.main:app`, FastAPI) — `/api/v1/*` endpoints + `/dashboard` + OpenAPI docs.
- **Python SDK** (`dpie.DarkPatternEngine` / `dpie.sdk.sdk_core`) — programmatic analysis with `AnalysisResult`.
- **Dashboard UI** (`dpie.dashboard_ui` / `dashboard.py`) — lightweight HTML interface served by the API.

## Component diagram (logical)

```text
                +--------------------+
                |  CLI / SDK / API   |
                +---------+----------+
                          |
                +---------v----------+
                | OrchestrationEngine|
                |  (modes/routing/  |
                |   aggregation)     |
                +----+----+----+-----+
                     |    |    |
          +----------+    |    +----------+
          v               v               v
   +-------------+  +-------------+  +-------------+
   | Agent A     |  | Agent B     |  | Agent N     |
   | (BaseAgent) |  | (BaseAgent) |  | (BaseAgent) |
   +------+------+  +------+------+  +------+------+
          \              |                /
           \             v               /
            +------ SharedKnowledgeBase --+
            |  evidence/taxonomy/history  |
            |  memory + optional SQLite   |
            +-----------------------------+

   Optional: LLM provider abstraction (dpie.providers / sdk_providers)
   Data contracts: Pydantic v2 schemas (dpie.schemas)
```

## Package layout

| Path | Responsibility |
|---|---|
| `src/dpie/_version.py` | Runtime `__version__` (single source for runtime; keep `pyproject.toml` in sync). |
| `src/dpie/cli.py` | `dpie` entrypoint: `analyze`, `serve`, `agents`. |
| `src/dpie/schemas.py` | Enums and Pydantic models: `EvidenceRecord`, `AgentInput/Output`, `AnalysisRequest/Response`, orchestration/config models. |
| `src/dpie/orchestration.py` | `OrchestrationEngine`: mode selection, dependency-aware waves, optional producer parallelism, routing, timeouts, partial results, aggregation/normalization/dedup. |
| `src/dpie/agents/base.py` | `BaseAgent` contract, exports key enums, registry helpers. |
| `src/dpie/agents/registry.py` | `AgentRegistry` (register/enable/get/list). |
| `src/dpie/agents/*.py` | 11 agent implementations (triage, investigator, threat_hunter, correlator, forensics, threat_intelligence, compliance, reporter, responder, auto_responder, mitre_analyst). |
| `src/dpie/knowledge_base.py` | `SharedKnowledgeBase`/`get_knowledge_base`: evidence storage, taxonomy, investigation/execution logs; RLock, bounded in-memory retention, SQLite batch commits. |
| `src/dpie/providers.py` | LLM provider abstraction (OpenAI/Anthropic/Gemini/Ollama, mock/wrapper/factory). *Integration depth varies; treat as optional.* |
| `src/dpie/config.py` | Pydantic `Settings` (`DPIE_` env prefix, `.env` support), KB/provider/dashboard knobs. |
| `src/dpie/api/main.py` | FastAPI app, lifespan init, CORS, analysis/agent/health endpoints, `/dashboard`. |
| `src/dpie/dashboard_ui.py` | Dashboard HTML generation/rendering (served by API). |
| `src/dpie/sdk/sdk_core.py` | `DarkPatternEngine`, `AnalysisConfig`, `AnalysisResult`; sync wrappers/async engine execution. |
| `tests/` | Maintained pytest suite (schemas, agents, KB, orchestration). |
| `legacy_scripts/` | Archived ad-hoc scripts; **not maintained**. |

## Execution/data flow

1. **Input** is normalized to `AgentInput` (URL/HTML/DOM/elements, optional config, optional `previous_findings`).
2. **Engine** selects agents for the requested mode (or config) and ensures default agents are registered when needed.
3. **Agent waves** execute:
   - Independent producer agents may run in parallel when `parallel_execution=true` (bounded by `max_parallel_agents`).
   - Dependent agents that consume findings (`CORRELATOR`, `REPORTER`, `COMPLIANCE`, `THREAT_INTELLIGENCE`, `RESPONDER`, `AUTO_RESPONDER`, `MITRE_ANALYST`) run after producers with accumulated `previous_findings`.
   - Agents may emit `next_agents`; routing is bounded and enqueued at most once per agent type per run.
4. **Resilience**: per-agent timeouts/error handling can yield partial results; the engine aggregates available outputs.
5. **Aggregation**: findings are collected, deduplicated where applicable, and confidence/risk are normalized/derived (risk may be derived from confidence if missing). Results are returned as `AnalysisResponse` (API/engine) or mapped to `AnalysisResult` (SDK).
6. **Persistence/logging**: agents/engine can store evidence and logs in `SharedKnowledgeBase` (memory and optional SQLite).

## Key design choices

- **Structured contracts over chat**: agent-to-agent communication uses Pydantic models (`previous_findings`, typed outputs).
- **Registry-based modularity**: agents are pluggable and discoverable via `AgentRegistry`.
- **Graceful degradation**: missing providers/keys or agent failures should not always crash the whole analysis; partial outputs are possible.
- **Heuristic-first detection**: current implementations emphasize deterministic/heuristic analysis; treat results as assistive, not authoritative.

## Current boundaries / caveats

- Global singleton patterns (registry/KB/settings usage in places) limit multi-tenant isolation.
- LLM provider paths are not uniformly contract-tested end-to-end; real API behavior depends on keys/models/network.
- API defaults (e.g., permissive CORS) favor local/dev use; production requires hardening (auth, rate limits, CORS restrictions).
