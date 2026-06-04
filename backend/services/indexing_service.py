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


def _determine_symmetry_merge_mode(
    alpha_deg: float, beta_deg: float, gamma_deg: float, tol: float = 3.0
) -> int:
    """与 Fortran determine_symmetry_merge_mode 一致。

    Returns:
        0 = 无对称 / 三斜, 1 = 正交, 2 = α-unique 单斜,
        3 = β-unique 单斜, 4 = γ-unique 单斜
    """
    alpha_near = abs(alpha_deg - 90.0) <= tol
    beta_near = abs(beta_deg - 90.0) <= tol
    gamma_near = abs(gamma_deg - 90.0) <= tol

    if alpha_near and beta_near and gamma_near:
        return 1
    elif (not alpha_near) and beta_near and gamma_near:
        return 2
    elif alpha_near and (not beta_near) and gamma_near:
        return 3
    elif alpha_near and beta_near and (not gamma_near):
        return 4
    return 0


def _apply_glide_to_cell(
    cell_params: List[float], n_a: float, n_b: float, l0: float
) -> List[float]:
    return postprocess_core.apply_glide_to_cell(cell_params, n_a, n_b, l0)


class IndexingService:
    """Service for managing fiber diffraction indexing tasks."""

    _running_tasks: Dict[str, dict] = {}
    _tasks_lock = threading.Lock()
    _results_cache: Dict[str, Dict[str, Any]] = {}
    _results_cache_lock = threading.Lock()

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
        def _p(name, default=None):
            if params is None:
                return default
            if isinstance(params, dict):
                return params.get(name, default)
            return getattr(params, name, default)

        enabled = bool(
            _p("peakSymmetryEnabled", _p("mergeNearbyEnabled", False))
        )
        symmetry_tq = _p("symmetryTq", _p("mergeTq", DEFAULT_PEAK_SYMMETRY_Q_THRESHOLD))
        symmetry_ta = _p("symmetryTa", _p("mergeTa", DEFAULT_PEAK_SYMMETRY_ANGLE_THRESHOLD))
        return {
            "enabled": enabled,
            "symmetryTq": float(
                DEFAULT_PEAK_SYMMETRY_Q_THRESHOLD if symmetry_tq is None else symmetry_tq
            ),
            "symmetryTa": float(
                DEFAULT_PEAK_SYMMETRY_ANGLE_THRESHOLD if symmetry_ta is None else symmetry_ta
            ),
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

    @staticmethod
    def _recalc_theoretical_q_psi(
        h: int, k: int, l: int,
        cell_params: Dict[str, float],
        wavelength: float = 1.542,
    ) -> tuple:
        """根据 HKL 和晶胞参数重新计算理论 q, psi, psi_root 值。

        使用与 Fortran out.f90 compute_reflection_coordinates 相同的公式：
        - q = 2π/d，其中 d 从倒易点阵计算
        - psi = arcsin(l/(c * d1))，光纤衍射几何
        - psi_root = √|psi|

        Returns:
            (q_val, psi_val, psi_root) 三元组
        """
        import math as _m

        a = float(cell_params.get("a", 1.0))
        b = float(cell_params.get("b", 1.0))
        c = float(cell_params.get("c", 1.0))
        alpha = _m.radians(float(cell_params.get("alpha", 90.0)))
        beta = _m.radians(float(cell_params.get("beta", 90.0)))
        gamma = _m.radians(float(cell_params.get("gamma", 90.0)))

        cos_a, cos_b, cos_g = _m.cos(alpha), _m.cos(beta), _m.cos(gamma)
        sin_a, sin_b, sin_g = _m.sin(alpha), _m.sin(beta), _m.sin(gamma)

        v_sq = 1.0 - cos_a**2 - cos_b**2 - cos_g**2 + 2.0 * cos_a * cos_b * cos_g
        if v_sq <= 0 or wavelength <= 0:
            return 0.0, 0.0, 0.0
        V = a * b * c * _m.sqrt(v_sq)

        # 倒易点阵参数 (已包含 V^2 除法)
        A11 = b**2 * c**2 * sin_a**2 / V**2
        B11 = a**2 * c**2 * sin_b**2 / V**2
        C11 = a**2 * b**2 * sin_g**2 / V**2
        D11 = a * b * c**2 * (cos_a * cos_b - cos_g) / V**2
        E11 = a**2 * b * c * (cos_b * cos_g - cos_a) / V**2
        F11 = a * b**2 * c * (cos_g * cos_a - cos_b) / V**2

        hf, kf, lf = float(h), float(k), float(l)
        d_star_sq = (
            A11 * hf**2 + B11 * kf**2 + C11 * lf**2
            + 2.0 * D11 * hf * kf + 2.0 * E11 * kf * lf + 2.0 * F11 * hf * lf
        )
        if d_star_sq <= 0:
            return 0.0, 0.0, 0.0

        d_star = _m.sqrt(d_star_sq)
        d_val = 1.0 / d_star
        theta = _m.asin(min(wavelength / (2.0 * d_val), 1.0))
        q_val = 2.0 * _m.pi / d_val

        # psi 计算 (匹配 Fortran out.f90: phi_value = asin(y1/d1))
        y1 = 0.0 if lf == 0.0 else lf / c
        d1 = _m.sin(2.0 * theta) / wavelength
        if d1 <= 0:
            psi_rad = _m.pi / 2.0
        else:
            ratio = y1 / d1
            if abs(ratio) > 1.0:
                psi_rad = _m.pi / 2.0 if ratio > 0 else -_m.pi / 2.0
            else:
                psi_rad = _m.asin(ratio)
        psi_val = _m.degrees(psi_rad)
        psi_root = _m.sqrt(abs(psi_val)) if abs(psi_val) >= 0 else 0.0

        return q_val, psi_val, psi_root

    def _apply_deduplicate(
        self,
        results_data: Dict[str, Any],
        params: Optional[AnalysisParams],
    ) -> Dict[str, Any]:
        """Inject dedup summary into results_data from Fortran-computed outputMiller.

        Since v1.9.1 the actual dedup runs inside Fortran (error_cal_dedup).
        This method infers dedup statistics from the final millerData to populate
        the frontend ResultExport panel.
        """
        enabled = bool(
            getattr(params, "deduplicateEnabled", False) if params else False
        )

        if not enabled:
            results_data["deduplicate"] = {"enabled": False}
            return results_data

        miller_data = results_data.get("millerData", [])
        total_peaks = len(miller_data)

        if total_peaks == 0:
            results_data["deduplicate"] = {
                "enabled": True,
                "usedHklCount": 0,
                "totalPeaks": 0,
                "conflictsResolved": 0,
                "deduplicatedPeakIndices": [],
            }
            return results_data

        # 尝试从 Fortran 输出的 dedup_conflicts.txt 获取真实冲突信息
        dedup_peaks = []
        dedup_conflicts = 0
        work_dir = results_data.get("workDir")
        if work_dir:
            conflict_file = os.path.join(work_dir, "dedup_conflicts.txt")
            if os.path.exists(conflict_file):
                try:
                    with open(conflict_file, "r") as _f:
                        for _line in _f:
                            _s = _line.strip()
                            if not _s or _s.startswith("#") or _s.startswith("-"):
                                continue
                            parts = _s.split()
                            if len(parts) >= 8 and parts[-1] == "REMAP":
                                peak_idx = int(parts[0])
                                dedup_peaks.append(peak_idx)
                                dedup_conflicts += 1
                except (OSError, ValueError, IndexError):
                    pass

        if dedup_conflicts > 0:
            # Fortran 报告了实际冲突，直接使用
            results_data["deduplicate"] = {
                "enabled": True,
                "usedHklCount": total_peaks - dedup_conflicts,
                "totalPeaks": total_peaks,
                "conflictsResolved": dedup_conflicts,
                "deduplicatedPeakIndices": dedup_peaks,
                "symmetryApplied": [],
            }
            return results_data

        # 回退：从最终 HKL 去重统计（仅在无 dedup_conflicts.txt 时使用）
        cell_params = results_data.get("cellParams", {}) or {}
        merge_mode = _determine_symmetry_merge_mode(
            cell_params.get("alpha", 90),
            cell_params.get("beta", 90),
            cell_params.get("gamma", 90),
        )
        # sym_stat 始终为 0（Python 端硬编码）→ dedup 不使用对称等价比较
        if merge_mode != 0:
            merge_mode = 0

        def canonical_hkl(h, k, l, mode):
            """两步归一 canonical form（与 Fortran 版一致）。

            第一层：轴向 Friedel 对（mode 无关，abs 正确）
            第二层：l=0 面内反射（mode 感知）
            第三层：l≠0 体反射（两步归一：独立 abs 是错的，符号联动）
            """
            # ── 第一层：轴向反射（至少两个 index 为 0）──
            if h == 0 and k == 0:
                return (0, 0, abs(l))
            elif h == 0 and l == 0:
                return (0, abs(k), 0)
            elif k == 0 and l == 0:
                return (abs(h), 0, 0)

            # ── 第二层：l=0 面内反射 ──
            if l == 0:
                if mode in (1, 2, 3):
                    return (abs(h), abs(k), 0)
                else:  # mode=0 或 4: Friedel 对 (h,k,0)~(-h,-k,0)
                    return (h, k, 0) if h >= 0 else (-h, -k, 0)

            # ── 第三层：l≠0 体反射，两步归一 ──
            hc, kc, lc = h, k, l

            if mode == 1:
                return (abs(h), abs(k), abs(l))
            elif mode == 2:
                if hc < 0:
                    hc, kc, lc = -hc, -kc, -lc
                if kc < 0 or (kc == 0 and lc < 0):
                    kc, lc = -kc, -lc
                return (hc, kc, lc)
            elif mode == 3:
                if kc < 0:
                    hc, kc, lc = -hc, -kc, -lc
                if hc < 0 or (hc == 0 and lc < 0):
                    hc, lc = -hc, -lc
                return (hc, kc, lc)
            elif mode == 4:
                if lc < 0:
                    hc, kc, lc = -hc, -kc, -lc
                if hc < 0 or (hc == 0 and kc < 0):
                    hc, kc = -hc, -kc
                return (hc, kc, lc)
            else:
                return (h, k, l)

        canonical_set = set()
        for md in miller_data:
            ch = canonical_hkl(md.get("h", 0), md.get("k", 0), md.get("l", 0), merge_mode)
            canonical_set.add(ch)

        used_hkl_count = len(canonical_set)
        conflicts_resolved = total_peaks - used_hkl_count

        results_data["deduplicate"] = {
            "enabled": True,
            "usedHklCount": used_hkl_count,
            "totalPeaks": total_peaks,
            "conflictsResolved": max(0, conflicts_resolved),
            "deduplicatedPeakIndices": [],
            "symmetryApplied": [],
        }
        return results_data

    def _generate_adapted_miller_files(
        self,
        work_dir: str,
        zeroed_cell: Dict[str, float],
        miller_data: List[Dict[str, Any]],
        diffraction_data: List[Dict[str, Any]],
        wavelength: float = 1.542,
    ) -> Dict[str, str]:
        """v1.9.1: 生成归零重评适配的 Miller 文件。

        不调用 Fortran，纯 Python 计算。
        生成文件:
          - fullmiller_adapted.txt (7列: H K L q psi psi-root 2theta)
          - outputmiller_adapted.txt (5-6列: H K L q psi [psi-root] + volume)

        Returns:
            {"fullmillerPath": str, "outputmillerPath": str}
        """
        import math as _m

        a = zeroed_cell.get("a", 1.0)
        b = zeroed_cell.get("b", 1.0)
        c = zeroed_cell.get("c", 1.0)
        alpha = _m.radians(zeroed_cell.get("alpha", 90.0))
        beta = _m.radians(zeroed_cell.get("beta", 90.0))
        gamma = _m.radians(zeroed_cell.get("gamma", 90.0))

        cos_a = _m.cos(alpha)
        cos_b = _m.cos(beta)
        cos_g = _m.cos(gamma)
        sin_a = _m.sin(alpha)
        sin_b = _m.sin(beta)
        sin_g = _m.sin(gamma)

        v_sq = 1.0 - cos_a * cos_a - cos_b * cos_b - cos_g * cos_g + 2.0 * cos_a * cos_b * cos_g
        if v_sq <= 0:
            return {}
        volume = a * b * c * _m.sqrt(v_sq)
        if volume <= 0:
            return {}

        # 倒易点阵参数
        A11 = (b * b * c * c * sin_a * sin_a) / (volume * volume)
        B11 = (a * a * c * c * sin_b * sin_b) / (volume * volume)
        C11 = (a * a * b * b * sin_g * sin_g) / (volume * volume)
        D11 = 2.0 * a * b * c * c * (cos_a * cos_b - cos_g) / (volume * volume)
        E11 = 2.0 * a * a * b * c * (cos_g * cos_a - cos_b) / (volume * volume)
        F11 = 2.0 * a * b * b * c * (cos_b * cos_g - cos_a) / (volume * volume)

        fullmiller_lines = [
            " H K L q(A-1) psi(degree) psi-root(degree) 2theta(degree)\n"
        ]
        outputmiller_lines = [
            " H K L q psi psi-root\n"
        ]

        for item in miller_data:
            h = int(item.get("h", 0))
            k = int(item.get("k", 0))
            l = int(item.get("l", 0))

            hf, kf, lf = float(h), float(k), float(l)
            d_star_sq = (
                A11 * hf * hf + B11 * kf * kf + C11 * lf * lf
                + D11 * hf * kf + E11 * kf * lf + F11 * hf * lf
            )
            if d_star_sq <= 0:
                continue
            d_star = _m.sqrt(d_star_sq)
            q_val = d_star * 2.0 * _m.pi / wavelength if wavelength > 0 else 0.0
            d_val = 1.0 / d_star if d_star > 0 else 0.0
            two_theta = _m.degrees(2.0 * _m.asin(min(wavelength / (2.0 * d_val), 1.0))) if d_val > 0 else 0.0

            # psi: 从倒易向量方位角近似
            psi_val = 0.0
            if abs(hf) + abs(kf) + abs(lf) > 0:
                ax = hf * _m.sqrt(A11) + kf * _m.sqrt(B11) * cos_g + lf * _m.sqrt(C11) * cos_b
                ay = kf * _m.sqrt(B11) * _m.sqrt(max(0, 1 - cos_g * cos_g))
                psi_val = _m.degrees(_m.atan2(ay, ax)) if abs(ax) > 1e-12 else 90.0

            psi_root = _m.sqrt(abs(psi_val)) if psi_val >= 0 else 0.0

            hf = float(h); kf = float(k); lf = float(l)
            fullmiller_lines.append(
                f"          {hf:.16e}          {kf:.16e}           {lf:.16e}   {q_val:.16e}      {psi_val:.16e}        {psi_root:.16e}        {two_theta:.16e}\n"
            )

            # outputMiller: match with observed peaks
            q_obs = 0.0
            psi_obs = 0.0
            # Find matching observed peak by index
            idx = item.get("peakIndex", 0)
            if idx > 0 and idx <= len(diffraction_data):
                obs = diffraction_data[idx - 1]
                q_obs = float(obs.get("q_obs", obs.get("q", 0.0)))
                psi_obs = float(obs.get("psi_obs", obs.get("psi", 0.0)))
            hf = float(h); kf = float(k); lf = float(l)
            outputmiller_lines.append(
                f"   {hf:.16e}       {kf:.16e}        {lf:.16e}        {q_obs:.16e}      {psi_obs:.16e}    {psi_root:.16e}     \n"
            )

        outputmiller_lines.append(f" volume:   {volume:.16e}     \n")

        fullmiller_path = os.path.join(work_dir, "fullmiller_adapted.txt")
        outputmiller_path = os.path.join(work_dir, "outputmiller_adapted.txt")

        with open(fullmiller_path, "w", encoding="utf-8") as f:
            f.writelines(fullmiller_lines)
        with open(outputmiller_path, "w", encoding="utf-8") as f:
            f.writelines(outputmiller_lines)

        return {
            "fullmillerPath": fullmiller_path,
            "outputmillerPath": outputmiller_path,
        }

    def _run_angle_zeroing_refinement(
        self,
        work_dir: str,
        zeroed_cell: Dict[str, float],
        zeroed_angles: List[str],
        params: AnalysisParams,
        diffraction_file: str,
    ) -> Optional[Dict[str, Any]]:
        """v1.9.1: 归零重评通过后，以固定角度重新运行 Fortran 优化。

        在独立子目录 _refinement/ 中运行，不覆盖原始结果文件。
        通过 _refinement/result.json 缓存，避免重复执行。

        Returns:
            优化后的结果 dict，或 None（失败时）
        """
        refine_dir = os.path.join(work_dir, "_refinement")
        cached_path = os.path.join(refine_dir, "result.json")

        if os.path.exists(cached_path):
            try:
                import json as _json
                with open(cached_path, "r") as f:
                    cached = _json.load(f)
                logger.info("Returning cached refinement result from %s", cached_path)
                return cached
            except Exception:
                pass

        logger.info("Starting angle zeroing refinement: zeroed_angles=%s", zeroed_angles)
        try:
            os.makedirs(refine_dir, exist_ok=True)

            import shutil
            diffraction_basename = os.path.basename(diffraction_file)
            refine_diffraction = os.path.join(refine_dir, diffraction_basename)
            if not os.path.exists(refine_diffraction) and os.path.exists(diffraction_file):
                shutil.copy2(diffraction_file, refine_diffraction)

            fixed_params = AnalysisParams(
                steps=min(getattr(params, "steps", 30), 10),
                generations=1,
                liveRatio=getattr(params, "liveRatio", 10),
                exchangeRatio=getattr(params, "exchangeRatio", 20),
                mutateRatio=getattr(params, "mutateRatio", 50),
                newRatio=getattr(params, "newRatio", 20),
                aMin=getattr(params, "aMin", 3.0),
                aMax=getattr(params, "aMax", 10.0),
                bMin=getattr(params, "bMin", 3.0),
                bMax=getattr(params, "bMax", 10.0),
                cMin=getattr(params, "cMin", 5.0),
                cMax=getattr(params, "cMax", 15.0),
                wavelength=float(getattr(params, "wavelength", 1.542)),
                esym=getattr(params, "esym", 0.95),
                lmMode=True,
                tiltCheck=getattr(params, "tiltCheck", False),
                pseuOrth=getattr(params, "pseuOrth", False),
                hklMode=getattr(params, "hklMode", "Default"),
                custH=getattr(params, "custH", 5),
                custK=getattr(params, "custK", 5),
                custL=getattr(params, "custL", 0),
                ompThreads=getattr(params, "ompThreads", 1),
            )

            angle_map = {"alpha": "alpha", "beta": "beta", "gamma": "gamma"}
            for angle_name in zeroed_angles:
                attr_min = angle_map.get(angle_name, angle_name) + "Min"
                attr_max = angle_map.get(angle_name, angle_name) + "Max"
                if hasattr(fixed_params, attr_min):
                    setattr(fixed_params, attr_min, 90.0)
                if hasattr(fixed_params, attr_max):
                    setattr(fixed_params, attr_max, 90.0)

            input_path = self._params_to_input_config(fixed_params, refine_dir, refine_diffraction, 0)

            cell_values = [
                zeroed_cell.get("a", 5.0),
                zeroed_cell.get("b", 5.0),
                zeroed_cell.get("c", 10.0),
                zeroed_cell.get("alpha", 90.0),
                zeroed_cell.get("beta", 90.0),
                zeroed_cell.get("gamma", 90.0),
            ]
            self._write_cell_parameters(os.path.join(refine_dir, "cell_0.txt"), cell_values)

            import threading as _th
            stop_event = _th.Event()
            try:
                FiberDiffractionIndexer(
                    input_path, refine_diffraction,
                    hdf5_file=None, use_hdf5=False, stop_event=stop_event
                ).run()
            except Exception as exc:
                logger.warning("Angle zeroing refinement Fortran run failed: %s", exc)
                return None

            postprocess_ok = self._run_miller_postprocess(refine_dir, 0)
            if not postprocess_ok:
                logger.warning("Angle zeroing refinement post-process failed")
                return None

            bundle = postprocess_core.read_postprocess_bundle(refine_dir, 0)
            refinement_result = {
                "cellParams": bundle.get("cellParams"),
                "volume": bundle.get("volume"),
                "totalReflections": bundle.get("totalReflections", 0),
                "fullMillerContent": bundle.get("fullMillerContent", ""),
            }

            try:
                import json as _json
                with open(cached_path, "w") as f:
                    _json.dump(refinement_result, f)
            except Exception:
                pass

            logger.info("Angle zeroing refinement completed successfully")
            return refinement_result

        except Exception as exc:
            logger.warning("Angle zeroing refinement failed: %s", exc)
            return None

    def _apply_angle_zeroing(
        self,
        results_data: Dict[str, Any],
        params: Optional[AnalysisParams],
    ) -> Dict[str, Any]:
        """v1.8.5: 归零重评。"""
        enabled = bool(getattr(params, "angleZeroingEnabled", False) if params else False)
        if not enabled:
            results_data["angleZeroing"] = {"enabled": False}
            return results_data

        import importlib.util as _iu

        spec = _iu.spec_from_file_location(
            "angle_zeroing",
            os.path.join(os.path.dirname(__file__), "angle_zeroing.py"),
        )
        if spec is None or spec.loader is None:
            results_data["angleZeroing"] = {"enabled": False, "error": "module_not_found"}
            return results_data

        angle_zeroing_mod = _iu.module_from_spec(spec)
        try:
            spec.loader.exec_module(angle_zeroing_mod)
        except Exception:
            results_data["angleZeroing"] = {"enabled": False, "error": "module_load_failed"}
            return results_data

        threshold = float(getattr(params, "angleZeroingThreshold", 1.0) if params else 1.0)
        tolerance = float(getattr(params, "angleZeroingTolerance", 0.5) if params else 0.5)

        candidate = {
            "cellParams": results_data.get("cellParams", {}),
            "residual": results_data.get("qualityMetrics", {}).get("r_factor", 0.0),
            "observedPeaks": results_data.get("diffractionData", []),
            "hklAssignments": results_data.get("millerData", []),
            "wavelength": float(getattr(params, "wavelength", 1.542) if params else 1.542),
        }
        zr = angle_zeroing_mod.evaluate_angle_zeroing(candidate, threshold, tolerance)

        # v1.9.1: 生成 adapted 文件
        if zr.get("adapted") and results_data.get("workDir"):
            try:
                adapted_files = self._generate_adapted_miller_files(
                    results_data["workDir"],
                    zr["zeroedCell"],
                    results_data.get("millerData", []),
                    results_data.get("diffractionData", []),
                    float(getattr(params, "wavelength", 1.542) if params else 1.542),
                )
                if adapted_files:
                    zr["adaptedFiles"] = adapted_files
            except Exception:
                pass

            # v1.9.1: 固定角度重优化（后台执行，不阻塞 get_results）
            refine_enabled = bool(
                getattr(params, "angleZeroingRefineEnabled", False) if params else False
            )
            if refine_enabled:
                refine_dir = os.path.join(results_data["workDir"], "_refinement")
                cached_path = os.path.join(refine_dir, "result.json")
                if os.path.exists(cached_path):
                    try:
                        import json as _json
                        with open(cached_path, "r") as _f:
                            zr["refinementResult"] = _json.load(_f)
                        logger.info("Loaded cached refinement result from %s", cached_path)
                    except Exception as _exc:
                        logger.warning("Failed to load cached refinement: %s", _exc)
                else:
                    try:
                        task_paths = _build_task_paths(results_data["workDir"])
                        diffraction_file = task_paths["diffraction_file"]
                        import threading as _th
                        _ref_thread = _th.Thread(
                            target=self._run_angle_zeroing_refinement,
                            args=(
                                results_data["workDir"],
                                zr["zeroedCell"],
                                zr.get("zeroedAngles", []),
                                params,
                                diffraction_file,
                            ),
                            daemon=True,
                        )
                        _ref_thread.start()
                        logger.info("Scheduled background refinement thread")
                    except Exception as _exc:
                        logger.warning("Failed to start background refinement: %s", _exc)

        results_data["angleZeroing"] = zr
        return results_data

    def _persist_peak_symmetry_artifact(
        self, work_dir: str, params: Optional[AnalysisParams]
    ) -> Dict[str, Any]:
        task_paths = _build_task_paths(work_dir)
        artifact_path = task_paths["peak_symmetry_groups_file"]
        config = self._get_peak_symmetry_config(params)

        if not config["enabled"]:
            if os.path.exists(artifact_path):
                os.remove(artifact_path)
            return {
                "enabled": False,
                "artifactPath": artifact_path,
                "groupCount": 0,
                "peakSymmetryGroups": [],
                "peakSymmetryGroupsSource": "disabled",
            }

        diffraction_data = self._read_diffraction_data(task_paths["diffraction_file"])
        miller_data = self._read_miller_data(task_paths["output_miller_file"])
        peak_symmetry_groups = build_peak_symmetry_groups_from_results(
            diffraction_data,
            miller_data,
            q_threshold=config["symmetryTq"],
            angle_threshold=config["symmetryTa"],
        )
        peak_symmetry_groups_source = "direct_computation"

        payload = {
            "peakSymmetryConfig": config,
            "peakSymmetryGroups": peak_symmetry_groups,
            "peakSymmetryGroupsSource": peak_symmetry_groups_source,
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
            "peakSymmetryGroupsSource": peak_symmetry_groups_source,
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

    def _parse_fixed_l_text(self, fixed_l_text: str) -> List[str]:
        """Normalize fixed-l text into fixhkl-compatible lines (peak_index 0 0 l)."""
        if not fixed_l_text:
            return []
        normalized_lines = []
        for index, raw_line in enumerate(fixed_l_text.splitlines(), start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            parts = stripped.split()
            if len(parts) != 2:
                raise ValueError(
                    f"Invalid fixed-l format on line {index}. Expected: peak_index l"
                )
            try:
                peak_idx = int(parts[0])
                l_val = int(parts[1])
                normalized_lines.append(f"{peak_idx} 0 0 {l_val}")
            except ValueError as exc:
                raise ValueError(
                    f"Invalid fixed-l integer on line {index}. Expected: peak_index l"
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

    def _write_fixed_l_file(self, work_dir: str, fixed_l_text: str) -> int:
        """Write fixhkl.txt in task work_dir for fixed-l mode and return entry count."""
        fixed_l_lines = self._parse_fixed_l_text(fixed_l_text)
        fixhkl_path = os.path.join(work_dir, "fixhkl.txt")
        if fixed_l_lines:
            with open(fixhkl_path, "w") as f:
                f.write("\n".join(fixed_l_lines) + "\n")
        elif os.path.exists(fixhkl_path):
            os.remove(fixhkl_path)
        return len(fixed_l_lines)

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
        lines.append("0")  # Line 2: placeholder (Fortran skips i=2)
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
        lines.append("1")  # LM优化必须始终开启

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

        # Line 20: sym_tq (q绝对容差), Line 21: sym_ta (角度绝对容差)
        symmetry_tq = float(
            getattr(params, "symmetryTq",
                    getattr(params, "mergeTq", DEFAULT_PEAK_SYMMETRY_Q_THRESHOLD))
            or DEFAULT_PEAK_SYMMETRY_Q_THRESHOLD
        )
        symmetry_ta = float(
            getattr(params, "symmetryTa",
                    getattr(params, "mergeTa", DEFAULT_PEAK_SYMMETRY_ANGLE_THRESHOLD))
            or DEFAULT_PEAK_SYMMETRY_ANGLE_THRESHOLD
        )
        lines.append(str(symmetry_tq))
        lines.append(str(symmetry_ta))
        lines.append("0")

        lines.append("0")
        lines.append(f"{params.esym}")

        lines.append(
            f"{params.aMin} {params.bMin} {params.cMin} {params.alphaMin} {params.betaMin} {params.gammaMin}"
        )
        lines.append(
            f"{params.aMax} {params.bMax} {params.cMax} {params.alphaMax} {params.betaMax} {params.gammaMax}"
        )

        lines.append("1" if params.tiltCheck else "0")
        lines.append(str(fixed_peak_count_val))

        fixl_mode = 1 if getattr(params, "fixLModeEnabled", False) else 0
        lines.append(str(fixl_mode))

        dedup_enabled = 1 if getattr(params, "deduplicateEnabled", False) else 0
        lines.append(str(dedup_enabled))

        dedup_penalty_val = getattr(params, "deduplicatePenalty", 1.0)
        if dedup_penalty_val < 1.0:
            dedup_penalty_val = 1.0
        lines.append(str(dedup_penalty_val))

        dedup_sym_mode = 1 if getattr(params, "angleZeroingEnabled", False) else 0
        lines.append(str(dedup_sym_mode))

        if len(lines) != 32:
            raise ValueError(f"Unexpected input.txt line count: {len(lines)}")

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
                    fix_l_mode_enabled = getattr(params, "fixLModeEnabled", False)
                    fixed_peak_count_for_input = 0
                    if fix_mode_enabled:
                        fixed_peak_count_for_input = self._write_fixed_peak_file(
                            work_dir, getattr(params, "fixedPeakText", "")
                        )
                    elif fix_l_mode_enabled:
                        fixed_peak_count_for_input = self._write_fixed_l_file(
                            work_dir, getattr(params, "fixedLText", "")
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

                # Unconditional final sync before COMPLETED - fixes best_fitness drop to 0.0
                await self.task_manager.update_task_progress(
                    task_id,
                    tracker.current_step,
                    tracker.best_fitness,
                    tracker.get_logs()[-1] if tracker.get_logs() else None,
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

        with tempfile.TemporaryDirectory(prefix="manual_") as work_dir:
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
                "0",
                "0.95",
                "3.0 3.0 5.0 60.0 60.0 60.0",
                "10.0 10.0 15.0 150.0 150.0 150.0",
                "0",
                "0",
                "0",
                "0",
                "1.0",
            ]
            if len(lines) != 31:
                return {"success": False, "message": f"Unexpected manual input line count: {len(lines)}"}

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
                    "totalReflections": bundle["totalReflections"],
                    "millerData": diffraction_utils.parse_fullmiller_to_miller_data(
                        bundle.get("fullMillerContent", "")
                    ),
                },
            }

    def run_reverse_glide_fullmiller(
        self,
        a: float,
        b: float,
        c: float,
        alpha: float,
        beta: float,
        gamma: float,
        wavelength: float,
        glide_candidates: list,
    ) -> Dict[str, Any]:
        import tempfile

        base_result = postprocess_core.compute_reverse_glide(
            a, b, c, alpha, beta, gamma, wavelength,
            [{"label": getattr(gc, "label", ""), "nA": getattr(gc, "nA", 0), "nB": getattr(gc, "nB", 0), "l0": getattr(gc, "l0", 1)}
             for gc in glide_candidates],
        )

        with tempfile.TemporaryDirectory(prefix="reverse_glide_") as work_dir:
            input_file = os.path.join(work_dir, "input.txt")
            lines = [
                str(wavelength), "0", "flat", "2000", "30",
                "0.100", "0.200", "0.500", "0.200", "2",
                "0", "1", "1", "1", "100.0", "500.0", "1.0",
                "0", "0", "0", "0", "0", "0", "0.95",
                "3.0 3.0 5.0 60.0 60.0 60.0",
                "10.0 10.0 15.0 150.0 150.0 150.0",
                "0", "0", "0", "0",
            ]
            with open(input_file, "w") as f:
                f.write("\n".join(lines))

            diffraction_file = os.path.join(work_dir, "observed_diffraction.txt")
            with open(diffraction_file, "w") as f:
                f.write("0.1 0.0\n")

            for cr in base_result["candidateResults"]:
                if cr.get("status") != "computed":
                    continue
                cp = cr["cellParams"]
                cell_values = [cp["a"], cp["b"], cp["c"], cp["alpha"], cp["beta"], cp["gamma"]]
                batch_dir = os.path.join(work_dir, cr["label"])
                os.makedirs(batch_dir, exist_ok=True)

                shutil.copy2(input_file, os.path.join(batch_dir, "input.txt"))
                shutil.copy2(diffraction_file, os.path.join(batch_dir, "observed_diffraction.txt"))
                self._write_cell_parameters(
                    os.path.join(batch_dir, "cell_0.txt"), cell_values,
                )

                success = self._run_miller_postprocess(batch_dir, 0)
                if success:
                    bundle = postprocess_core.read_postprocess_bundle(batch_dir, 0)
                    cr["fullMillerContent"] = bundle.get("fullMillerContent", "")
                    cr["totalReflections"] = bundle.get("totalReflections", 0)
                    cr["workDir"] = batch_dir
                else:
                    cr["fullMillerContent"] = ""
                    cr["totalReflections"] = 0
                    cr["workDir"] = batch_dir

        return {"success": True, "data": base_result}

    def run_supercell_fullmiller(
        self,
        a: float,
        b: float,
        c: float,
        alpha: float,
        beta: float,
        gamma: float,
        wavelength: float,
    ) -> Dict[str, Any]:
        return self.run_manual_fullmiller(
            a=a, b=b, c=c,
            alpha=alpha, beta=beta, gamma=gamma,
            wavelength=wavelength,
        )

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
                "0",
                "0.95",
                "3.0 3.0 5.0 60.0 60.0 60.0",
                "10.0 10.0 15.0 150.0 150.0 150.0",
                "0",
                "0",
                "0",
                "0",
                "1.0",
                "0",
            ]
            if len(lines) != 32:
                return {"success": False, "message": f"Unexpected glide input line count: {len(lines)}"}

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
        _gt = time.time()

        # 内存缓存：同一 task_id 第二次起直接返回
        with self._results_cache_lock:
            cached = self._results_cache.get(task_id)
            if cached is not None:
                logger.debug("get_results cache HIT for %s", task_id)
                return cached

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
                peak_symmetry_config = self._get_peak_symmetry_config(task.params)
                if not task.params and peak_symmetry_artifact.get("peakSymmetryConfig"):
                    peak_symmetry_config = peak_symmetry_artifact["peakSymmetryConfig"]
                if peak_symmetry_config.get("enabled"):
                    peak_symmetry_groups = peak_symmetry_artifact.get("peakSymmetryGroups", [])
                    peak_symmetry_groups_source = peak_symmetry_artifact.get(
                        "peakSymmetryGroupsSource", "direct_computation"
                    )
                else:
                    peak_symmetry_groups = []
                    peak_symmetry_groups_source = "disabled"
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

                result_data = {
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
                                "diffractionData": diffraction_data,
"totalReflections": full_miller_count,
                    "indexedPeaks": len(miller_data),
                    "peakSymmetryConfig": peak_symmetry_config,
                    "peakSymmetryGroups": peak_symmetry_groups,
                    "peakSymmetryGroupsSource": peak_symmetry_groups_source,
                    "glideBatchOutputs": glide_batch_artifact,
                    "workDir": work_dir,
                    "files": {
                        "cell_file": f"cell_{task.total_steps - 1}.txt",
                        "miller_file": "outputMiller.txt",
                        "full_miller_file": "FullMiller.txt",
                        "glide_batch_root": glide_batch_artifact.get("batchRoot"),
                    },
                }

                import time as _gt2

                for md in result_data.get("millerData", []):
                    h, k, l = md.get("h", 0), md.get("k", 0), md.get("l", 0)
                    if h == 0 and k == 0:
                        md["h"], md["k"], md["l"] = 0, 0, abs(l)
                    elif h == 0 and l == 0:
                        md["h"], md["k"], md["l"] = 0, abs(k), 0
                    elif k == 0 and l == 0:
                        md["h"], md["k"], md["l"] = abs(h), 0, 0
                    elif l == 0 and h < 0:
                        md["h"], md["k"], md["l"] = -h, -k, 0

                _canon_file = os.path.join(work_dir, "outputMiller.txt")
                try:
                    with open(_canon_file, "r") as _f:
                        _lines = _f.readlines()
                    with open(_canon_file, "w") as _f:
                        for _line in _lines:
                            _s = _line.strip()
                            _p = _s.split()
                            if len(_p) >= 3 and _s[:1] not in ("H", "h", "v", "V") and not _s.startswith("volume"):
                                try:
                                    _h, _k, _l = int(float(_p[0])), int(float(_p[1])), int(float(_p[2]))
                                    if _h == 0 and _k == 0:
                                        _h, _k, _l = 0, 0, abs(_l)
                                    elif _h == 0 and _l == 0:
                                        _h, _k, _l = 0, abs(_k), 0
                                    elif _k == 0 and _l == 0:
                                        _h, _k, _l = abs(_h), 0, 0
                                    elif _l == 0 and _h < 0:
                                        _h, _k, _l = -_h, -_k, 0
                                    _p[0:3] = [str(_h), str(_k), str(_l)]
                                    _f.write(" ".join(_p) + "\n")
                                except ValueError:
                                    _f.write(_line)
                            else:
                                _f.write(_line)
                except OSError:
                    pass

                result_data = self._apply_deduplicate(result_data, task.params)
                result_data = self._apply_angle_zeroing(result_data, task.params)
                _t_angle_end = _gt2.time()
                _elapsed = _gt2.time() - _gt
                logger.info(
                    "get_results timing: total=%.3fs angle_zeroing=%.3fs",
                    _elapsed, _t_angle_end - _gt,
                )
                # 缓存结果，后续调用跳过文件 I/O
                with self._results_cache_lock:
                    self._results_cache[task_id] = result_data
                return result_data

        except Exception as e:
            return {"error": str(e)}
