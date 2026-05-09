"""Smoke test: verify fix-mode enable gate via _normalize_fixed_peak_text.

Fix mode is enabled when user provides non-empty fixedPeakText.
The _normalize_fixed_peak_text function in api.analysis is the gate that:
- Accepts valid "peak_index h k l" lines
- Rejects malformed lines with HTTPException
- Empty string means fix mode disabled
"""

import sys
from pathlib import Path

_backend_dir = Path(__file__).parent.parent.resolve()
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from fastapi import HTTPException
from api.analysis import _normalize_fixed_peak_text


def test_fix_mode_empty_disabled():
    """Empty fixedPeakText means fix mode is disabled (returns empty string)."""
    result = _normalize_fixed_peak_text("")
    assert result == ""


def test_fix_mode_valid_single_line():
    """Valid single-line fixedPeakText is accepted and normalized."""
    result = _normalize_fixed_peak_text("1 0 0 0")
    assert result == "1 0 0 0"


def test_fix_mode_valid_multi_line():
    """Valid multi-line fixedPeakText is accepted and normalized."""
    text = "1 0 0 0\n2 1 1 0\n3 0 2 1"
    result = _normalize_fixed_peak_text(text)
    lines = result.splitlines()
    assert len(lines) == 3
    assert "1 0 0 0" in lines
    assert "2 1 1 0" in lines


def test_fix_mode_valid_with_whitespace():
    """fixedPeakText with extra whitespace is normalized."""
    result = _normalize_fixed_peak_text("  1  0  0  0  ")
    assert result == "1 0 0 0"


def test_fix_mode_valid_negative_indices():
    """Negative indices in fixedPeakText are valid."""
    result = _normalize_fixed_peak_text("-1 0 0 0")
    assert result == "-1 0 0 0"


def test_fix_mode_rejects_wrong_column_count():
    """FixedPeakText with wrong column count is rejected."""
    try:
        _normalize_fixed_peak_text("1 0 0")
        assert False, "Should have raised HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "line 1" in str(exc.detail).lower()


def test_fix_mode_rejects_non_integer():
    """FixedPeakText with non-integer values is rejected."""
    try:
        _normalize_fixed_peak_text("1 0.5 0 0")
        assert False, "Should have raised HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400


def test_fix_mode_rejects_empty_line():
    """FixedPeakText with empty lines skips them (doesn't reject)."""
    result = _normalize_fixed_peak_text("1 0 0 0\n\n2 1 1 0")
    lines = result.splitlines()
    assert len(lines) == 2
