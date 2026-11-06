# DPIE - DarkPattern Intelligence Engine

## Project Overview

DPIE is a modular, reusable Multi-Agent AI Framework for detecting, investigating,
correlating, classifying, and reporting deceptive user-interface practices and dark
patterns. It is an **independent software product**, not built specifically for any
existing browser extension or website.

### Project Vision

To create a specialized AI intelligence engine capable of detecting deceptive UI
patterns, with a modular architecture that enables use by browser extensions, web
applications, security platforms, UX auditing tools, research systems, and external
developers.

## Project Structure

```
dpie/
├── __init__.py                          # Root package helper (extends path to src/dpie)
├── pyproject.toml                       # Package configuration (src layout, dev/dashboard extras, pytest/ruff)
├── dashboard.py                         # Dashboard launcher (uses src/dpie/dashboard_ui.py)
├── SUMMARY.md                           # This document
├── add_evidencerecord_access.py         # Maintenance helper (idempotent schema compatibility)
├── verify.py                            # Lightweight verifier (syntax/import/basic behavior)
├── .github/workflows/dpie-ci.yml        # CI: install dev deps, ruff, pytest
├── legacy_scripts/                      # Archived ad-hoc/root scripts (not maintained tests)
│
├── src/dpie/                            # Core package (authoritative implementation)
│   ├── __init__.py
│   ├── config.py
│   ├── schemas.py
│   ├── providers.py
│   ├── knowledge_base.py
│   ├── orchestration.py
│   ├── dashboard_ui.py                  # Shared dashboard HTML/UI
│   ├── cli.py
│   ├── agents/                          # Specialized agents
│   ├── api/                             # FastAPI app (lifespan init)
│   └── sdk/                             # Python SDK (DarkPatternEngine, providers)
│
└── tests/                               # Maintained test suite (pytest/unittest-compatible)
    ├── test_agents.py
    ├── test_schemas.py
    ├── test_knowledge_base.py
    └── test_orchestration.py
```

## Agent Architecture

### 11 Specialized Agents (Phase 2+)

| Agent | Type | Key Features |
|-------|------|-------------|
| **TriageAgent** | `AgentType.TRIAGE` | Fast screening, routing, minimal LLM calls |
| **InvestigatorAgent** | `AgentType.INVESTIGATOR` | Detailed DOM analysis, 5 pattern categories |
| **CorrelatorAgent** | `AgentType.CORRELATOR` | Finding combination, risk scoring, interaction flows |
| **ReporterAgent** | `AgentType.REPORTER` | JSON + plain-text reports, recommendations |
| **ThreatHunterAgent** | `AgentType.THREAT_HUNTER` | Subtle patterns (low contrast, hidden fields, pre-checked) |
| **ForensicsAgent** | `AgentType.FORENSICS` | Evidence preservation with hashes/snapshots |
| **ThreatIntelligenceAgent** | `AgentType.THREAT_INTELLIGENCE` | Known pattern verification vs hypotheses |
| **ComplianceAgent** | `AgentType.COMPLIANCE` | GDPR/CCPA/General rule mappings |
| **ResponderAgent** | `AgentType.RESPONDER` | Remediation recommendations + authorization |
| **AutoResponderAgent** | `AgentType.AUTO_RESPONDER` | Workflow coordination + safety policies |
| **MitreAnalystAgent** | `AgentType.MITRE_ANALYST` | MITRE ATT&CK technique mappings (optional) |

### Supported Dark Pattern Categories

- **Interface Interference** - Elements that distract or mislead
- **Obstruction** - Barriers to user goals (confirmshaming, hard to cancel)
- **Sneaking** - Hidden information, bait-and-switch, hidden costs
- **Forced Action** - Actions forced without reasonable alternatives
- **Nagging** - Excessive repeated prompts

### Execution Modes (OrchestrationEngine)

| Mode | Default agents (configurable) | Description |
|------|-------------------------------|-------------|
| **FAST** | Triage | Quick screening |
| **DEEP** | Triage + Investigator + Correlator | Deeper analysis |
| **FULL** | Triage, Investigator, Threat Hunter, Correlator, Forensics, Compliance, Reporter | Broader analysis/reporting set |

Execution is dependency-aware: independent **producer** agents may run in parallel when `OrchestrationConfiguration.parallel_execution=true` (bounded by `max_parallel_agents`); agents that primarily consume `previous_findings` run after producers with accumulated findings. If an agent returns `next_agents` and follow-up is indicated, eligible agents can be enqueued **once per run** (bounded). All agents still run with timeouts and partial-result handling.

### Core Data Models (Pydantic Schemas)

- `EvidenceRecord` - Structured evidence with confidence/risk scores
- `DarkPatternCategory` - 5 core categories with subcategories
- `AgentType` - 11 agent types
- `AgentStatus` - PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
- `ReportFormat` - JSON, MARKDOWN, PLAIN_TEXT, HTML
- `OrchestrationMode` - FAST, DEEP, FULL
- `DetectionStatus` - PASSED, DETECTED, UNCERTAIN

