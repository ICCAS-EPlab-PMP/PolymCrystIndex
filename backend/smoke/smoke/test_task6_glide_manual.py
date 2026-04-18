import sys
from pathlib import Path
from types import SimpleNamespace

_backend_dir = Path(__file__).parent.parent.resolve()
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import pytest

import services.indexing_service as indexing_service_module
from services.indexing_service import IndexingService
from services.task_manager import TaskManager

postprocess_core = indexing_service_module.postprocess_core


# --- Model validation tests ---


def test_manual_batch_request_model():
    from models.analysis import ManualBatchRequest, ManualBatchItem

    req = ManualBatchRequest(
        groups=[
            ManualBatchItem(a=7.4, b=4.93, c=2.54, alpha=90, beta=90, gamma=90),
            ManualBatchItem(
                a=5.0, b=6.0, c=7.0, alpha=90, beta=90, gamma=90, wavelength=1.0
            ),
        ]
    )
    assert len(req.groups) == 2
    assert req.groups[0].a == 7.4
    assert req.groups[1].wavelength == 1.0


def test_manual_batch_request_min_one_group():
    from models.analysis import ManualBatchRequest

    with pytest.raises(Exception):
        ManualBatchRequest(groups=[])


def test_glide_batch_request_model():
    from models.analysis import GlideBatchRequest, GlideBatchParams

    req = GlideBatchRequest(
        a=7.4,
        b=4.93,
        c=2.54,
        alpha=90,
        beta=90,
        gamma=90,
        glideGroups=[
            GlideBatchParams(nA=0.5, nB=0, l0=0.5),
            GlideBatchParams(nA=1.0, nB=0.5, l0=2.0, label="shear_B"),
        ],
    )
    assert req.a == 7.4
    assert len(req.glideGroups) == 2


def test_glide_batch_request_requires_groups():
    from models.analysis import GlideBatchRequest

    with pytest.raises(Exception):
        GlideBatchRequest(
            a=7.4,
            b=4.93,
            c=2.54,
            alpha=90,
            beta=90,
            gamma=90,
            glideGroups=[],
        )


def test_api_routes_registered():
    from fastapi.routing import APIRoute
    from backend.main import app

    paths = [r.path for r in app.routes if isinstance(r, APIRoute)]
    assert "/api/analysis/manual-batch" in paths
    assert "/api/analysis/glide-batch" in paths


# --- Shared test helpers ---


def _make_fake_bundle(cell_a, cell_b, cell_c, cell_alpha, cell_beta, cell_gamma):
    return {
        "cellParams": {
            "a": cell_a,
            "b": cell_b,
            "c": cell_c,
            "alpha": cell_alpha,
            "beta": cell_beta,
            "gamma": cell_gamma,
        },
        "volume": cell_a * cell_b * cell_c,
        "fullMillerContent": f"1 0 0 0.1 0.0\n0 1 0 0.2 10.0\n",
        "outputMillerContent": f"H K L q psi\n1 0 0 0.1 0.0\nvolume: {cell_a * cell_b * cell_c}\n",
        "totalReflections": 2,
        "fullMillerSize": 30,
        "outputMillerSize": 40,
    }


def _fake_generate_glide(work_dir, step, batches):
    groups = []
    for b in batches:
        transformed = postprocess_core.apply_glide_to_cell(
            [7.4, 4.93, 2.54, 90.0, 90.0, 90.0], b["nA"], b["nB"], b["l0"]
        )
        groups.append(
            {
                "index": b["index"],
                "label": b["label"],
                "directory": f"glide_batches/{b['label']}",
                "fullMillerFile": f"glide_batches/{b['label']}/FullMiller.txt",
                "outputMillerFile": f"glide_batches/{b['label']}/outputMiller.txt",
                "fullMillerSize": 30,
                "outputMillerSize": 40,
                "input": {"nA": b["nA"], "nB": b["nB"], "l0": b["l0"]},
                "cellParams": postprocess_core.cell_values_to_dict(transformed),
            }
        )
    return {
        "enabled": True,
        "batchRoot": "glide_batches",
        "baseCell": postprocess_core.cell_values_to_dict(
            [7.4, 4.93, 2.54, 90.0, 90.0, 90.0]
        ),
        "groups": groups,
    }


