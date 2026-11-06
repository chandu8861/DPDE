# Data Models

Core data contracts live in `src/dpie/schemas.py` (Pydantic v2). These models enable structured agent communication and stable API/SDK responses.

## Enums

| Enum | Values (conceptual) | Purpose |
|---|---|---|
| `DetectionStatus` | `passed`, `detected`, `uncertain` | Detection outcome |
| `AgentType` | `triage`, `investigator`, `threat_hunter`, `correlator`, `forensics`, `threat_intelligence`, `compliance`, `reporter`, `responder`, `auto_responder`, `mitre_analyst` | Agent identity/routing |
| `AgentStatus` | `pending`, `running`, `completed`, `failed`, `cancelled`, `skipped` | Execution status |
| `ReportFormat` | `json`, `markdown`, `plain_text`, `html` | Report formatting |
| `OrchestrationMode` | `fast`, `deep`, `full` | Engine execution mode |

## `EvidenceRecord`

Represents a structured finding/evidence item produced by an agent.

Key fields (see `schemas.py` for full definition/defaults/validators):
- Identity/source: `evidence_id`, `source_agent`, `source_element_id`, `source_url`, timestamps
- Element context: `element_type`, `element_selector`, `element_text`, `element_attributes`
- Detection: `detected_pattern`, `detected_subcategory`, `confidence_score` (0–1), `evidence_text`, `visual_properties`, `interaction_context`
- Risk/meta: `risk_score` (0–1, optional), `tags`, `metadata`, `verified`, `verification_notes`

Compatibility helpers: dict-like `__getitem__`/`get` are provided for some integrations/tests.

## `AgentInput`

Input to an agent/analysis run:
- `url`, `html`, `dom_data`, `elements`, `screenshot_metadata`
- `investigation_id`, `previous_findings: Optional[List[EvidenceRecord]]`, `configuration`
- `timestamp`

## `AgentOutput`

Output from an agent:
- `agent_type`, `status`
- `findings: List[EvidenceRecord]`, `summary`
- `overall_confidence` (0–1), `overall_risk` (optional 0–1)
- `execution_time_ms`, `model_used`, `tokens_consumed`
- `next_agents` (routing hints), `requires_followup`

## `AnalysisRequest` / API `AnalyzeRequest`

`schemas.AnalysisRequest` extends `AgentInput` with `mode`, `include_report`, `include_evidence`.

The REST API defines its own `AnalyzeRequest` model in `dpie.api.main` (URL/HTML/DOM/elements, `mode`, `include_report`). Treat the **API model** as the wire contract for `/api/v1/analyze` and check `schemas.py`/OpenAPI (`/docs`) for the authoritative runtime shape.

## `AnalysisResponse`

Aggregated engine/API response (Pydantic model): `request_id`, `status`, per-agent outputs, `all_findings`, `aggregated_confidence`/`aggregated_risk`, execution/model metadata, optional `report`.

## Configuration models

- `AgentConfiguration` — per-agent enablement/threshold/timeout/model/custom params.
- `OrchestrationConfiguration` — mode, enabled agents, `parallel_execution`, `max_parallel_agents`, confidence/timeout settings.

## Validation notes

- Confidence/risk fields are validated to the `[0.0, 1.0]` range.
- Models are rebuilt (`model_rebuild()`) in `schemas.py` to resolve forward/cross references (Pydantic v2).
- When consuming outputs, prefer typed access; dict-like evidence access exists for compatibility but typed fields are canonical.
