"""Indexing service - interfaces with fiber_diffraction_indexing package."""
import os
import sys
import shutil
import time
import asyncio
import threading
import subprocess
import math
import re
import glob
from pathlib import Path
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, Future

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "fiber_diffraction_indexing"))

from fiberdiffraction import (
    FiberDiffractionIndexer,
)
from fiberdiffraction.callbacks import IndexingCallback
from fiberdiffraction.hdf5 import HDF5Manager

from models.analysis import AnalysisParams
from services.task_manager import TaskManager, TaskStatus
from services.fortran_runtime import ensure_fortran_binaries
from core.config import settings


class ProgressTracker:
    """Thread-safe progress tracker for async updates."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._logs: List[str] = []
        self._current_step = 0
        self._best_fitness = 0.0
        self._best_cell: List[float] = []
        self._hdf5_file: str = ""
        self._last_best_log_step: int = -1
    
    def append_log(self, msg: str) -> None:
        with self._lock:
            self._logs.append(msg)
    
    def set_progress(self, step: int, best_fitness: float, best_cell: List[float] = None) -> None:
        with self._lock:
            self._current_step = step
            self._best_fitness = best_fitness
            if best_cell:
                self._best_cell = best_cell
    
    def set_hdf5_file(self, hdf5_file: str) -> None:
        with self._lock:
            self._hdf5_file = hdf5_file
    
    def get_logs(self) -> List[str]:
        with self._lock:
            return self._logs.copy()
    
    def get_summary_logs(self) -> List[str]:
        """Return filtered summary logs (throttled, key events only).
        
        Summary mode keeps:
        - All [System] logs
        - [Progress] step start/end only
        - One [Best] per step (last one)
        - All [Error] logs
        
        Summary mode filters:
        - [Warning] logs
        - High-frequency [Best] updates (only last per step)
        """
        with self._lock:
            summary_logs: List[str] = []
            step_best_logs: Dict[int, str] = {}
            step_first_progress: Dict[int, str] = {}
            last_error_log = ""
            
            for log in self._logs:
                if "[System]" in log:
                    summary_logs.append(log)
                elif "[Error]" in log or "[ERROR]" in log:
                    last_error_log = log
                elif "[Progress]" in log:
                    if "Starting step" in log or "Completed step" in log:
                        summary_logs.append(log)
                    else:
                        pass
                elif "[Best]" in log:
                    try:
                        step = self._extract_step_from_log(log)
                        step_best_logs[step] = log
                    except:
                        step_best_logs.setdefault(self._current_step, log)
                elif "[Warning]" in log:
                    pass
                else:
                    summary_logs.append(log)
            
            for step in sorted(step_best_logs.keys()):
                summary_logs.append(step_best_logs[step])
            
            if last_error_log:
                summary_logs.append(last_error_log)
            
            return summary_logs
    
    def _extract_step_from_log(self, log: str) -> int:
        """Extract step number from log message."""
        import re
        match = re.search(r'step (\d+)', log, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return -1
    
    @property
    def current_step(self) -> int:
        with self._lock:
            return self._current_step
    
    @property
    def best_fitness(self) -> float:
        with self._lock:
            return self._best_fitness
    
    @property
    def best_cell(self) -> List[float]:
        with self._lock:
            return self._best_cell.copy()
    
    @property
    def hdf5_file(self) -> str:
        with self._lock:
            return self._hdf5_file


class TaskCancelledException(Exception):
    """Custom exception for task cancellation."""
    pass


class CancellableIndexingCallback(IndexingCallback):
    """Callback that supports cancellation and progress tracking."""
    
    def __init__(self, tracker: ProgressTracker, stop_event: threading.Event):
        self.tracker = tracker
        self.stop_event = stop_event
        self._last_error_step = -1
        self._cancelled = False
        self._last_best_log_step = -1
    
    def on_step_start(self, step: int, total: int) -> None:
        if self.stop_event.is_set():
            self._cancelled = True
            return
        msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Progress] Starting step {step + 1}/{total}"
        self.tracker.append_log(msg)
        self.tracker.set_progress(step, 0.0)
    
    def on_step_end(self, step: int, total: int, elapsed: float) -> None:
        if self.stop_event.is_set():
            self._cancelled = True
            return
        msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Progress] Completed step {step + 1}/{total} in {elapsed:.2f}s"
        self.tracker.append_log(msg)
    
    def on_progress(self, step: int, message: str) -> None:
        if self.stop_event.is_set():
            return
        best_fitness = 0.0
        best_cell = None
        if "Now error is" in message:
            try:
                parts = message.split("Now error is")
                if len(parts) > 1:
                    best_fitness = float(parts[1].strip().split()[0])
                    self._last_error_step = step
            except (ValueError, IndexError):
                pass
        
        if best_fitness > 0 or self._last_error_step == step:
            self.tracker.set_progress(step, best_fitness, best_cell)
        
        if best_fitness > 0:
            if step != self._last_best_log_step:
                msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Best] Step {step + 1}: error={best_fitness:.6f}"
                self.tracker.append_log(msg)
                self._last_best_log_step = step
        elif "Now error is" in message:
            msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Progress] {message}"
            self.tracker.append_log(msg)
    
    def on_error(self, step: int, error: Exception) -> None:
        msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Error] {str(error)}"
        self.tracker.append_log(msg)
    
    def on_complete(self, total_time: float, results: Dict[str, Any]) -> None:
        msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [System] Indexing completed in {total_time:.2f}s"
        self.tracker.append_log(msg)
        if results:
            cell = results.get("best_cell", [])
            if cell:
                cell_msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [System] Final cell: a={cell[0]:.3f} b={cell[1]:.3f} c={cell[2]:.3f} alpha={cell[3]:.2f} beta={cell[4]:.2f} gamma={cell[5]:.2f}"
                self.tracker.append_log(cell_msg)
    
    def is_cancelled(self) -> bool:
        return self._cancelled
    
    def get_logs(self) -> List[str]:
        return self.tracker.get_logs()


def _build_task_paths(work_dir: str) -> dict:
    """Build a dictionary of all task-related file paths.
    
    Args:
        work_dir: The task's work directory path
        
    Returns:
        Dictionary containing all relevant paths for the task
    """
    return {
        "work_dir": work_dir,
        "result_dir": os.path.join(work_dir, "result"),
        "figures_dir": os.path.join(work_dir, "figures"),
        "input_file": os.path.join(work_dir, "input.txt"),
        "diffraction_file": os.path.join(work_dir, "observed_diffraction.txt"),
        "hdf5_file": os.path.join(work_dir, "results.h5"),
        "output_miller_file": os.path.join(work_dir, "outputMiller.txt"),
        "full_miller_file": os.path.join(work_dir, "FullMiller.txt"),
    }


def _resolve_cell_file(work_dir: str, step: int) -> Optional[str]:
    """Resolve a cell file from work_dir or archived result/ directory."""
    candidates = [
        os.path.join(work_dir, f"cell_{step}.txt"),
        os.path.join(work_dir, "result", f"cell_{step}.txt"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    latest_step = -1
    latest_path = None
    for base_dir in (work_dir, os.path.join(work_dir, "result")):
        pattern = os.path.join(base_dir, "cell_*.txt")
        for path in glob.glob(pattern):
            name = os.path.basename(path)
            if "_annealing" in name:
                continue
            match = re.fullmatch(r"cell_(\d+)\.txt", name)
            if not match:
                continue
            current_step = int(match.group(1))
            if current_step > latest_step:
                latest_step = current_step
                latest_path = path

    return latest_path


class IndexingService:
    """Service for managing fiber diffraction indexing tasks."""
    
    _running_tasks: Dict[str, dict] = {}
    _tasks_lock = threading.Lock()
    
    def __init__(self, task_manager: TaskManager):
        """Initialize indexing service.
        
        Args:
            task_manager: Task manager instance
        """
        self.task_manager = task_manager
    
    def _count_diffraction_points(self, data_file: str) -> int:
        """Count the number of diffraction points in a data file."""
        try:
            with open(data_file, 'r') as f:
                count = sum(1 for line in f if line.strip())
            return count
        except Exception:
            return 62
    
    def _params_to_input_config(self, params: AnalysisParams, work_dir: str, data_file: str = None) -> str:
        """Convert AnalysisParams to input.txt file (30-line format for Fortran)."""
        lines = []
        
        lines.append(str(params.wavelength))
        lines.append("0")
        lines.append("flat")
        lines.append(str(params.generations))
        lines.append(str(params.steps))
        
        survival_rate = params.liveRatio / 100.0
        crossover_rate = params.exchangeRatio / 100.0
        mutation_rate = params.mutateRatio / 100.0
        new_rate = params.newRatio / 100.0
        
        lines.append(f"{survival_rate:.3f}")
        lines.append(f"{crossover_rate:.3f}")
        lines.append(f"{mutation_rate:.3f}")
        lines.append(f"{new_rate:.3f}")
        
        lines.append("2")
        lines.append("0")
        diffraction_point_count = self._count_diffraction_points(data_file)
        lines.append(str(diffraction_point_count))
        lines.append("1" if params.lmMode else "0")
        
        lines.append("0")
        
        lines.append(f"{params.e1}")
        lines.append(f"{params.e2}")
        lines.append(f"{params.e3}")
        
        lines.append("0")
        if params.hklMode == 'Full':
            lines.append("0")
        elif params.hklMode == 'Custom':
            lines.append(f"{params.custH} {params.custK} {params.custL}")
        else:  # Default
            lines.append("5 5 0")
        
        lines.append("0")
        lines.append("0")
        lines.append("0")
        
        lines.append("1")
        lines.append(f"{params.esym}")
        
        lines.append(f"{params.aMin} {params.bMin} {params.cMin} {params.alphaMin} {params.betaMin} {params.gammaMin}")
        lines.append(f"{params.aMax} {params.bMax} {params.cMax} {params.alphaMax} {params.betaMax} {params.gammaMax}")
        
        lines.append("1" if params.tiltCheck else "0")
        lines.append("0")
        lines.append("0")
        lines.append("0")
        
        work_dir_abs = os.path.abspath(work_dir)
        input_file = os.path.join(work_dir_abs, "input.txt")
        with open(input_file, 'w') as f:
            f.write('\n'.join(lines))
        
        return input_file
    
    def _run_miller_postprocess(self, work_dir: str, step: int) -> bool:
        """Run Miller index post-processing after main indexing completes.
        
        Args:
            work_dir: Working directory containing input.txt, observed diffraction data, and cell files
            step: The step number to process (typically total_steps - 1 for final result)
            
        Returns:
            True if successful, False otherwise
        """
        _, postprocess_path = ensure_fortran_binaries()
        postprocess_exe = str(postprocess_path)
        
        if not os.path.exists(postprocess_exe):
            print(f"[PostProcess] Warning: Post-process executable not found at {postprocess_exe}")
            return False
        
        input_file = os.path.join(work_dir, "input.txt")
        diffraction_file = os.path.join(work_dir, "observed_diffraction.txt")
        cell_file = _resolve_cell_file(work_dir, step)
        
        if not os.path.exists(input_file):
            print(f"[PostProcess] Warning: input.txt not found")
            return False
        if not os.path.exists(diffraction_file):
            print(f"[PostProcess] Warning: observed_diffraction.txt not found")
            return False
        if not cell_file:
            print(f"[PostProcess] Warning: cell_{step}.txt not found in work_dir or result/")
            return False

        cell_file_name = os.path.basename(cell_file)
        
        cmd = [
            postprocess_exe,
            "-i", "input.txt",
            "-d", "observed_diffraction.txt",
            "-c", cell_file_name
        ]
        print(f"[PostProcess] Running: {' '.join(cmd)}")

        if os.path.dirname(cell_file) != work_dir:
            shutil.copy2(cell_file, os.path.join(work_dir, cell_file_name))
        
        result = subprocess.run(
            cmd,
            cwd=work_dir,
            capture_output=True,
            text=True
        )
        
        output_miller_file = os.path.join(work_dir, "outputMiller.txt")
        full_miller_file = os.path.join(work_dir, "FullMiller.txt")

        if result.returncode == 0 and os.path.exists(output_miller_file) and os.path.exists(full_miller_file):
            print(f"[PostProcess] Successfully generated FullMiller.txt and outputMiller.txt")
            return True
        else:
            print(f"[PostProcess] Warning: Post-process returned code {result.returncode}")
            if result.stdout:
                print(f"[PostProcess] stdout: {result.stdout}")
            if result.stderr:
                print(f"[PostProcess] stderr: {result.stderr}")
            if result.returncode == 0:
                print("[PostProcess] Warning: Post-process exited successfully but output files were not generated")
            return False
    
    async def run_indexing(
        self,
        task_id: str,
        data_file: str,
        params: AnalysisParams
    ) -> Dict[str, Any]:
        """Run fiber diffraction indexing."""
        task = await self.task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        user_id = task.user_id or "anonymous"
        
        user_result_dir = os.path.abspath(
            os.path.join(settings.USER_RESULT_DIR, user_id)
        )
        Path(user_result_dir).mkdir(parents=True, exist_ok=True)
        
        work_dir = os.path.abspath(os.path.join(user_result_dir, task_id))
        Path(work_dir).mkdir(parents=True, exist_ok=True)
        
        result_dir = os.path.join(work_dir, "result")
        figures_dir = os.path.join(work_dir, "figures")
        Path(result_dir).mkdir(parents=True, exist_ok=True)
        Path(figures_dir).mkdir(parents=True, exist_ok=True)
        
        await self.task_manager.update_task_status(task_id, TaskStatus.RUNNING)
        await self.task_manager.increment_running()
        
        tracker = ProgressTracker()
        stop_event = threading.Event()
        executor = ThreadPoolExecutor(max_workers=1)
        future = None
        process = None
        
        with self._tasks_lock:
            self._running_tasks[task_id] = {
                'executor': executor,
                'future': None,
                'stop_event': stop_event,
                'tracker': tracker,
                'work_dir': work_dir
            }
        
        async def progress_updater():
            """Periodically update task progress from tracker."""
            while True:
                await asyncio.sleep(0.5)
                task = await self.task_manager.get_task(task_id)
                if not task or task.status not in (TaskStatus.RUNNING, TaskStatus.PENDING):
                    break
                
                logs = tracker.get_logs()
                current_step = tracker.current_step
                best_fitness = tracker.best_fitness
                
                hdf5_file = tracker.hdf5_file
                if hdf5_file and os.path.exists(hdf5_file):
                    try:
                        with HDF5Manager(hdf5_file, mode='r') as hdf5:
                            convergence = hdf5.read_convergence()
                            if convergence and "best_cells" in convergence and "best_errors" in convergence:
                                cells = convergence["best_cells"]
                                errors = convergence["best_errors"]
                                if len(cells) > 0 and len(errors) > 0:
                                    latest_cell = cells[-1].tolist() if hasattr(cells[-1], 'tolist') else list(cells[-1])
                                    latest_error = float(errors[-1])
                                    current_step = len(cells) - 1
                                    tracker.set_progress(current_step, latest_error, latest_cell)
                                    cell_msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Best] Current best: error={latest_error:.6f} a={latest_cell[0]:.3f} b={latest_cell[1]:.3f} c={latest_cell[2]:.3f} alpha={latest_cell[3]:.2f} beta={latest_cell[4]:.2f} gamma={latest_cell[5]:.2f}"
                                    tracker.append_log(cell_msg)
                                    logs = tracker.get_logs()
                                    best_fitness = latest_error
                    except Exception:
                        pass
                
                await self.task_manager.update_task_progress(
                    task_id, current_step, best_fitness,
                    logs[-1] if logs else None
                )
                
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    break
        
        hdf5_file = os.path.join(work_dir, "results.h5")
        tracker.set_hdf5_file(hdf5_file)
        
        async def run_in_thread():
            """Run indexing in thread pool."""
            callback = None
            def run_indexing_sync():
                nonlocal callback
                collected_logs = []
                try:
                    opt_path, post_path = ensure_fortran_binaries()
                    tracker.append_log(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [System] Fortran runtime ready: "
                        f"opt={opt_path.name}, post={post_path.name}"
                    )

                    from core.dependencies import get_system_config_service
                    system_config_svc = get_system_config_service()
                    requested = getattr(params, 'ompThreads', 1) or 1
                    admin_limit = system_config_svc.get_max_omp_threads()
                    effective = min(requested, admin_limit)
                    os.environ['OMP_NUM_THREADS'] = str(effective)
                    
                    tracker.append_log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [System] OMP threads: requested={requested}, admin_limit={admin_limit}, effective={effective}")
                    
                    callback = CancellableIndexingCallback(tracker, stop_event)
                    
                    diffraction_file = os.path.join(work_dir, "observed_diffraction.txt")
                    shutil.copy(data_file, diffraction_file)
                    
                    input_file = self._params_to_input_config(params, work_dir, diffraction_file)
                    
                    indexer = FiberDiffractionIndexer(
                        input_file=input_file,
                        diffraction_file=diffraction_file,
                        callback=callback,
                        use_hdf5=True,
                        hdf5_file=hdf5_file
                    )
                    
                    indexer.run()
                    
                    return {
                        "status": "completed",
                        "work_dir": work_dir,
                        "hdf5_file": hdf5_file,
                        "logs": callback.get_logs() if callback else collected_logs
                    }
                except Exception as e:
                    if stop_event.is_set():
                        return {"status": "cancelled", "logs": callback.get_logs() if callback else collected_logs}
                    return {"status": "failed", "error": str(e), "logs": callback.get_logs() if callback else collected_logs}
            
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(executor, run_indexing_sync)
            return result
        
        try:
            running_future = asyncio.create_task(run_in_thread())
            
            with self._tasks_lock:
                if task_id in self._running_tasks:
                    self._running_tasks[task_id]['future'] = running_future
            
            progress_task = asyncio.create_task(progress_updater())
            
            try:
                result = await running_future
            except asyncio.CancelledError:
                result = {"status": "cancelled", "logs": []}
            finally:
                progress_task.cancel()
            
            if result.get("status") == "completed":
                work_dir = result.get("work_dir", "")
                total_steps = params.steps if params else 30
                final_step = total_steps - 1
                
                tracker.append_log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [System] Running Miller post-processing...")
                
                loop = asyncio.get_running_loop()
                postprocess_success = await loop.run_in_executor(
                    executor,
                    lambda: self._run_miller_postprocess(work_dir, final_step)
                )
                
                if postprocess_success:
                    tracker.append_log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [System] Miller indices generated successfully")
                else:
                    tracker.append_log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Warning] Miller post-processing may have failed")
                
                await self.task_manager.update_task_status(task_id, TaskStatus.COMPLETED)
            elif result.get("status") == "cancelled":
                await self.task_manager.update_task_status(task_id, TaskStatus.CANCELLED)
            else:
                await self.task_manager.update_task_status(
                    task_id, TaskStatus.FAILED, result.get("error", "Unknown error")
                )
            
            await self.task_manager.set_task_result(task_id, result)
            
            return result
            
        except Exception as e:
            await self.task_manager.update_task_status(
                task_id, TaskStatus.FAILED, str(e)
            )
            raise
        finally:
            with self._tasks_lock:
                if task_id in self._running_tasks:
                    del self._running_tasks[task_id]
            executor.shutdown(wait=False)
            await self.task_manager.decrement_running()
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        with self._tasks_lock:
            if task_id in self._running_tasks:
                task_info = self._running_tasks[task_id]
                task_info['stop_event'].set()
                
                executor = task_info['executor']
                future = task_info['future']
                
                if future:
                    future.cancel()
                
                return True
        
        task = await self.task_manager.get_task(task_id)
        if task and task.status == TaskStatus.RUNNING:
            await self.task_manager.update_task_status(task_id, TaskStatus.CANCELLED)
            return True
        return False
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        with self._tasks_lock:
            if task_id in self._running_tasks:
                tracker = self._running_tasks[task_id]['tracker']
                return {
                    "status": "running",
                    "current_step": tracker.current_step,
                    "total_steps": 0,
                    "best_fitness": tracker.best_fitness,
                    "error_message": None
                }
        
        task = await self.task_manager.get_task(task_id)
        if not task:
            return None
        
        return {
            "status": task.status.value,
            "current_step": task.current_step,
            "total_steps": task.total_steps,
            "best_fitness": task.best_fitness,
            "error_message": task.error_message
        }
    
    async def get_task_logs(self, task_id: str, mode: str = "full") -> Optional[List[str]]:
        """Get task logs.
        
        Args:
            task_id: Task ID
            mode: Log mode - "full" for all logs, "summary" for filtered logs
        """
        with self._tasks_lock:
            if task_id in self._running_tasks:
                tracker = self._running_tasks[task_id]['tracker']
                if mode == "summary":
                    return tracker.get_summary_logs()
                return tracker.get_logs()
        
        task = await self.task_manager.get_task(task_id)
        if not task:
            return None
        return task.logs
    
    async def get_results(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get analysis results."""
        task = await self.task_manager.get_task(task_id)
        if not task:
            return None
        
        user_id = task.user_id or "anonymous"
        user_result_dir = os.path.abspath(
            os.path.join(settings.USER_RESULT_DIR, user_id)
        )
        work_dir = os.path.join(user_result_dir, task_id)
        hdf5_file = os.path.join(work_dir, "results.h5")
        
        print(f"[DEBUG] get_results: task_id={task_id}, user_id={user_id}")
        print(f"[DEBUG] get_results: user_result_dir={user_result_dir}")
        print(f"[DEBUG] get_results: work_dir={work_dir}")
        print(f"[DEBUG] get_results: hdf5_file={hdf5_file}, exists={os.path.exists(hdf5_file)}")
        
        if not os.path.exists(hdf5_file):
            return None
        
        try:
            with HDF5Manager(hdf5_file, mode='r') as hdf5:
                config = hdf5.read_config()
                convergence = hdf5.read_convergence()
                
                best_error = 0.0
                best_cell = []
                tilt_enabled = config.get('tilt_status', 0) == 1
                print(f"[DEBUG] tilt_enabled={tilt_enabled}, config={config}")
                if convergence and "best_errors" in convergence and "best_cells" in convergence:
                    errors = convergence["best_errors"]
                    cells = convergence["best_cells"]
                    if len(errors) > 0:
                        best_error = float(errors[-1])
                    if len(cells) > 0:
                        best_cell = cells[-1].tolist() if hasattr(cells[-1], 'tolist') else list(cells[-1])
                        print(f"[DEBUG] best_cell has {len(best_cell)} elements")
                
                cell_params = {
                    "a": best_cell[0] if len(best_cell) > 0 else 0.0,
                    "b": best_cell[1] if len(best_cell) > 1 else 0.0,
                    "c": best_cell[2] if len(best_cell) > 2 else 0.0,
                    "alpha": best_cell[3] if len(best_cell) > 3 else 0.0,
                    "beta": best_cell[4] if len(best_cell) > 4 else 0.0,
                    "gamma": best_cell[5] if len(best_cell) > 5 else 0.0,
                }
                if tilt_enabled:
                    final_step = task.total_steps
                    cell_file = _resolve_cell_file(work_dir, final_step)
                    if cell_file and os.path.exists(cell_file):
                        try:
                            with open(cell_file, 'r') as f:
                                lines = f.readlines()
                                if lines:
                                    first_line = lines[0].strip().split()
                                    if len(first_line) >= 7:
                                        cell_params["tilt"] = float(first_line[6])
                                        print(f"[DEBUG] Added tilt={first_line[6]} from cell file")
                                    elif len(first_line) >= 6:
                                        cell_params["tilt"] = 0.0
                                        print(f"[DEBUG] Cell file has 6 cols, tilt=0")
                        except Exception as e:
                            print(f"[DEBUG] Error reading cell file for tilt: {e}")
                
                miller_data = []
                output_miller_file = os.path.join(work_dir, "outputMiller.txt")
                if os.path.exists(output_miller_file):
                    try:
                        with open(output_miller_file, 'r') as f:
                            lines = f.readlines()
                            print(f"[DEBUG] Reading outputMiller.txt ({len(lines)} lines)")
                            for line in lines:
                                parts = line.strip().split()
                                if len(parts) >= 5 and not line.startswith('H') and not line.startswith('h') and not line.startswith('v') and not line.startswith('volume'):
                                    try:
                                        if len(parts) >= 6:
                                            print(f"[DEBUG] Detected 6-column format (tilt mode)")
                                            miller_data.append({
                                                "h": int(float(parts[0])),
                                                "k": int(float(parts[1])),
                                                "l": int(float(parts[2])),
                                                "qcalc": float(parts[3]),
                                                "psicalc": float(parts[4]),
                                                "psiRootCalc": float(parts[5]),
                                                "qobs": float(parts[3]),
                                                "psiobs": float(parts[4])
                                            })
                                        else:
                                            miller_data.append({
                                                "h": int(float(parts[0])),
                                                "k": int(float(parts[1])),
                                                "l": int(float(parts[2])),
                                                "qcalc": float(parts[3]),
                                                "psicalc": float(parts[4]),
                                                "psiRootCalc": None,
                                                "qobs": float(parts[3]),
                                                "psiobs": float(parts[4])
                                            })
                                    except ValueError as e:
                                        continue
                            print(f"[DEBUG] Parsed {len(miller_data)} Miller indices from outputMiller")
                    except Exception as e:
                        print(f"[DEBUG] Error reading outputMiller file: {e}")
                        pass

                full_miller_count = 0
                full_miller_file = os.path.join(work_dir, "FullMiller.txt")
                if os.path.exists(full_miller_file):
                    try:
                        with open(full_miller_file, 'r') as f:
                            full_lines = [line for line in f if line.strip() and not line.startswith(('H', 'h', 'v', 'V', 'volume'))]
                            full_miller_count = len(full_lines)
                            print(f"[DEBUG] FullMiller.txt has {full_miller_count} reflections")
                    except Exception as e:
                        print(f"[DEBUG] Error reading FullMiller file: {e}")

                diffraction_data = []
                diffraction_file = os.path.join(work_dir, "observed_diffraction.txt")
                if os.path.exists(diffraction_file):
                    try:
                        with open(diffraction_file, 'r') as f:
                            for line in f:
                                parts = line.strip().split()
                                if len(parts) >= 2:
                                    try:
                                        diffraction_data.append({
                                            "q_obs": float(parts[0]),
                                            "psi_obs": float(parts[1])
                                        })
                                    except ValueError:
                                        continue
                        print(f"[DEBUG] Read {len(diffraction_data)} diffraction points")
                    except Exception as e:
                        print(f"[DEBUG] Error reading diffraction file: {e}")

                r_factor_q = 0.0
                r_factor_psi = 0.0
                max_deviation_q = 0.0
                max_deviation_psi = 0.0
                max_deviation_q_point = {"h": 0, "k": 0, "l": 0}
                max_deviation_psi_point = {"h": 0, "k": 0, "l": 0}

                if len(miller_data) > 0 and len(diffraction_data) > 0:
                    n = min(len(miller_data), len(diffraction_data))
                    q_deviations = []
                    psi_deviations = []
                    
                    for i in range(n):
                        q_calc = miller_data[i].get("qcalc", 0)
                        psi_calc = miller_data[i].get("psicalc", 0)
                        q_obs = diffraction_data[i].get("q_obs", 0)
                        psi_obs = diffraction_data[i].get("psi_obs", 0)
                        
                        q_dev = abs(q_calc - q_obs)
                        psi_dev = abs(psi_calc - psi_obs)
                        
                        q_deviations.append(q_dev)
                        psi_deviations.append(psi_dev)
                        
                        if q_dev > max_deviation_q:
                            max_deviation_q = q_dev
                            max_deviation_q_point = {
                                "h": miller_data[i].get("h", 0),
                                "k": miller_data[i].get("k", 0),
                                "l": miller_data[i].get("l", 0)
                            }
                        
                        if psi_dev > max_deviation_psi:
                            max_deviation_psi = psi_dev
                            max_deviation_psi_point = {
                                "h": miller_data[i].get("h", 0),
                                "k": miller_data[i].get("k", 0),
                                "l": miller_data[i].get("l", 0)
                            }
                    
                    if n > 0:
                        r_factor_q = sum(q_deviations) / n
                        r_factor_psi = sum(psi_deviations) / n
                    
                    print(f"[DEBUG] R_q={r_factor_q:.4f}, R_psi={r_factor_psi:.4f}")
                    print(f"[DEBUG] Max q dev: {max_deviation_q:.4f} at ({max_deviation_q_point})")
                    print(f"[DEBUG] Max psi dev: {max_deviation_psi:.4f} at ({max_deviation_psi_point})")

                return {
                    "cellParams": cell_params,
                    "millerData": miller_data,
                    "qualityMetrics": {
                        "r_factor": best_error,
                        "r_factor_q": r_factor_q,
                        "r_factor_psi": r_factor_psi,
                        "max_deviation_q": max_deviation_q,
                        "max_deviation_psi": max_deviation_psi,
                        "max_deviation_q_point": max_deviation_q_point,
                        "max_deviation_psi_point": max_deviation_psi_point
                    },
                    "taskId": task_id,
                    "totalReflections": full_miller_count,
                    "indexedPeaks": len(miller_data),
                    "files": {
                        "cell_file": f"cell_{task.total_steps - 1}.txt",
                        "miller_file": "outputMiller.txt",
                        "full_miller_file": "FullMiller.txt"
                    }
                }
        except Exception as e:
            return {"error": str(e)}
