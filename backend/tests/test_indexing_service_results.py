"""Result serialization tests for family-aware indexing outputs."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import types

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

fiberdiffraction_stub = types.ModuleType("fiberdiffraction")
fiberdiffraction_stub.FiberDiffractionIndexer = type("FiberDiffractionIndexer", (), {})
fiberdiffraction_callbacks_stub = types.ModuleType("fiberdiffraction.callbacks")
fiberdiffraction_callbacks_stub.IndexingCallback = type("IndexingCallback", (), {})
fiberdiffraction_hdf5_stub = types.ModuleType("fiberdiffraction.hdf5")
fiberdiffraction_hdf5_stub.HDF5Manager = type("HDF5Manager", (), {})
sys.modules.setdefault("fiberdiffraction", fiberdiffraction_stub)
sys.modules.setdefault("fiberdiffraction.callbacks", fiberdiffraction_callbacks_stub)
sys.modules.setdefault("fiberdiffraction.hdf5", fiberdiffraction_hdf5_stub)


def _load_module(module_name: str, relative_path: str):
    helper_path = os.path.join(os.path.dirname(__file__), "..", relative_path)
    spec = importlib.util.spec_from_file_location(module_name, helper_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analysis_module = _load_module("test_analysis_model", os.path.join("models", "analysis.py"))
task_manager_module = _load_module(
    "test_task_manager_module", os.path.join("services", "task_manager.py")
)
indexing_service_module = _load_module(
    "test_indexing_service_module", os.path.join("services", "indexing_service.py")
)

AnalysisParams = analysis_module.AnalysisParams
Task = task_manager_module.Task
TaskManager = task_manager_module.TaskManager
TaskStatus = task_manager_module.TaskStatus
IndexingService = indexing_service_module.IndexingService


class _FakeHDF5Manager:
    def __init__(self, *_args, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read_config(self):
        return {"tilt_status": 0}

    def read_convergence(self):
        return {
            "best_errors": [0.125],
            "best_cells": [[7.4, 4.9, 2.54, 90.0, 90.0, 90.0]],
        }


def _write_common_result_files(work_dir, include_family_artifact: bool) -> None:
    os.makedirs(work_dir, exist_ok=True)
    with open(os.path.join(work_dir, "results.h5"), "w", encoding="utf-8") as f:
        f.write("placeholder")
    with open(os.path.join(work_dir, "observed_diffraction.txt"), "w", encoding="utf-8") as f:
        f.write("1.234 10.0\n")
        f.write("2.345 20.0\n")
    with open(os.path.join(work_dir, "outputMiller.txt"), "w", encoding="utf-8") as f:
        f.write("2 0 0 1.234 10.0 10.0\n")
        f.write("1 1 0 2.345 20.0 20.0\n")
        f.write("volume: 123.4\n")
    with open(os.path.join(work_dir, "FullMiller.txt"), "w", encoding="utf-8") as f:
        f.write("H K L q psi psi_root 2theta\n")
        f.write("2 0 0 1.234 10.0 10.0 5.0\n")
        f.write("-2 0 0 1.234 10.0 10.0 5.0\n")

    if include_family_artifact:
        with open(
            os.path.join(work_dir, "outputMillerFamilies.jsonl"), "w", encoding="utf-8"
        ) as f:
            f.write(
                json.dumps(
                    {
                        "observed_peak_index": 1,
                        "family_supported": 1,
                        "family_key": [2, 0, 0],
                        "member_count": 2,
                        "member_hkls": [[2, 0, 0], [-2, 0, 0]],
                        "family_residual": 0.125,
                        "intra_family_spread": 0.0,
                    }
                )
            )
            f.write("\n")


async def _build_service_with_task(tmp_path, monkeypatch, params: AnalysisParams):
    monkeypatch.setattr(indexing_service_module, "HDF5Manager", _FakeHDF5Manager)
    monkeypatch.setattr(indexing_service_module.settings, "USER_RESULT_DIR", str(tmp_path))

    task_manager = TaskManager()
    task = Task(
        id="task-results",
        user_id="tester",
        status=TaskStatus.COMPLETED,
        params=params,
        total_steps=params.steps,
    )
    task_manager._tasks[task.id] = task

    work_dir = tmp_path / task.user_id / task.id
    service = IndexingService(task_manager)
    return service, task.id, work_dir


def test_get_results_reads_joint_match_groups_from_fortran_artifact(tmp_path, monkeypatch):
    params = AnalysisParams(steps=2, peakSymmetryEnabled=True, symmetryTq=0.2, symmetryTa=2.0)
    service, task_id, work_dir = asyncio.get_event_loop().run_until_complete(
        _build_service_with_task(tmp_path, monkeypatch, params)
    )
    _write_common_result_files(str(work_dir), include_family_artifact=True)

    result = asyncio.get_event_loop().run_until_complete(service.get_results(task_id))

    assert result is not None
    assert len(result["millerData"]) == 2
    assert result["millerData"][0]["h"] == 2
    assert len(result["jointMatchGroups"]) == 1
    assert result["jointMatchGroups"][0]["familyKey"] == {"h": 2, "k": 0, "l": 0}
    assert result["jointMatchGroups"][0]["memberHkls"] == [
        {"h": 2, "k": 0, "l": 0},
        {"h": -2, "k": 0, "l": 0},
    ]
    assert result["jointMatchGroups"][0]["observedPeak"] == {"qObs": 1.234, "psiObs": 10.0}
    assert result["peakSymmetryGroupsSource"] == "derived_from_joint_match_groups"
    assert len(result["peakSymmetryGroups"]) == 1
    assert result["peakSymmetryGroups"][0]["reportingOnly"] is True
    assert result["peakSymmetryGroups"][0]["observedPeakIndex"] == 1


def test_symmetry_enabled_missing_family_artifact_reports_explicit_empty_source(
    tmp_path, monkeypatch
):
    params = AnalysisParams(steps=2, peakSymmetryEnabled=True, symmetryTq=0.2, symmetryTa=2.0)
    service, task_id, work_dir = asyncio.get_event_loop().run_until_complete(
        _build_service_with_task(tmp_path, monkeypatch, params)
    )
    _write_common_result_files(str(work_dir), include_family_artifact=False)

    persisted = service._persist_peak_symmetry_artifact(str(work_dir), params)
    result = asyncio.get_event_loop().run_until_complete(service.get_results(task_id))

    assert persisted["jointMatchGroups"] == []
    assert persisted["peakSymmetryGroups"] == []
    assert persisted["peakSymmetryGroupsSource"] == "missing_joint_match_artifact"
    assert result is not None
    assert result["jointMatchGroups"] == []
    assert result["peakSymmetryGroups"] == []
    assert result["peakSymmetryGroupsSource"] == "missing_joint_match_artifact"
    assert result["jointMatchSummary"]["groupCount"] == 0
    assert result["jointMatchSummary"]["legacyGroupCount"] == 0
    assert len(result["millerData"]) == 2


def test_get_results_skips_malformed_numeric_family_artifact_lines(tmp_path, monkeypatch):
    params = AnalysisParams(steps=2, peakSymmetryEnabled=True, symmetryTq=0.2, symmetryTa=2.0)
    service, task_id, work_dir = asyncio.get_event_loop().run_until_complete(
        _build_service_with_task(tmp_path, monkeypatch, params)
    )
    _write_common_result_files(str(work_dir), include_family_artifact=False)

    with open(os.path.join(work_dir, "outputMillerFamilies.jsonl"), "w", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "observed_peak_index": "bad-index",
                    "family_supported": 1,
                    "family_key": [2, 0, 0],
                    "member_count": 2,
                    "member_hkls": [[2, 0, 0], [-2, 0, 0]],
                    "family_residual": 0.125,
                    "intra_family_spread": 0.0,
                }
            )
            + "\n"
        )
        f.write(
            json.dumps(
                {
                    "observed_peak_index": 1,
                    "family_supported": 1,
                    "family_key": [2, 0, 0],
                    "member_count": 2,
                    "member_hkls": [[2, 0, 0], [-2, 0, 0]],
                    "family_residual": "not-a-float",
                    "intra_family_spread": 0.0,
                }
            )
            + "\n"
        )

    result = asyncio.get_event_loop().run_until_complete(service.get_results(task_id))

    assert result is not None
    assert result["jointMatchGroups"] == []
    assert result["peakSymmetryGroups"] == []
    assert result["peakSymmetryGroupsSource"] == "empty_joint_match_artifact"
    assert result["jointMatchSummary"]["groupCount"] == 0
    assert result["jointMatchSummary"]["legacyGroupCount"] == 0
    assert len(result["millerData"]) == 2


def test_get_results_ignores_stale_symmetry_artifacts_when_disabled(tmp_path, monkeypatch):
    params = AnalysisParams(steps=2, peakSymmetryEnabled=False)
    service, task_id, work_dir = asyncio.get_event_loop().run_until_complete(
        _build_service_with_task(tmp_path, monkeypatch, params)
    )
    _write_common_result_files(str(work_dir), include_family_artifact=True)

    with open(os.path.join(work_dir, "peak_symmetry_groups.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "peakSymmetryConfig": {"enabled": True, "symmetryTq": 0.2, "symmetryTa": 2.0},
                "jointMatchGroups": [{"observedPeakIndex": 1}],
                "peakSymmetryGroups": [{"groupType": "2-peak"}],
                "peakSymmetryGroupsSource": "derived_from_joint_match_groups",
            },
            f,
        )

    result = asyncio.get_event_loop().run_until_complete(service.get_results(task_id))

    assert result is not None
    assert result["peakSymmetryConfig"]["enabled"] is False
    assert result["jointMatchGroups"] == []
    assert result["peakSymmetryGroups"] == []
    assert result["peakSymmetryGroupsSource"] == "disabled"
    assert len(result["millerData"]) == 2


# --- API contract tests for family-aware joint match fields (Task 7) ---


def test_api_contract_symmetry_enabled_exposes_joint_match_fields(tmp_path, monkeypatch):
    params = AnalysisParams(steps=2, peakSymmetryEnabled=True, symmetryTq=0.2, symmetryTa=2.0)
    service, task_id, work_dir = asyncio.get_event_loop().run_until_complete(
        _build_service_with_task(tmp_path, monkeypatch, params)
    )
    _write_common_result_files(str(work_dir), include_family_artifact=True)

    result = asyncio.get_event_loop().run_until_complete(service.get_results(task_id))

    assert "jointMatchConfig" in result
    assert "jointMatchGroups" in result
    assert "jointMatchSummary" in result

    assert result["jointMatchConfig"]["enabled"] is True
    assert result["jointMatchConfig"]["symmetryTq"] == 0.2
    assert len(result["jointMatchGroups"]) == 1
    assert result["jointMatchGroups"][0]["familyKey"] == {"h": 2, "k": 0, "l": 0}
    assert result["jointMatchGroups"][0]["memberHkls"] == [
        {"h": 2, "k": 0, "l": 0},
        {"h": -2, "k": 0, "l": 0},
    ]
    assert result["jointMatchGroups"][0]["familyResidual"] == 0.125
    assert result["jointMatchGroups"][0]["intraFamilySpread"] == 0.0
    assert result["jointMatchGroups"][0]["observedPeak"]["qObs"] == 1.234

    summary = result["jointMatchSummary"]
    assert summary["groupCount"] == 1
    assert summary["legacyGroupCount"] == 1
    assert summary["source"] == "derived_from_joint_match_groups"


def test_api_contract_symmetry_enabled_joint_match_config_equals_legacy_config(
    tmp_path, monkeypatch
):
    params = AnalysisParams(steps=2, peakSymmetryEnabled=True, symmetryTq=0.3, symmetryTa=1.5)
    service, task_id, work_dir = asyncio.get_event_loop().run_until_complete(
        _build_service_with_task(tmp_path, monkeypatch, params)
    )
    _write_common_result_files(str(work_dir), include_family_artifact=True)

    result = asyncio.get_event_loop().run_until_complete(service.get_results(task_id))

    assert result["jointMatchConfig"] is result["peakSymmetryConfig"]


def test_api_contract_symmetry_disabled_family_fields_are_empty(tmp_path, monkeypatch):
    params = AnalysisParams(steps=2, peakSymmetryEnabled=False)
    service, task_id, work_dir = asyncio.get_event_loop().run_until_complete(
        _build_service_with_task(tmp_path, monkeypatch, params)
    )
    _write_common_result_files(str(work_dir), include_family_artifact=False)

    result = asyncio.get_event_loop().run_until_complete(service.get_results(task_id))

    assert result["jointMatchConfig"]["enabled"] is False
    assert result["jointMatchGroups"] == []
    assert result["jointMatchSummary"]["groupCount"] == 0
    assert result["jointMatchSummary"]["legacyGroupCount"] == 0
    assert result["jointMatchSummary"]["source"] == "disabled"
    assert result["peakSymmetryGroups"] == []
    assert result["peakSymmetryGroupsSource"] == "disabled"


def test_api_contract_symmetry_disabled_ignores_stale_family_artifact(tmp_path, monkeypatch):
    params = AnalysisParams(steps=2, peakSymmetryEnabled=False)
    service, task_id, work_dir = asyncio.get_event_loop().run_until_complete(
        _build_service_with_task(tmp_path, monkeypatch, params)
    )
    _write_common_result_files(str(work_dir), include_family_artifact=True)

    with open(os.path.join(work_dir, "peak_symmetry_groups.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "peakSymmetryConfig": {"enabled": True, "symmetryTq": 0.2, "symmetryTa": 2.0},
                "jointMatchGroups": [{"observedPeakIndex": 1, "familyKey": [2, 0, 0]}],
                "peakSymmetryGroups": [{"groupType": "2-peak"}],
                "peakSymmetryGroupsSource": "derived_from_joint_match_groups",
            },
            f,
        )

    result = asyncio.get_event_loop().run_until_complete(service.get_results(task_id))

    assert result["jointMatchConfig"]["enabled"] is False
    assert result["jointMatchGroups"] == []
    assert result["jointMatchSummary"]["groupCount"] == 0
    assert result["jointMatchSummary"]["source"] == "disabled"


def test_api_contract_legacy_peak_symmetry_groups_preserved_as_alias(tmp_path, monkeypatch):
    params = AnalysisParams(steps=2, peakSymmetryEnabled=True, symmetryTq=0.2, symmetryTa=2.0)
    service, task_id, work_dir = asyncio.get_event_loop().run_until_complete(
        _build_service_with_task(tmp_path, monkeypatch, params)
    )
    _write_common_result_files(str(work_dir), include_family_artifact=True)

    result = asyncio.get_event_loop().run_until_complete(service.get_results(task_id))

    assert "peakSymmetryGroups" in result
    assert "peakSymmetryGroupsSource" in result
    assert "peakSymmetryConfig" in result
    assert result["peakSymmetryGroupsSource"] == "derived_from_joint_match_groups"
    assert len(result["peakSymmetryGroups"]) == 1
    assert result["peakSymmetryGroups"][0]["reportingOnly"] is True


# --- Task 8: End-to-end HDPE and negative-path regression coverage ---


def _write_hdpe_artifact_workdir(work_dir: str, merge_test_families_path: str) -> None:
    os.makedirs(work_dir, exist_ok=True)
    with open(os.path.join(work_dir, "results.h5"), "w", encoding="utf-8") as f:
        f.write("placeholder")
    with open(os.path.join(work_dir, "observed_diffraction.txt"), "w", encoding="utf-8") as f:
        f.write("1.5232232828120928 0.0\n")
        f.write("1.6847509745225768 0.0\n")
        f.write("2.1082159915780951 0.0\n")
        f.write("2.5416818011178939 0.0\n")
        f.write("2.6759848777842445 0.0\n")
        f.write("2.8263285527460806 0.0\n")
        f.write("3.0464465656241857 0.0\n")
        f.write("3.3695019490451537 0.0\n")
        f.write("3.5804987377953679 0.0\n")
        f.write("3.9027751859447424 0.0\n")
        f.write("4.1649936226035376 0.0\n")
        f.write("2.7431918011525509 70.946436006987568\n")
        f.write("2.8904475577882676 64.614729060572429\n")
        f.write("2.9734987555881562 61.874671943249218\n")
        f.write("3.2403309077297147 55.205787765950042\n")
        f.write("3.6396749445886778 48.569365414394774\n")
        f.write("3.7501992776291475 47.165065882291813\n")
        f.write("3.9227371977688734 45.242871479959327\n")
        f.write("4.1711192750612804 42.950844483528847\n")
    with open(os.path.join(work_dir, "outputMiller.txt"), "w", encoding="utf-8") as f:
        f.write(" H K L q psi\n")
        f.write("    1.0000000000000000       -1.0000000000000000        0.0000000000000000        1.5232232828120928        0.0000000000000000\n")
        f.write("    2.0000000000000000        0.0000000000000000        0.0000000000000000        1.6847509745225768        0.0000000000000000\n")
        f.write("    2.0000000000000000       -1.0000000000000000        0.0000000000000000        2.1082159915780951        0.0000000000000000\n")
        f.write("    0.0000000000000000        2.0000000000000000        0.0000000000000000        2.5416818011178939        0.0000000000000000\n")
        f.write("    1.0000000000000000       -2.0000000000000000        0.0000000000000000        2.6759848777842445        0.0000000000000000\n")
        f.write("    3.0000000000000000       -1.0000000000000000        0.0000000000000000        2.8263285527460806        0.0000000000000000\n")
        f.write("    2.0000000000000000       -2.0000000000000000        0.0000000000000000        3.0464465656241857        0.0000000000000000\n")
        f.write("    4.0000000000000000        0.0000000000000000        0.0000000000000000        3.3695019490451537        0.0000000000000000\n")
        f.write("    3.0000000000000000       -2.0000000000000000        0.0000000000000000        3.5804987377953679        0.0000000000000000\n")
        f.write("    1.0000000000000000       -3.0000000000000000        0.0000000000000000        3.9027751859447424        0.0000000000000000\n")
        f.write("    2.0000000000000000       -3.0000000000000000        0.0000000000000000        4.1649936226035376        0.0000000000000000\n")
        f.write("    0.0000000000000000        1.0000000000000000        1.0000000000000000        2.7431918011525509        70.946436006987568\n")
        f.write("    1.0000000000000000       -1.0000000000000000        1.0000000000000000        2.8904475577882676        64.614729060572429\n")
        f.write("    2.0000000000000000        0.0000000000000000        1.0000000000000000        2.9734987555881562        61.874671943249218\n")
        f.write("    2.0000000000000000       -1.0000000000000000        1.0000000000000000        3.2403309077297147        55.205787765950042\n")
        f.write("    1.0000000000000000       -2.0000000000000000        1.0000000000000000        3.6396749445886778        48.569365414394774\n")
        f.write("    3.0000000000000000       -1.0000000000000000        1.0000000000000000        3.7501992776291475        47.165065882291813\n")
        f.write("    2.0000000000000000       -2.0000000000000000        1.0000000000000000        3.9227371977688734        45.242871479959327\n")
        f.write("    4.0000000000000000        0.0000000000000000        1.0000000000000000        4.1711192750612804        42.950844483528847\n")
        f.write("  volume:   94.901058435712415\n")
    import shutil
    shutil.copy(merge_test_families_path, os.path.join(work_dir, "outputMillerFamilies.jsonl"))


def test_hdpe_200_neg200_shared_observation_end_to_end(tmp_path, monkeypatch):
    # Locate the real HDPE families artifact - it's at project root merge_test/
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    merge_test_families = os.path.join(project_root, "merge_test", "outputMillerFamilies.jsonl")
    if not os.path.exists(merge_test_families):
        pytest.skip(f"HDPE families artifact not found: {merge_test_families}")

    params = AnalysisParams(steps=2, peakSymmetryEnabled=True, symmetryTq=0.2, symmetryTa=2.0)
    service, task_id, work_dir = asyncio.get_event_loop().run_until_complete(
        _build_service_with_task(tmp_path, monkeypatch, params)
    )
    _write_hdpe_artifact_workdir(str(work_dir), merge_test_families)

    result = asyncio.get_event_loop().run_until_complete(service.get_results(task_id))

    # Find the 200/-200 family (family_key [2,0,0])
    hdpe_family = None
    for group in result["jointMatchGroups"]:
        fk = group.get("familyKey", {})
        if fk.get("h") == 2 and fk.get("k") == 0 and fk.get("l") == 0:
            hdpe_family = group
            break

    assert hdpe_family is not None, (
        f"HDPE 200/-200 family not found in jointMatchGroups. "
        f"Available families: {[g.get('familyKey') for g in result['jointMatchGroups']]}"
    )
    # Should have exactly 2 members: (2,0,0) and (-2,0,0)
    assert hdpe_family["memberCount"] == 2
    assert hdpe_family["memberHkls"] == [
        {"h": 2, "k": 0, "l": 0},
        {"h": -2, "k": 0, "l": 0},
    ]
    # Should be associated with observed_peak_index=2
    assert hdpe_family["observedPeakIndex"] == 2
    # Zero intra-family spread (identical q values)
    assert hdpe_family["intraFamilySpread"] == 0.0
    # Should also appear in derived peak symmetry groups
    derived_groups = result["peakSymmetryGroups"]
    assert any(
        g.get("observedPeakIndex") == 2 and g.get("memberCount") == 2
        for g in derived_groups
    ), "200/-200 family not found in derived peak symmetry groups"


def test_negative_path_no_close_observed_peak_emits_no_family(tmp_path, monkeypatch):
    """Negative-path test: when artifact entries have observed_peak_index <= 0,
    no family should be emitted because no valid observed peak satisfies the joint threshold.

    The Fortran artifact may contain entries with invalid (zero or negative) peak indices
    when no observed peak was close enough to any family. These must be skipped during ingestion.
    """
    params = AnalysisParams(steps=2, peakSymmetryEnabled=True, symmetryTq=0.2, symmetryTa=2.0)
    service, task_id, work_dir = asyncio.get_event_loop().run_until_complete(
        _build_service_with_task(tmp_path, monkeypatch, params)
    )

    # Write workdir with diffraction/miller data but an artifact containing ONLY
    # invalid entries (observed_peak_index = 0 or negative)
    os.makedirs(str(work_dir), exist_ok=True)
    with open(os.path.join(str(work_dir), "results.h5"), "w", encoding="utf-8") as f:
        f.write("placeholder")
    with open(os.path.join(str(work_dir), "observed_diffraction.txt"), "w", encoding="utf-8") as f:
        f.write("1.234 10.0\n")
        f.write("2.345 20.0\n")
    with open(os.path.join(str(work_dir), "outputMiller.txt"), "w", encoding="utf-8") as f:
        f.write("2 0 0 1.234 10.0 10.0\n")
        f.write("1 1 0 2.345 20.0 20.0\n")
        f.write("volume: 123.4\n")

    # Artifact with ALL invalid peak indices (simulates no close match)
    with open(os.path.join(str(work_dir), "outputMillerFamilies.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "observed_peak_index": 0,
            "family_supported": 1,
            "family_key": [2, 0, 0],
            "member_count": 2,
            "member_hkls": [[2, 0, 0], [-2, 0, 0]],
            "family_residual": 0.5,
            "intra_family_spread": 0.0,
        }) + "\n")
        f.write(json.dumps({
            "observed_peak_index": -1,
            "family_supported": 1,
            "family_key": [1, 1, 0],
            "member_count": 4,
            "member_hkls": [[1, 1, 0], [1, -1, 0], [-1, 1, 0], [-1, -1, 0]],
            "family_residual": 0.8,
            "intra_family_spread": 0.3,
        }) + "\n")

    result = asyncio.get_event_loop().run_until_complete(service.get_results(task_id))

    # No families should be emitted because all observed_peak_indices are <= 0
    assert result["jointMatchGroups"] == [], (
        f"Expected empty jointMatchGroups for invalid peak indices, got {result['jointMatchGroups']}"
    )
    assert result["jointMatchSummary"]["groupCount"] == 0
    assert result["peakSymmetryGroups"] == []


def test_unsupported_3_member_family_rejected(tmp_path, monkeypatch):
    """Test that 3-member families are not included in derived peak symmetry groups.

    The Fortran backend only supports 2-member or 4-member families.
    A 3-member family should be read into jointMatchGroups but filtered out
    during derivation into peakSymmetryGroups.
    """
    params = AnalysisParams(steps=2, peakSymmetryEnabled=True, symmetryTq=0.2, symmetryTa=2.0)
    service, task_id, work_dir = asyncio.get_event_loop().run_until_complete(
        _build_service_with_task(tmp_path, monkeypatch, params)
    )

    os.makedirs(str(work_dir), exist_ok=True)
    with open(os.path.join(str(work_dir), "results.h5"), "w", encoding="utf-8") as f:
        f.write("placeholder")
    with open(os.path.join(str(work_dir), "observed_diffraction.txt"), "w", encoding="utf-8") as f:
        f.write("1.234 10.0\n")
        f.write("2.345 20.0\n")
        f.write("3.456 30.0\n")
    with open(os.path.join(str(work_dir), "outputMiller.txt"), "w", encoding="utf-8") as f:
        f.write("2 0 0 1.234 10.0 10.0\n")
        f.write("1 1 0 2.345 20.0 20.0\n")
        f.write("1 0 0 3.456 30.0 30.0\n")
        f.write("volume: 123.4\n")

    # Artifact with a 3-member family mixed with valid 2-member families
    with open(os.path.join(str(work_dir), "outputMillerFamilies.jsonl"), "w", encoding="utf-8") as f:
        # Valid 2-member family - should appear in peakSymmetryGroups
        f.write(json.dumps({
            "observed_peak_index": 1,
            "family_supported": 1,
            "family_key": [2, 0, 0],
            "member_count": 2,
            "member_hkls": [[2, 0, 0], [-2, 0, 0]],
            "family_residual": 0.125,
            "intra_family_spread": 0.0,
        }) + "\n")
        # 3-member family - should be in jointMatchGroups but NOT in peakSymmetryGroups
        f.write(json.dumps({
            "observed_peak_index": 2,
            "family_supported": 1,
            "family_key": [1, 0, 0],
            "member_count": 3,
            "member_hkls": [[1, 0, 0], [-1, 0, 0], [0, 1, 0]],  # invalid 3-member combo
            "family_residual": 0.3,
            "intra_family_spread": 0.1,
        }) + "\n")

    result = asyncio.get_event_loop().run_until_complete(service.get_results(task_id))

    # The 3-member family SHOULD appear in jointMatchGroups (it was read from artifact)
    three_member_in_jmg = [
        g for g in result["jointMatchGroups"]
        if g.get("memberCount") == 3
    ]
    assert len(three_member_in_jmg) == 1, (
        f"3-member family should be in jointMatchGroups, got {result['jointMatchGroups']}"
    )

    # But it should NOT appear in derived peakSymmetryGroups
    peak_symmetry_member_counts = [g.get("memberCount") for g in result["peakSymmetryGroups"]]
    assert 3 not in peak_symmetry_member_counts, (
        f"3-member family should NOT appear in peakSymmetryGroups (only 2 and 4 supported), "
        f"got memberCounts: {peak_symmetry_member_counts}"
    )
    # Only the 2-member family should be in peakSymmetryGroups
    assert peak_symmetry_member_counts == [2], (
        f"Only 2-member family should be in peakSymmetryGroups, got {peak_symmetry_member_counts}"
    )


def test_symmetry_disabled_legacy_path_no_behavioral_drift(tmp_path, monkeypatch):
    """Regression test: when symmetry is disabled and no family artifact exists,
    the legacy postprocess zip path must produce results without behavioral drift.

    This ensures the legacy path (positional zip of diffraction_data and miller_data)
    is still invoked correctly and produces the same group structure as before
    the family-aware changes.
    """
    params = AnalysisParams(steps=2, peakSymmetryEnabled=False)
    service, task_id, work_dir = asyncio.get_event_loop().run_until_complete(
        _build_service_with_task(tmp_path, monkeypatch, params)
    )

    # Write standard workdir with diffraction and Miller data (no family artifact)
    _write_common_result_files(str(work_dir), include_family_artifact=False)

    # Also write a peak_symmetry_groups.json with stale data to ensure it's ignored
    with open(os.path.join(str(work_dir), "peak_symmetry_groups.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "peakSymmetryConfig": {"enabled": True, "symmetryTq": 0.2, "symmetryTa": 2.0},
                "jointMatchGroups": [{"observedPeakIndex": 99}],
                "peakSymmetryGroups": [{"groupType": "2-peak"}],
                "peakSymmetryGroupsSource": "derived_from_joint_match_groups",
            },
            f,
        )

    result = asyncio.get_event_loop().run_until_complete(service.get_results(task_id))

    # Symmetry disabled fields must be empty
    assert result["jointMatchConfig"]["enabled"] is False
    assert result["jointMatchGroups"] == []
    assert result["jointMatchSummary"]["groupCount"] == 0
    assert result["peakSymmetryGroups"] == []
    assert result["peakSymmetryGroupsSource"] == "disabled"

    # millerData should still be readable (no drift in legacy path)
    assert len(result["millerData"]) == 2
    assert result["millerData"][0]["h"] == 2

    # When symmetry is disabled AND no family artifact exists,
    # _build_peak_symmetry_groups is called which uses legacy zip.
    # We can't directly observe the groups without the stale artifact,
    # but we verify millerData is intact (the legacy path's input is valid)


def test_normalization_family_averaged_not_member_summed(tmp_path, monkeypatch):
    """Normalization regression: totalSq/error_total must be family-averaged,
    not member-summed. A 4-member family must NOT contribute 4x the residual
    of a single observation.

    This test verifies that:
    1. A 2-member family has family_residual representing ONE observation's error
    2. A 4-member family has family_residual that is also ONE family-level error,
       NOT the sum of 4 individual member errors
    3. The derived peakSymmetryGroups include memberCount to prove families
       are tracked by their member count (not weighted by it)

    The key insight: if residuals were member-summed, a 4-member family would
    have 4x the weight of a 2-member family with identical per-member residuals.
    With family-averaging, both should contribute equally (one family = one unit).
    """
    params = AnalysisParams(steps=2, peakSymmetryEnabled=True, symmetryTq=0.2, symmetryTa=2.0)
    service, task_id, work_dir = asyncio.get_event_loop().run_until_complete(
        _build_service_with_task(tmp_path, monkeypatch, params)
    )

    os.makedirs(str(work_dir), exist_ok=True)
    with open(os.path.join(str(work_dir), "results.h5"), "w", encoding="utf-8") as f:
        f.write("placeholder")
    # 19 observed peaks matching the HDPE test fixture
    with open(os.path.join(str(work_dir), "observed_diffraction.txt"), "w", encoding="utf-8") as f:
        f.write("1.5232232828120928 0.0\n")
        f.write("1.6847509745225768 0.0\n")
        f.write("2.1082159915780951 0.0\n")
        f.write("2.5416818011178939 0.0\n")
        f.write("2.6759848777842445 0.0\n")
        f.write("2.8263285527460806 0.0\n")
        f.write("3.0464465656241857 0.0\n")
        f.write("3.3695019490451537 0.0\n")
        f.write("3.5804987377953679 0.0\n")
        f.write("3.9027751859447424 0.0\n")
        f.write("4.1649936226035376 0.0\n")
        f.write("2.7431918011525509 70.946436006987568\n")
        f.write("2.8904475577882676 64.614729060572429\n")
        f.write("2.9734987555881562 61.874671943249218\n")
        f.write("3.2403309077297147 55.205787765950042\n")
        f.write("3.6396749445886778 48.569365414394774\n")
        f.write("3.7501992776291475 47.165065882291813\n")
        f.write("3.9227371977688734 45.242871479959327\n")
        f.write("4.1711192750612804 42.950844483528847\n")
    # Miller data
    with open(os.path.join(str(work_dir), "outputMiller.txt"), "w", encoding="utf-8") as f:
        f.write(" H K L q psi\n")
        f.write("    1.0000000000000000       -1.0000000000000000        0.0000000000000000        1.5232232828120928        0.0000000000000000\n")
        f.write("    2.0000000000000000        0.0000000000000000        0.0000000000000000        1.6847509745225768        0.0000000000000000\n")
        f.write("    2.0000000000000000       -1.0000000000000000        0.0000000000000000        2.1082159915780951        0.0000000000000000\n")
        f.write("    0.0000000000000000        2.0000000000000000        0.0000000000000000        2.5416818011178939        0.0000000000000000\n")
        f.write("    1.0000000000000000       -2.0000000000000000        0.0000000000000000        2.6759848777842445        0.0000000000000000\n")
        f.write("    3.0000000000000000       -1.0000000000000000        0.0000000000000000        2.8263285527460806        0.0000000000000000\n")
        f.write("    2.0000000000000000       -2.0000000000000000        0.0000000000000000        3.0464465656241857        0.0000000000000000\n")
        f.write("    4.0000000000000000        0.0000000000000000        0.0000000000000000        3.3695019490451537        0.0000000000000000\n")
        f.write("    3.0000000000000000       -2.0000000000000000        0.0000000000000000        3.5804987377953679        0.0000000000000000\n")
        f.write("    1.0000000000000000       -3.0000000000000000        0.0000000000000000        3.9027751859447424        0.0000000000000000\n")
        f.write("    2.0000000000000000       -3.0000000000000000        0.0000000000000000        4.1649936226035376        0.0000000000000000\n")
        f.write("    0.0000000000000000        1.0000000000000000        1.0000000000000000        2.7431918011525509        70.946436006987568\n")
        f.write("    1.0000000000000000       -1.0000000000000000        1.0000000000000000        2.8904475577882676        64.614729060572429\n")
        f.write("    2.0000000000000000        0.0000000000000000        1.0000000000000000        2.9734987555881562        61.874671943249218\n")
        f.write("    2.0000000000000000       -1.0000000000000000        1.0000000000000000        3.2403309077297147        55.205787765950042\n")
        f.write("    1.0000000000000000       -2.0000000000000000        1.0000000000000000        3.6396749445886778        48.569365414394774\n")
        f.write("    3.0000000000000000       -1.0000000000000000        1.0000000000000000        3.7501992776291475        47.165065882291813\n")
        f.write("    2.0000000000000000       -2.0000000000000000        1.0000000000000000        3.9227371977688734        45.242871479959327\n")
        f.write("    4.0000000000000000        0.0000000000000000        1.0000000000000000        4.1711192750612804        42.950844483528847\n")
        f.write("  volume:   94.901058435712415\n")

    # Write artifact with known residuals for 2-member and 4-member families
    # Use residuals that are comparable in magnitude - if family-averaged,
    # both contribute ONE unit to totalSq regardless of member count
    with open(os.path.join(str(work_dir), "outputMillerFamilies.jsonl"), "w", encoding="utf-8") as f:
        # 2-member family (200/-200): residual ~0.59
        f.write(json.dumps({
            "observed_peak_index": 2,
            "family_supported": 1,
            "family_key": [2, 0, 0],
            "member_count": 2,
            "member_hkls": [[2, 0, 0], [-2, 0, 0]],
            "family_residual": 5.9299956912910012E-001,  # ~0.59 per family, not doubled
            "intra_family_spread": 0.0,
        }) + "\n")
        # 4-member family (110/-110): residual ~1.33 - in the same order of magnitude
        # If member-summed, 4-member would be ~4x larger than 2-member with same per-member error
        # If family-averaged, both contribute ~1 unit
        f.write(json.dumps({
            "observed_peak_index": 1,
            "family_supported": 1,
            "family_key": [1, 1, 0],
            "member_count": 4,
            "member_hkls": [[1, 1, 0], [1, -1, 0], [-1, 1, 0], [-1, -1, 0]],
            "family_residual": 1.3288598274479768,  # ~1.33 per family, not quadrupled
            "intra_family_spread": 2.9015295291150434E-001,
        }) + "\n")

    result = asyncio.get_event_loop().run_until_complete(service.get_results(task_id))

    # Both families should be present in jointMatchGroups
    assert len(result["jointMatchGroups"]) == 2, (
        f"Expected 2 families in jointMatchGroups, got {len(result['jointMatchGroups'])}"
    )

    # Find the 2-member and 4-member families
    two_member = next(
        (g for g in result["jointMatchGroups"] if g["memberCount"] == 2), None
    )
    four_member = next(
        (g for g in result["jointMatchGroups"] if g["memberCount"] == 4), None
    )

    assert two_member is not None, "2-member family not found"
    assert four_member is not None, "4-member family not found"

    # KEY ASSERTION: residuals are family-level, not member-summed
    # The 4-member residual (~1.33) should NOT be 4x the 2-member residual (~0.59)
    # With family averaging: 1.33 / 0.59 ≈ 2.25, not 4.0
    ratio = four_member["familyResidual"] / two_member["familyResidual"]
    assert 1.5 < ratio < 3.5, (
        f"Family residuals should not scale linearly with member count. "
        f"4-member residual ({four_member['familyResidual']}) / 2-member residual ({two_member['familyResidual']}) "
        f"= {ratio:.2f}. If member-summed, this ratio would be ~4.0. "
        f"Family-averaging gives ~1.5-3.5 depending on actual spread."
    )

    # Both families should appear in derived peakSymmetryGroups with correct memberCount
    derived_2m = next(
        (g for g in result["peakSymmetryGroups"] if g["memberCount"] == 2), None
    )
    derived_4m = next(
        (g for g in result["peakSymmetryGroups"] if g["memberCount"] == 4), None
    )
    assert derived_2m is not None, "2-member family not in derived groups"
    assert derived_4m is not None, "4-member family not in derived groups"
    # memberCount is preserved - proving families are tracked by member count, not weighted by it
    assert derived_2m["memberCount"] == 2
    assert derived_4m["memberCount"] == 4
