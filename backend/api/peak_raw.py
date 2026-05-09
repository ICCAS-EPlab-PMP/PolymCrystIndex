"""api/peak_raw.py – Raw detector image peak-picking endpoints."""

from __future__ import annotations
import csv, io, math, traceback, uuid
from typing import Optional

import numpy as np
import fabio
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.session_store import raw_store
from services.image_service import render_main, render_zoom
from services.physics import q_and_psi, pixel_from_q_psi, normalize_angle_180

try:
    import pyFAI as _pyfai_module
    from pyFAI import detector_factory as _detector_factory
    from pyFAI.integrator.azimuthal import AzimuthalIntegrator as _AI
    _AI_CLS = _AI
    _PYFAI = True
except (ImportError, AttributeError):
    _PYFAI = False
    _pyfai_module = None
    _detector_factory = None
    _AI_CLS = None

router = APIRouter(prefix="/peak/raw")


class RenderReq(BaseModel):
    session_id: str
    colormap: str = "灰度"
    contrast_min: float = 0
    contrast_max: float = 65535
    contrast_mode: str = "Linear"


class ThresholdReq(BaseModel):
    session_id: str
    threshold_min: float
    threshold_max: float
    colormap: str = "灰度"
    contrast_min: float = 0
    contrast_max: float = 65535


class ClickReq(BaseModel):
    session_id: str
    image_x: int
    image_y: int
    zoom_size: int = 30
    colormap: str = "灰度"
    contrast_min: float = 0
    contrast_max: float = 65535
    wavelength: float = 1.0
    pixel_size_x: float = 100.0
    pixel_size_y: float = 100.0
    center_x: float = 0.0
    center_y: float = 0.0
    distance: float = 1000.0


class ZoomClickReq(BaseModel):
    session_id: str
    local_x: int
    local_y: int
    center_x_img: int
    center_y_img: int
    zoom_size: int = 30
    colormap: str = "灰度"
    contrast_min: float = 0
    contrast_max: float = 65535
    wavelength: float = 1.0
    pixel_size_x: float = 100.0
    pixel_size_y: float = 100.0
    beam_center_x: float = 0.0
    beam_center_y: float = 0.0
    distance: float = 1000.0


class IntegrateReq(BaseModel):
    session_id: str
    image_x: int
    image_y: int
    current_q: float
    current_psi: float
    azimuth_range_half: float = 5.0
    radial_range_half: float = 0.35
    npt: int = 500
    npt_rad: int = 30
    azimuth_range_half_r: float = 30.0
    radial_range_half_r: float = 0.05
    npt_r: int = 50
    npt_rad_r: int = 150
    threshold_min: float = 0
    threshold_max: float = 65535
    wavelength: float = 1.0
    pixel_size_x: float = 100.0
    pixel_size_y: float = 100.0
    center_x: float = 0.0
    center_y: float = 0.0
    distance: float = 1000.0


class RecordPointReq(BaseModel):
    session_id: str
    x: int
    y: int
    intensity: float
    q: float
    psi_rad: float


class DeleteRecordReq(BaseModel):
    session_id: str
    index: int


class SaveRecordsReq(BaseModel):
    session_id: str
    name: str = ""


class LoadRecordsReq(BaseModel):
    session_id: str
    record_id: str


class ClearRecordsReq(BaseModel):
    session_id: str


class CalcPixelReq(BaseModel):
    session_id: str
    selected_q: Optional[float] = None
    selected_psi: Optional[float] = None
    current_q: float
    current_psi: float
    wavelength: float = 1.0
    pixel_size_x: float = 100.0
    pixel_size_y: float = 100.0
    center_x: float = 0.0
    center_y: float = 0.0
    distance: float = 1000.0


def _split_azimuth_window(center_deg: float, half_width_deg: float) -> list[dict[str, float]]:
    center = normalize_angle_180(center_deg)
    start = center - half_width_deg
    end = center + half_width_deg
    if start >= -180.0 and end <= 180.0:
        return [{"start": start, "end": end, "width": end - start}]
    if start < -180.0:
        return [
            {"start": start + 360.0, "end": 180.0, "width": 180.0 - (start + 360.0)},
            {"start": -180.0, "end": end, "width": end + 180.0},
        ]
    return [
        {"start": start, "end": 180.0, "width": 180.0 - start},
        {"start": -180.0, "end": end - 360.0, "width": end - 180.0},
    ]


