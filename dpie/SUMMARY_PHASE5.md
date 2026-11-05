# DPIE Phase 5: REST API and Python SDK

## Overview
Phase 5 implements the REST API and Python SDK for the DPIE (DarkPattern Intelligence Engine) framework, enabling programmatic access to the multi-agent dark pattern detection system.

## REST API

### Base URL
`http://localhost:8000/api/v1/`

### Essential Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/agents` | GET | List available agents |
| `/agents/triage` | POST | Run triage agent only |
| `/agents/investigate` | POST | Run investigator agent only |
| `/agents/correlate` | POST | Run correlator agent only |
| `/agents/report` | POST | Run reporter agent only |
| `/analyze` | POST | Run full analysis (all agents per mode) |

### Request/Response Models

#### AnalyzeRequest
```json
{
  "url": "https://example.com",
  "html": "<html>...</html>",
  "dom_data": {...}",
  "elements": [...],
  "mode": "fast",  // fast, deep, full
  "include_report": false
}
```

#### AnalyzeResponse
```json
{
  "request_id": "unique-id",
  "status": "completed",
  "triage": {...},
  "investigator": {...},
  "correlator": {...},
  "reporter": {...},
  "all_findings": [...],
  "aggregated_confidence": 0.75,
  "aggregated_risk": 0.8,
  "execution_summary": "...",
  "total_execution_time_ms": 1250,
  "models_used": ["gpt-4o-mini"],
  "tokens_total": 1250
}
```

### Example Usage

```bash
# Health check
curl http://localhost:8000/api/v1/health

# List agents
curl http://localhost:8000/api/v1/agents

# Triage analysis
curl -X POST http://localhost:8000/api/v1/agents/triage \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","html":"<button>Free trial!</button>"}'

# Full analysis
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","mode":"deep"}'
```

### API Configuration
Set via environment variables:
- `DPIE_ENVIRONMENT`
- `DPIE_DEFAULT_PROVIDER` (openai, anthropic, google_gemini, ollama)
- `DPIE_DEFAULT_MODE` (fast, deep, full)
- `DPIE_CONFIDENCE_THRESHOLD` (0.0-1.0)
- `DPIE_API_PORT` (default: 8000)
- `DPIE_ENABLE_FALLBACK` (true/false)

## Python SDK

### Installation
```bash
pip install dpie
```

### Quick Start
```python
from dpie import DarkPatternEngine

# Initialize engine
engine = DarkPatternEngine(mode="deep")

# Analyze a webpage
result = engine.analyze({
    "url": "https://example.com",
    "elements": [
        {"element_type": "button", "element_text": "Subscribe now!", "element_selector": ".subscribe-btn"}
    ]
})

# Print findings
print(result.findings)
print(f"Confidence: {result.aggregated_confidence}")
print(f"Risk: {result.aggregated_risk}")

# Get summary
summary = engine.get_status()
print(f"Engine mode: {summary['mode']}")
print(f"Agents loaded: {summary['agents_registered']}")
```

### SDK Classes

#### DarkPatternEngine
Main entry point for developers.

```python
from dpie import DarkPatternEngine

engine = DarkPatternEngine(
    mode="deep",
    api_key="sk-...",  # Optional, for OpenAI/Anthropic/Gemini
    provider="openai"  # or "anthropic", "google_gemini", "ollama"
)
```

#### AnalysisConfig
```python
from dpie import AnalysisConfig

config = AnalysisConfig(
    mode="deep",
    include_report=True,
    include_evidence=True,
    confidence_threshold=0.5
)
```

#### AnalysisResult
```python
from dpie import AnalysisResult

result = engine.analyze(data, config=config)

# Access results
print(result.aggregated_confidence)
print(result.all_findings)
print(result.report)  # If include_report=True
print(result.metadata)  # Report JSON/plain text
```

#### Provider Management
```python
from dpie import set_api_key, get_provider, list_providers

set_api_key("openai", "sk-...")
set_api_key("anthropic", "anthropic-...")
set_api_key("google_gemini", "AIza...")

providers_status = list_providers()
# {"openai": True, "anthropic": True, "google_gemini": True, "ollama": True}
```

