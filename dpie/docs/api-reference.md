# REST API Reference

The API is a FastAPI app (`dpie.api.main:app`), served by `dpie serve` (Uvicorn) by default on `0.0.0.0:8000`.

- OpenAPI/Swagger: `GET /docs`
- ReDoc: `GET /redoc`
- Dashboard: `GET /dashboard`

## Base URL

```text
http://<host>:<port>
```

## Authentication / CORS

- **No built-in authentication** is enforced in the current implementation.
- CORS middleware is configured permissively (`allow_origins=["*"]`, all methods/headers) for development convenience. **Restrict for production.**

## Endpoints

### `GET /api/v1/health`
Returns service health and basic stats.

**Response (`HealthCheck`)**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "agents_available": 11,
  "knowledge_base_entities": 0
}
```

### `GET /api/v1/agents`
Lists registered agents and enabled state.

**Response**
```json
{ "agents": [ { "agent_type": "...", "enabled": true, "...": "..." } ], "total": 11 }
```

### `POST /api/v1/agents/triage`
Runs only the triage agent.

### `POST /api/v1/agents/investigate`
Runs only the investigator agent.

### `POST /api/v1/agents/correlate`
Runs only the correlator agent.

### `POST /api/v1/agents/report`
Runs the reporter agent and returns a lightweight report payload alongside the agent output.

**Agent endpoint request body** (shared `AnalyzeRequest` shape): accepts `url`, `html`, `dom_data`, `elements`, `mode`, `include_report` (some agent-only routes may ignore orchestration-specific fields).

### `POST /api/v1/analyze`
Runs multi-agent analysis via `OrchestrationEngine` in the requested mode.

**Request (`AnalyzeRequest`, `dpie.api.main`)**
```json
{
  "url": "https://example.com",
  "html": "<html>...</html>",
  "dom_data": { },
  "elements": [
    { "element_type": "button", "element_text": "Accept all", "element_selector": "#accept" }
  ],
  "mode": "deep",
  "include_report": false
}
```

Fields:
- `url` *(string, optional)*
- `html` *(string, optional)*
- `dom_data` *(object, optional)*
- `elements` *(array of objects, optional)*
- `mode` *(enum: `fast` | `deep` | `full`, default `fast`)*
- `include_report` *(bool, default `false`)*

**Response:** `AnalysisResponse` (Pydantic model from `dpie.schemas`). Key fields:
- `request_id`, `status`
- per-agent outputs: `triage`, `investigator`, `correlator`, `reporter`, `threat_hunter`, `forensics`, `compliance`, `threat_intelligence`, `responder`, `auto_responder`, `mitre_analyst`
- `all_findings` (list of `EvidenceRecord`)
- `aggregated_confidence`, `aggregated_risk`
- `execution_summary`, `total_execution_time_ms`, `models_used`, `tokens_total`
- optional `report`

### `GET /dashboard`
Serves the interactive developer dashboard HTML (if `dpie.dashboard_ui` is available); falls back to a simple message linking to `/docs`.

## Example (PowerShell)

```powershell
$body = @{
  url = 'https://example.com'
  mode = 'deep'
  elements = @(@{ element_type='button'; element_text='No thanks, I hate saving money'; element_selector='.decline' })
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/api/v1/analyze' -ContentType 'application/json' -Body $body
```

## Notes / limitations

- The API registers default agents at startup/import paths to ensure endpoints function; registry/KB are process-level components.
- Request-level controls such as per-request parallelism/agent selection are **not** fully exposed in the current `AnalyzeRequest` model; extend `api/main.py` + schemas/config + tests if needed.
- For production, add auth, rate limiting, stricter CORS, request size limits, and observability.