def _clean_series(values: list[float]) -> list[float | None]:
    cleaned: list[float | None] = []
    for value in values:
        if value is None or (isinstance(value, float) and not math.isfinite(value)):
            cleaned.append(None)
        else:
            cleaned.append(value)
    return cleaned


def _weighted_merge_curves(curves: list[tuple[np.ndarray, float]]) -> list[float]:
    if not curves:
        return []
    weighted_sum = np.zeros_like(curves[0][0], dtype=float)
    weight_sum = np.zeros_like(curves[0][0], dtype=float)
    for curve, width in curves:
        valid = np.isfinite(curve)
        weighted_sum[valid] += curve[valid] * width
        weight_sum[valid] += width
    merged = np.divide(
        weighted_sum,
        weight_sum,
        out=np.full_like(weighted_sum, np.nan, dtype=float),
        where=weight_sum > 0,
    )
    return merged.tolist()


def _allocate_bins(total_bins: int, segments: list[dict[str, float]]) -> list[int]:
    if len(segments) == 1:
        return [max(2, total_bins)]
    total_width = sum(seg["width"] for seg in segments)
    raw = [(seg["width"] / total_width) * total_bins for seg in segments]
    bins = [max(2, int(math.floor(value))) for value in raw]
    while sum(bins) < total_bins:
        idx = max(range(len(raw)), key=lambda i: raw[i] - bins[i])
        bins[idx] += 1
    while sum(bins) > total_bins:
        idx = max(range(len(bins)), key=lambda i: bins[i])
        if bins[idx] <= 2:
            break
        bins[idx] -= 1
    return bins


def _collapse_psi_intensity(intensity: np.ndarray) -> np.ndarray:
    if intensity.ndim == 2:
        return np.nanmean(intensity, axis=0)
    return intensity.astype(float)


def _stitch_psi_segments(segments: list[tuple[np.ndarray, np.ndarray]], center_deg: float) -> tuple[list[float], list[float]]:
    if not segments:
        return [], []
    stitched: list[tuple[float, float]] = []
    for axis, intensity in segments:
        for az, value in zip(axis.tolist(), intensity.tolist()):
            local_az = center_deg + normalize_angle_180(az - center_deg)
            stitched.append((local_az, value))
    stitched.sort(key=lambda item: item[0])
    psi_values = [item[0] for item in stitched]
    i_values = [item[1] for item in stitched]
    return psi_values, i_values


@router.post("/load")
async def load_image(file: UploadFile = File(...)):
    """Upload an EDF or TIFF detector image."""
    content = await file.read()
    try:
        import tempfile, os
        suffix = os.path.splitext(file.filename or "")[1] or ".edf"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content); tmp_path = tmp.name
        fimg = fabio.open(tmp_path)
        original = fimg.data.astype(float)
        fimg.close()
        os.unlink(tmp_path)
    except Exception as e:
        raise HTTPException(400, f"Cannot load image: {e}")

    flat = original.flatten()
    if flat.size > 50:
        top50 = np.partition(flat, -50)[-50:]
        thr_max = float((np.median(top50) + np.max(top50)) / 2)
    else:
        thr_max = float(np.max(original))

    mask = (original < 0) | (original > thr_max)
    display = np.where(mask, 0, original)

    cmin = float(np.min(original))
    cmax = float(np.percentile(original, 99)) if original.size > 1 else float(np.max(original))

    sid = str(uuid.uuid4())
    raw_store.create(sid, {
        "original": original,
        "display":  display,
        "records":  [],
        "threshold_min": 0.0,
        "threshold_max": thr_max,
    })

    img_b64, scale, disp_h, disp_w = render_main(display, "灰度", cmin, cmax)
    h, w = original.shape
    return {
        "session_id": sid,
        "orig_width": w, "orig_height": h,
        "disp_width": disp_w, "disp_height": disp_h,
        "image_b64": img_b64,
        "threshold_min": 0.0,
        "threshold_max": thr_max,
        "contrast_min": cmin,
        "contrast_max": cmax,
    }


