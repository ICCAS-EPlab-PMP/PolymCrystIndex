"""services/image_service.py – NumPy array → base64 PNG helpers."""

from __future__ import annotations
import io, base64
import numpy as np
from PIL import Image

MAX_DISPLAY = 1024   # max pixels in any dimension for the main view


def _normalize(data: np.ndarray, cmin: float, cmax: float) -> np.ndarray:
    d = np.clip(data.astype(float), cmin, cmax)
    span = float(cmax - cmin) or 1e-10
    return (d - cmin) / span


def _colormap(norm: np.ndarray, cmap: str) -> np.ndarray:
    h, w = norm.shape
    if cmap == "灰度":
        g = (255 * norm).astype(np.uint8)
        return np.stack([g, g, g], -1)
    if cmap == "反转灰度":
        g = (255 * (1 - norm)).astype(np.uint8)
        return np.stack([g, g, g], -1)
    if cmap == "热力图":
        return np.stack([
            (255 * norm).astype(np.uint8),
            (128 * (1 - norm)).astype(np.uint8),
            (255 * (1 - norm)).astype(np.uint8),
        ], -1)
    if cmap == "彩虹":
        rgb = np.zeros((h, w, 3), np.uint8)
        m1 = (norm >= 0.00) & (norm < 0.25)
        rgb[m1, 1] = (1020 * norm[m1]).clip(0, 255).astype(np.uint8)
        rgb[m1, 2] = 255
        m2 = (norm >= 0.25) & (norm < 0.50)
        rgb[m2, 1] = 255
        rgb[m2, 2] = (255 - 1020 * (norm[m2] - 0.25)).clip(0, 255).astype(np.uint8)
        m3 = (norm >= 0.50) & (norm < 0.75)
        rgb[m3, 0] = (1020 * (norm[m3] - 0.50)).clip(0, 255).astype(np.uint8)
        rgb[m3, 1] = 255
        m4 = norm >= 0.75
        rgb[m4, 0] = 255
        rgb[m4, 1] = (255 - 1020 * (norm[m4] - 0.75)).clip(0, 255).astype(np.uint8)
        return rgb
    # default gray
    g = (255 * norm).astype(np.uint8)
    return np.stack([g, g, g], -1)


def _to_b64(rgb: np.ndarray) -> str:
    img = Image.fromarray(rgb, "RGB")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def render_main(
    data: np.ndarray,
    cmap: str,
    cmin: float,
    cmax: float,
    max_px: int = MAX_DISPLAY,
) -> tuple[str, float, int, int]:
    """Render downsampled main image. Returns (b64_png, scale, disp_h, disp_w)."""
    h, w = data.shape
    scale = min(1.0, max_px / max(h, w))
    if scale < 1.0:
        nh, nw = max(1, int(h * scale)), max(1, int(w * scale))
        iy = np.linspace(0, h - 1, nh, dtype=int)
        ix = np.linspace(0, w - 1, nw, dtype=int)
        data = data[np.ix_(iy, ix)]
    else:
        nh, nw = h, w
    norm = _normalize(data, cmin, cmax)
    rgb  = _colormap(norm, cmap)
    return _to_b64(rgb), scale, nh, nw


def render_zoom(
    original: np.ndarray,
    display: np.ndarray,
    cx: int, cy: int,
    zoom_size: int,
    cmap: str,
    cmin: float,
    cmax: float,
    magnify: int = 4,
) -> tuple[str, int, int, float]:
    """Render zoom area. Returns (b64, max_x, max_y, max_intensity)."""
    h, w = display.shape
    half = zoom_size // 2
    x1 = max(0, cx - half); y1 = max(0, cy - half)
    x2 = min(w, cx + half); y2 = min(h, cy + half)
    zone = display[y1:y2, x1:x2]
    norm = _normalize(zone, cmin, cmax)
    rgb  = _colormap(norm, cmap)

    # Magnify
    img = Image.fromarray(rgb, "RGB")
    img = img.resize((img.width * magnify, img.height * magnify), Image.NEAREST)

    # Find max in zone
    local_y, local_x = np.unravel_index(np.argmax(zone), zone.shape)
    max_x = x1 + local_x
    max_y = y1 + local_y

    # Draw red square on max (scaled)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    mx = local_x * magnify
    my = local_y * magnify
    draw.rectangle([mx - 3, my - 3, mx + 3, my + 3], outline=(255, 0, 0), width=2)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    intensity = float(original[max_y, max_x]) if (0 <= max_y < original.shape[0] and 0 <= max_x < original.shape[1]) else 0.0
    return b64, int(max_x), int(max_y), intensity


def downsample_2d(data: np.ndarray, max_pts: int = 500) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Downsample 2D array for Plotly heatmap. Returns (z, row_idx, col_idx)."""
    rows, cols = data.shape
    rs = max(1, rows // max_pts)
    cs = max(1, cols // max_pts)
    row_idx = np.arange(0, rows, rs)
    col_idx = np.arange(0, cols, cs)
    z = data[np.ix_(row_idx, col_idx)]
    return z, row_idx, col_idx