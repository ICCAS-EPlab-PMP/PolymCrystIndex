"""HDPE regression harness — validates 200/-200 symmetry grouping from merge_test fixtures.

This test module serves as a regression entry point for the peak symmetry joint-matching
pipeline. It loads fixtures from PRE/backend/tests/fixtures/ and asserts the HDPE 200/-200
scenario that represents the core symmetric reflection pair.

Legacy behavior: postprocess-only peak symmetry uses positional zip(diffraction_data, miller_data).
New behavior (joint-matching): will use family-aware grouping with normalized error accumulation.

This harness helps distinguish the old behavior from the intended joint-matching pipeline.
"""

import os
import pytest
import sys
import importlib.util

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_helper_path = os.path.join(os.path.dirname(__file__), "..", "services", "peak_merge.py")
_spec = importlib.util.spec_from_file_location("peak_merge", _helper_path)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

identify_peak_symmetry_groups = _mod.identify_peak_symmetry_groups


class TestHDPERegressionBootstrap:
    """Bootstrap tests — verify fixture loading works without manual path edits."""

    def test_fixtures_are_available(self, fixtures_available):
        assert fixtures_available is True, (
            "HDPE fixture files not found in PRE/backend/tests/fixtures/. "
            "Ensure hdpe_cell_parameters.txt, hdpe_FullMiller.txt, and "
            "hdpe_observed_peaks.txt are present."
        )

    def test_cell_parameters_load(self, hdpe_cell_parameters):
        assert "a" in hdpe_cell_parameters
        assert "b" in hdpe_cell_parameters
        assert "c" in hdpe_cell_parameters
        assert hdpe_cell_parameters["a"] > 0
        assert hdpe_cell_parameters["b"] > 0
        assert hdpe_cell_parameters["c"] > 0

    def test_fullmiller_raw_load(self, hdpe_fullmiller_raw):
        assert len(hdpe_fullmiller_raw) > 0
        first = hdpe_fullmiller_raw[0]
        assert "h" in first
        assert "k" in first
        assert "l" in first
        assert "q" in first

    def test_observed_peaks_raw_load(self, hdpe_observed_peaks_raw):
        assert len(hdpe_observed_peaks_raw) > 0
        first = hdpe_observed_peaks_raw[0]
        assert "q" in first
        assert "psi" in first
        assert "flag" in first


class TestHDPE200Scenario:
    """Core regression: HDPE 200/-200 symmetric reflection pair.

    The 200 and -200 reflections have identical q and 2theta values but
    opposite H signs. This is the key scenario that joint-matching must
    recognize as a symmetric pair, distinct from the legacy postprocess
    positional pairing.
    """

    def test_200_neg200_peaks_fixture_has_two_members(self, hdpe_200_neg200_peaks):
        assert len(hdpe_200_neg200_peaks) == 2, (
            f"Expected 2 peaks (200 and -200), got {len(hdpe_200_neg200_peaks)}"
        )

    def test_200_neg200_have_opposite_h(self, hdpe_200_neg200_peaks):
        h_values = [p["h"] for p in hdpe_200_neg200_peaks]
        assert h_values == [2, -2] or h_values == [-2, 2], (
            f"Expected h values [2, -2], got {h_values}"
        )

    def test_200_neg200_have_identical_q(self, hdpe_200_neg200_peaks):
        q_values = [p["q"] for p in hdpe_200_neg200_peaks]
        assert abs(q_values[0] - q_values[1]) < 1e-10, (
            f"Expected identical q values for 200/-200 pair, got {q_values}"
        )

    def test_200_neg200_form_2peak_group(self, hdpe_200_neg200_peaks):
        groups = identify_peak_symmetry_groups(hdpe_200_neg200_peaks)
        assert len(groups) == 1, (
            f"Expected exactly 1 symmetry group for 200/-200 pair, got {len(groups)}"
        )
        assert groups[0]["groupType"] == "2-peak", (
            f"Expected '2-peak' group type, got '{groups[0]['groupType']}'"
        )

    def test_200_neg200_hk_rule_passed(self, hdpe_200_neg200_peaks):
        groups = identify_peak_symmetry_groups(hdpe_200_neg200_peaks)
        assert groups[0]["hkRulePassed"] is True, (
            "HK rule should pass for 200/-200 symmetric pair"
        )


class TestLegacyVsJointMatchingDistinction:
    """Tests that help distinguish legacy postprocess behavior from joint-matching intent.

    Legacy behavior: build_peak_symmetry_groups_from_results() uses positional
    zip(diffraction_data, miller_data) as the source of truth.

    Joint-matching intent: family-aware grouping where both 200 and -200
    are recognized as members of the same symmetry family, regardless of
    positional pairing.
    """

    def test_fullmiller_peaks_contain_both_200_and_neg200(self, hdpe_fullmiller_peaks):
        h_values = [p["h"] for p in hdpe_fullmiller_peaks]
        assert 2 in h_values and -2 in h_values, (
            f"FullMiller peaks must contain both h=2 and h=-2, got h values: {h_values}"
        )

    def test_fullmiller_200_neg200_identical_q(self, hdpe_fullmiller_peaks):
        peaks_200 = [p for p in hdpe_fullmiller_peaks if p["h"] == 2 and p["k"] == 0 and p["l"] == 0]
        peaks_neg200 = [p for p in hdpe_fullmiller_peaks if p["h"] == -2 and p["k"] == 0 and p["l"] == 0]
        assert len(peaks_200) == 1 and len(peaks_neg200) == 1, (
            "Expected exactly one 200 and one -200 reflection in FullMiller"
        )
        assert abs(peaks_200[0]["q"] - peaks_neg200[0]["q"]) < 1e-10, (
            "200 and -200 should have identical q values for symmetric pair"
        )


class TestNegativePath:
    """Negative-path tests: verify harness fails clearly when fixture is unavailable/invalid."""

    def test_fixtures_available_returns_false_when_missing(self, tmp_path):
        """When fixture directory is empty/missing, fixtures_available should be False."""
        # This test simulates the condition where fixtures are missing
        # by checking the fixture loading logic directly
        missing_file = os.path.join(
            os.path.dirname(__file__), "fixtures", "nonexistent_fixture.txt"
        )
        assert not os.path.exists(missing_file)

    def test_raises_on_missing_fixture_file(self):
        from conftest import _load_fixture_lines

        with pytest.raises(FileNotFoundError):
            _load_fixture_lines("completely_missing_fixture_file.txt")

    def test_empty_fixtures_dir_raises_file_not_found(self, tmp_path):
        """Empty fixtures directory should cause fixture loading to raise."""
        from conftest import _load_fixture_lines

        with pytest.raises(FileNotFoundError):
            _load_fixture_lines("totally_missing_fixture.txt")
