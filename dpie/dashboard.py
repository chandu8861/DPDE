#!/usr/bin/env python
"""DPIE Developer Dashboard

Launches the DPIE Web Dashboard.
Automatically serves via FastAPI (default) or Flask (if available).
"""

import sys
from pathlib import Path

# Add src to sys.path
_src = str(Path(__file__).parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

import uvicorn
from dpie.api.main import app
from dpie.config import settings

def main():
    port = settings.dashboard_port if hasattr(settings, "dashboard_port") else 8000
    host = "127.0.0.1"
    print("=" * 60)
    print("  DPIE Developer Dashboard")
    print(f"  Access the dashboard at: http://{host}:{port}/dashboard")
    print(f"  Access Swagger API docs: http://{host}:{port}/docs")
    print("=" * 60)
    uvicorn.run(app, host=host, port=port, access_log=True)

if __name__ == "__main__":
    main()
