# Development Guide

## Environment

- **Python:** 3.11+
- **Project root (commands below):** `D:\Project\Project-1\dpie`
- **Layout:** `src/dpie` (tests use `pythonpath=["src"]`)
- **OS note:** development environment may be Windows/PowerShell; commands shown are cross-platform where possible.

## Setup

```powershell
cd D:\Project\Project-1\dpie
python -m pip install -e ".[dev]"
```

Optional:

```powershell
python -m pip install -e ".[dashboard]"
```

## Quality checks

```powershell
python -m ruff check src tests
python -m pytest -q tests
python verify.py
```

`verify.py` performs lightweight syntax/import and basic behavior checks (includes a fast analysis smoke). Treat it as a fast sanity check, not a substitute for the full test suite.

## Test suite

Maintained tests (`tests/`): `test_agents.py`, `test_schemas.py`, `test_knowledge_base.py`, `test_orchestration.py`.

`legacy_scripts/` contains archived ad-hoc scripts (some require old import paths or external deps); they are **not** part of CI/maintained test runs.

## Linting/formatting

- **Ruff** configured in `pyproject.toml` (`target-version = "py311"`, `line-length = 120`, rules `E,F`, `E501` ignored).
- CI runs `ruff check src tests`.

## CI

`.github/workflows/dpie-ci.yml` installs `.[dev]` and runs lint/tests (and/or verification steps as configured). Keep CI green before merging.

## Project conventions

- Prefer **structured Pydantic models** for agent I/O and evidence.
- Keep agent behavior **defensive** (missing fields, partial context, timeouts).
- Preserve **backward-compatible** response fields where practical (API/SDK consumers).
- Avoid hardcoding secrets; use `DPIE_` settings/env vars.
- When changing orchestration semantics, update `docs/agents-and-orchestration.md` and `SUMMARY.md`.

## Adding/maintaining agents

1. Implement under `src/dpie/agents/` following `BaseAgent`.
2. Register in `AgentRegistry` / default registration path as appropriate.
3. Ensure `AgentType`/output fields align with `schemas.py` and aggregation logic.
4. Add tests and validate with `fast/deep/full` smoke runs if relevant.

## Release/versioning

- Update `src/dpie/_version.py` (runtime `__version__`).
- Keep `pyproject.toml` `[project].version` in sync for packaging.
- Update docs (`README`, `SUMMARY.md`, changelog if added) to reflect user-visible behavior.

## Known gaps (good next contributions)

- API request options for parallelism/agent selection + auth/CORS/rate-limit hardening.
- Provider retries/backoff standardization, schema-validated parsing, contract tests, prompt-injection/secret hygiene.
- Labeled evaluation dataset + precision/recall/F1 benchmarking.
- `mypy`/`pyright` typing in CI, `py.typed`.
- Multi-tenant isolation for registry/KB/settings contexts.
