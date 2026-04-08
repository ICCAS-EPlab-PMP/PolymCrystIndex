from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Tuple

from core.config import settings


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _repo_root() -> Path:
    return _workspace_root().parent


def _fortran_source_dir() -> Path:
    return _workspace_root() / "fortrancode"


def _binary_names() -> Tuple[str, str]:
    if os.name == "nt":
        return "lm_opt2.exe", "lm_postprocess.exe"
    return "lm_opt2", "lm_postprocess"


def _fallback_output_dir() -> Path:
    return _repo_root() / "execute" / "fortran-runtime"


def _update_runtime_settings(opt_path: Path, post_path: Path) -> None:
    opt_str = str(opt_path.resolve())
    post_str = str(post_path.resolve())
    os.environ["FORTRAN_EXECUTABLE"] = opt_str
    os.environ["FORTRAN_POSTPROCESS_EXECUTABLE"] = post_str
    settings.FORTRAN_EXECUTABLE = opt_str
    settings.FORTRAN_POSTPROCESS_EXECUTABLE = post_str


def _configured_paths() -> Tuple[Path, Path]:
    return Path(settings.FORTRAN_EXECUTABLE), Path(settings.FORTRAN_POSTPROCESS_EXECUTABLE)


def _compile_binary(command: list[str], source_dir: Path, label: str) -> None:
    result = subprocess.run(
        command,
        cwd=str(source_dir),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        details = stderr or stdout or "unknown compiler error"
        raise RuntimeError(f"Failed to build {label}: {details}")


def ensure_fortran_binaries() -> Tuple[Path, Path]:
    configured_opt, configured_post = _configured_paths()
    if configured_opt.exists() and configured_post.exists():
        _update_runtime_settings(configured_opt, configured_post)
        return configured_opt, configured_post

    source_dir = _fortran_source_dir()
    if not source_dir.exists():
        raise RuntimeError(f"Fortran source directory not found: {source_dir}")

    gfortran = shutil.which("gfortran")
    if not gfortran:
        raise RuntimeError(
            "Fortran binaries are missing and gfortran is not available. "
            "Please install gfortran or provide FORTRAN_EXECUTABLE / FORTRAN_POSTPROCESS_EXECUTABLE."
        )

    opt_name, post_name = _binary_names()
    output_dir = _fallback_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    opt_path = output_dir / opt_name
    post_path = output_dir / post_name

    if not opt_path.exists():
        _compile_binary(
            [
                gfortran,
                "-O2",
                "-fopenmp",
                "-o",
                str(opt_path),
                "minpack.f90",
                "lm_opt2.f90",
            ],
            source_dir,
            "lm_opt2",
        )

    if not post_path.exists():
        _compile_binary(
            [
                gfortran,
                "-O2",
                "-o",
                str(post_path),
                "out.f90",
            ],
            source_dir,
            "lm_postprocess",
        )

    _update_runtime_settings(opt_path, post_path)
    return opt_path, post_path