## Key Features

### 1. LLM Provider Abstraction (Phase 1)
- OpenAI (GPT-4o, GPT-4o-mini)
- Anthropic (Claude 3 Opus/Sonnet/Haiku)
- Google Gemini (1.5 Flash/Pro)
- Ollama (local models)
- Provider fallback and mock mode for testing
- Configurable per-agent with environment-based API keys

### 2. Shared Knowledge Base (Phase 1)
- Central in-memory/SQLite store
- Evidence storage, retrieval, update, deletion
- Taxonomy management with default dark pattern categories
- Investigation history logging
- Agent execution tracking
- Search by pattern, element, confidence
- Snapshot import/export

### 3. Agent Orchestration (Phase 4)
- Three execution modes: FAST/DEEP/FULL (default agent sets)
- Dependency-aware execution with optional bounded parallelism for producer agents
- `previous_findings` propagation and bounded `next_agents` enqueueing (once per run)
- Configurable timeouts (default 60s)
- Partial results when agents fail
- Finding deduplication and confidence/risk normalization (risk derived when missing)
- Aggregated confidence and risk metrics
- Optional agent selection via `selected_agents`

### 4. Detection Taxonomy (Established Research)

Based on established dark pattern research:

| Category | Code | Description | Severity |
|----------|------|-------------|----------|
| Interface Interference | ii | Elements that distract/mislead | medium (0.6) |
| Obstruction | ob | Barriers to user goals | high (0.7) |
| Sneaking | sn | Hidden/deceptive info | medium (0.65) |
| Forced Action | fa | Forced actions without alternatives | high (0.8) |
| Nagging | na | Excessive repeated prompts | low (0.5) |

### 5. REST API (Phase 5)

Endpoints (FastAPI; agent registration via lifespan/init):
- `GET /api/v1/health` - Health check
- `GET /api/v1/agents` - List agents
- `POST /api/v1/agents/triage` - Triage only
- `POST /api/v1/agents/investigate` - Investigate only
- `POST /api/v1/agents/correlate` - Correlate only
- `POST /api/v1/agents/report` - Report only
- `POST /api/v1/analyze` - Analysis per selected mode
- `GET /dashboard` - Developer dashboard UI

### 6. Python SDK (Phase 5)

```python
from dpie import DarkPatternEngine

engine = DarkPatternEngine(mode="deep")
result = engine.analyze({
    "url": "https://example.com",
    "elements": [
        {"element_type": "button", "element_text": "Subscribe now!", "element_selector": ".cta"}
    ],
})
print(result.all_findings)
print(result.aggregated_confidence)
print(result.aggregated_risk)
```

`AnalysisResult` fields (current): `status`, `all_findings`, `aggregated_confidence`, `aggregated_risk`, per-agent outputs (e.g. `triage`/`investigator`/`correlator`/`reporter`/`threat_hunter`/`forensics`/`compliance`), `execution_summary`, `total_execution_time_ms`, `models_used`, `tokens_total`, `report`.

## Project Status

| Area | Status / notes |
|------|----------------|
| Core schemas, agents, KB, orchestration | Implemented; maintained tests in `tests/` |
| REST API + dashboard UI | Implemented (`/api/v1/*`, `/dashboard`, lifespan init) |
| Python SDK + CLI entrypoint | Implemented |
| Detection approach | Primarily heuristic/rule-based baseline; confidence/risk normalized (not calibrated probabilities) |
| LLM providers | Abstraction present (OpenAI/Anthropic/Gemini/Ollama); runtime behavior depends on configuration/keys and is not fully contract-tested end-to-end |

Validation (local, after fixes): `python -m pytest -q tests` → **20 passed, 0 warnings**; `python -m ruff check src tests` → **clean**; `python verify.py` → **PASS**. Ad-hoc root scripts were moved to `legacy_scripts/` (not maintained). Accuracy/precision-recall evaluation on a labeled dataset and full provider contract tests remain follow-up work.

### Installation

```bash
# from dpie/ (development)
pip install -e ".[dev]"
# optional
pip install -e ".[dashboard]"
```

## Quick Start

```python
from dpie import DarkPatternEngine

engine = DarkPatternEngine(mode="deep")
result = engine.analyze({
    "url": "https://example.com",
    "elements": [
        {"element_type": "button", "element_text": "Subscribe now!", "element_selector": ".cta"}
    ]
})

print([f.detected_pattern for f in result.all_findings])
print(result.aggregated_confidence)
print(result.aggregated_risk)
```

## Testing & Quality (maintained)

```bash
python -m pytest -q tests
python -m ruff check src tests
python verify.py
```

## Licensing

DPIE is open source software available under a permissive license for commercial and non-commercial use. See LICENSE for details.

## Contact

For questions, contributions, or support, please refer to the project documentation or contact the maintainers.

---
*DPIE - DarkPattern Intelligence Engine v0.1.0*
*An independent software product for dark pattern detection and analysis.*