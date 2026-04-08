"""API package initialization."""
from .auth import router as auth_router
from .data import router as data_router
from .analysis import router as analysis_router
from .results import router as results_router
from .visualizer import router as visualizer_router
from .status import router as status_router
from .peak_raw import router as peak_raw_router
from .peak_integrated import router as peak_integrated_router
from .admin.users import router as admin_users_router
from .admin.tasks import router as admin_tasks_router
from .admin.dashboard import router as admin_dashboard_router
from .admin.system import router as admin_system_router

__all__ = [
    "auth_router",
    "data_router",
    "analysis_router",
    "results_router",
    "visualizer_router",
    "status_router",
    "peak_raw_router",
    "peak_integrated_router",
    "admin_users_router",
    "admin_tasks_router",
    "admin_dashboard_router",
    "admin_system_router",
]
