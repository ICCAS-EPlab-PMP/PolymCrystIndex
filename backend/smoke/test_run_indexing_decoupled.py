"""Smoke test: run_indexing should not auto-generate glide batches."""

import asyncio
import sys
from pathlib import Path

_backend_dir = Path(__file__).parent.parent.resolve()
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from core import dependencies
from core.config import settings
from models.analysis import AnalysisParams, GlideBatchParams
from services.indexing_service import IndexingService
from services.task_manager import TaskManager, TaskStatus


class _FakeSystemConfigService:
    def get_max_omp_threads(self) -> int:
        return 8


class _FakeIndexer:
    def __init__(
        self,
        input_file: str,
        diffraction_file: str,
        callback,
        use_hdf5: bool,
        hdf5_file: str,
    ):
        self.input_file = input_file
        self.callback = callback

    def run(self) -> None:
        work_dir = Path(self.input_file).parent
        (work_dir / "cell_1.txt").write_text(
            "7.0 8.0 9.0 90.0 90.0 90.0\n", encoding="utf-8"
        )
        if self.callback is not None:
            self.callback.on_complete(
                0.01, {"best_cell": [7.0, 8.0, 9.0, 90.0, 90.0, 90.0]}
            )


def test_run_indexing_no_longer_auto_generates_glide(monkeypatch, tmp_path):
    user_result_dir = tmp_path / "userresult"
    upload_file = tmp_path / "observed_diffraction.txt"
    upload_file.write_text("0.1 0.0\n0.2 10.0\n", encoding="utf-8")

    params = AnalysisParams(
        steps=2,
        generations=1,
        mergeNearbyEnabled=False,
        glideBatches=[GlideBatchParams(label="g1", nA=1.0, nB=0.5, l0=2.0)],
    )
    task_manager = TaskManager()
    task = asyncio.run(task_manager.create_task("smoke-user", str(upload_file), params))
    service = IndexingService(task_manager)

    def _fake_postprocess(work_dir: str, step: int) -> bool:
        Path(work_dir, "outputMiller.txt").write_text(
            "H K L q psi\n1 0 0 0.1 0.0\nvolume: 1.0\n", encoding="utf-8"
        )
        Path(work_dir, "FullMiller.txt").write_text("1 0 0 0.1 0.0\n", encoding="utf-8")
        return True

    def _unexpected_glide(*args, **kwargs):
        raise AssertionError(
            "run_indexing() should not auto-trigger glide batch generation"
        )

    monkeypatch.setattr(settings, "USER_RESULT_DIR", str(user_result_dir))
    monkeypatch.setattr(
        dependencies, "get_system_config_service", lambda: _FakeSystemConfigService()
    )
    monkeypatch.setattr(
        "services.indexing_service.ensure_fortran_binaries",
        lambda: (Path("opt"), Path("post")),
    )
    monkeypatch.setattr(
        "services.indexing_service.FiberDiffractionIndexer", _FakeIndexer
    )
    monkeypatch.setattr(service, "_run_miller_postprocess", _fake_postprocess)
    monkeypatch.setattr(
        service, "_generate_glide_fullmiller_batches", _unexpected_glide
    )

    result = asyncio.run(service.run_indexing(task.id, str(upload_file), params))
    stored_task = asyncio.run(task_manager.get_task(task.id))
    work_dir = user_result_dir / "smoke-user" / task.id

    assert result["status"] == "completed"
    assert "glideBatches" not in result
    assert stored_task is not None
    assert stored_task.status == TaskStatus.COMPLETED
    assert not (work_dir / "glide_batches").exists()
