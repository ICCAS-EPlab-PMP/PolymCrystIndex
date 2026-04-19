"""Indexing service - interfaces with fiber_diffraction_indexing package."""

import os
import sys
import shutil
import time
import asyncio
import threading
import re
import json
import logging
import importlib.util
from pathlib import Path
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, Future

sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "fiber_diffraction_indexing")
)

from fiberdiffraction import (  # pyright: ignore[reportMissingImports]
    FiberDiffractionIndexer,
)
from fiberdiffraction.callbacks import IndexingCallback  # pyright: ignore[reportMissingImports]
from fiberdiffraction.hdf5 import HDF5Manager  # pyright: ignore[reportMissingImports]

from models.analysis import AnalysisParams
from services.task_manager import TaskManager, TaskStatus
from services.fortran_runtime import ensure_fortran_binaries
from core.config import settings


logger = logging.getLogger(__name__)


def _load_peak_merge_helper():
    helper_path = Path(__file__).with_name("peak_merge.py")
    spec = importlib.util.spec_from_file_location("services_peak_merge", helper_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load peak_merge helper from {helper_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_peak_merge_helper = _load_peak_merge_helper()
build_peak_symmetry_groups_from_results = (
    _peak_merge_helper.build_peak_symmetry_groups_from_results
)
DEFAULT_PEAK_SYMMETRY_Q_THRESHOLD = _peak_merge_helper.DEFAULT_PEAK_SYMMETRY_Q_THRESHOLD
DEFAULT_PEAK_SYMMETRY_ANGLE_THRESHOLD = _peak_merge_helper.DEFAULT_PEAK_SYMMETRY_ANGLE_THRESHOLD


def _load_postprocess_core_helper():
    helper_path = Path(__file__).with_name("postprocess_core.py")
    spec = importlib.util.spec_from_file_location(
        "services_postprocess_core", helper_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load postprocess_core helper from {helper_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_diffraction_utils_helper():
    helper_path = Path(__file__).with_name("diffraction_utils.py")
    spec = importlib.util.spec_from_file_location(
        "services_diffraction_utils", helper_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load diffraction_utils helper from {helper_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


postprocess_core = _load_postprocess_core_helper()
diffraction_utils = _load_diffraction_utils_helper()


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

    def set_progress(
        self, step: int, best_fitness: float, best_cell: Optional[List[float]] = None
    ) -> None:
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

        match = re.search(r"step (\d+)", log, re.IGNORECASE)
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
        best_cell: Optional[List[float]] = None
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
        "input_file": os.path.join(work_dir, "input.txt"),
        "diffraction_file": os.path.join(work_dir, "observed_diffraction.txt"),
        "hdf5_file": os.path.join(work_dir, "results.h5"),
        "output_miller_file": os.path.join(work_dir, "outputMiller.txt"),
        "full_miller_file": os.path.join(work_dir, "FullMiller.txt"),
        "peak_symmetry_groups_file": os.path.join(work_dir, "peak_symmetry_groups.json"),
    }


def _resolve_cell_file(work_dir: str, step: int) -> Optional[str]:
    return postprocess_core.resolve_cell_file(work_dir, step)


def _sanitize_glide_label(label: str, index: int) -> str:
    return postprocess_core.sanitize_glide_label(label, index)


def _cell_to_lattice_vectors(cell_params: List[float]) -> List[List[float]]:
    return postprocess_core._cell_to_lattice_vectors(cell_params)


def _vector_length(vector: List[float]) -> float:
    return postprocess_core._vector_length(vector)


def _dot_product(left: List[float], right: List[float]) -> float:
    return postprocess_core._dot_product(left, right)


def _angle_between(left: List[float], right: List[float]) -> float:
    return postprocess_core._angle_between(left, right)


def _apply_glide_to_cell(
    cell_params: List[float], n_a: float, n_b: float, l0: float
) -> List[float]:
    return postprocess_core.apply_glide_to_cell(cell_params, n_a, n_b, l0)


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

    def _count_diffraction_points(self, data_file: Optional[str]) -> int:
        """Count the number of diffraction points in a data file."""
        try:
            if not data_file:
                return 62
            with open(data_file, "r") as f:
                count = sum(1 for line in f if line.strip())
            return count
        except Exception:
            return 62

    def _get_peak_symmetry_config(self, params: Optional[AnalysisParams]) -> Dict[str, Any]:
        enabled = bool(
            getattr(params, "peakSymmetryEnabled",
                    getattr(params, "mergeNearbyEnabled", False))
        )
        symmetry_tq = getattr(params, "symmetryTq",
                              getattr(params, "mergeTq", DEFAULT_PEAK_SYMMETRY_Q_THRESHOLD))
        symmetry_ta = getattr(params, "symmetryTa",
                              getattr(params, "mergeTa", DEFAULT_PEAK_SYMMETRY_ANGLE_THRESHOLD))
        merge_gradient_enabled = getattr(params, "mergeGradientEnabled", False)
        merge_gradient_threshold = float(getattr(params, "mergeGradientThreshold", 0.0) or 0.0)
        return {
            "enabled": enabled,
            "symmetryTq": float(
                DEFAULT_PEAK_SYMMETRY_Q_THRESHOLD if symmetry_tq is None else symmetry_tq
            ),
            "symmetryTa": float(
                DEFAULT_PEAK_SYMMETRY_ANGLE_THRESHOLD if symmetry_ta is None else symmetry_ta
            ),
            "mergeGradientEnabled": merge_gradient_enabled,
            "mergeGradientThreshold": merge_gradient_threshold,
        }

    def _format_peak_symmetry_summary_log(
        self, peak_symmetry_groups: List[Dict[str, Any]]
    ) -> str:
        two_peak_count = sum(
            1 for group in peak_symmetry_groups if group.get("groupType") == "2-peak"
        )
        four_peak_count = sum(
            1 for group in peak_symmetry_groups if group.get("groupType") == "4-peak"
        )
        return (
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [System] Peak symmetry groups: "
            f"2-peak={two_peak_count}, 4-peak={four_peak_count}, total={len(peak_symmetry_groups)}"
        )

    def _build_peak_symmetry_groups(
        self,
        diffraction_data: List[Dict[str, Any]],
        miller_data: List[Dict[str, Any]],
        params: Optional[AnalysisParams],
    ) -> List[Dict[str, Any]]:
        config = self._get_peak_symmetry_config(params)
        if not config["enabled"]:
            return []

        return build_peak_symmetry_groups_from_results(
            diffraction_data,
            miller_data,
            q_threshold=config["symmetryTq"],
            angle_threshold=config["symmetryTa"],
            merge_gradient_enabled=config["mergeGradientEnabled"],
            merge_gradient_threshold=config["mergeGradientThreshold"],
        )

    def _read_diffraction_data(self, diffraction_file: str) -> List[Dict[str, Any]]:
        diffraction_data = []
        if not os.path.exists(diffraction_file):
            return diffraction_data

        with open(diffraction_file, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    try:
                        diffraction_data.append(
                            {
                                "q_obs": float(parts[0]),
                                "psi_obs": float(parts[1]),
                            }
                        )
                    except ValueError:
                        continue

        return diffraction_data

    def _read_miller_data(self, output_miller_file: str) -> List[Dict[str, Any]]:
        miller_data = []
        if not os.path.exists(output_miller_file):
            return miller_data

        with open(output_miller_file, "r") as f:
            for line in f:
                stripped = line.strip()
                parts = stripped.split()
                if (
                    len(parts) >= 5
                    and not stripped.startswith("H")
                    and not stripped.startswith("h")
                    and not stripped.startswith("v")
                    and not stripped.startswith("volume")
                ):
                    try:
                        if len(parts) >= 6:
                            miller_data.append(
                                {
                                    "h": int(float(parts[0])),
                                    "k": int(float(parts[1])),
                                    "l": int(float(parts[2])),
                                    "qcalc": float(parts[3]),
                                    "psicalc": float(parts[4]),
                                    "psiRootCalc": float(parts[5]),
                                    "qobs": float(parts[3]),
                                    "psiobs": float(parts[4]),
                                }
                            )
                        else:
                            miller_data.append(
                                {
                                    "h": int(float(parts[0])),
                                    "k": int(float(parts[1])),
                                    "l": int(float(parts[2])),
                                    "qcalc": float(parts[3]),
                                    "psicalc": float(parts[4]),
                                    "psiRootCalc": None,
                                    "qobs": float(parts[3]),
                                    "psiobs": float(parts[4]),
                                }
                            )
                    except ValueError:
                        continue

        return miller_data

    def _read_cell_parameters(self, cell_file: str) -> List[float]:
        return postprocess_core.read_cell_parameters(cell_file)

    def _write_cell_parameters(self, cell_file: str, cell_values: List[float]) -> None:
        postprocess_core.write_cell_parameters(cell_file, cell_values)

    def _build_glide_batch_payload(
        self, params: Optional[AnalysisParams]
    ) -> List[Dict[str, Any]]:
        raw_batches = getattr(params, "glideBatches", []) if params else []
        return postprocess_core.build_glide_batch_payload(raw_batches)

    def _generate_glide_fullmiller_batches(
        self,
        work_dir: str,
        step: int,
        params: Optional[AnalysisParams],
    ) -> Dict[str, Any]:
        return postprocess_core.generate_glide_fullmiller_batches(
            work_dir,
            step,
            self._build_glide_batch_payload(params),
        )

    def _read_glide_batch_artifact(self, work_dir: str) -> Dict[str, Any]:
        return postprocess_core.read_glide_batch_artifact(work_dir)

    def _persist_peak_symmetry_artifact(
        self, work_dir: str, params: Optional[AnalysisParams]
    ) -> Dict[str, Any]:
        task_paths = _build_task_paths(work_dir)
        artifact_path = task_paths["peak_symmetry_groups_file"]
        config = self._get_peak_symmetry_config(params)

        if not config["enabled"]:
            if os.path.exists(artifact_path):
                os.remove(artifact_path)
            return {"enabled": False, "artifactPath": artifact_path, "groupCount": 0}

        diffraction_data = self._read_diffraction_data(task_paths["diffraction_file"])
        miller_data = self._read_miller_data(task_paths["output_miller_file"])
        peak_symmetry_groups = self._build_peak_symmetry_groups(
            diffraction_data,
            miller_data,
            params,
        )

        payload = {
            "peakSymmetryConfig": config,
            "peakSymmetryGroups": peak_symmetry_groups,
            "generatedDuringRun": True,
            "source": "run_indexing",
            "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return {
            "enabled": True,
            "artifactPath": artifact_path,
            "groupCount": len(peak_symmetry_groups),
            "peakSymmetryGroups": peak_symmetry_groups,
        }

    def _read_peak_symmetry_artifact(self, work_dir: str) -> Dict[str, Any]:
        artifact_path = _build_task_paths(work_dir)["peak_symmetry_groups_file"]
        if not os.path.exists(artifact_path):
            return {}

        try:
            with open(artifact_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _parse_fixed_peak_text(self, fixed_peak_text: str) -> List[str]:
        """Normalize fixed peak text into Fortran-compatible lines."""
        if not fixed_peak_text:
            return []

        normalized_lines = []
        for index, raw_line in enumerate(fixed_peak_text.splitlines(), start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            parts = stripped.split()
            if len(parts) != 4:
                raise ValueError(
                    f"Invalid fixed peak format on line {index}. Expected: peak_index h k l"
                )
            try:
                normalized_lines.append(" ".join(str(int(part)) for part in parts))
            except ValueError as exc:
                raise ValueError(
                    f"Invalid fixed peak integer on line {index}. Expected: peak_index h k l"
                ) from exc

        return normalized_lines

    def _write_fixed_peak_file(self, work_dir: str, fixed_peak_text: str) -> int:
        """Write fixhkl.txt in task work_dir and return fixed peak count."""
        fixed_peak_lines = self._parse_fixed_peak_text(fixed_peak_text)
        fixhkl_path = os.path.join(work_dir, "fixhkl.txt")

        if fixed_peak_lines:
            with open(fixhkl_path, "w") as f:
                f.write("\n".join(fixed_peak_lines) + "\n")
        elif os.path.exists(fixhkl_path):
            os.remove(fixhkl_path)

        return len(fixed_peak_lines)

    def _params_to_input_config(
        self,
        params: AnalysisParams,
        work_dir: str,
        data_file: Optional[str] = None,
        fixed_peak_count: Optional[int] = None,
    ) -> str:
        """Convert AnalysisParams to input.txt file (30-line format for Fortran)."""
        lines = []
        if fixed_peak_count is not None:
            fixed_peak_count_val = fixed_peak_count
        else:
            fix_mode_enabled = getattr(params, "fixModeEnabled", False)
            if fix_mode_enabled:
                fixed_peak_count_val = len(
                    self._parse_fixed_peak_text(getattr(params, "fixedPeakText", ""))
                )
            else:
                fixed_peak_count_val = 0

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

        lines.append("1" if params.pseuOrth else "0")

        lines.append(f"{params.e1}")
        lines.append(f"{params.e2}")
        lines.append(f"{params.e3}")

        lines.append("0")
        if params.hklMode == "Full":
            lines.append("0")
        elif params.hklMode == "Custom":
            lines.append(f"{params.custH} {params.custK} {params.custL}")
        else:  # Default
            lines.append("5 5 0")

        lines.append("0")
        lines.append("0")
        lines.append("0")

        lines.append("1")
        lines.append(f"{params.esym}")

        lines.append(
            f"{params.aMin} {params.bMin} {params.cMin} {params.alphaMin} {params.betaMin} {params.gammaMin}"
        )
        lines.append(
            f"{params.aMax} {params.bMax} {params.cMax} {params.alphaMax} {params.betaMax} {params.gammaMax}"
        )

        lines.append("1" if params.tiltCheck else "0")
        lines.append(str(fixed_peak_count_val))
        lines.append("0")
        lines.append("0")

        work_dir_abs = os.path.abspath(work_dir)
        input_file = os.path.join(work_dir_abs, "input.txt")
        with open(input_file, "w") as f:
            f.write("\n".join(lines))

        return input_file

    def _run_miller_postprocess(self, work_dir: str, step: int, stop_event: Optional[threading.Event] = None) -> bool:
        return postprocess_core.run_miller_postprocess(work_dir, step, stop_event)

    async def run_indexing(
        self, task_id: str, data_file: str, params: AnalysisParams
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
        Path(result_dir).mkdir(parents=True, exist_ok=True)

        await self.task_manager.update_task_status(task_id, TaskStatus.RUNNING)
        await self.task_manager.increment_running()

        tracker = ProgressTracker()
        stop_event = threading.Event()
        executor = ThreadPoolExecutor(max_workers=1)
        future = None
        process = None

        with self._tasks_lock:
            self._running_tasks[task_id] = {
                "executor": executor,
                "future": None,
                "stop_event": stop_event,
                "tracker": tracker,
                "work_dir": work_dir,
            }

        async def progress_updater():
            """Periodically update task progress from tracker."""
            while True:
                await asyncio.sleep(0.5)
                task = await self.task_manager.get_task(task_id)
                if not task or task.status not in (
                    TaskStatus.RUNNING,
                    TaskStatus.PENDING,
                ):
                    break

                logs = tracker.get_logs()
                current_step = tracker.current_step
                best_fitness = tracker.best_fitness

                hdf5_file = tracker.hdf5_file
                if hdf5_file and os.path.exists(hdf5_file):
                    try:
                        with HDF5Manager(hdf5_file, mode="r") as hdf5:
                            convergence = hdf5.read_convergence()
                            if (
                                convergence
                                and "best_cells" in convergence
                                and "best_errors" in convergence
                            ):
                                cells = convergence["best_cells"]
                                errors = convergence["best_errors"]
                                if len(cells) > 0 and len(errors) > 0:
                                    latest_cell = (
                                        cells[-1].tolist()
                                        if hasattr(cells[-1], "tolist")
                                        else list(cells[-1])
                                    )
                                    latest_error = float(errors[-1])
                                    current_step = len(cells) - 1
                                    tracker.set_progress(
                                        current_step, latest_error, latest_cell
                                    )
                                    cell_msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Best] Current best: error={latest_error:.6f} a={latest_cell[0]:.3f} b={latest_cell[1]:.3f} c={latest_cell[2]:.3f} alpha={latest_cell[3]:.2f} beta={latest_cell[4]:.2f} gamma={latest_cell[5]:.2f}"
                                    tracker.append_log(cell_msg)
                                    logs = tracker.get_logs()
                                    best_fitness = latest_error
                    except Exception:
                        pass

                await self.task_manager.update_task_progress(
                    task_id, current_step, best_fitness, logs[-1] if logs else None
                )

                if task.status in (
                    TaskStatus.COMPLETED,
                    TaskStatus.FAILED,
                    TaskStatus.CANCELLED,
                ):
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
                    requested = getattr(params, "ompThreads", 1) or 1
                    admin_limit = system_config_svc.get_max_omp_threads()
                    effective = min(requested, admin_limit)
                    os.environ["OMP_NUM_THREADS"] = str(effective)

                    tracker.append_log(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [System] OMP threads: requested={requested}, admin_limit={admin_limit}, effective={effective}"
                    )

                    callback = CancellableIndexingCallback(tracker, stop_event)

                    diffraction_file = os.path.join(
                        work_dir, "observed_diffraction.txt"
                    )
                    shutil.copy(data_file, diffraction_file)

                    fix_mode_enabled = getattr(params, "fixModeEnabled", False)
                    fixed_peak_count_for_input = 0
                    if fix_mode_enabled:
                        fixed_peak_count_for_input = self._write_fixed_peak_file(
                            work_dir, getattr(params, "fixedPeakText", "")
                        )
                    tracker.append_log(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [System] Fixed peaks prepared: count={fixed_peak_count_for_input}"
                    )

                    input_file = self._params_to_input_config(
                        params, work_dir, diffraction_file, fixed_peak_count_for_input
                    )

                    indexer = FiberDiffractionIndexer(
                        input_file=input_file,
                        diffraction_file=diffraction_file,
                        callback=callback,
                        use_hdf5=True,
                        hdf5_file=hdf5_file,
                        stop_event=stop_event,
                    )

                    self._running_tasks[task_id]["indexer"] = indexer

                    indexer.run()

                    return {
                        "status": "completed",
                        "work_dir": work_dir,
                        "hdf5_file": hdf5_file,
                        "logs": callback.get_logs() if callback else collected_logs,
                    }
                except Exception as e:
                    if stop_event.is_set():
                        return {
                            "status": "cancelled",
                            "logs": callback.get_logs() if callback else collected_logs,
                        }
                    return {
                        "status": "failed",
                        "error": str(e),
                        "logs": callback.get_logs() if callback else collected_logs,
                    }

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(executor, run_indexing_sync)
            return result

        try:
            running_future = asyncio.create_task(run_in_thread())

            with self._tasks_lock:
                if task_id in self._running_tasks:
                    self._running_tasks[task_id]["future"] = running_future

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

                tracker.append_log(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [System] Running Miller post-processing..."
                )

                loop = asyncio.get_running_loop()
                postprocess_success = await loop.run_in_executor(
                    executor, lambda: self._run_miller_postprocess(work_dir, final_step, stop_event)
                )

                if postprocess_success:
                    tracker.append_log(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [System] Miller indices generated successfully"
                    )
                    try:
                        peak_symmetry_result = self._persist_peak_symmetry_artifact(
                            work_dir,
                            params,
                        )
                        peak_symmetry_groups = (
                            peak_symmetry_result.get("peakSymmetryGroups", []) or []
                        )
                        if peak_symmetry_result.get("enabled"):
                            tracker.append_log(
                                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [System] Peak symmetry merge artifact written: {os.path.basename(peak_symmetry_result['artifactPath'])}"
                            )
                        else:
                            tracker.append_log(
                                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [System] Peak symmetry merge disabled; execution artifact skipped"
                            )
                        tracker.append_log(
                            self._format_peak_symmetry_summary_log(peak_symmetry_groups)
                        )
                        await self.task_manager.update_task_progress(
                            task_id,
                            tracker.current_step,
                            tracker.best_fitness,
                            tracker.get_logs()[-1],
                        )
                    except Exception as exc:
                        tracker.append_log(
                            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Warning] Peak symmetry summary skipped: {exc}"
                        )
                else:
                    tracker.append_log(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Warning] Miller post-processing may have failed"
                    )

                await self.task_manager.update_task_status(
                    task_id, TaskStatus.COMPLETED
                )
            elif result.get("status") == "cancelled":
                await self.task_manager.update_task_status(
                    task_id, TaskStatus.CANCELLED
                )
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

    def run_manual_fullmiller(
        self,
        a: float,
        b: float,
        c: float,
        alpha: float,
        beta: float,
        gamma: float,
        wavelength: float,
    ) -> Dict[str, Any]:
        import tempfile

        with tempfile.TemporaryDirectory(prefix="manual_fm_") as work_dir:
            self._write_cell_parameters(
                os.path.join(work_dir, "cell_0.txt"),
                [a, b, c, alpha, beta, gamma],
            )

            input_file = os.path.join(work_dir, "input.txt")
            lines = [
                str(wavelength),
                "0",
                "flat",
                "2000",
                "30",
                "0.100",
                "0.200",
                "0.500",
                "0.200",
                "2",
                "0",
                "1",
                "1",
                "1",
                "100.0",
                "500.0",
                "1.0",
                "0",
                "0",
                "0",
                "0",
                "0",
                "1",
                "0.95",
                "3.0 3.0 5.0 60.0 60.0 60.0",
                "10.0 10.0 15.0 150.0 150.0 150.0",
                "0",
                "0",
                "0",
                "0",
            ]
            with open(input_file, "w") as f:
                f.write("\n".join(lines))

            diffraction_file = os.path.join(work_dir, "observed_diffraction.txt")
            with open(diffraction_file, "w") as f:
                f.write("0.1 0.0\n")

            success = self._run_miller_postprocess(work_dir, 0)
            if not success:
                return {"success": False, "message": "Fortran post-process failed"}

            bundle = postprocess_core.read_postprocess_bundle(work_dir, 0)
            if bundle["fullMillerSize"] <= 0:
                return {
                    "success": False,
                    "message": "FullMiller.txt is empty or missing",
                }

            return {
                "success": True,
                "data": {
                    "resultType": "manual",
                    "workDir": work_dir,
                    "cellParams": bundle["cellParams"]
                    or postprocess_core.cell_values_to_dict(
                        [a, b, c, alpha, beta, gamma]
                    ),
                    "volume": bundle["volume"],
                    "fullMillerContent": bundle["fullMillerContent"],
                    "outputMillerContent": bundle["outputMillerContent"],
                    "totalReflections": bundle["totalReflections"],
                    "millerData": diffraction_utils.parse_fullmiller_to_miller_data(
                        bundle.get("fullMillerContent", "")
                    ),
                },
            }

    def run_glide_batch(
        self,
        a: float,
        b: float,
        c: float,
        alpha: float,
        beta: float,
        gamma: float,
        wavelength: float,
        glide_groups: list,
    ) -> Dict[str, Any]:
        import tempfile

        with tempfile.TemporaryDirectory(prefix="glide_batch_") as work_dir:
            cell_values = [a, b, c, alpha, beta, gamma]
            self._write_cell_parameters(
                os.path.join(work_dir, "cell_0.txt"),
                cell_values,
            )

            input_file = os.path.join(work_dir, "input.txt")
            lines = [
                str(wavelength),
                "0",
                "flat",
                "2000",
                "30",
                "0.100",
                "0.200",
                "0.500",
                "0.200",
                "2",
                "0",
                "1",
                "1",
                "1",
                "100.0",
                "500.0",
                "1.0",
                "0",
                "0",
                "0",
                "0",
                "0",
                "1",
                "0.95",
                "3.0 3.0 5.0 60.0 60.0 60.0",
                "10.0 10.0 15.0 150.0 150.0 150.0",
                "0",
                "0",
                "0",
                "0",
            ]
            with open(input_file, "w") as f:
                f.write("\n".join(lines))

            diffraction_file = os.path.join(work_dir, "observed_diffraction.txt")
            with open(diffraction_file, "w") as f:
                f.write("0.1 0.0\n")

            success = self._run_miller_postprocess(work_dir, 0)
            if not success:
                return {
                    "success": False,
                    "message": "Base cell Fortran post-process failed",
                }

            base_bundle = postprocess_core.read_postprocess_bundle(work_dir, 0)
            if base_bundle["fullMillerSize"] <= 0:
                return {"success": False, "message": "Base cell FullMiller is empty"}

            glide_payload = []
            for idx, g in enumerate(glide_groups):
                label = getattr(g, "label", "") or f"glide_{idx + 1:02d}"
                glide_payload.append(
                    {
                        "index": idx + 1,
                        "label": postprocess_core.sanitize_glide_label(label, idx + 1),
                        "nA": float(getattr(g, "nA", 0.0)),
                        "nB": float(getattr(g, "nB", 0.0)),
                        "l0": float(getattr(g, "l0", 0.5)),
                    }
                )

            glide_result = postprocess_core.generate_glide_fullmiller_batches(
                work_dir, 0, glide_payload
            )

            groups_out = []
            for grp in glide_result.get("groups", []):
                batch_dir = os.path.join(work_dir, grp["directory"])
                bundle = postprocess_core.read_postprocess_bundle(batch_dir, 0)
                groups_out.append(
                    {
                        "resultType": "glide",
                        "label": grp["label"],
                        "directory": grp["directory"],
                        "workDir": batch_dir,
                        "fullMillerFile": grp.get("fullMillerFile"),
                        "outputMillerFile": grp.get("outputMillerFile"),
                        "fullMillerSize": grp.get("fullMillerSize", 0),
                        "outputMillerSize": grp.get("outputMillerSize", 0),
                        "cellParams": grp.get("cellParams"),
                        "fullMillerContent": bundle.get("fullMillerContent", ""),
                        "outputMillerContent": bundle.get("outputMillerContent", ""),
                        "totalReflections": bundle.get("totalReflections", 0),
                        "volume": bundle.get("volume"),
                        "input": grp.get("input"),
                        "millerData": diffraction_utils.parse_fullmiller_to_miller_data(
                            bundle.get("fullMillerContent", "")
                        ),
                    }
                )

            return {
                "success": True,
                "data": {
                    "baseCell": glide_result.get("baseCell"),
                    "glideBatchOutputs": {
                        "enabled": True,
                        "batchRoot": glide_result.get("batchRoot", ""),
                        "groups": groups_out,
                    },
                },
            }

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        with self._tasks_lock:
            if task_id in self._running_tasks:
                task_info = self._running_tasks[task_id]
                task_info["stop_event"].set()

                executor = task_info["executor"]
                future = task_info["future"]

                if future:
                    future.cancel()

                indexer = task_info.get("indexer")
                if indexer is not None:
                    indexer.fortran_caller.kill_current_process()

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
                tracker = self._running_tasks[task_id]["tracker"]
                return {
                    "status": "running",
                    "current_step": tracker.current_step,
                    "total_steps": 0,
                    "best_fitness": tracker.best_fitness,
                    "error_message": None,
                }

        task = await self.task_manager.get_task(task_id)
        if not task:
            return None

        return {
            "status": task.status.value,
            "current_step": task.current_step,
            "total_steps": task.total_steps,
            "best_fitness": task.best_fitness,
            "error_message": task.error_message,
        }

    async def get_task_logs(
        self, task_id: str, mode: str = "full"
    ) -> Optional[List[str]]:
        """Get task logs.

        Args:
            task_id: Task ID
            mode: Log mode - "full" for all logs, "summary" for filtered logs
        """
        with self._tasks_lock:
            if task_id in self._running_tasks:
                tracker = self._running_tasks[task_id]["tracker"]
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

        if not os.path.exists(hdf5_file):
            return None

        try:
            with HDF5Manager(hdf5_file, mode="r") as hdf5:
                config = hdf5.read_config()
                convergence = hdf5.read_convergence()

                best_error = 0.0
                best_cell = []
                tilt_enabled = config.get("tilt_status", 0) == 1
                if (
                    convergence
                    and "best_errors" in convergence
                    and "best_cells" in convergence
                ):
                    errors = convergence["best_errors"]
                    cells = convergence["best_cells"]
                    if len(errors) > 0:
                        best_error = float(errors[-1])
                    if len(cells) > 0:
                        best_cell = (
                            cells[-1].tolist()
                            if hasattr(cells[-1], "tolist")
                            else list(cells[-1])
                        )

                volume = None
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
                            with open(cell_file, "r") as f:
                                lines = f.readlines()
                                if lines:
                                    first_line = lines[0].strip().split()
                                    if len(first_line) >= 7:
                                        cell_params["tilt"] = float(first_line[6])
                                    elif len(first_line) >= 6:
                                        cell_params["tilt"] = 0.0
                        except Exception as e:
                            logger.debug(
                                "Failed to read tilt from %s: %s", cell_file, e
                            )

                output_miller_file = os.path.join(work_dir, "outputMiller.txt")
                miller_data = self._read_miller_data(output_miller_file)
                volume = None
                if os.path.exists(output_miller_file):
                    try:
                        with open(output_miller_file, "r") as f:
                            all_lines = f.readlines()
                        if all_lines:
                            last_line = all_lines[-1].strip()
                            if last_line.startswith("volume:"):
                                parts = last_line.split()
                                if len(parts) >= 2:
                                    try:
                                        volume = float(parts[1])
                                    except ValueError:
                                        logger.debug(
                                            "Failed to parse volume line: %s", last_line
                                        )
                    except Exception as e:
                        logger.debug(
                            "Failed to read volume from %s: %s", output_miller_file, e
                        )

                full_miller_count = 0
                full_miller_file = os.path.join(work_dir, "FullMiller.txt")
                if os.path.exists(full_miller_file):
                    try:
                        with open(full_miller_file, "r") as f:
                            full_lines = [
                                line
                                for line in f
                                if line.strip()
                                and not line.strip().startswith(
                                    ("H", "h", "v", "V", "volume")
                                )
                            ]
                            full_miller_count = len(full_lines)
                    except Exception as e:
                        logger.debug(
                            "Failed to read FullMiller count from %s: %s",
                            full_miller_file,
                            e,
                        )

                diffraction_file = os.path.join(work_dir, "observed_diffraction.txt")
                diffraction_data = self._read_diffraction_data(diffraction_file)
                peak_symmetry_artifact = self._read_peak_symmetry_artifact(work_dir)
                peak_symmetry_groups = peak_symmetry_artifact.get("peakSymmetryGroups", []) or []
                peak_symmetry_config = peak_symmetry_artifact.get(
                    "peakSymmetryConfig", self._get_peak_symmetry_config(task.params)
                )
                glide_batch_artifact = self._read_glide_batch_artifact(work_dir)

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
                                "l": miller_data[i].get("l", 0),
                            }

                        if psi_dev > max_deviation_psi:
                            max_deviation_psi = psi_dev
                            max_deviation_psi_point = {
                                "h": miller_data[i].get("h", 0),
                                "k": miller_data[i].get("k", 0),
                                "l": miller_data[i].get("l", 0),
                            }

                    if n > 0:
                        r_factor_q = sum(q_deviations) / n
                        r_factor_psi = sum(psi_deviations) / n

                if volume is not None:
                    cell_params["volume"] = volume

                return {
                    "resultType": "indexing",
                    "cellParams": cell_params,
                    "millerData": miller_data,
                    "qualityMetrics": {
                        "r_factor": best_error,
                        "r_factor_q": r_factor_q,
                        "r_factor_psi": r_factor_psi,
                        "max_deviation_q": max_deviation_q,
                        "max_deviation_psi": max_deviation_psi,
                        "max_deviation_q_point": max_deviation_q_point,
                        "max_deviation_psi_point": max_deviation_psi_point,
                    },
                    "taskId": task_id,
                    "totalReflections": full_miller_count,
                    "indexedPeaks": len(miller_data),
                    "peakSymmetryConfig": peak_symmetry_config,
                    "peakSymmetryGroups": peak_symmetry_groups,
                    "glideBatchOutputs": glide_batch_artifact,
                    "files": {
                        "cell_file": f"cell_{task.total_steps - 1}.txt",
                        "miller_file": "outputMiller.txt",
                        "full_miller_file": "FullMiller.txt",
                        "glide_batch_root": glide_batch_artifact.get("batchRoot"),
                    },
                }
        except Exception as e:
            return {"error": str(e)}
