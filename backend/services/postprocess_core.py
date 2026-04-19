"""Shared post-processing core for Miller outputs and glide batches."""

from __future__ import annotations

import glob
import math
import os
import re
import shutil
import subprocess
import time
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.fortran_runtime import ensure_fortran_binaries


class TaskCancelledException(Exception):
    """Custom exception for task cancellation."""
    pass


def resolve_cell_file(work_dir: str, step: int) -> Optional[str]:
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


def sanitize_glide_label(label: str, index: int) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", (label or "").strip())
    normalized = normalized.strip("._")
    return normalized or f"glide_{index:02d}"


def read_cell_parameters(cell_file: str) -> List[float]:
    with open(cell_file, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    if not first_line:
        raise ValueError(f"Cell file is empty: {cell_file}")
    values = [float(part) for part in first_line.split()]
    if len(values) < 6:
        raise ValueError(f"Cell file must contain at least 6 values: {cell_file}")
    return values


def write_cell_parameters(cell_file: str, cell_values: List[float]) -> None:
    with open(cell_file, "w", encoding="utf-8") as f:
        f.write(" ".join(f"{value:.10f}" for value in cell_values))
        f.write("\n")


def cell_values_to_dict(cell_values: List[float]) -> Dict[str, float]:
    return {
        "a": cell_values[0],
        "b": cell_values[1],
        "c": cell_values[2],
        "alpha": cell_values[3],
        "beta": cell_values[4],
        "gamma": cell_values[5],
    }


def compute_cell_volume(cell_values: List[float]) -> Optional[float]:
    alpha_r = math.radians(cell_values[3])
    beta_r = math.radians(cell_values[4])
    gamma_r = math.radians(cell_values[5])
    cos_a = math.cos(alpha_r)
    cos_b = math.cos(beta_r)
    cos_g = math.cos(gamma_r)
    v_sq = 1 - cos_a**2 - cos_b**2 - cos_g**2 + 2 * cos_a * cos_b * cos_g
    if v_sq <= 0:
        return None
    return cell_values[0] * cell_values[1] * cell_values[2] * math.sqrt(v_sq)


def _cell_to_lattice_vectors(cell_params: List[float]) -> List[List[float]]:
    a, b, c, alpha_deg, beta_deg, gamma_deg = cell_params[:6]
    alpha = math.radians(alpha_deg)
    beta = math.radians(beta_deg)
    gamma = math.radians(gamma_deg)
    sin_gamma = math.sin(gamma)
    if abs(sin_gamma) < 1e-12:
        raise ValueError("gamma angle is too close to 0 or 180 degrees for glide shear")

    a_vec = [a, 0.0, 0.0]
    b_vec = [b * math.cos(gamma), b * sin_gamma, 0.0]
    c_x = c * math.cos(beta)
    c_y = c * (math.cos(alpha) - math.cos(beta) * math.cos(gamma)) / sin_gamma
    c_z_sq = max(c * c - c_x * c_x - c_y * c_y, 0.0)
    c_vec = [c_x, c_y, math.sqrt(c_z_sq)]
    return [a_vec, b_vec, c_vec]


def _vector_length(vector: List[float]) -> float:
    return math.sqrt(sum(component * component for component in vector))


def _dot_product(left: List[float], right: List[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _angle_between(left: List[float], right: List[float]) -> float:
    left_norm = _vector_length(left)
    right_norm = _vector_length(right)
    if left_norm < 1e-12 or right_norm < 1e-12:
        raise ValueError("glide shear produced a degenerate lattice vector")
    cosine = _dot_product(left, right) / (left_norm * right_norm)
    cosine = max(-1.0, min(1.0, cosine))
    return math.degrees(math.acos(cosine))


def apply_glide_to_cell(
    cell_params: List[float], n_a: float, n_b: float, l0: float
) -> List[float]:
    if abs(l0) < 1e-12:
        raise ValueError("glide batch parameter l0 cannot be 0")

    a_vec, b_vec, c_vec = _cell_to_lattice_vectors(cell_params)
    a_scale = n_a / l0
    b_scale = n_b / l0

    a_prime_vec = [
        a_component + a_scale * c_component
        for a_component, c_component in zip(a_vec, c_vec)
    ]
    b_prime_vec = [
        b_component + b_scale * c_component
        for b_component, c_component in zip(b_vec, c_vec)
    ]
    c_prime_vec = list(c_vec)

    return [
        _vector_length(a_prime_vec),
        _vector_length(b_prime_vec),
        cell_params[2],
        _angle_between(b_prime_vec, c_prime_vec),
        _angle_between(a_prime_vec, c_prime_vec),
        _angle_between(a_prime_vec, b_prime_vec),
    ]


@dataclass
class GlideBatchSpec:
    index: int
    label: str
    nA: float
    nB: float
    l0: float


def build_glide_batch_payload(raw_batches: Optional[List[Any]]) -> List[Dict[str, Any]]:
    payload: List[Dict[str, Any]] = []
    for index, batch in enumerate(raw_batches or [], start=1):
        payload.append(
            {
                "index": index,
                "label": sanitize_glide_label(getattr(batch, "label", ""), index),
                "nA": float(getattr(batch, "nA", 0.0)),
                "nB": float(getattr(batch, "nB", 0.0)),
                "l0": float(getattr(batch, "l0", 0.0)),
            }
        )
    return payload


def run_miller_postprocess(work_dir: str, step: int, stop_event: Optional[threading.Event] = None) -> bool:
    """Run Fortran Miller post-process in a prepared work directory."""
    _, postprocess_path = ensure_fortran_binaries()
    postprocess_exe = str(postprocess_path)

    if not os.path.exists(postprocess_exe):
        print(
            f"[PostProcess] Warning: Post-process executable not found at {postprocess_exe}"
        )
        return False

    input_file = os.path.join(work_dir, "input.txt")
    diffraction_file = os.path.join(work_dir, "observed_diffraction.txt")
    cell_file = resolve_cell_file(work_dir, step)

    if not os.path.exists(input_file):
        print("[PostProcess] Warning: input.txt not found")
        return False
    if not os.path.exists(diffraction_file):
        print("[PostProcess] Warning: observed_diffraction.txt not found")
        return False
    if not cell_file:
        print(
            f"[PostProcess] Warning: cell_{step}.txt not found in work_dir or result/"
        )
        return False

    cell_file_name = os.path.basename(cell_file)
    cmd = [
        postprocess_exe,
        "-i",
        "input.txt",
        "-d",
        "observed_diffraction.txt",
        "-c",
        cell_file_name,
    ]
    print(f"[PostProcess] Running: {' '.join(cmd)}")

    if os.path.dirname(cell_file) != work_dir:
        shutil.copy2(cell_file, os.path.join(work_dir, cell_file_name))

    process = subprocess.Popen(cmd, cwd=work_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    while process.poll() is None:
        if stop_event and stop_event.is_set():
            process.kill()
            process.wait()
            raise TaskCancelledException("Task cancelled during miller postprocess")
        time.sleep(0.1)
    stdout, stderr = process.communicate()
    returncode = process.returncode

    output_miller_file = os.path.join(work_dir, "outputMiller.txt")
    full_miller_file = os.path.join(work_dir, "FullMiller.txt")

    if (
        returncode == 0
        and os.path.exists(output_miller_file)
        and os.path.exists(full_miller_file)
    ):
        print(
            "[PostProcess] Successfully generated FullMiller.txt and outputMiller.txt"
        )
        return True

    print(f"[PostProcess] Warning: Post-process returned code {returncode}")
    if stdout:
        print(f"[PostProcess] stdout: {stdout}")
    if stderr:
        print(f"[PostProcess] stderr: {stderr}")
    if returncode == 0:
        print(
            "[PostProcess] Warning: Post-process exited successfully but output files were not generated"
        )
    return False


def read_glide_batch_artifact(work_dir: str) -> Dict[str, Any]:
    batch_root = os.path.join(work_dir, "glide_batches")
    if not os.path.isdir(batch_root):
        return {"enabled": False, "groups": []}

    groups: List[Dict[str, Any]] = []
    for label in sorted(os.listdir(batch_root)):
        batch_dir = os.path.join(batch_root, label)
        if not os.path.isdir(batch_dir):
            continue
        full_miller_path = os.path.join(batch_dir, "FullMiller.txt")
        output_miller_path = os.path.join(batch_dir, "outputMiller.txt")
        cell_file = resolve_cell_file(batch_dir, 0) or resolve_cell_file(batch_dir, 1)
        if cell_file is None:
            matches = glob.glob(os.path.join(batch_dir, "cell_*.txt"))
            cell_file = matches[0] if matches else None

        cell_params = None
        if cell_file and os.path.exists(cell_file):
            try:
                cell_params = cell_values_to_dict(read_cell_parameters(cell_file))
            except Exception:
                cell_params = None

        groups.append(
            {
                "label": label,
                "directory": os.path.relpath(batch_dir, work_dir).replace("\\", "/"),
                "fullMillerFile": os.path.relpath(full_miller_path, work_dir).replace(
                    "\\", "/"
                )
                if os.path.exists(full_miller_path)
                else None,
                "outputMillerFile": os.path.relpath(
                    output_miller_path, work_dir
                ).replace("\\", "/")
                if os.path.exists(output_miller_path)
                else None,
                "fullMillerSize": os.path.getsize(full_miller_path)
                if os.path.exists(full_miller_path)
                else 0,
                "outputMillerSize": os.path.getsize(output_miller_path)
                if os.path.exists(output_miller_path)
                else 0,
                "cellParams": cell_params,
            }
        )

    return {
        "enabled": len(groups) > 0,
        "batchRoot": os.path.relpath(batch_root, work_dir).replace("\\", "/"),
        "groups": groups,
    }


def read_postprocess_bundle(work_dir: str, step: int) -> Dict[str, Any]:
    cell_file = resolve_cell_file(work_dir, step)
    full_miller_path = os.path.join(work_dir, "FullMiller.txt")
    output_miller_path = os.path.join(work_dir, "outputMiller.txt")

    full_miller_content = ""
    full_miller_size = 0
    if os.path.exists(full_miller_path):
        full_miller_size = os.path.getsize(full_miller_path)
        with open(full_miller_path, "r", encoding="utf-8") as f:
            full_miller_content = f.read()

    output_miller_content = ""
    if os.path.exists(output_miller_path):
        with open(output_miller_path, "r", encoding="utf-8") as f:
            output_miller_content = f.read()

    cell_values = read_cell_parameters(cell_file) if cell_file else None
    full_miller_lines = [
        line
        for line in full_miller_content.splitlines()
        if line.strip() and not line.strip().startswith(("H", "h", "v", "V", "volume"))
    ]

    return {
        "cellFile": cell_file,
        "cellValues": cell_values,
        "cellParams": cell_values_to_dict(cell_values) if cell_values else None,
        "volume": compute_cell_volume(cell_values) if cell_values else None,
        "fullMillerPath": full_miller_path,
        "outputMillerPath": output_miller_path,
        "fullMillerContent": full_miller_content,
        "outputMillerContent": output_miller_content,
        "fullMillerSize": full_miller_size,
        "outputMillerSize": os.path.getsize(output_miller_path)
        if os.path.exists(output_miller_path)
        else 0,
        "totalReflections": len(full_miller_lines),
    }


def generate_glide_fullmiller_batches(
    work_dir: str,
    step: int,
    glide_batches: List[Dict[str, Any]],
) -> Dict[str, Any]:
    batch_root = os.path.join(work_dir, "glide_batches")
    if not glide_batches:
        if os.path.isdir(batch_root):
            shutil.rmtree(batch_root)
        return {"enabled": False, "batchRoot": batch_root, "groups": []}

    base_input = os.path.join(work_dir, "input.txt")
    base_diffraction = os.path.join(work_dir, "observed_diffraction.txt")
    base_cell_file = resolve_cell_file(work_dir, step)
    if not os.path.exists(base_input):
        raise FileNotFoundError(f"input.txt not found for glide batches: {base_input}")
    if not os.path.exists(base_diffraction):
        raise FileNotFoundError(
            f"observed_diffraction.txt not found for glide batches: {base_diffraction}"
        )
    if not base_cell_file:
        raise FileNotFoundError(f"cell_{step}.txt not found for glide batches")

    base_cell = read_cell_parameters(base_cell_file)
    tilt_tail = base_cell[6:]
    Path(batch_root).mkdir(parents=True, exist_ok=True)

    groups: List[Dict[str, Any]] = []
    used_labels = set()
    for batch in glide_batches:
        label = batch["label"]
        if label in used_labels:
            label = f"{label}_{batch['index']:02d}"
        used_labels.add(label)

        batch_dir = os.path.join(batch_root, label)
        if os.path.isdir(batch_dir):
            shutil.rmtree(batch_dir)
        Path(batch_dir).mkdir(parents=True, exist_ok=True)

        shutil.copy2(base_input, os.path.join(batch_dir, "input.txt"))
        shutil.copy2(
            base_diffraction, os.path.join(batch_dir, "observed_diffraction.txt")
        )

        transformed_cell = apply_glide_to_cell(
            base_cell, batch["nA"], batch["nB"], batch["l0"]
        )
        output_cell = transformed_cell + tilt_tail
        write_cell_parameters(os.path.join(batch_dir, f"cell_{step}.txt"), output_cell)

        if not run_miller_postprocess(batch_dir, step):
            raise RuntimeError(
                f"Failed to generate glide FullMiller for batch '{label}'"
            )

        bundle = read_postprocess_bundle(batch_dir, step)
        if bundle["fullMillerSize"] <= 0 or bundle["outputMillerSize"] <= 0:
            raise RuntimeError(f"Glide batch '{label}' generated empty Miller output")

        groups.append(
            {
                "index": batch["index"],
                "label": label,
                "directory": os.path.relpath(batch_dir, work_dir).replace("\\", "/"),
                "fullMillerFile": os.path.relpath(
                    bundle["fullMillerPath"], work_dir
                ).replace("\\", "/"),
                "outputMillerFile": os.path.relpath(
                    bundle["outputMillerPath"], work_dir
                ).replace("\\", "/"),
                "fullMillerSize": bundle["fullMillerSize"],
                "outputMillerSize": bundle["outputMillerSize"],
                "input": {
                    "nA": batch["nA"],
                    "nB": batch["nB"],
                    "l0": batch["l0"],
                },
                "cellParams": cell_values_to_dict(transformed_cell),
            }
        )

    return {
        "enabled": True,
        "batchRoot": os.path.relpath(batch_root, work_dir).replace("\\", "/"),
        "baseCell": cell_values_to_dict(base_cell),
        "groups": groups,
    }
