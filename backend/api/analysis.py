"""Analysis task API routes."""

import os
import asyncio
from pathlib import Path
from typing import Optional
import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from core.dependencies import (
    get_current_user,
    get_task_manager,
    get_indexing_service,
    get_user_service,
    get_system_config_service,
)
from core.config import settings
from models.analysis import (
    AnalysisRunRequest,
    AnalysisRunResponse,
    AnalysisStatusResponse,
    AnalysisLogsResponse,
    ManualCellRequest,
    ManualCellResponse,
    ManualBatchRequest,
    ManualBatchResponse,
    GlideBatchRequest,
    GlideBatchResponse,
)
from services.task_manager import TaskManager, TaskStatus
from services.indexing_service import IndexingService
from services.file_service import FileService
from services.user_service import UserService
from services.system_config_service import SystemConfigService

router = APIRouter(prefix="/analysis", tags=["Analysis"])


def _normalize_fixed_peak_text(text: str) -> str:
    if not text:
        return ""

    normalized_lines = []
    for index, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) != 4 or any(
            not re.fullmatch(r"[+-]?\d+", part) for part in parts
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid fixed peak format on line {index}. Expected: peak_index h k l",
            )
        normalized_lines.append(" ".join(parts))

    return "\n".join(normalized_lines)


def _normalize_glide_batch_labels(request: AnalysisRunRequest) -> None:
    for index, batch in enumerate(request.params.glideBatches, start=1):
        batch.label = (batch.label or "").strip() or f"glide_{index:02d}"


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
            message="Server is at maximum job capacity. Please try again later.",
        )

    db_user = await user_service.get_user(current_user["username"])
    if db_user is None:
        return AnalysisRunResponse(success=False, message="User not found")

    limits = system_config_service.get_effective_user_limits(db_user)
    if (
        limits["effective_run_limit"] > 0
        and db_user.run_count >= limits["effective_run_limit"]
    ):
        return AnalysisRunResponse(
            success=False,
            message=f"Indexing quota reached ({db_user.run_count}/{limits['effective_run_limit']}). Please contact an administrator.",
        )

    request.params.ompThreads = min(
        max(1, request.params.ompThreads or 1),
        limits["effective_max_threads"],
    )
    if request.params.fixModeEnabled:
        request.params.fixedPeakText = _normalize_fixed_peak_text(
            request.params.fixedPeakText
        )
    else:
        request.params.fixedPeakText = ""
    _normalize_glide_batch_labels(request)
    request.params.mergeTq = max(0.0, request.params.mergeTq or 0.2)
    request.params.mergeTa = max(0.0, request.params.mergeTa or 2.0)

    data_file_path = request.dataFile.replace("\\", "/") if request.dataFile else None

    if data_file_path and not os.path.exists(data_file_path):
        potential_path = (
            Path(settings.UPLOAD_DIR)
            / current_user["username"]
            / Path(data_file_path).name
        )
        if potential_path.exists():
            data_file_path = str(potential_path)
        else:
            return AnalysisRunResponse(
                success=False, message=f"Data file not found: {data_file_path}"
            )

    if not data_file_path or not os.path.exists(data_file_path):
        return AnalysisRunResponse(
            success=False, message=f"Data file not found: {data_file_path}"
        )

    task = await task_manager.create_task(
        user_id=current_user["username"],
        data_file=data_file_path,
        params=request.params,
    )
    if db_user.id is None:
        raise HTTPException(status_code=500, detail="User id is missing")
    await user_service.increment_run_count(db_user.id)

    indexing_service = IndexingService(task_manager)

    background_tasks.add_task(
        indexing_service.run_indexing, task.id, data_file_path, request.params
    )

    return AnalysisRunResponse(success=True, data={"taskId": task.id})


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
        return AnalysisStatusResponse(success=False, message="Task not found")

    if task.user_id != current_user["username"] and current_user["role"] != "admin":
        return AnalysisStatusResponse(success=False, message="Access denied")

    if task.status == TaskStatus.RUNNING:
        running_status = await indexing_service.get_task_status(task_id)
        if running_status:
            status_data = {
                "status": running_status["status"],
                "currentGen": running_status["current_step"],
                "totalGen": running_status.get("total_steps", task.total_steps),
                "bestFitness": running_status["best_fitness"],
            }
            if running_status.get("error_message"):
                status_data["error"] = running_status["error_message"]
            return AnalysisStatusResponse(success=True, data=status_data)

    status_data = {
        "status": task.status.value,
        "currentGen": task.current_step,
        "totalGen": task.total_steps,
        "bestFitness": task.best_fitness,
    }

    if task.error_message:
        status_data["error"] = task.error_message

    return AnalysisStatusResponse(success=True, data=status_data)


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

            match = re.search(r"step (\d+)", log, re.IGNORECASE)
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
        return AnalysisLogsResponse(success=False, message="Task not found")

    if task.user_id != current_user["username"] and current_user["role"] != "admin":
        return AnalysisLogsResponse(success=False, message="Access denied")

    if task.status == TaskStatus.RUNNING:
        running_logs = await indexing_service.get_task_logs(task_id, mode=mode)
        if running_logs is not None:
            return AnalysisLogsResponse(success=True, data={"logs": running_logs})

    if mode == "summary" and task.logs:
        return AnalysisLogsResponse(
            success=True, data={"logs": _filter_summary_logs(task.logs)}
        )

    return AnalysisLogsResponse(success=True, data={"logs": task.logs})


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

    return {
        "success": False,
        "message": f"Cannot cancel task in {task.status.value} state",
    }