### SDK Module Reference

```python
from dpie.sdk import (
    DarkPatternEngine,
    AnalysisConfig,
    AnalysisResult,
    set_api_key,
    get_provider,
    list_providers,
    DetectionStatus,
    AgentType,
    OrchestrationMode,
    EvidenceRecord,
    ReportFormat,
)
```

### SDK SDK Core (`sdk/sdk_core.py`)
- `DarkPatternEngine` class with `analyze()` method
- `AnalysisConfig` and `AnalysisResult` data models
- Provider setup and configuration

### SDK Provider Management (`sdk/sdk_providers.py`)
- `set_api_key(provider, api_key)`
- `get_api_key(provider)`
- `list_providers_status()`

## API Specification

### Endpoint Details

#### `GET /api/v1/health`
- **Response**: `HealthCheck` status OK
- **Purpose**: Quick health check for load balancers and monitoring

#### `GET /api/v1/agents`
- **Response**: List of all agents with status, configuration, and enablement status
- **Purpose**: Dashboard display and agent management

#### `POST /api/v1/agents/triage`
- **Request**: `AnalyzeRequest` (url, html, elements, mode)
- **Response**: `AgentOutput` from triage agent
- **Purpose**: Quick initial analysis without full investigation

#### `POST /api/v1/agents/investigate`
- **Request**: `AnalyzeRequest`
- **Response**: `AgentOutput` from investigator agent
- **Purpose**: Detailed dark pattern investigation

#### `POST /api/v1/agents/correlate`
- **Request**: `AnalyzeRequest`
- **Response**: `AgentOutput` from correlator agent
- **Purpose**: Combine findings and detect interaction flows

#### `POST /api/v1/agents/report`
- **Request**: `AnalyzeRequest`
- **Response**: `AgentOutput` + report content
- **Purpose**: Generate formatted reports from analysis findings

#### `POST /api/v1/analyze`
- **Request**: `AnalyzeRequest` with `mode` parameter
- **Response**: `AnalysisResponse` with all agent outputs
- **Purpose**: Complete analysis in specified execution mode

## SDK Example: Full Workflow

```python
from dpie import DarkPatternEngine, AnalysisConfig

# Initialize engine with deep mode
engine = DarkPatternEngine(mode="deep")

# Configure analysis
config = AnalysisConfig(
    mode="deep",
    include_report=True,
    include_evidence=True,
    confidence_threshold=0.5
)

# Analyze a webpage
result = engine.analyze({
    "url": "https://example.com",
    "elements": [
        {"element_type": "button", "element_text": "Subscribe now!", "element_selector": ".cta"},
        {"element_type": "input", "element_text": "Email", "element_selector": ".email-field", "element_attributes": {"type": "email"}}
    ]
}, config=config)

# Print comprehensive results
print("=== DPIE Analysis Results ===")
print(f"Overall Confidence: {result.aggregated_confidence}")
print(f"Overall Risk: {result.aggregated_risk}")
print(f"\nFindings ({len(result.all_findings)}):")
for i, f in enumerate(result.all_findings, 1):
    print(f"  {i}. {f.detected_pattern or 'unknown'}")
    print(f"     Confidence: {f.confidence_score}")
    print(f"     Risk: {f.risk_score}")
    print(f"     Text: {f.evidence_text[:80]}...")
    print(f"     Tags: {', '.join(f.tags)}")

print(f"\nReport Summary: {result.summary}")
print(f"Report JSON: {result.metadata.get('report_json', {})['patterns_detected']}")
print(f"Report Plain: {result.metadata.get('report_plain', '')[:200]}...")
```

## API Configuration via Environment

```bash
# Set API key for OpenAI
export DPIE_API_KEY="sk-..."

# Set default mode
export DPIE_DEFAULT_MODE="deep"

# Set confidence threshold
export DPIE_CONFIDENCE_THRESHOLD="0.5"

# Set port
export DPIE_API_PORT="8000"

# Enable model fallback
export DPIE_ENABLE_FALLBACK="true"

# Run the API
python -m dpie.api.run_api
# or
dpie api --host 0.0.0.0 --port 8000
```