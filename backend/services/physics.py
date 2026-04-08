"""services/physics.py – Scattering geometry calculations."""

from __future__ import annotations
import math
import numpy as np


def q_and_psi(
    x: float, y: float,
    wavelength: float,   # Å
    pixel_x: float,      # µm
    pixel_y: float,      # µm
    center_x: float,     # pixels
    center_y: float,     # pixels
    distance: float,     # mm
) -> tuple[float, float]:
    """Return (q [Å⁻¹], ψ [rad])."""
    dx = (x - center_x) * (pixel_x / 1000.0)   # mm
    dy = (y - center_y) * (pixel_y / 1000.0)   # mm
    r  = math.sqrt(dx**2 + dy**2)
    theta = math.atan(r / distance) / 2.0
    q     = (4 * math.pi * math.sin(theta)) / wavelength
    psi   = math.atan2(dy, dx)
    return q, psi


def pixel_from_q_psi(
    q: float, psi_deg: float,
    wavelength: float, pixel_x: float, pixel_y: float,
    center_x: float, center_y: float, distance: float,
) -> tuple[int, int]:
    """Inverse mapping: (q, ψ°) → pixel (x, y)."""
    sin_th = (q * wavelength) / (4 * math.pi)
    if abs(sin_th) > 1:
        raise ValueError("q value out of range")
    theta = math.asin(sin_th)
    r_mm  = distance * math.tan(2 * theta)
    psi_r = math.radians(psi_deg)
    dx_mm = r_mm * math.cos(psi_r)
    dy_mm = r_mm * math.sin(psi_r)
    nx = int(round(center_x + (dx_mm * 1000.0) / pixel_x))
    ny = int(round(center_y + (dy_mm * 1000.0) / pixel_y))
    return nx, ny


def normalize_angle_180(a: float) -> float:
    a = (a % 360 + 360) % 360
    return a - 360 if a >= 180 else a