@router.post("/manual-fullmiller", response_model=ManualCellResponse)
async def manual_fullmiller(
    request: ManualCellRequest,
    current_user: dict = Depends(get_current_user),
    task_manager: TaskManager = Depends(get_task_manager),
):
    indexing_service = IndexingService(task_manager)
    try:
        result = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: indexing_service.run_manual_fullmiller(
                a=request.a,
                b=request.b,
                c=request.c,
                alpha=request.alpha,
                beta=request.beta,
                gamma=request.gamma,
                wavelength=request.wavelength,
            ),
        )
        return ManualCellResponse(
            success=result.get("success", False),
            data=result.get("data"),
            message=result.get("message"),
        )
    except Exception as exc:
        return ManualCellResponse(success=False, message=str(exc))


@router.post("/manual-batch", response_model=ManualBatchResponse)
async def manual_batch_fullmiller(
    request: ManualBatchRequest,
    current_user: dict = Depends(get_current_user),
    task_manager: TaskManager = Depends(get_task_manager),
):
    indexing_service = IndexingService(task_manager)
    try:
        results = []
        for idx, group in enumerate(request.groups):
            label = group.label or f"manual_{idx + 1:02d}"
            try:
                result = await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda g=group: indexing_service.run_manual_fullmiller(
                        a=g.a,
                        b=g.b,
                        c=g.c,
                        alpha=g.alpha,
                        beta=g.beta,
                        gamma=g.gamma,
                        wavelength=g.wavelength,
                    ),
                )
                if result.get("success") and result.get("data"):
                    result["data"]["label"] = label
                results.append(result)
            except Exception as exc:
                results.append({"success": False, "message": str(exc), "label": label})

        all_success = all(r.get("success") for r in results)
        return ManualBatchResponse(
            success=all_success,
            data=results,
            message=None if all_success else "Some groups failed",
        )
    except Exception as exc:
        return ManualBatchResponse(success=False, message=str(exc))


@router.post("/glide-batch", response_model=GlideBatchResponse)
async def glide_batch_fullmiller(
    request: GlideBatchRequest,
    current_user: dict = Depends(get_current_user),
    task_manager: TaskManager = Depends(get_task_manager),
):
    indexing_service = IndexingService(task_manager)
    try:
        result = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: indexing_service.run_glide_batch(
                a=request.a,
                b=request.b,
                c=request.c,
                alpha=request.alpha,
                beta=request.beta,
                gamma=request.gamma,
                wavelength=request.wavelength,
                glide_groups=request.glideGroups,
            ),
        )
        return GlideBatchResponse(
            success=result.get("success", False),
            data=result.get("data"),
            message=result.get("message"),
        )
    except Exception as exc:
        return GlideBatchResponse(success=False, message=str(exc))