@router.post("/import-poni")
async def import_poni(file: UploadFile = File(...)):
    """Parse a pyFAI PONI file and return instrument parameters."""
    if not _PYFAI or _pyfai_module is None:
        raise HTTPException(400, "pyFAI not installed.")
    content = await file.read()
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".poni", delete=False) as tmp:
        tmp.write(content); tmp_path = tmp.name
    try:
        ai = _pyfai_module.load(tmp_path)
        detector = ai.detector
        detector_pixel1 = detector.pixel1 if detector is not None and detector.pixel1 is not None else 100e-6
        detector_pixel2 = detector.pixel2 if detector is not None and detector.pixel2 is not None else 100e-6
        p1 = ai.pixel1 if ai.pixel1 is not None else detector_pixel1
        p2 = ai.pixel2 if ai.pixel2 is not None else detector_pixel2
        wavelength = ai.wavelength if ai.wavelength is not None else 1e-10
        distance = ai.dist if ai.dist is not None else 1.0
        py = p1 * 1e6
        px = p2 * 1e6
        cx = ai.poni2 / p2
        cy = ai.poni1 / p1
    finally:
        os.unlink(tmp_path)
    return {
        "wavelength":   wavelength * 1e10,
        "pixel_size_x": px,
        "pixel_size_y": py,
        "center_x":     cx,
        "center_y":     cy,
        "distance":     distance * 1e3,
    }


@router.post("/render")
def render(req: RenderReq):
    """Re-render current display image with new colormap / contrast."""
    sess = raw_store.require(req.session_id)
    img_b64, _, _, _ = render_main(sess["display"], req.colormap, req.contrast_min, req.contrast_max)
    return {"image_b64": img_b64}


@router.post("/apply-threshold")
def apply_threshold(req: ThresholdReq):
    sess = raw_store.require(req.session_id)
    original = sess["original"]
    mask = (original < req.threshold_min) | (original > req.threshold_max)
    display = np.where(mask, 0, original)
    raw_store.update(req.session_id, {
        "display": display,
        "threshold_min": req.threshold_min,
        "threshold_max": req.threshold_max,
    })
    img_b64, _, _, _ = render_main(display, req.colormap, req.contrast_min, req.contrast_max)
    return {"image_b64": img_b64}


@router.post("/click")
def click_main_image(req: ClickReq):
    """User clicks the main image → return zoom view + q/ψ at max point."""
    sess = raw_store.require(req.session_id)
    original = sess["original"]
    display  = sess["display"]

    zoom_b64, max_x, max_y, intensity = render_zoom(
        original, display,
        req.image_x, req.image_y, req.zoom_size,
        req.colormap, req.contrast_min, req.contrast_max,
    )
    try:
        q, psi = q_and_psi(max_x, max_y, req.wavelength, req.pixel_size_x,
                            req.pixel_size_y, req.center_x, req.center_y, req.distance)
    except Exception:
        q, psi = 0.0, 0.0

    return {
        "zoom_b64":  zoom_b64,
        "max_x": max_x, "max_y": max_y,
        "intensity": intensity,
        "q": q, "psi_rad": psi, "psi_deg": math.degrees(psi),
    }


