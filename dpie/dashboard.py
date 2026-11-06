#!/usr/bin/env python
"""DPIE Developer Dashboard

Launches the DPIE Web Dashboard / API server.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

try:
    from dpie.dashboard_ui import DASHBOARD_HTML, get_dashboard_html
except Exception:
    DASHBOARD_HTML = "<html><body>DPIE dashboard unavailable.</body></html>"
    def get_dashboard_html() -> str:
        return DASHBOARD_HTML


def main() -> None:
    try:
        import uvicorn  # type: ignore
        from dpie.api.main import app
        from dpie.config import settings
    except Exception as e:
        print("Failed to start DPIE dashboard:")
        print(e)
        print("Install dependencies: pip install -e .[dashboard]")
        raise

    host = "127.0.0.1"
    port = getattr(settings, "dashboard_port", 8000) or 8000
    print("=" * 60)
    print("  DPIE Developer Dashboard")
    print(f"  Dashboard: http://{host}:{port}/dashboard")
    print(f"  API Docs:  http://{host}:{port}/docs")
    print("=" * 60)
    uvicorn.run(app, host=host, port=port, access_log=True)


if __name__ == "__main__":
    main()
