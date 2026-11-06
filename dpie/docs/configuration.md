# Configuration

Runtime configuration is implemented in `src/dpie/config.py` via a Pydantic `Settings` model.

## Loading behavior

- Environment prefix: **`DPIE_`** (e.g., `DPIE_DEFAULT_MODE=deep`).
- `.env` file is supported (`env_file=".env"`), UTF-8; extra env vars are ignored.
- `load_settings()` is called by key entrypoints (CLI/API/SDK initialization paths).

## Core settings (selected)

| Setting | Env var | Default | Description |
|---|---|---|---|
| `app_name` | `DPIE_APP_NAME` | `DPIE - DarkPattern Intelligence Engine` | App name |
| `app_version` | `DPIE_APP_VERSION` | `0.1.0` | App version (metadata; runtime version also comes from `src/dpie/_version.py`) |
| `environment` | `DPIE_ENVIRONMENT` | `development` | Environment label |
| `debug` | `DPIE_DEBUG` | `false` | Debug flag |
| `log_level` | `DPIE_LOG_LEVEL` | `INFO` | Logging level |
| `default_mode` | `DPIE_DEFAULT_MODE` | `deep` | Default orchestration mode |
| `orchestration_timeout` | `DPIE_ORCHESTRATION_TIMEOUT` | `60` | Orchestration timeout (seconds) |
| `confidence_threshold` | `DPIE_CONFIDENCE_THRESHOLD` | `0.5` | Confidence threshold (0–1) |
| `api_host` | `DPIE_API_HOST` | `0.0.0.0` | API bind host |
| `api_port` | `DPIE_API_PORT` | `8000` | API port |

## LLM/provider keys (optional)

Provider usage depends on implementation path and available keys. Common env vars supported by settings:

- `DPIE_OPENAI_API_KEY`
- `DPIE_ANTHROPIC_API_KEY`
- `DPIE_GOOGLE_API_KEY`
- `DPIE_OLLAMA_BASE_URL` (default `http://localhost:11434`)
- `DPIE_DEFAULT_LLM_PROVIDER` (default `openai`)
- `DPIE_DEFAULT_LLM_MODEL` (optional)

> Do not commit secrets. Prefer environment variables or a local `.env` excluded from source control. LLM integrations may fall back to heuristic behavior or fail if misconfigured; test with `verify.py`/pytest.

## Knowledge base / runtime knobs

| Setting | Env var | Default | Description |
|---|---|---|---|
| `kb_max_evidence` | `DPIE_KB_MAX_EVIDENCE` | `5000` | Max evidence records kept in memory (`0` = unbounded) |
| `kb_max_history` | `DPIE_KB_MAX_HISTORY` | `2000` | Max investigation/execution log entries in memory (`0` = unbounded) |
| `kb_batch_commits` | `DPIE_KB_BATCH_COMMITS` | `true` | Batch SQLite commits for write bursts |
| `provider_max_retries` | `DPIE_PROVIDER_MAX_RETRIES` | `2` | Max LLM provider retries (0–5) |
| `provider_retry_backoff_s` | `DPIE_PROVIDER_RETRY_BACKOFF_S` | `0.5` | Base retry backoff seconds |
| `api_enable_dashboard` | `DPIE_API_ENABLE_DASHBOARD` | `true` | Serve `/dashboard` (where implemented) |

## Example `.env`

```dotenv
DPIE_ENVIRONMENT=development
DPIE_DEFAULT_MODE=deep
DPIE_API_HOST=127.0.0.1
DPIE_API_PORT=8000
DPIE_LOG_LEVEL=INFO
# DPIE_OPENAI_API_KEY=...
# DPIE_OLLAMA_BASE_URL=http://localhost:11434
DPIE_KB_MAX_EVIDENCE=5000
DPIE_KB_MAX_HISTORY=2000
```

## Versioning note

- Runtime package version is defined in `src/dpie/_version.py` and exported via `dpie.__version__`.
- `pyproject.toml` also declares `version`; **keep them synchronized** for build/distribution metadata.
