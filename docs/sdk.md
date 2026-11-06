# Python SDK

The Python SDK provides a programmatic interface over the DPIE orchestration engine.

## Import

```python
from dpie import DarkPatternEngine, __version__
# also available: DarkPatternAgent, AgentRegistry, get_agent_registry
```

## `DarkPatternEngine`

`dpie.sdk.sdk_core.DarkPatternEngine` (exported from `dpie`).

### Constructor

```python
DarkPatternEngine(
    mode: str = "fast",                # "fast" | "deep" | "full"
    api_key: Optional[str] = None,      # optional LLM provider key (if used)
    provider: str = "openai",           # provider name hint
    model: Optional[str] = None,        # model override hint
    knowledge_base: Optional[Any] = None,
)
```

Notes:
- Loads settings (`load_settings()`).
- Initializes/selects an orchestration mode and attempts to configure provider integration; if provider init fails, the engine may fall back to heuristic-only behavior (implementation-dependent). Do not assume live LLM calls without valid keys/config.

### Synchronous analysis

```python
result = engine.analyze({
    "url": "https://example.com",
    "html": "<html>...</html>",          # optional
    "elements": [                         # optional structured elements
        {"element_type": "button", "element_text": "...", "element_selector": "..."}
    ],
    "dom_data": {...},                    # optional
})
```

- `analyze(input_data: Union[Dict, Any], config: Optional[AnalysisConfig]=None) -> AnalysisResult`
- **Sync wrapper**: runs the async engine via `asyncio.run(...)` when no loop is running. **Do not call from inside a running event loop**; use the engine’s async `execute_*_mode`/`execute(...)` methods instead.

### Mode helpers (async-oriented engine methods)

The underlying orchestration exposes async execution paths (e.g., `execute_fast_mode`/`execute_deep_mode`/`execute_full_mode` and/or `execute` with mode). Use these in async applications.

### `AnalysisConfig` (SDK)

```python
from dpie.sdk.sdk_core import AnalysisConfig
from dpie.schemas import OrchestrationMode

cfg = AnalysisConfig(
    mode=OrchestrationMode.DEEP,
    include_report=False,
    include_evidence=True,
    agents=None,                 # optional override
    confidence_threshold=0.5,
    model=None,
    fallback_provider=None,
)
```

### `AnalysisResult` (SDK)

Returned by `engine.analyze(...)` (Pydantic model). Key fields:

- `request_id`, `status`
- per-agent outputs (dicts, optional): `triage`, `investigator`, `correlator`, `reporter`, `threat_hunter`, `forensics`, `compliance`
- `all_findings` *(list of dicts)*
- `aggregated_confidence`, `aggregated_risk`
- `execution_summary`, `total_execution_time_ms`
- `models_used`, `tokens_total`
- `report` *(optional dict when requested/supported)*

> Some agent outputs present in the engine/API (`AnalysisResponse`) may not all be mapped as first-class fields on `AnalysisResult`; check `result.all_findings` and returned payloads for completeness. Treat SDK/API model shapes as implementation-defined and consult `sdk_core.py`/`schemas.py` when integrating tightly.

## Minimal example

```python
from dpie import DarkPatternEngine

engine = DarkPatternEngine(mode="fast")
result = engine.analyze({
    "url": "https://example.com",
    "elements": [{"element_type": "checkbox", "element_text": "I agree to receive marketing (preselected)", "element_selector": "#mkt"}],
})
if result.status == "completed":
    for f in result.all_findings:
        print(f.get("detected_pattern"), f.get("confidence_score"))
```

## Error handling guidance

- Catch exceptions around `analyze()` for configuration/provider/runtime issues.
- Inspect `result.status`, summaries, and finding confidences; absence of findings is not proof of absence.
- For async apps, prefer async engine APIs to avoid event-loop conflicts.
