"""
utils.py  –  Standalone utility functions for the WAXS Viewer.
"""

from __future__ import annotations


def normalize_angle_to_180(angle: float) -> float:
    """Normalise an angle (degrees) to the half-open interval [-180, 180)."""
    angle = (angle % 360 + 360) % 360
    if angle >= 180:
        angle -= 360
    return angle


def parse_info_file(file_path: str) -> dict | None:
    """Parse a *processing_info.txt* file for q and azimuth coordinate ranges.

    Returns a dict with keys ``q_min``, ``q_max``, ``azimuth_min``,
    ``azimuth_max`` (all floats) on success, or *None* on failure.
    """
    ranges: dict = {}
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if "X-axis (q" in line and "range:" in line:
                    parts = line.split("range:")[1].strip().split(" to ")
                    if len(parts) == 2:
                        ranges["q_min"] = float(parts[0])
                        ranges["q_max"] = float(parts[1])
                elif "Y-axis (chi)" in line and "range (degrees):" in line:
                    parts = line.split("range (degrees):")[1].strip().split(" to ")
                    if len(parts) == 2:
                        ranges["azimuth_min"] = float(parts[0])
                        ranges["azimuth_max"] = float(parts[1])
    except Exception as exc:  # noqa: BLE001
        print(f"[parse_info_file] Error: {exc}")
        return None
    return ranges if ranges else None
