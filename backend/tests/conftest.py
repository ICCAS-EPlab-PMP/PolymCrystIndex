"""Pytest fixtures for HDPE regression harness — TDD for peak symmetry joint matching."""

import os
import pytest
from typing import Dict, List, Any


# Path to fixtures directory (relative to this file)
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture_lines(filename: str) -> List[str]:
    """Load a fixture file, raising FileNotFoundError if missing."""
    filepath = os.path.join(FIXTURES_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Fixture not found: {filepath}")
    with open(filepath, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


@pytest.fixture
def hdpe_cell_parameters() -> Dict[str, float]:
    """Load HDPE unit cell parameters as a dict.

    Returns:
        dict with keys: a, b, c, alpha, beta, gamma
    """
    lines = _load_fixture_lines("hdpe_cell_parameters.txt")
    if not lines:
        raise ValueError("hdpe_cell_parameters.txt is empty")
    parts = lines[0].split()
    if len(parts) < 6:
        raise ValueError(f"hdpe_cell_parameters.txt has too few columns: {lines[0]}")
    return {
        "a": float(parts[0]),
        "b": float(parts[1]),
        "c": float(parts[2]),
        "alpha": float(parts[3]),
        "beta": float(parts[4]),
        "gamma": float(parts[5]),
    }


@pytest.fixture
def hdpe_fullmiller_raw() -> List[Dict[str, Any]]:
    """Load raw HDPE FullMiller data as list of dicts.

    Columns: H, K, L, q, psi, psi_root, 2theta

    Returns:
        List of dicts with keys: h, k, l, q, psi, psi_root, two_theta
    """
    lines = _load_fixture_lines("hdpe_FullMiller.txt")
    # Skip header line if present
    data_lines = lines
    for i, line in enumerate(data_lines):
        if line.startswith("H K L") or line.startswith(" H K L"):
            data_lines = data_lines[i + 1 :]
            break

    peaks = []
    for line in data_lines:
        parts = line.split()
        if len(parts) < 7:
            continue
        peaks.append(
            {
                "h": int(parts[0]),
                "k": int(parts[1]),
                "l": int(parts[2]),
                "q": float(parts[3]),
                "psi": float(parts[4]),
                "psi_root": float(parts[5]),
                "two_theta": float(parts[6]),
            }
        )
    return peaks


@pytest.fixture
def hdpe_observed_peaks_raw() -> List[Dict[str, Any]]:
    """Load raw HDPE observed peaks (q, psi, flag).

    Returns:
        List of dicts with keys: q, psi, flag
    """
    lines = _load_fixture_lines("hdpe_observed_peaks.txt")
    peaks = []
    for line in lines:
        parts = line.split()
        if len(parts) < 3:
            continue
        peaks.append(
            {
                "q": float(parts[0]),
                "psi": float(parts[1]),
                "flag": int(parts[2]),
            }
        )
    return peaks


@pytest.fixture
def hdpe_200_neg200_peaks() -> List[Dict[str, Any]]:
    """Build peak list for the HDPE 200/-200 regression scenario.

    These two reflections have identical q and 2theta values,
    differing only in the sign of H. This is the key symmetric pair
    the joint-matching pipeline must recognize.

    Returns:
        List of 2 peak dicts suitable for identify_peak_symmetry_groups
    """
    lines = _load_fixture_lines("hdpe_FullMiller.txt")
    # Skip header
    data_lines = lines
    for i, line in enumerate(data_lines):
        if line.startswith("H K L") or line.startswith(" H K L"):
            data_lines = data_lines[i + 1 :]
            break

    peaks = []
    peak_index = 1
    for line in data_lines:
        parts = line.split()
        if len(parts) < 7:
            continue
        h, k, l = int(parts[0]), int(parts[1]), int(parts[2])
        # Only include the 200 and -200 reflections for this scenario
        if abs(h) == 2 and k == 0 and l == 0:
            peaks.append(
                {
                    "peakIndex": peak_index,
                    "h": h,
                    "k": k,
                    "l": l,
                    "q": float(parts[3]),
                    "psi": float(parts[4]),
                }
            )
            peak_index += 1
    return peaks


@pytest.fixture
def hdpe_fullmiller_peaks() -> List[Dict[str, Any]]:
    """Load FullMiller data as peak dicts suitable for identify_peak_symmetry_groups.

    Returns:
        List of peak dicts with h, k, l, q, psi, peakIndex
    """
    lines = _load_fixture_lines("hdpe_FullMiller.txt")
    # Skip header
    data_lines = lines
    for i, line in enumerate(data_lines):
        if line.startswith("H K L") or line.startswith(" H K L"):
            data_lines = data_lines[i + 1 :]
            break

    peaks = []
    peak_index = 1
    for line in data_lines:
        parts = line.split()
        if len(parts) < 7:
            continue
        peaks.append(
            {
                "peakIndex": peak_index,
                "h": int(parts[0]),
                "k": int(parts[1]),
                "l": int(parts[2]),
                "q": float(parts[3]),
                "psi": float(parts[4]),
            }
        )
        peak_index += 1
    return peaks


@pytest.fixture
def fixtures_available() -> bool:
    """Check that the HDPE fixture files are present and readable.

    Returns:
        True if fixtures are available, False otherwise.
    """
    required = ["hdpe_cell_parameters.txt", "hdpe_FullMiller.txt", "hdpe_observed_peaks.txt"]
    for name in required:
        filepath = os.path.join(FIXTURES_DIR, name)
        if not os.path.exists(filepath):
            return False
    return True
