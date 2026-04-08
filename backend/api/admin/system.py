"""Admin system runtime configuration API routes."""
from fastapi import APIRouter, Depends

from core.dependencies import require_permission, get_system_config_service, get_task_manager
from core.permissions import PERM_SYSTEM_READ, PERM_SYSTEM_WRITE
from models.system_config import (
    RuntimeConfigResponse,
    RuntimeConfigUpdateRequest,
    RuntimeConfigUpdateResponse,
    RuntimeConfigData,
)
from services.system_config_service import SystemConfigService
from services.task_manager import TaskManager

router = APIRouter(prefix="/admin/system", tags=["Admin System"])


@router.get("/runtime-config", response_model=RuntimeConfigResponse)
async def get_runtime_config(
    current_user: dict = Depends(require_permission(PERM_SYSTEM_READ)),
    system_config_service: SystemConfigService = Depends(get_system_config_service),
):
    config = system_config_service.get_runtime_config()
    return RuntimeConfigResponse(
        success=True,
        data=RuntimeConfigData(
            maxJobs=config["max_jobs"],
            maxOmpThreads=config["max_omp_threads"],
            defaultUserRunLimit=config["default_user_run_limit"],
            defaultUserMaxThreads=config["default_user_max_threads"],
            approvedUserRunLimit=config["approved_user_run_limit"],
            approvedUserMaxThreads=config["approved_user_max_threads"],
            cpuCount=config["cpu_count"],
            updatedAt=config.get("updated_at"),
            updatedBy=config.get("updated_by"),
        ),
    )


@router.put("/runtime-config", response_model=RuntimeConfigUpdateResponse)
async def update_runtime_config(
    request: RuntimeConfigUpdateRequest,
    current_user: dict = Depends(require_permission(PERM_SYSTEM_WRITE)),
    system_config_service: SystemConfigService = Depends(get_system_config_service),
    task_manager: TaskManager = Depends(get_task_manager),
):
    operator = current_user.get("username", "admin")
    config = system_config_service.update_runtime_config(
        max_jobs=request.maxJobs,
        max_omp_threads=request.maxOmpThreads,
        default_user_run_limit=request.defaultUserRunLimit,
        default_user_max_threads=request.defaultUserMaxThreads,
        approved_user_run_limit=request.approvedUserRunLimit,
        approved_user_max_threads=request.approvedUserMaxThreads,
        operator=operator,
    )
    task_manager.set_max_jobs(config["max_jobs"])
    return RuntimeConfigUpdateResponse(
        success=True,
        data=RuntimeConfigData(
            maxJobs=config["max_jobs"],
            maxOmpThreads=config["max_omp_threads"],
            defaultUserRunLimit=config["default_user_run_limit"],
            defaultUserMaxThreads=config["default_user_max_threads"],
            approvedUserRunLimit=config["approved_user_run_limit"],
            approvedUserMaxThreads=config["approved_user_max_threads"],
            cpuCount=config["cpu_count"],
            updatedAt=config.get("updated_at"),
            updatedBy=config.get("updated_by"),
        ),
    )
