# Agents & Orchestration

## Agent contract

Agents live under `src/dpie/agents/` and follow a common base contract (`BaseAgent` in `agents/base.py`). Core types come from `dpie.schemas`:

- `AgentType` — agent identity enum (e.g., `triage`, `investigator`, `correlator`, ...).
- `AgentStatus` — execution status.
- `AgentInput` — URL/HTML/DOM/elements, optional `previous_findings`, config/context.
- `AgentOutput` — findings (`EvidenceRecord` list), summary, confidence/risk, timing/model metadata, `next_agents` routing hints.

`AgentRegistry` (`agents/registry.py`) provides registration, enablement, and lookup (`get`/`get_agent`/`is_agent_enabled`/`get_all_agents`/`get_enabled_agents`/listing helpers).

## Registered agent types (default set)

The framework registers default implementations for:

| AgentType | Typical role |
|---|---|
| `TRIAGE` | Fast initial screening / prioritization |
| `INVESTIGATOR` | Deeper element/pattern investigation |
| `THREAT_HUNTER` | Broader threat-seeking heuristics |
| `CORRELATOR` | Correlates findings across agents/evidence |
| `FORENSICS` | Evidence/trace-oriented analysis |
| `THREAT_INTELLIGENCE` | Threat-intel style enrichment/context |
| `COMPLIANCE` | Compliance/policy-oriented mapping (heuristic) |
| `REPORTER` | Summarization/report-oriented output |
| `RESPONDER` | Response recommendations |
| `AUTO_RESPONDER` | Automated response suggestions/actions (advisory) |
| `MITRE_ANALYST` | MITRE-style mapping/analysis (best-effort) |

> Implementation maturity varies; many agents are heuristic-first. Outputs should be validated.

## Orchestration engine

`OrchestrationEngine` (`src/dpie/orchestration.py`) coordinates agent execution.

### Modes (default agent sets)

| Mode | Default agents (base mapping) |
|---|---|
| `fast` | `triage` |
| `deep` | `triage`, `investigator`, `correlator` |
| `full` | `triage`, `investigator`, `threat_hunter`, `correlator`, `forensics`, `compliance`, `reporter` |

### Dependency-aware execution

- Agents that **consume prior findings** are treated as dependents and run after producers with accumulated `previous_findings`:
  - `CORRELATOR`, `REPORTER`, `COMPLIANCE`, `THREAT_INTELLIGENCE`, `RESPONDER`, `AUTO_RESPONDER`, `MITRE_ANALYST`
- Independent producer agents may execute earlier; with parallelism enabled, producers can run concurrently (bounded).

### Parallelism

Controlled by `OrchestrationConfiguration` (and engine config paths):

- `parallel_execution: bool` — enable bounded parallelism for independent producer agents.
- `max_parallel_agents: int` — concurrency bound.

Dependents still respect ordering relative to the findings they consume.

### Routing (`next_agents`)

- An agent may emit `next_agents` to request follow-up agents.
- Routing is **bounded** and each agent type is enqueued **at most once per run** (prevents infinite/duplicate loops).

### Resilience and aggregation

- **Timeouts/error handling**: agent failures/timeouts are handled to allow **partial results** when possible.
- **Findings aggregation**: collects findings across agents.
- **Deduplication**: removes duplicate findings where applicable.
- **Normalization**: confidence/risk values are normalized; risk may be **derived from confidence** if missing.
- **Metadata**: execution timing/model/token fields are propagated/aggregated as available.

## `AnalysisResponse` fields

The engine/API return `AnalysisResponse` (see `schemas.py`) including:

- `request_id`, `status`, `all_findings`
- per-agent outputs (e.g., `triage`, `investigator`, `correlator`, `reporter`, `threat_hunter`, `forensics`, `compliance`, `threat_intelligence`, `responder`, `auto_responder`, `mitre_analyst`)
- `aggregated_confidence`, `aggregated_risk`
- `execution_summary`, `total_execution_time_ms`
- `models_used`, `tokens_total`, optional `report`

## Extending with a custom agent

1. Implement an agent subclassing `BaseAgent` with the required `agent_type` and `analyze(AgentInput) -> AgentOutput` behavior.
2. Register it in the `AgentRegistry` (and ensure it’s enabled) before orchestration.
3. Keep outputs **structured** (valid `EvidenceRecord`/scores) and handle missing context defensively.
4. Add/extend tests under `tests/` and run `pytest` + `ruff`.

## Practical notes

- Use `fast` for quick screening, `deep` for investigation+correlation, `full` for broader multi-agent analysis.
- Prefer explicit timeouts/config in production-like runs.
- Validate findings before downstream enforcement/compliance actions.
