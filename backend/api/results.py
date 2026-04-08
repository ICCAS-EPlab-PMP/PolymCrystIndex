"""Results API routes."""
import os
import shutil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from core.dependencies import get_current_user, get_task_manager
from core.config import settings
from models.results import ResultsResponse
from services.task_manager import TaskManager
from services.indexing_service import IndexingService

router = APIRouter(prefix="/results", tags=["Results"])


@router.get("", response_model=ResultsResponse)
async def get_results(
    current_user: dict = Depends(get_current_user),
    task_manager: TaskManager = Depends(get_task_manager),
):
    """Get analysis results.
    
    Returns the best unit cell parameters, Miller indices, and quality metrics.
    """
    tasks = await task_manager.list_user_tasks(current_user["username"])
    
    if not tasks:
        return ResultsResponse(
            success=False,
            message="No results found"
        )
    
    completed_tasks = [t for t in tasks if t.status.value == "completed"]
    
    if not completed_tasks:
        return ResultsResponse(
            success=False,
            message="No completed tasks found"
        )
    
    latest_task = completed_tasks[-1]
    
    indexing_service = IndexingService(task_manager)
    results = await indexing_service.get_results(latest_task.id)
    
    if not results:
        return ResultsResponse(
            success=False,
            message="Results data not available"
        )
    
    return ResultsResponse(
        success=True,
        data=results
    )


@router.get("/download")
async def download_results(
    type: str = "zip",
    task_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    task_manager: TaskManager = Depends(get_task_manager),
):
    """Download analysis results.
    
    Args:
        type: Download type - "zip", "hdf5", "cell", or "miller"
        task_id: Optional specific task ID, uses latest if not provided
    """
    tasks = await task_manager.list_user_tasks(current_user["username"])
    
    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found")
    
    completed_tasks = [t for t in tasks if t.status.value == "completed"]
    
    if not completed_tasks:
        raise HTTPException(status_code=404, detail="No completed tasks found")
    
    if task_id:
        target_task = next((t for t in completed_tasks if t.id == task_id), None)
        if not target_task:
            raise HTTPException(status_code=404, detail="Task not found")
    else:
        target_task = completed_tasks[-1]
    
    user_id = target_task.user_id or "anonymous"
    user_result_dir = os.path.abspath(
        os.path.join(settings.USER_RESULT_DIR, user_id)
    )
    work_dir = os.path.join(user_result_dir, target_task.id)
    
    if type == "zip":
        archive_path = os.path.join(settings.RESULT_DIR, f"{target_task.id}.zip")
        
        if not os.path.exists(archive_path):
            os.makedirs(settings.RESULT_DIR, exist_ok=True)
            shutil.make_archive(
                archive_path.replace('.zip', ''),
                'zip',
                work_dir
            )
        
        return FileResponse(
            archive_path,
            media_type="application/zip",
            filename=f"results_{target_task.id}.zip"
        )
    
    elif type == "hdf5":
        hdf5_path = os.path.join(work_dir, "results.h5")
        
        if not os.path.exists(hdf5_path):
            raise HTTPException(status_code=404, detail="HDF5 file not found")
        
        return FileResponse(
            hdf5_path,
            media_type="application/x-hdf5",
            filename=f"results_{target_task.id}.h5"
        )
    
    elif type == "cell":
        cell_files = [f for f in os.listdir(work_dir) if f.startswith("cell_") and f.endswith("_annealing.txt")]
        
        if not cell_files:
            raise HTTPException(status_code=404, detail="Cell file not found")
        
        latest_cell = sorted(cell_files)[-1]
        cell_path = os.path.join(work_dir, latest_cell)
        
        return FileResponse(
            cell_path,
            media_type="text/plain",
            filename=f"cell_{target_task.id}.txt"
        )
    
    elif type == "miller":
        output_miller = os.path.join(work_dir, "outputMiller.txt")
        full_miller = os.path.join(work_dir, "FullMiller.txt")
        miller_path = output_miller if os.path.exists(output_miller) else full_miller
        
        if not os.path.exists(miller_path):
            raise HTTPException(status_code=404, detail="Miller file not found")
        
        filename = "outputMiller.txt" if os.path.exists(output_miller) else "FullMiller.txt"
        
        return FileResponse(
            miller_path,
            media_type="text/plain",
            filename=f"miller_{target_task.id}.txt"
        )
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown download type: {type}")