def _patch_service_core(monkeypatch):
    """Apply standard monkeypatches for service-level tests."""
    service = IndexingService(TaskManager())
    monkeypatch.setattr(service, "_run_miller_postprocess", lambda work_dir, step: True)
    return service


# --- Service-level execution tests (monkeypatched Fortran) ---


def test_manual_batch_returns_two_groups(monkeypatch):
    service = _patch_service_core(monkeypatch)

    bundle_index = {"count": 0}

    def _fake_read_bundle(work_dir, step):
        bundle_index["count"] += 1
        if bundle_index["count"] == 1:
            return _make_fake_bundle(7.4, 4.93, 2.54, 90.0, 90.0, 90.0)
        return _make_fake_bundle(5.0, 6.0, 7.0, 90.0, 90.0, 90.0)

    monkeypatch.setattr(postprocess_core, "read_postprocess_bundle", _fake_read_bundle)

    r1 = service.run_manual_fullmiller(7.4, 4.93, 2.54, 90.0, 90.0, 90.0, 1.542)
    r2 = service.run_manual_fullmiller(5.0, 6.0, 7.0, 90.0, 90.0, 90.0, 1.0)

    assert r1["success"] is True
    assert r2["success"] is True

    d1 = r1["data"]
    d2 = r2["data"]

    assert d1["totalReflections"] > 0
    assert d2["totalReflections"] > 0
    assert d1["cellParams"]["a"] == 7.4
    assert d2["cellParams"]["a"] == 5.0
    assert d1["volume"] != d2["volume"]
    assert len(d1["fullMillerContent"]) > 0
    assert len(d2["fullMillerContent"]) > 0


def test_glide_batch_returns_two_groups(monkeypatch):
    service = _patch_service_core(monkeypatch)

    monkeypatch.setattr(
        postprocess_core,
        "read_postprocess_bundle",
        lambda wd, s: _make_fake_bundle(7.4, 4.93, 2.54, 90.0, 90.0, 90.0),
    )
    monkeypatch.setattr(
        postprocess_core, "generate_glide_fullmiller_batches", _fake_generate_glide
    )

    ns_groups = [
        SimpleNamespace(label="shear_A", nA=0.5, nB=0.0, l0=0.5),
        SimpleNamespace(label="shear_B", nA=1.0, nB=0.5, l0=2.0),
    ]

    result = service.run_glide_batch(
        7.4, 4.93, 2.54, 90.0, 90.0, 90.0, 1.542, ns_groups
    )

    assert result["success"] is True
    data = result["data"]
    assert data is not None

    glide_out = data["glideBatchOutputs"]
    assert glide_out["enabled"] is True
    assert len(glide_out["groups"]) == 2

    g1, g2 = glide_out["groups"]
    assert g1["label"] == "shear_A"
    assert g2["label"] == "shear_B"
    assert g1["totalReflections"] > 0
    assert g2["totalReflections"] > 0
    assert g1["fullMillerContent"] != ""
    assert g2["fullMillerContent"] != ""
    assert g1["cellParams"]["a"] != g2["cellParams"]["a"]
    assert g1["input"]["l0"] == 0.5
    assert g2["input"]["l0"] == 2.0
    assert data["baseCell"]["a"] == 7.4


# --- Route-level tests (TestClient, API-layer) ---


def _get_test_client_and_patch(monkeypatch):
    """Create a TestClient with monkeypatched IndexingService for route-level testing."""
    from fastapi.testclient import TestClient
    from backend.main import app

    _patch_service_core(monkeypatch)

    def _fake_indexing_service():
        return IndexingService(TaskManager())

    monkeypatch.setattr(
        indexing_service_module, "IndexingService", _fake_indexing_service
    )

    original_init = IndexingService.__init__

    def _patched_init(self, task_manager=None):
        original_init(self, task_manager or TaskManager())
        self._run_miller_postprocess = lambda work_dir, step: True

    monkeypatch.setattr(IndexingService, "__init__", _patched_init)

    return TestClient(app)


