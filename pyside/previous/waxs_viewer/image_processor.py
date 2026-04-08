"""
image_processor.py  –  Pure image-processing helpers (colormap, contrast).

All methods are static so the class can be used without instantiation.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtGui import QImage


class ImageProcessor:
    """Centralised image-rendering utilities shared between both viewer tabs."""

    @staticmethod
    def _grayscale_image(data: np.ndarray) -> QImage:
        h, w = data.shape
        image = QImage(data.tobytes(), w, h, w, QImage.Format.Format_Grayscale8)
        return image.copy()

    @staticmethod
    def _rgb_image(rgb: np.ndarray) -> QImage:
        h, w, _ = rgb.shape
        image = QImage(rgb.tobytes(), w, h, 3 * w, QImage.Format.Format_RGB888)
        return image.copy()

    # ------------------------------------------------------------------ #
    #  Colourmap dispatcher                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def apply_colormap(
        img_data: np.ndarray,
        colormap: str,
        contrast_min: float,
        contrast_max: float,
        contrast_mode: str = "Linear",
    ) -> QImage:
        """Normalise *img_data* and apply the requested colourmap.

        Args:
            img_data:      2-D float array.
            colormap:      One of ``"灰度"``, ``"反转灰度"``, ``"热力图"``, ``"彩虹"``.
            contrast_min:  Lower clamp value (linear) or log-space floor.
            contrast_max:  Upper clamp value.
            contrast_mode: ``"Linear"`` or ``"Log"``.

        Returns:
            A ``QImage`` ready for display.
        """
        if contrast_mode == "Log":
            floor = max(float(np.min(img_data)), 0.1)
            data = np.where(img_data < 0.1, floor, img_data.astype(float))
            data = np.log10(data)
        else:
            data = img_data.astype(float)

        denom = float(contrast_max - contrast_min) or 1e-10
        norm = np.clip(data, contrast_min, contrast_max)
        norm = (norm - contrast_min) / denom

        dispatch = {
            "灰度":    ImageProcessor._grayscale,
            "反转灰度": ImageProcessor._inverted_grayscale,
            "热力图":  ImageProcessor._heatmap,
            "彩虹":   ImageProcessor._rainbow,
        }
        fn = dispatch.get(colormap, ImageProcessor._grayscale)
        return fn(norm)

    # ------------------------------------------------------------------ #
    #  Individual colourmap implementations                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _grayscale(norm: np.ndarray) -> QImage:
        data = np.asarray(255 * norm, dtype=np.uint8)
        return ImageProcessor._grayscale_image(data)

    @staticmethod
    def _inverted_grayscale(norm: np.ndarray) -> QImage:
        data = np.asarray(255 * (1.0 - norm), dtype=np.uint8)
        return ImageProcessor._grayscale_image(data)

    @staticmethod
    def _heatmap(norm: np.ndarray) -> QImage:
        h, w = norm.shape
        rgb = np.zeros((h, w, 3), dtype=np.uint8)
        rgb[:, :, 0] = np.uint8(255 * norm)
        rgb[:, :, 1] = np.uint8(128 * (1.0 - norm))
        rgb[:, :, 2] = np.uint8(255 * (1.0 - norm))
        return ImageProcessor._rgb_image(rgb)

    @staticmethod
    def _rainbow(norm: np.ndarray) -> QImage:
        h, w = norm.shape
        rgb = np.zeros((h, w, 3), dtype=np.uint8)

        m1 = (norm >= 0.00) & (norm < 0.25)
        rgb[m1, 1] = np.uint8(1020 * norm[m1])
        rgb[m1, 2] = 255

        m2 = (norm >= 0.25) & (norm < 0.50)
        rgb[m2, 1] = 255
        rgb[m2, 2] = np.uint8(255 - 1020 * (norm[m2] - 0.25))

        m3 = (norm >= 0.50) & (norm < 0.75)
        rgb[m3, 0] = np.uint8(1020 * (norm[m3] - 0.50))
        rgb[m3, 1] = 255

        m4 = norm >= 0.75
        rgb[m4, 0] = 255
        rgb[m4, 1] = np.uint8(255 - 1020 * (norm[m4] - 0.75))

        return ImageProcessor._rgb_image(rgb)

    # ------------------------------------------------------------------ #
    #  Matplotlib colourmap name (used by IntegratedTab)                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def matplotlib_cmap(colormap: str) -> str:
        """Return the matplotlib colormap name for the given UI label."""
        return {
            "灰度":    "gray",
            "反转灰度": "gray_r",
            "热力图":  "hot",
            "彩虹":   "jet",
        }.get(colormap, "gray")
