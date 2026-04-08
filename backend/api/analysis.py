"""Analysis task API routes."""
import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from core.dependencies import get_current_user, get_task_manager, get_indexing_service, get_user_service, get_system_config_service
from models.analysis import (
    AnalysisRunRequest,
    AnalysisRunResponse,
    AnalysisStatusResponse,
    AnalysisLogsResponse,
)
from services.task_manager import TaskManager, TaskStatus
from services.indexing_service import IndexingService
from services.file_service import FileService
from services.user_service import UserService
from services.system_config_service import SystemConfigService

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("/run", response_model=AnalysisRunResponse)
async def run_analysis(
    request: AnalysisRunRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    task_manager: TaskManager = Depends(get_task_manager),
    user_service: UserService = Depends(get_user_service),
    system_config_service: SystemConfigService = Depends(get_system_config_service),
):
    """Start a new analysis task.
    
    Creates a new indexing task and returns task ID for status tracking.
    """
    if not await task_manager.can_start_new_job():
        return AnalysisRunResponse(
            success=False,
            message="Server is at maximum job capacity. Please try again later."
        )

    db_user = await user_service.get_user(current_user["username"])
    if db_user is None:
        return AnalysisRunResponse(success=False, message="User not found")

    limits = system_config_service.get_effective_user_limits(db_user)
    if limits["effective_run_limit"] > 0 and db_user.run_count >= limits["effective_run_limit"]:
        return AnalysisRunResponse(
            success=False,
            message=f"Indexing quota reached ({db_user.run_count}/{limits['effective_run_limit']}). Please contact an administrator."
        )

    request.params.ompThreads = min(
        max(1, request.params.ompThreads or 1),
        limits["effective_max_threads"],
    )
    
    data_file_path = request.dataFile.replace('\\', '/') if request.dataFile else None
    
    if data_file_path and not os.path.exists(data_file_path):
        potential_path = f"./temp/{current_user['username']}/{data_file_path.split('/')[-1]}"
        if os.path.exists(potential_path):
            data_file_path = potential_path
        else:
            return AnalysisRunResponse(
                success=False,
                message=f"Data file not found: {data_file_path}"
            )
    
    if not data_file_path or not os.path.exists(data_file_path):
        return AnalysisRunResponse(
            success=False,
            message=f"Data file not found: {data_file_path}"
        )
    
    task = await task_manager.create_task(
        user_id=current_user["username"],
        data_file=data_file_path,
        params=request.params
    )
    await user_service.increment_run_count(db_user.id)
    
    indexing_service = IndexingService(task_manager)
    
    background_tasks.add_task(
        indexing_service.run_indexing,
        task.id,
        data_file_path,
        request.params
    )
    
    return AnalysisRunResponse(
        success=True,
        data={"taskId": task.id}
    )


@router.get("/status/{task_id}", response_model=AnalysisStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    task_manager: TaskManager = Depends(get_task_manager),
    indexing_service: IndexingService = Depends(get_indexing_service),
):
    """Get analysis task status.
    
    Returns current progress including step, fitness, and error info.
    """
    task = await task_manager.get_task(task_id)
    
    if not task:
        return AnalysisStatusResponse(
            success=False,
            message="Task not found"
        )
    
    if task.user_id != current_user["username"] and current_user["role"] != "admin":
        return AnalysisStatusResponse(
            success=False,
            message="Access denied"
        )
    
    if task.status == TaskStatus.RUNNING:
        running_status = await indexing_service.get_task_status(task_id)
        if running_status:
            status_data = {
                "status": running_status["status"],
                "currentGen": running_status["current_step"],
                "totalGen": running_status.get("total_steps", task.total_steps),
                "bestFitness": running_status["best_fitness"]
            }
            if running_status.get("error_message"):
                status_data["error"] = running_status["error_message"]
            return AnalysisStatusResponse(success=True, data=status_data)
    
    status_data = {
        "status": task.status.value,
        "currentGen": task.current_step,
        "totalGen": task.total_steps,
        "bestFitness": task.best_fitness
    }
    
    if task.error_message:
        status_data["error"] = task.error_message
    
    return AnalysisStatusResponse(
        success=True,
        data=status_data
    )


def _filter_summary_logs(logs: list) -> list:
    """Filter logs for summary mode - same logic as ProgressTracker.get_summary_logs."""
    summary_logs = []
    step_best_logs = {}
    last_error_log = ""
    
    for log in logs:
        if "[System]" in log:
            summary_logs.append(log)
        elif "[Error]" in log or "[ERROR]" in log:
            last_error_log = log
        elif "[Progress]" in log:
            if "Starting step" in log or "Completed step" in log:
                summary_logs.append(log)
        elif "[Best]" in log:
            import re
            match = re.search(r'step (\d+)', log, re.IGNORECASE)
            if match:
                step = int(match.group(1))
                step_best_logs[step] = log
        elif "[Warning]" in log:
            pass
        else:
            summary_logs.append(log)
    
    for step in sorted(step_best_logs.keys()):
        summary_logs.append(step_best_logs[step])
    
    if last_error_log:
        summary_logs.append(last_error_log)
    
    return summary_logs


@router.get("/logs/{task_id}", response_model=AnalysisLogsResponse)
async def get_task_logs(
    task_id: str,
    mode: str = "summary",
    current_user: dict = Depends(get_current_user),
    task_manager: TaskManager = Depends(get_task_manager),
    indexing_service: IndexingService = Depends(get_indexing_service),
):
    """Get analysis task logs.
    
    Args:
        task_id: Task ID
        mode: Log mode - "full" for all logs, "summary" for filtered logs
    
    Returns filtered or full log messages generated during task execution.
    """
    task = await task_manager.get_task(task_id)
    
    if not task:
        return AnalysisLogsResponse(
            success=False,
            message="Task not found"
        )
    
    if task.user_id != current_user["username"] and current_user["role"] != "admin":
        return AnalysisLogsResponse(
            success=False,
            message="Access denied"
        )
    
    if task.status == TaskStatus.RUNNING:
        running_logs = await indexing_service.get_task_logs(task_id, mode=mode)
        if running_logs is not None:
            return AnalysisLogsResponse(success=True, data={"logs": running_logs})

    if mode == "summary" and task.logs:
        return AnalysisLogsResponse(
            success=True,
            data={"logs": _filter_summary_logs(task.logs)}
        )
    
    return AnalysisLogsResponse(
        success=True,
        data={"logs": task.logs}
    )


@router.post("/cancel/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    task_manager: TaskManager = Depends(get_task_manager),
    indexing_service: IndexingService = Depends(get_indexing_service),
):
    """Cancel a running analysis task."""
    task = await task_manager.get_task(task_id)
    
    if not task:
        return {"success": False, "message": "Task not found"}
    
    if task.user_id != current_user["username"] and current_user["role"] != "admin":
        return {"success": False, "message": "Access denied"}
    
    if task.status == TaskStatus.RUNNING:
        cancelled = await indexing_service.cancel_task(task_id)
        if cancelled:
            return {"success": True, "message": "Task cancellation requested"}
        return {"success": False, "message": "Failed to cancel task"}
    
    return {"success": False, "message": f"Cannot cancel task in {task.status.value} state"}
