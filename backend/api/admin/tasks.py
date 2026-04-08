"""Admin task audit API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from core.dependencies import get_task_manager, get_indexing_service, require_permission
from core.permissions import PERM_TASK_READ_ALL, PERM_TASK_CANCEL_ALL
from models.admin_task import (
    AdminTaskItem,
    AdminTaskListResponse,
    AdminTaskDetailResponse,
    AdminTaskLogsResponse,
    AdminTaskActionResponse,
)
from services.indexing_service import IndexingService
from services.task_manager import TaskManager, TaskStatus

router = APIRouter(prefix="/admin/tasks", tags=["Admin Tasks"])


def _task_to_item(task) -> AdminTaskItem:
    """Convert Task dataclass to AdminTaskItem."""
    return AdminTaskItem(
        id=task.id,
        userId=task.user_id,
        status=task.status.value,
        currentStep=task.current_step,
        totalSteps=task.total_steps,
        bestFitness=task.best_fitness,
        errorMessage=task.error_message,
        createdAt=task.created_at,
        startedAt=task.started_at,
        completedAt=task.completed_at,
    )


@router.get("", response_model=AdminTaskListResponse)
async def list_tasks(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(require_permission(PERM_TASK_READ_ALL)),
    task_manager: TaskManager = Depends(get_task_manager),
):
    """Get all tasks for admin audit (global view).

    Optional filters:
    - user_id: filter by user
    - status: filter by task status (pending/running/completed/failed/cancelled)
    """
    tasks = await task_manager.list_tasks(user_id=user_id, status=status)
    items = [_task_to_item(t) for t in tasks]
    return AdminTaskListResponse(success=True, data=items)


@router.get("/{task_id}", response_model=AdminTaskDetailResponse)
async def get_task(
    task_id: str,
    current_user: dict = Depends(require_permission(PERM_TASK_READ_ALL)),
    task_manager: TaskManager = Depends(get_task_manager),
):
    """Get task details by ID (admin view)."""
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return AdminTaskDetailResponse(success=True, data=_task_to_item(task))


@router.get("/{task_id}/logs", response_model=AdminTaskLogsResponse)
async def get_task_logs(
    task_id: str,
    mode: str = "summary",
    current_user: dict = Depends(require_permission(PERM_TASK_READ_ALL)),
    task_manager: TaskManager = Depends(get_task_manager),
    indexing_service: IndexingService = Depends(get_indexing_service),
):
    """Get task logs by ID (admin view).
    
    Args:
        task_id: Task ID
        mode: Log mode - "summary" (default) for filtered logs, "full" for all logs
    """
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Unified log retrieval: running tasks use indexing_service, completed tasks filter from task.logs
    if task.status == TaskStatus.RUNNING:
        running_logs = await indexing_service.get_task_logs(task_id, mode=mode)
        if running_logs is not None:
            return AdminTaskLogsResponse(success=True, data={"logs": running_logs})
    else:
        # For completed/failed/cancelled tasks, apply mode filtering if needed
        if mode == "summary" and task.logs:
            filtered_logs = _filter_summary_logs(task.logs)
            return AdminTaskLogsResponse(success=True, data={"logs": filtered_logs})
    
    return AdminTaskLogsResponse(success=True, data={"logs": task.logs})


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


@router.post("/{task_id}/cancel", response_model=AdminTaskActionResponse)
async def cancel_task(
    task_id: str,
    current_user: dict = Depends(require_permission(PERM_TASK_CANCEL_ALL)),
    task_manager: TaskManager = Depends(get_task_manager),
    indexing_service: IndexingService = Depends(get_indexing_service),
):
    """Cancel a task by ID (admin can cancel any task)."""
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != TaskStatus.RUNNING:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel task in {task.status.value} state",
        )
    cancelled = await indexing_service.cancel_task(task_id)
    if cancelled:
        return AdminTaskActionResponse(success=True, message="Task cancellation requested")
    raise HTTPException(status_code=500, detail="Failed to cancel task")
