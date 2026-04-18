"""Smoke test: verify GLIDE independent entry contract.

GLIDE independent entry: ManualCellRequest/ManualCellResponse provide a
stand-alone contract for generating FullMiller.txt from 6 cell parameters
WITHOUT requiring a full run_indexing() task.

This smoke establishes:
- ManualCellRequest model accepts 6 lattice parameters + wavelength
- ManualCellResponse model structure is defined
- The contract does NOT depend on run_indexing() automatic result binding
- Future implementations (task 5/6) must respect this separation
"""

import sys
from pathlib import Path

_backend_dir = Path(__file__).parent.parent.resolve()
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from pydantic import ValidationError
import pytest

from models.analysis import ManualCellRequest, ManualCellResponse


def test_manual_cell_request_valid():
    """ManualCellRequest accepts valid lattice parameters."""
    req = ManualCellRequest(
        a=7.5,
        b=8.2,
        c=10.1,
        alpha=90.0,
        beta=90.0,
        gamma=90.0,
        wavelength=1.5406,
    )
    assert req.a == 7.5
    assert req.b == 8.2
    assert req.c == 10.1
    assert req.alpha == 90.0
    assert req.beta == 90.0
    assert req.gamma == 90.0
    assert req.wavelength == 1.5406


def test_manual_cell_request_default_wavelength():
    """Default wavelength is 1.542 when not specified."""
    req = ManualCellRequest(a=5.0, b=5.0, c=7.0, alpha=90.0, beta=90.0, gamma=90.0)
    assert req.wavelength == 1.542


def test_manual_cell_request_invalid_angle_rejected():
    """Angles outside 0-180 range are rejected."""
    with pytest.raises(ValidationError):
        ManualCellRequest(a=5.0, b=5.0, c=7.0, alpha=200.0, beta=90.0, gamma=90.0)


def test_manual_cell_request_nonpositive_a_rejected():
    """Non-positive lattice parameter 'a' is rejected."""
    with pytest.raises(ValidationError):
        ManualCellRequest(a=-1.0, b=5.0, c=7.0, alpha=90.0, beta=90.0, gamma=90.0)


def test_manual_cell_response_structure():
    """ManualCellResponse has expected success/data/message fields."""
    resp = ManualCellResponse(success=True, data={"result": "ok"}, message=None)
    assert resp.success is True
    assert resp.data == {"result": "ok"}
    assert resp.message is None


def test_manual_cell_response_failure():
    """ManualCellResponse can represent failure state."""
    resp = ManualCellResponse(success=False, message="Cell computation failed")
    assert resp.success is False
    assert resp.message == "Cell computation failed"
