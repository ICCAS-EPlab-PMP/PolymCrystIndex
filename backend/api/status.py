"""Server status API routes."""
import os
import psutil
import platform

from fastapi import APIRouter, Depends

from core.dependencies import get_current_user, get_task_manager, get_system_config_service, get_user_service
from core.config import settings

router = APIRouter(prefix="/status", tags=["Status"])


def _get_disk_info():
    """Get disk usage info cross-platform."""
    try:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        disk = psutil.disk_usage(app_dir)
        return {
            'percent': disk.percent,
            'used': round(disk.used / (1024 ** 3), 2),
            'total': round(disk.total / (1024 ** 3), 2)
        }
    except Exception:
        return {'percent': 0, 'used': 0, 'total': 0}


@router.get("")
async def get_server_status(
    current_user: dict = Depends(get_current_user),
    task_manager = Depends(get_task_manager),
    system_config_service = Depends(get_system_config_service),
    user_service = Depends(get_user_service),
):
    """Get server current status.
    
    Returns CPU usage, active jobs, max jobs, and overall status.
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
    except Exception:
        cpu_percent = 0
    
    try:
        mem = psutil.virtual_memory()
        memory_percent = mem.percent
        memory_used = round(mem.used / (1024 ** 3), 2)
        memory_total = round(mem.total / (1024 ** 3), 2)
    except Exception:
        memory_percent = 0
        memory_used = 0
        memory_total = 0
    
    try:
        disk_info = _get_disk_info()
        disk_percent = disk_info['percent']
        disk_used = disk_info['used']
        disk_total = disk_info['total']
    except Exception:
        disk_percent = 0
        disk_used = 0
        disk_total = 0
    
    active_jobs = task_manager.running_count
    max_jobs = task_manager.max_jobs
    max_omp_threads = system_config_service.get_max_omp_threads()
    current_db_user = await user_service.get_user(current_user["username"])
    limits = system_config_service.get_effective_user_limits(current_db_user) if current_db_user else {
        "effective_run_limit": 0,
        "effective_max_threads": max_omp_threads,
        "remaining_runs": -1,
        "server_max_omp_threads": max_omp_threads,
    }
    
    if cpu_percent < 50 and active_jobs < max_jobs:
        status = "idle"
    elif cpu_percent > 85 or active_jobs >= max_jobs:
        status = "full"
    else:
        status = "busy"
    
    return {
        "success": True,
        "data": {
            "cpuPercent": cpu_percent,
            "activeJobs": active_jobs,
            "maxJobs": max_jobs,
            "maxOmpThreads": limits["effective_max_threads"],
            "serverMaxOmpThreads": max_omp_threads,
            "runLimit": limits["effective_run_limit"],
            "remainingRuns": limits["remaining_runs"],
            "runCount": current_db_user.run_count if current_db_user else 0,
            "isApproved": current_db_user.is_approved if current_db_user else False,
            "status": status,
            "platform": platform.system(),
            "pythonVersion": platform.python_version(),
            "memoryPercent": memory_percent,
            "memoryUsed": memory_used,
            "memoryTotal": memory_total,
            "diskPercent": disk_percent,
            "diskUsed": disk_used,
            "diskTotal": disk_total
        }
    }


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "PolymCrystIndex API",
        "version": settings.VERSION,
        "profile": settings.APP_PROFILE,
        "frontendProfile": settings.APP_PROFILE,
        "authDisabled": settings.AUTH_DISABLED,
    }