def test_route_manual_batch_two_groups(monkeypatch):
    client = _get_test_client_and_patch(monkeypatch)

    call_idx = {"n": 0}

    def _alternating_bundle(wd, s):
        call_idx["n"] += 1
        if call_idx["n"] == 1:
            return _make_fake_bundle(7.4, 4.93, 2.54, 90.0, 90.0, 90.0)
        return _make_fake_bundle(5.0, 6.0, 7.0, 90.0, 90.0, 90.0)

    monkeypatch.setattr(
        postprocess_core, "read_postprocess_bundle", _alternating_bundle
    )

    resp = client.post(
        "/api/analysis/manual-batch",
        json={
            "groups": [
                {
                    "label": "manual_01",
                    "a": 7.4,
                    "b": 4.93,
                    "c": 2.54,
                    "alpha": 90,
                    "beta": 90,
                    "gamma": 90,
                    "wavelength": 1.542,
                },
                {
                    "label": "manual_02",
                    "a": 5.0,
                    "b": 6.0,
                    "c": 7.0,
                    "alpha": 90,
                    "beta": 90,
                    "gamma": 90,
                    "wavelength": 1.0,
                },
            ]
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 2

    g1, g2 = body["data"]
    assert g1["success"] is True
    assert g2["success"] is True
    assert g1["data"]["totalReflections"] > 0
    assert g2["data"]["totalReflections"] > 0
    assert g1["data"]["cellParams"]["a"] != g2["data"]["cellParams"]["a"]


def test_route_manual_batch_partial_success(monkeypatch):
    """Route-level: manual-batch returns success=false but data=[...] when one group fails."""
    client = _get_test_client_and_patch(monkeypatch)

    call_count = {"n": 0}

    def _alternating_bundle(wd, s):
        call_count["n"] += 1
        if call_count["n"] % 2 == 1:
            return _make_fake_bundle(7.4, 4.93, 2.54, 90.0, 90.0, 90.0)
        return None

    monkeypatch.setattr(
        postprocess_core, "read_postprocess_bundle", _alternating_bundle
    )

    resp = client.post(
        "/api/analysis/manual-batch",
        json={
            "groups": [
                {
                    "label": "group_ok",
                    "a": 7.4,
                    "b": 4.93,
                    "c": 2.54,
                    "alpha": 90,
                    "beta": 90,
                    "gamma": 90,
                    "wavelength": 1.542,
                },
                {
                    "label": "group_fail",
                    "a": 5.0,
                    "b": 6.0,
                    "c": 7.0,
                    "alpha": 90,
                    "beta": 90,
                    "gamma": 90,
                    "wavelength": 1.0,
                },
            ]
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 2
    assert body["message"] is not None

    g1, g2 = body["data"]
    successes = [g["success"] for g in body["data"] if g.get("success") is True]
    failures = [g for g in body["data"] if g.get("success") is not True]
    assert len(successes) >= 1
    assert len(failures) >= 1


def test_route_glide_batch_two_groups(monkeypatch):
    """Route-level: POST /api/analysis/glide-batch returns 2 distinguishable groups."""
    client = _get_test_client_and_patch(monkeypatch)

    monkeypatch.setattr(
        postprocess_core,
        "read_postprocess_bundle",
        lambda wd, s: _make_fake_bundle(7.4, 4.93, 2.54, 90.0, 90.0, 90.0),
    )
    monkeypatch.setattr(
        postprocess_core, "generate_glide_fullmiller_batches", _fake_generate_glide
    )

    resp = client.post(
        "/api/analysis/glide-batch",
        json={
            "a": 7.4,
            "b": 4.93,
            "c": 2.54,
            "alpha": 90,
            "beta": 90,
            "gamma": 90,
            "wavelength": 1.542,
            "glideGroups": [
                {"label": "shear_A", "nA": 0.5, "nB": 0, "l0": 0.5},
                {"label": "shear_B", "nA": 1.0, "nB": 0.5, "l0": 2.0},
            ],
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"] is not None

    glide_out = body["data"]["glideBatchOutputs"]
    assert glide_out["enabled"] is True
    assert len(glide_out["groups"]) == 2

    g1, g2 = glide_out["groups"]
    assert g1["label"] == "shear_A"
    assert g2["label"] == "shear_B"
    assert g1["totalReflections"] > 0
    assert g2["totalReflections"] > 0
    assert g1["cellParams"]["a"] != g2["cellParams"]["a"]
