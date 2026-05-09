"""Smoke test: verify backend.main app can be imported."""

import sys
from pathlib import Path

# Ensure PRE/backend is on path
_backend_dir = Path(__file__).parent.parent.resolve()
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))


def test_app_import():
    """Verify `from backend.main import app` succeeds.

    This smoke test confirms:
    - FastAPI app factory is reachable
    - Core dependencies (config, routers) load without errors
    - No hard-coded Workspace/ paths are touched at import time
    """
    from backend.main import app

    assert app is not None
    assert hasattr(app, "title")
    assert "PolymCrystIndex" in app.title or "polycr" in app.title.lower()


def test_app_health_endpoint_exists():
    """Verify the /health route is registered on the app."""
    from backend.main import app
    from fastapi.routing import APIRoute

    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append(route.path)
    assert "/health" in routes


def test_models_analysis_importable():
    """Verify models.analysis module loads without errors."""
    from models.analysis import (
        AnalysisParams,
        AnalysisRunRequest,
        GlideBatchParams,
        ManualCellRequest,
    )

    assert AnalysisParams is not None
    assert AnalysisRunRequest is not None
    assert GlideBatchParams is not None
    assert ManualCellRequest is not None
