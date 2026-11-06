# Troubleshooting & Caveats

## Common issues

### `No module named pytest` / `ruff` not found
Install dev dependencies from the `dpie/` directory:

```powershell
python -m pip install -e ".[dev]"
```

### Import/path issues
- Run commands from `D:\Project\Project-1\dpie`.
- The package uses a `src/` layout; tests configure `pythonpath=["src"]`. For ad-hoc scripts, use `pip install -e .` or set `PYTHONPATH` appropriately.

### `analyze()` called inside an async event loop
`DarkPatternEngine.analyze()` is a sync wrapper. In async contexts (FastAPI handlers, notebooks with running loops), use async engine methods (e.g., `execute_*_mode` / `execute`) instead of the sync wrapper.

### API starts but returns limited/empty findings
- Ensure input contains meaningful `url`/`html`/`elements`/`dom_data`.
- Detection is **heuristic-first**; some inputs may legitimately produce few findings.
- Check `/api/v1/health` and `/api/v1/agents` for agent registration.

### Dashboard unavailable
`GET /dashboard` depends on `dpie.dashboard_ui`. If unavailable, the API returns a fallback message; use `/docs` for API interaction.

### LLM provider errors / missing keys
- Provider integrations require correct keys and network/model availability.
- Some paths may degrade to heuristic behavior; others may raise. Configure `DPIE_*` provider settings or run without LLM-dependent features.

### Legacy scripts fail
Scripts under `legacy_scripts/` are archived and may reference outdated modules/paths or external resources. Use `tests/`, `verify.py`, CLI, or SDK examples instead.

## Known caveats

- **Heuristic detection, not calibrated ML accuracy.** Do not treat outputs as definitive legal/compliance determinations.
- **Global singleton patterns** (registry/KB/settings usage) can affect multi-tenant isolation and test/process reuse.
- **Permissive CORS / no auth** in the default API configuration — development-oriented; harden before exposure.
- **Model/response mapping differences** may exist between `AnalysisResponse` (engine/API) and `AnalysisResult` (SDK); verify fields when integrating.
- **Version synchronization**: keep `src/dpie/_version.py` and `pyproject.toml` version aligned.
- **SQLite concurrency**: KB uses SQLite with WAL settings for local persistence patterns; high-concurrency/multi-process production use needs careful validation.

## Getting accurate behavior details

When docs and code disagree, trust the implementation in `src/dpie/` and OpenAPI at `/docs`, then update documentation accordingly.
