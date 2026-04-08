"""Task manager for tracking analysis jobs."""
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any

from models.analysis import AnalysisParams


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents an analysis task."""
    id: str
    user_id: str
    status: TaskStatus = TaskStatus.PENDING
    params: Optional[AnalysisParams] = None
    data_file: str = ""
    input_file: str = ""
    
    current_step: int = 0
    total_steps: int = 0
    best_fitness: float = 0.0
    
    logs: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    result_data: Optional[Dict[str, Any]] = None
    
    progress_callback: Optional[Callable] = None


class TaskManager:
    """Manages analysis tasks and job scheduling."""
    
    def __init__(self, max_jobs: int = 3):
        """Initialize task manager.
        
        Args:
            max_jobs: Maximum number of concurrent jobs
        """
        self._tasks: Dict[str, Task] = {}
        self._max_jobs = max_jobs
        self._running_count = 0
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock
    
    async def create_task(
        self, 
        user_id: str, 
        data_file: str, 
        params: AnalysisParams
    ) -> Task:
        """Create a new analysis task.
        
        Args:
            user_id: User identifier
            data_file: Path to diffraction data file
            params: Analysis parameters
            
        Returns:
            Created task
        """
        task_id = f"task-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"
        
        task = Task(
            id=task_id,
            user_id=user_id,
            params=params,
            data_file=data_file,
            total_steps=params.steps
        )
        
        async with self._get_lock():
            self._tasks[task_id] = task
        
        return task
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        async with self._get_lock():
            return self._tasks.get(task_id)
    
    async def update_task_status(
        self, 
        task_id: str, 
        status: TaskStatus,
        error_message: Optional[str] = None
    ) -> None:
        """Update task status."""
        async with self._get_lock():
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = status
                if error_message:
                    task.error_message = error_message
                if status == TaskStatus.RUNNING:
                    task.started_at = time.time()
                elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    task.completed_at = time.time()
    
    async def update_task_progress(
        self,
        task_id: str,
        step: int,
        best_fitness: float,
        log_message: Optional[str] = None
    ) -> None:
        """Update task progress."""
        async with self._get_lock():
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.current_step = step
                task.best_fitness = best_fitness
                if log_message:
                    task.logs.append(log_message)
    
    async def set_task_result(self, task_id: str, result_data: Dict[str, Any]) -> None:
        """Set task result data."""
        async with self._get_lock():
            if task_id in self._tasks:
                self._tasks[task_id].result_data = result_data
    
    async def list_user_tasks(self, user_id: str) -> List[Task]:
        """List all tasks for a user."""
        async with self._get_lock():
            return [t for t in self._tasks.values() if t.user_id == user_id]

    async def list_all_tasks(self) -> List[Task]:
        """List all tasks for admin use. Returns tasks sorted by created_at DESC."""
        async with self._get_lock():
            tasks = list(self._tasks.values())
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks

    async def list_tasks(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Task]:
        """List tasks with optional filters for admin use.

        Args:
            user_id: Filter by user ID
            status: Filter by task status string

        Returns:
            Filtered task list sorted by created_at DESC
        """
        tasks = await self.list_all_tasks()
        if user_id:
            tasks = [t for t in tasks if t.user_id == user_id]
        if status:
            tasks = [t for t in tasks if t.status.value == status]
        return tasks
    
    @property
    def running_count(self) -> int:
        """Get number of running tasks."""
        return self._running_count
    
    @property
    def max_jobs(self) -> int:
        """Get maximum concurrent jobs."""
        return self._max_jobs
    
    def set_max_jobs(self, value: int) -> None:
        """Set maximum concurrent jobs at runtime.
        
        Args:
            value: New max jobs value (will be clamped to >= 1)
        """
        self._max_jobs = max(1, value)
    
    async def can_start_new_job(self) -> bool:
        """Check if a new job can be started."""
        async with self._get_lock():
            return self._running_count < self._max_jobs
    
    async def increment_running(self) -> None:
        """Increment running job count."""
        async with self._get_lock():
            self._running_count += 1
    
    async def decrement_running(self) -> None:
        """Decrement running job count."""
        async with self._get_lock():
            self._running_count = max(0, self._running_count - 1)
