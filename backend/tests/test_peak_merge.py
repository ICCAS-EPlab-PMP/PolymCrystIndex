"""Tests for peak_merge.py — postprocess audit / reporting helpers.

These tests validate the Python-side hk-rule validation, sign-pattern
logic, and group-identification helpers that ship in ``peak_merge.py``.
They do NOT test the Fortran-backed production matching path; that
coverage lives in ``indexing_service`` integration tests.

Because ``peak_merge.py`` is a secondary reporting utility (not the
canonical source), some historical assertions (e.g. exact group-type
labeling) reflect the Python implementation's conventions rather than
the Fortran artifact semantics.
"""

import pytest
import sys
import os
import importlib.util

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_helper_path = os.path.join(os.path.dirname(__file__), "..", "services", "peak_merge.py")
_spec = importlib.util.spec_from_file_location("peak_merge", _helper_path)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

identify_peak_symmetry_groups = _mod.identify_peak_symmetry_groups
_hk_rule_details = _mod._hk_rule_details
_sign = _mod._sign


def _make_peak(index: int, h: int, k: int, l: int,
               q: float = 1.0, psi: float = 0.0) -> dict:
    return {
        "peakIndex": index,
        "q": q,
        "psi": psi,
        "h": h,
        "k": k,
        "l": l,
    }


class TestSignFunction:
    def test_positive(self):
        assert _sign(5) == 1

    def test_negative(self):
        assert _sign(-3) == -1

    def test_zero(self):
        assert _sign(0) == 0


class TestHkRuleDetails:

    def test_h_plus_minus_1_k_plus_minus_1_l0_4peak(self):
        peaks = [
            _make_peak(1, 1, 1, 0),
            _make_peak(2, 1, -1, 0),
            _make_peak(3, -1, 1, 0),
            _make_peak(4, -1, -1, 0),
        ]
        details = _hk_rule_details(peaks)
        assert details["hkRulePassed"] is True

    def test_h0_k_plus_minus_1_l0_2peak(self):
        peaks = [
            _make_peak(1, 0, 1, 0),
            _make_peak(2, 0, -1, 0),
        ]
        details = _hk_rule_details(peaks)
        assert details["hkRulePassed"] is True

    def test_h_plus_minus_1_k0_l0_2peak(self):
        peaks = [
            _make_peak(1, 1, 0, 0),
            _make_peak(2, -1, 0, 0),
        ]
        details = _hk_rule_details(peaks)
        assert details["hkRulePassed"] is True

    def test_h0_k0_l0_no_group(self):
        peaks = [
            _make_peak(1, 0, 0, 0),
            _make_peak(2, 0, 0, 0),
        ]
        details = _hk_rule_details(peaks)
        assert details["hkRulePassed"] is False

    def test_h0_k_plus_minus_1_l0_4peak(self):
        peaks = [
            _make_peak(1, 0, 1, 0),
            _make_peak(2, 0, -1, 0),
            _make_peak(3, 0, 1, 0, q=1.05),
            _make_peak(4, 0, -1, 0, q=1.05),
        ]
        details = _hk_rule_details(peaks)
        assert details["hkRulePassed"] is True

    def test_h_plus_minus_1_k0_l0_4peak(self):
        peaks = [
            _make_peak(1, 1, 0, 0),
            _make_peak(2, -1, 0, 0),
            _make_peak(3, 1, 0, 0, q=1.05),
            _make_peak(4, -1, 0, 0, q=1.05),
        ]
        details = _hk_rule_details(peaks)
        assert details["hkRulePassed"] is True

    def test_3member_bucket_is_rejected(self):
        peaks = [
            _make_peak(1, 2, 1, 0),
            _make_peak(2, -2, 1, 0),
            _make_peak(3, 2, -1, 0),
        ]
        details = _hk_rule_details(peaks)
        assert details["requiresSupportedMemberCount"] is False
        assert details["hkRulePassed"] is False

    def test_mismatched_sign_bucket_is_rejected(self):
        peaks = [
            _make_peak(1, 2, 1, 0),
            _make_peak(2, -2, 1, 0),
            _make_peak(3, -2, 1, 0, q=1.02),
            _make_peak(4, 2, 1, 0, q=1.03),
        ]
        details = _hk_rule_details(peaks)
        assert details["requiresSupportedMemberCount"] is True
        assert details["signPatternOk"] is False
        assert details["hkRulePassed"] is False


