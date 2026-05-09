"""Smoke tests for shared post-process core reuse."""

import importlib
import sys
from pathlib import Path

_backend_dir = Path(__file__).parent.parent.resolve()
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import pytest

import services.indexing_service as indexing_service_module
from services.indexing_service import IndexingService
from services.task_manager import TaskManager


postprocess_core = indexing_service_module.postprocess_core


def test_shared_core_generates_glide_artifact_structure(monkeypatch, tmp_path):
    postprocess_core.write_cell_parameters(
        str(tmp_path / "cell_0.txt"),
        [7.0, 8.0, 9.0, 90.0, 92.0, 88.0],
    )
    (tmp_path / "input.txt").write_text("1.542\n", encoding="utf-8")
    (tmp_path / "observed_diffraction.txt").write_text("0.1 0.0\n", encoding="utf-8")

    def _fake_postprocess(work_dir: str, step: int) -> bool:
        Path(work_dir, "outputMiller.txt").write_text(
            "H K L q psi\n1 0 0 0.1 0.0\nvolume: 1.0\n", encoding="utf-8"
        )
        Path(work_dir, "FullMiller.txt").write_text("1 0 0 0.1 0.0\n", encoding="utf-8")
        return True

    monkeypatch.setattr(postprocess_core, "run_miller_postprocess", _fake_postprocess)

    generated = postprocess_core.generate_glide_fullmiller_batches(
        str(tmp_path),
        0,
        [{"index": 1, "label": "g1", "nA": 1.0, "nB": 0.5, "l0": 2.0}],
    )
    artifact = postprocess_core.read_glide_batch_artifact(str(tmp_path))

    assert generated["enabled"] is True
    assert artifact["enabled"] is True
    assert generated["groups"][0]["label"] == artifact["groups"][0]["label"] == "g1"
    assert generated["groups"][0]["directory"] == artifact["groups"][0]["directory"]
    assert (
        generated["groups"][0]["fullMillerFile"]
        == artifact["groups"][0]["fullMillerFile"]
    )
    assert (
        generated["groups"][0]["outputMillerFile"]
        == artifact["groups"][0]["outputMillerFile"]
    )
    assert artifact["groups"][0]["cellParams"] is not None
    for key, value in generated["groups"][0]["cellParams"].items():
        assert artifact["groups"][0]["cellParams"][key] == pytest.approx(
            value, abs=1e-9
        )
    assert generated["groups"][0]["fullMillerSize"] > 0
    assert generated["groups"][0]["outputMillerSize"] > 0


def test_manual_fullmiller_reuses_shared_bundle_reader(monkeypatch):
    service = IndexingService(TaskManager())
    bundle_calls = {"count": 0}
    expected_bundle = {
        "cellParams": {
            "a": 7.0,
            "b": 8.0,
            "c": 9.0,
            "alpha": 90.0,
            "beta": 90.0,
            "gamma": 90.0,
        },
        "volume": 504.0,
        "fullMillerContent": "1 0 0 0.1 0.0\n",
        "outputMillerContent": "H K L q psi\n1 0 0 0.1 0.0\n",
        "totalReflections": 1,
        "fullMillerSize": 16,
        "outputMillerSize": 30,
    }

    monkeypatch.setattr(service, "_run_miller_postprocess", lambda work_dir, step: True)

    def _fake_read_bundle(work_dir: str, step: int):
        bundle_calls["count"] += 1
        return expected_bundle

    monkeypatch.setattr(postprocess_core, "read_postprocess_bundle", _fake_read_bundle)

    result = service.run_manual_fullmiller(7.0, 8.0, 9.0, 90.0, 90.0, 90.0, 1.542)

    assert bundle_calls["count"] == 1
    assert result["success"] is True
    assert result["data"] == {
        "cellParams": expected_bundle["cellParams"],
        "volume": expected_bundle["volume"],
        "fullMillerContent": expected_bundle["fullMillerContent"],
        "outputMillerContent": expected_bundle["outputMillerContent"],
        "totalReflections": expected_bundle["totalReflections"],
    }
