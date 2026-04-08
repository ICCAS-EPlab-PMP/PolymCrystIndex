"""Admin dashboard API routes."""
import time

import psutil

from fastapi import APIRouter, Depends, Request

from core.dependencies import require_permission, get_user_service, get_task_manager
from core.permissions import PERM_USER_READ
from services.user_service import UserService

router = APIRouter(prefix="/admin/dashboard", tags=["Admin Dashboard"])


@router.get("")
async def get_dashboard(
    request: Request,
    current_user: dict = Depends(require_permission(PERM_USER_READ)),
    user_service: UserService = Depends(get_user_service),
    task_manager=Depends(get_task_manager),
):
    """Get admin dashboard summary data."""
    users = await user_service.list_users(include_inactive=True)
    total_users = len(users)
    active_users = sum(1 for u in users if u.is_active)

    tasks = await task_manager.list_all_tasks()
    total_tasks = len(tasks)
    running_tasks = sum(1 for t in tasks if t.status.value == "running")
    completed_tasks = sum(1 for t in tasks if t.status.value == "completed")
    failed_tasks = sum(1 for t in tasks if t.status.value == "failed")
    cancelled_tasks = sum(1 for t in tasks if t.status.value == "cancelled")

    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
    except Exception:
        cpu_percent = 0

    if cpu_percent < 50 and task_manager.running_count < task_manager.max_jobs:
        system_status = "idle"
    elif cpu_percent > 85 or task_manager.running_count >= task_manager.max_jobs:
        system_status = "full"
    else:
        system_status = "busy"

    start_time = getattr(request.app.state, 'start_time', time.time())
    uptime_seconds = int(time.time() - start_time)
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    if days > 0:
        uptime_str = f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        uptime_str = f"{hours}h {minutes}m"
    else:
        uptime_str = f"{minutes}m"

    return {
        "success": True,
        "data": {
            "totalUsers": total_users,
            "activeUsers": active_users,
            "totalTasks": total_tasks,
            "runningTasks": running_tasks,
            "completedTasks": completed_tasks,
            "failedTasks": failed_tasks,
            "cancelledTasks": cancelled_tasks,
            "systemStatus": system_status,
            "cpuPercent": cpu_percent,
            "uptime": uptime_str,
        }
    }
