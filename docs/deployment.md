# Deployment

## Local (development)

From `D:\Project\Project-1\dpie`:

```powershell
python -m pip install -e ".[dev]"
python verify.py
dpie serve --host 127.0.0.1 --port 8000
```

Endpoints: `/docs`, `/dashboard`, `/api/v1/health`.

## Docker

The repository includes a `Dockerfile` that installs the package and runs:

```text
dpie serve --host 0.0.0.0 --port 8000
```

Build and run (example):

```powershell
docker build -t dpie:0.1.0 .
docker run --rm -p 8000:8000 `
  -e DPIE_ENVIRONMENT=production `
  -e DPIE_DEFAULT_MODE=deep `
  dpie:0.1.0
```

## Docker Compose

`docker-compose.yml` defines a `dpie-api` service with port mapping, environment variables, a named volume (`dpie_data`), restart policy, and a healthcheck against `/api/v1/health`.

```powershell
docker compose up --build
```

Pass provider keys via environment variables / shell secrets as needed (do not hardcode).

## Production considerations

DPIE v0.1.0 is suitable for controlled/internal use with additional hardening:

- **Authentication & authorization**: not built in; place behind an authenticated gateway or add API auth.
- **CORS**: currently permissive in `api/main.py`; restrict `allow_origins`/methods/headers.
- **Rate limiting & abuse protection**: add middleware/reverse-proxy limits (analysis can be compute-intensive).
- **Request validation/limits**: constrain payload sizes (HTML/DOM/elements) and timeouts.
- **Secrets management**: inject LLM keys via secure env/secret stores; never log secrets.
- **Multi-tenancy/isolation**: registry/KB/settings patterns may be process-global in places; use separate processes/instances or implement per-tenant isolation.
- **Observability**: structured logging, metrics, tracing, and audit logs for findings/actions.
- **Persistence**: configure SQLite path/volume if durable evidence/history is required; understand retention bounds (`kb_max_*`).
- **LLM dependencies**: network/model availability affects LLM-backed behavior; validate fallback/timeout behavior.

## Health checks

- HTTP: `GET /api/v1/health` (used by container healthcheck patterns).
- CLI/API smoke: `python verify.py` and `pytest -q tests` before deployment.