@router.post("/zoom-click")
def click_zoom_image(req: ZoomClickReq):
    """User clicks the zoom canvas → refine selected point."""
    sess = raw_store.require(req.session_id)
    original = sess["original"]
    display  = sess["display"]
    h, w = original.shape
    half = req.zoom_size // 2
    gx = max(0, min(w - 1, req.center_x_img - half + req.local_x))
    gy = max(0, min(h - 1, req.center_y_img - half + req.local_y))
    intensity = float(original[gy, gx])
    try:
        q, psi = q_and_psi(gx, gy, req.wavelength, req.pixel_size_x,
                            req.pixel_size_y, req.beam_center_x, req.beam_center_y, req.distance)
    except Exception:
        q, psi = 0.0, 0.0

    from PIL import Image as PILImage, ImageDraw
    from PIL.Image import Resampling
    from services.image_service import _normalize, _colormap, _to_b64
    import base64, io as _io

    x1 = max(0, req.center_x_img - half); y1 = max(0, req.center_y_img - half)
    x2 = min(w, req.center_x_img + half); y2 = min(h, req.center_y_img + half)
    zone = display[y1:y2, x1:x2]
    magnify = 4
    rgb  = _colormap(_normalize(zone, req.contrast_min, req.contrast_max), req.colormap)
    img  = PILImage.fromarray(rgb, "RGB").resize(
        (rgb.shape[1] * magnify, rgb.shape[0] * magnify), Resampling.NEAREST
    )
    draw = ImageDraw.Draw(img)
    lx, ly = (req.local_x) * magnify, (req.local_y) * magnify
    draw.rectangle([lx-3, ly-3, lx+3, ly+3], outline=(0, 255, 0), width=2)
    buf = _io.BytesIO(); img.save(buf, "PNG")
    zoom_b64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "zoom_b64": zoom_b64,
        "x": gx, "y": gy, "intensity": intensity,
        "q": q, "psi_rad": psi, "psi_deg": math.degrees(psi),
    }


