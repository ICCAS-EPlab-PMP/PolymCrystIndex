"""Smoke test: verify fixModeEnabled gate in AnalysisParams model.

When fixModeEnabled=False:
- fixedPeakText should be empty/default
- API should clear fixedPeakText

When fixModeEnabled=True:
- fixedPeakText content is preserved and normalized
"""

import sys
from pathlib import Path

_backend_dir = Path(__file__).parent.parent.resolve()
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from models.analysis import AnalysisParams


def test_fix_mode_enabled_field_default():
    """fixModeEnabled field defaults to False."""
    params = AnalysisParams()
    assert params.fixModeEnabled is False


def test_fix_mode_enabled_can_be_set_true():
    """fixModeEnabled can be set to True."""
    params = AnalysisParams(fixModeEnabled=True)
    assert params.fixModeEnabled is True


def test_fix_mode_enabled_false_with_fixed_peak_text():
    """When fixModeEnabled=False, fixedPeakText still accepts content (model level)."""
    params = AnalysisParams(fixModeEnabled=False, fixedPeakText="1 0 0 0\n2 1 1 0")
    assert params.fixModeEnabled is False
    assert params.fixedPeakText == "1 0 0 0\n2 1 1 0"


def test_fix_mode_enabled_true_with_fixed_peak_text():
    """When fixModeEnabled=True, fixedPeakText content is preserved."""
    params = AnalysisParams(fixModeEnabled=True, fixedPeakText="1 0 0 0\n2 1 1 0")
    assert params.fixModeEnabled is True
    assert params.fixedPeakText == "1 0 0 0\n2 1 1 0"


def test_fix_mode_enabled_both_false_defaults():
    """Both flags False gives empty fixedPeakText."""
    params = AnalysisParams(fixModeEnabled=False)
    assert params.fixModeEnabled is False
    assert params.fixedPeakText == ""


def test_params_to_dict_includes_fix_mode_enabled():
    """AnalysisParams model_dump includes fixModeEnabled field."""
    params = AnalysisParams(fixModeEnabled=True, fixedPeakText="1 0 0 0")
    dumped = params.model_dump()
    assert "fixModeEnabled" in dumped
    assert dumped["fixModeEnabled"] is True
    assert dumped["fixedPeakText"] == "1 0 0 0"