class TestIdentifyPeakSymmetryGroups:

    def test_empty_input_returns_empty(self):
        result = identify_peak_symmetry_groups([])
        assert result == []

    def test_disabled_returns_empty(self):
        peaks = [_make_peak(1, 1, 1, 0)]
        result = identify_peak_symmetry_groups(peaks)
        assert result == []

    def test_4peak_group_baseline(self):
        peaks = [
            _make_peak(1, 1, 1, 0),
            _make_peak(2, 1, -1, 0),
            _make_peak(3, -1, 1, 0),
            _make_peak(4, -1, -1, 0),
        ]
        result = identify_peak_symmetry_groups(peaks)
        assert len(result) == 1
        assert result[0]["groupType"] == "4-peak"
        assert result[0]["hkRulePassed"] is True

    def test_2peak_h0_k_pm1(self):
        peaks = [
            _make_peak(1, 0, 1, 0),
            _make_peak(2, 0, -1, 0),
        ]
        result = identify_peak_symmetry_groups(peaks)
        assert len(result) == 1
        assert result[0]["groupType"] == "2-peak"
        assert result[0]["hkRulePassed"] is True

    def test_2peak_h_pm1_k0(self):
        peaks = [
            _make_peak(1, 1, 0, 0),
            _make_peak(2, -1, 0, 0),
        ]
        result = identify_peak_symmetry_groups(peaks)
        assert len(result) == 1
        assert result[0]["groupType"] == "2-peak"
        assert result[0]["hkRulePassed"] is True

    def test_h0_k0_l0_no_group(self):
        peaks = [
            _make_peak(1, 0, 0, 0),
            _make_peak(2, 0, 0, 0),
        ]
        result = identify_peak_symmetry_groups(peaks)
        assert len(result) == 0

    def test_4peak_h0_k_pm1(self):
        peaks = [
            _make_peak(1, 0, 1, 0),
            _make_peak(2, 0, -1, 0),
            _make_peak(3, 0, 1, 0, q=1.05),
            _make_peak(4, 0, -1, 0, q=1.05),
        ]
        result = identify_peak_symmetry_groups(peaks)
        assert len(result) == 1
        assert result[0]["groupType"] == "4-peak"
        assert result[0]["hkRulePassed"] is True

    def test_4peak_h_pm1_k0(self):
        peaks = [
            _make_peak(1, 1, 0, 0),
            _make_peak(2, -1, 0, 0),
            _make_peak(3, 1, 0, 0, q=1.05),
            _make_peak(4, -1, 0, 0, q=1.05),
        ]
        result = identify_peak_symmetry_groups(peaks)
        assert len(result) == 1
        assert result[0]["groupType"] == "4-peak"
        assert result[0]["hkRulePassed"] is True


class TestMergeGradient:

    def test_merge_gradient_disabled(self):
        peaks = [
            _make_peak(1, 1, 1, 0),
            _make_peak(2, 1, -1, 0),
            _make_peak(3, -1, 1, 0),
            _make_peak(4, -1, -1, 0),
        ]
        result_disabled = identify_peak_symmetry_groups(
            peaks, merge_gradient_enabled=False, merge_gradient_threshold=0.5
        )
        result_baseline = identify_peak_symmetry_groups(peaks)
        assert len(result_disabled) == len(result_baseline)
        assert result_disabled[0]["groupType"] == result_baseline[0]["groupType"]
        assert result_disabled[0]["hkRulePassed"] == result_baseline[0]["hkRulePassed"]

    def test_merge_gradient_threshold_zero(self):
        peaks = [
            _make_peak(1, 1, 1, 0),
            _make_peak(2, 1, -1, 0),
            _make_peak(3, -1, 1, 0),
            _make_peak(4, -1, -1, 0),
        ]
        result_zero = identify_peak_symmetry_groups(
            peaks, merge_gradient_enabled=True, merge_gradient_threshold=0.0
        )
        result_disabled = identify_peak_symmetry_groups(
            peaks, merge_gradient_enabled=False, merge_gradient_threshold=0.5
        )
        assert len(result_zero) == len(result_disabled)
        assert result_zero[0]["groupType"] == result_disabled[0]["groupType"]

    def test_merge_gradient_enabled_with_threshold(self):
        peaks = [
            _make_peak(1, 1, 1, 0),
            _make_peak(2, 1, -1, 0),
            _make_peak(3, -1, 1, 0),
            _make_peak(4, -1, -1, 0),
        ]
        result = identify_peak_symmetry_groups(
            peaks, merge_gradient_enabled=True, merge_gradient_threshold=0.5
        )
        assert len(result) == 1
        assert result[0]["groupType"] == "4-peak"
        assert result[0]["hkRulePassed"] is True
        assert result[0]["mergeGradient"]["enabled"] is True
        assert result[0]["mergeGradient"]["passed"] is True
        assert result[0]["mergeGradient"]["threshold"] == 0.5