@router.post("/integrate")
def integrate(req: IntegrateReq):
    """Run pyFAI 1D radial + azimuthal integration."""
    if not _PYFAI:
        raise HTTPException(400, "pyFAI not installed.")
    sess = raw_store.require(req.session_id)
    original = sess["original"]

    try:
        detector_factory = _detector_factory
        ai_cls = _AI_CLS
        if detector_factory is None or ai_cls is None:
            raise HTTPException(400, "pyFAI not installed.")
        wl  = req.wavelength * 1e-10
        px  = req.pixel_size_x * 1e-6
        py  = req.pixel_size_y * 1e-6
        det = detector_factory('detector', config={'pixel1': py, 'pixel2': px})
        ai  = ai_cls(detector=det, wavelength=wl)
        ai.dist = req.distance * 1e-3
        ai.poni1 = req.center_y * py
        ai.poni2 = req.center_x * px
        ai.rot1 = 0; ai.rot2 = 0; ai.rot3 = 0

        mask = np.where(
            (original >= req.threshold_min) & (original <= req.threshold_max), 0, 1
        ).astype(np.int8)

        q = req.current_q
        psi = req.current_psi

        q_min = max(0.001, q - req.radial_range_half)
        q_max = q + req.radial_range_half
        q_segments = _split_azimuth_window(psi, req.azimuth_range_half)
        q_results: list[tuple[np.ndarray, float]] = []
        q_axis = None
        for seg in q_segments:
            res_q = ai.integrate1d_ng(
                original,
                req.npt,
                unit="q_A^-1",
                method="splitpixel",
                correctSolidAngle=False,
                azimuth_range=(seg["start"], seg["end"]),
                radial_range=(q_min, q_max),
                mask=mask,
            )
            if q_axis is None:
                q_axis = np.array(res_q.radial, dtype=float)
            q_results.append((np.array(res_q.intensity, dtype=float), seg["width"]))

        q_min_r = max(0.001, q - req.radial_range_half_r)
        q_max_r = q + req.radial_range_half_r
        psi_segments = _split_azimuth_window(psi, req.azimuth_range_half_r)
        psi_bins = _allocate_bins(req.npt_r, psi_segments)
        psi_results: list[tuple[np.ndarray, np.ndarray]] = []
        for seg, npt_bins in zip(psi_segments, psi_bins):
            res_psi = ai.integrate_radial(
                original,
                npt_rad=req.npt_rad_r,
                npt=npt_bins,
                radial_range=(q_min_r, q_max_r),
                azimuth_range=(seg["start"], seg["end"]),
                unit="chi_deg",
                radial_unit="q_A^-1",
                method="splitpixel",
                correctSolidAngle=False,
                mask=mask,
            )
            psi_axis_segment = np.array(res_psi.radial, dtype=float)
            psi_intensity_segment = _collapse_psi_intensity(np.array(res_psi.intensity, dtype=float))
            psi_results.append((psi_axis_segment, psi_intensity_segment))

        psi_axis, i_psi = _stitch_psi_segments(psi_results, psi)
        merged_q = _weighted_merge_curves(q_results)

        return {
            "q_values": _clean_series(q_axis.tolist() if q_axis is not None else []),
            "i_q": _clean_series(merged_q),
            "psi_values": _clean_series(psi_axis),
            "i_psi": _clean_series(i_psi),
            "current_q": q,
            "current_psi": psi,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Integration error: {e}")


@router.post("/record-point")
def record_point(req: RecordPointReq):
    sess = raw_store.require(req.session_id)
    sess["records"].append({
        "x": req.x, "y": req.y,
        "intensity": req.intensity,
        "q": req.q,
        "psi_rad": req.psi_rad,
        "psi_deg": math.degrees(req.psi_rad),
    })
    return {"records": sess["records"]}


@router.post("/delete-record")
def delete_record(req: DeleteRecordReq):
    sess = raw_store.require(req.session_id)
    idx = req.index
    if 0 <= idx < len(sess["records"]):
        sess["records"].pop(idx)
    return {"records": sess["records"]}


@router.post("/clear-records")
def clear_records(req: ClearRecordsReq):
    # BUG FIX: was `req: dict` which Pydantic can't validate; now uses typed model.
    sess = raw_store.require(req.session_id)
    sess["records"].clear()
    return {"records": []}


@router.post("/save-records")
def save_records(req: SaveRecordsReq):
    try:
        saved = raw_store.save_records(req.session_id, name=req.name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"saved_record": saved, "records": raw_store.require(req.session_id).get("records", [])}


@router.get("/saved-records")
def list_saved_records():
    return {"items": raw_store.list_saved_records()}


@router.post("/load-records")
def load_records(req: LoadRecordsReq):
    try:
        loaded = raw_store.load_records(req.session_id, req.record_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"loaded_record": {k: v for k, v in loaded.items() if k != "records"}, "records": loaded["records"]}


@router.post("/calc-pixel")
def calc_pixel(req: CalcPixelReq):
    """Compute a new pixel position from selected q/ψ on the integration curves."""
    sess = raw_store.require(req.session_id)
    q_t     = req.selected_q   if req.selected_q   is not None else req.current_q
    psi_deg = normalize_angle_180(req.selected_psi if req.selected_psi is not None else req.current_psi)
    try:
        nx, ny = pixel_from_q_psi(
            q_t, psi_deg,
            req.wavelength, req.pixel_size_x, req.pixel_size_y,
            req.center_x, req.center_y, req.distance,
        )
        original = sess["original"]
        h, w = original.shape
        if not (0 <= ny < h and 0 <= nx < w):
            raise ValueError(f"Pixel ({nx},{ny}) outside image bounds")
        intensity = float(original[ny, nx])
        q, psi = q_and_psi(nx, ny, req.wavelength, req.pixel_size_x,
                            req.pixel_size_y, req.center_x, req.center_y, req.distance)
        return {"x": nx, "y": ny, "intensity": intensity, "q": q,
                "psi_rad": psi, "psi_deg": math.degrees(psi)}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/export-csv/{session_id}")
def export_csv(session_id: str, psi_offset: float = 0.0):
    """Stream recorded points as CSV (includes raw and corrected psi columns)."""
    sess = raw_store.require(session_id)
    records = sess.get("records", [])

    def gen():
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["index", "pixel_x", "pixel_y", "intensity", "q_A-1", "psi_deg_raw", "psi_deg_corrected"])
        for i, r in enumerate(records):
            psi_corrected = r["psi_deg"] - psi_offset
            w.writerow([i+1, r["x"], r["y"], r["intensity"], r["q"], r["psi_deg"], round(psi_corrected, 6)])
        yield buf.getvalue()

    return StreamingResponse(
        gen(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=raw_peaks.csv"},
    )


@router.get("/export-txt/{session_id}")
def export_txt(session_id: str, psi_offset: float = 0.0):
    """Stream corrected q/psi/1 as plain text (no header, three columns)."""
    sess = raw_store.require(session_id)
    records = sess.get("records", [])

    def gen():
        buf = io.StringIO()
        for r in records:
            psi_corrected = r["psi_deg"] - psi_offset
            buf.write(f"{r['q']:.6f}\t{psi_corrected:.6f}\t1\n")
        yield buf.getvalue()

    return StreamingResponse(
        gen(),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=raw_peaks.txt"},
    )
