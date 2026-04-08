"""api/peak_integrated.py – 2D integrated data peak-finding endpoints."""

from __future__ import annotations
import csv, io, re, uuid
from typing import Optional

import numpy as np
import fabio
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from scipy.signal import find_peaks

from services.session_store import int_store
from services.image_service import downsample_2d
from services.physics import normalize_angle_180

router = APIRouter(prefix="/peak/integrated")


class SliceReq(BaseModel):
    session_id: str
    center_q: float
    center_az: float
    az_int_width: float = 1.0
    q_int_width: float  = 0.01
    q_display_range: float  = 0.2
    az_display_range: float = 20.0
    az_crop_enabled: bool = False
    az_crop_min: Optional[float] = None
    az_crop_max: Optional[float] = None
    convention: str = "ccw"
    psi_offset: float = 0.0


class FindPeaksReq(BaseModel):
    session_id: str
    q_min: float; q_max: float
    az_min: float; az_max: float
    prominence: float = 100.0
    width: float = 1.0
    az_crop_enabled: bool = False
    az_crop_min: Optional[float] = None
    az_crop_max: Optional[float] = None
    convention: str = "ccw"
    psi_offset: float = 0.0


class RecordPeaksReq(BaseModel):
    session_id: str
    peaks: list[dict]


class DeleteReq(BaseModel):
    session_id: str
    index: int


class MillerSettingsReq(BaseModel):
    session_id: str
    convention: str = "0_horizontal_ccw"
    ref_azimuth: float = 0.0


def _coords_to_pixel(q, az, q_range, az_range, rows, cols):
    q  = np.clip(q, q_range[0], q_range[1])
    az = np.clip(az, az_range[0], az_range[1])
    px = (cols-1) * (q - q_range[0])  / (q_range[1] - q_range[0])
    py = (rows-1) * (az - az_range[0]) / (az_range[1] - az_range[0])
    return float(px), float(py)


def _pixel_to_coords(px, py, q_range, az_range, rows, cols):
    q  = q_range[0]  + (px / (cols-1)) * (q_range[1] - q_range[0])
    az = az_range[0] + (py / (rows-1)) * (az_range[1] - az_range[0])
    return float(q), float(az)


def _miller_az(psi_orig, convention, ref):
    """Convert Miller ψ to image azimuth."""
    norm = (psi_orig % 360 + 360) % 360
    if convention == "0_horizontal_ccw":
        az = -norm - ref
    else:
        az = norm + ref
    return normalize_angle_180(az)


def _psi_to_az(psi, convention, ref):
    """Map relative angle (psi) to real azimuth using convention + ref. ccw/cw."""
    norm = (psi % 360 + 360) % 360
    if convention == "ccw":
        az = -norm + ref
    else:
        az = norm + ref
    return normalize_angle_180(az)


def _angle_in_crop(az, crop_start, crop_end):
    """Check if az (normalized to [-180,180)) is within crop interval. Supports wrap-around."""
    az_norm = normalize_angle_180(az)
    if crop_start <= crop_end:
        return crop_start <= az_norm <= crop_end
    return az_norm >= crop_start or az_norm <= crop_end


def _az_mask_for_crop(azv, crop_start, crop_end):
    """Return boolean mask array for azv, True where az is within crop interval."""
    return np.array([_angle_in_crop(a, crop_start, crop_end) for a in azv], dtype=bool)


@router.post("/load")
async def load_image(file: UploadFile = File(...)):
    """Upload a .npy or .tif 2D integration file."""
    content = await file.read()
    fname = file.filename or ""
    try:
        import tempfile, os
        suffix = os.path.splitext(fname)[1] or ".npy"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content); tmp_path = tmp.name
        if suffix.lower() in (".tif", ".tiff"):
            fimg = fabio.open(tmp_path)
            data = fimg.data.astype(float)
            fimg.close()
        elif suffix.lower() == ".npy":
            data = np.load(tmp_path).astype(float)
        else:
            raise ValueError("Unsupported format. Use .npy or .tif")
        os.unlink(tmp_path)
    except Exception as e:
        raise HTTPException(400, f"Cannot load file: {e}")

    cmin = float(np.min(data))
    cmax = float(np.percentile(data, 99.9)) if data.size > 1 else float(np.max(data))

    q_range     = (0.0, 1.0)
    az_range    = (-180.0, 180.0)

    sid = str(uuid.uuid4())
    int_store.create(sid, {
        "data": data,
        "q_range": q_range,
        "az_range": az_range,
        "records": [],
        "miller_data": [],
        "miller_original": [],
    })

    rows, cols = data.shape
    z, r_idx, c_idx = downsample_2d(data)
    q_axis  = [float(q_range[0] + (c / (cols-1)) * (q_range[1]  - q_range[0]))  for c in c_idx]
    az_axis = [float(az_range[0] + (r / (rows-1)) * (az_range[1] - az_range[0])) for r in r_idx]

    return {
        "session_id": sid,
        "z_data": z.tolist(),
        "q_axis": q_axis,
        "az_axis": az_axis,
        "q_range": list(q_range),
        "az_range": list(az_range),
        "contrast_min": cmin,
        "contrast_max": cmax,
    }


@router.post("/import-info")
async def import_info(file: UploadFile = File(...)):
    """Parse a processing_info.txt and extract coordinate ranges."""
    text = (await file.read()).decode("utf-8", errors="ignore")
    ranges = {}
    for line in text.splitlines():
        line = line.strip()
        if "X-axis (q" in line and "range:" in line:
            parts = line.split("range:")[1].strip().split(" to ")
            if len(parts) == 2:
                ranges["q_min"] = float(parts[0]); ranges["q_max"] = float(parts[1])
        elif "Y-axis (chi)" in line and "range (degrees):" in line:
            parts = line.split("range (degrees):")[1].strip().split(" to ")
            if len(parts) == 2:
                ranges["az_min"] = float(parts[0]); ranges["az_max"] = float(parts[1])
    if not ranges:
        raise HTTPException(400, "Could not parse coordinate ranges from file.")
    return ranges


@router.post("/set-ranges")
def set_ranges(body: dict):
    """Update coordinate ranges for the session and return new Plotly data."""
    sid     = body["session_id"]
    q_min   = float(body["q_min"]);  q_max  = float(body["q_max"])
    az_min  = float(body["az_min"]); az_max = float(body["az_max"])
    if q_min >= q_max or az_min >= az_max:
        raise HTTPException(400, "Min must be strictly less than Max.")
    sess = int_store.require(sid)
    q_range  = (q_min,  q_max)
    az_range = (az_min, az_max)
    int_store.update(sid, {"q_range": q_range, "az_range": az_range})

    data  = sess["data"]
    rows, cols = data.shape
    z, r_idx, c_idx = downsample_2d(data)
    q_axis  = [float(q_min  + (c / (cols-1)) * (q_max  - q_min))  for c in c_idx]
    az_axis = [float(az_min + (r / (rows-1)) * (az_max - az_min)) for r in r_idx]
    return {"z_data": z.tolist(), "q_axis": q_axis, "az_axis": az_axis}


@router.post("/import-miller")
async def import_miller(file: UploadFile = File(...), session_id: str = ""):
    """Parse a Miller indices file (csv/txt) and return transformed points."""
    text = (await file.read()).decode("utf-8", errors="ignore")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        raise HTTPException(400, "Empty file.")

    header = [p.strip().lower() for p in re.split(r"\s+", lines[0]) if p.strip()]
    q_col = az_col = h_col = k_col = l_col = -1
    for i, n in enumerate(header):
        if "q(" in n or n == "q" or "q_value" in n: q_col  = i
        elif "psi(" in n or "azimuth" in n or "chi" in n: az_col = i
        elif n == "h": h_col = i
        elif n == "k": k_col = i
        elif n == "l": l_col = i
    if q_col < 0 or az_col < 0:
        raise HTTPException(400, "File must contain 'q' and 'azimuth'/'psi'/'chi' columns.")

    result = []
    for line in lines[1:]:
        parts = [p.strip() for p in re.split(r"\s+", line) if p.strip()]
        if not parts: continue
        try:
            q_val  = float(parts[q_col])
            psi_v  = float(parts[az_col])
            h = int(float(parts[h_col])) if 0 <= h_col < len(parts) else "?"
            k = int(float(parts[k_col])) if 0 <= k_col < len(parts) else "?"
            l = int(float(parts[l_col])) if 0 <= l_col < len(parts) else "?"
            if q_val <= 0 or np.isnan(q_val): continue
            result.append({"q": q_val, "original_psi": psi_v, "hkl": f"({h} {k} {l})"})
        except (ValueError, IndexError):
            continue

    if session_id:
        sess = int_store.require(session_id)
        int_store.update(session_id, {"miller_original": result})

    return {"miller_original": result, "count": len(result)}


@router.post("/transform-miller")
def transform_miller(req: MillerSettingsReq):
    """Re-transform Miller indices with new convention/reference."""
    sess = int_store.require(req.session_id)
    orig = sess.get("miller_original", [])
    transformed = [
        {
            "q": m["q"],
            "azimuth": _miller_az(m["original_psi"], req.convention, req.ref_azimuth),
            "hkl": m["hkl"],
            "original_psi": m["original_psi"],
        }
        for m in orig
    ]
    int_store.update(req.session_id, {
        "miller_data": transformed,
        "miller_convention": req.convention,
        "miller_ref": req.ref_azimuth,
    })
    return {"miller_data": transformed}


@router.post("/get-slice")
def get_slice(req: SliceReq):
    """Compute q-slice and azimuth-slice through (center_q, center_az)."""
    sess = int_store.require(req.session_id)
    data     = sess["data"]
    q_range  = sess["q_range"]
    az_range = sess["az_range"]
    rows, cols = data.shape

    if req.az_crop_enabled and req.az_crop_min is not None and req.az_crop_max is not None:
        crop_start = _psi_to_az(req.az_crop_min, req.convention, req.psi_offset)
        crop_end   = _psi_to_az(req.az_crop_max, req.convention, req.psi_offset)
        azv_all = np.linspace(az_range[0], az_range[1], rows)
        crop_mask = _az_mask_for_crop(azv_all, crop_start, crop_end)
    else:
        crop_start = None
        crop_end   = None
        crop_mask  = None

    def _row(az): return int(np.clip(round((az - az_range[0]) / (az_range[1] - az_range[0]) * (rows-1)), 0, rows-1))
    def _col(q):  return int(np.clip(round((q  - q_range[0])  / (q_range[1]  - q_range[0])  * (cols-1)), 0, cols-1))

    az0 = req.center_az - req.az_int_width / 2
    az1 = req.center_az + req.az_int_width / 2
    r0, r1 = sorted([_row(az0), _row(az1)])
    r0 = max(0, r0); r1 = min(rows-1, r1)
    if crop_mask is not None:
        slab_rows = np.where(crop_mask[r0:r1+1])[0] + r0
        if len(slab_rows) == 0:
            iq = np.zeros(cols)
        else:
            iq = np.mean(data[slab_rows, :], axis=0)
    else:
        slab = data[r0:r1+1, :]
        iq   = np.mean(slab, axis=0) if slab.shape[0] > 0 else np.zeros(cols)
    qv   = np.linspace(q_range[0], q_range[1], cols)

    q0 = req.center_q - req.q_int_width / 2
    q1 = req.center_q + req.q_int_width / 2
    c0, c1 = sorted([_col(q0), _col(q1)])
    c0 = max(0, c0); c1 = min(cols-1, c1)
    slab2 = data[:, c0:c1+1]
    iaz   = np.mean(slab2, axis=1) if slab2.shape[1] > 0 else np.zeros(rows)
    azv   = np.linspace(az_range[0], az_range[1], rows)

    qd0, qd1   = req.center_q - req.q_display_range/2, req.center_q + req.q_display_range/2
    azd0, azd1 = req.center_az - req.az_display_range/2, req.center_az + req.az_display_range/2
    mask_q  = (qv  >= qd0) & (qv  <= qd1)
    mask_az = (azv >= azd0) & (azv <= azd1)
    if crop_mask is not None:
        mask_az = mask_az & crop_mask

    return {
        "q_values":  qv[mask_q].tolist(),
        "i_q":       iq[mask_q].tolist(),
        "az_values": azv[mask_az].tolist(),
        "i_az":      iaz[mask_az].tolist(),
    }


@router.post("/find-peaks")
def find_peaks_in_region(req: FindPeaksReq):
    """Auto-find peaks within a selected q×azimuth rectangle, respecting crop if enabled."""
    sess = int_store.require(req.session_id)
    data     = sess["data"]
    q_range  = sess["q_range"]
    az_range = sess["az_range"]
    rows, cols = data.shape
    qv  = np.linspace(q_range[0],  q_range[1],  cols)
    azv = np.linspace(az_range[0], az_range[1], rows)

    if req.az_crop_enabled and req.az_crop_min is not None and req.az_crop_max is not None:
        crop_start = _psi_to_az(req.az_crop_min, req.convention, req.psi_offset)
        crop_end   = _psi_to_az(req.az_crop_max, req.convention, req.psi_offset)
        crop_mask  = _az_mask_for_crop(azv, crop_start, crop_end)
    else:
        crop_mask = None

    def row_idx(az): return int(np.clip(np.argmin(np.abs(azv - az)), 0, rows-1))
    def col_idx(q):  return int(np.clip(np.argmin(np.abs(qv  - q)),  0, cols-1))

    r0, r1 = sorted([row_idx(req.az_min), row_idx(req.az_max)])
    if crop_mask is not None:
        valid_rows = np.where(crop_mask[r0:r1+1])[0] + r0
        if len(valid_rows) == 0:
            iq_full = np.zeros(cols)
        else:
            iq_full = np.mean(data[valid_rows, :], axis=0)
    else:
        iq_full = np.mean(data[r0:r1+1, :], axis=0) if r1 >= r0 else np.zeros(cols)
    qi0, qi1 = sorted([col_idx(req.q_min), col_idx(req.q_max)])
    q_pks: list[dict] = []
    if qi1 > qi0:
        pks, _ = find_peaks(iq_full[qi0:qi1+1], prominence=req.prominence, width=req.width)
        for i in pks:
            q_pks.append({"q": float(qv[qi0+i]), "intensity": float(iq_full[qi0+i])})

    c0, c1 = sorted([col_idx(req.q_min), col_idx(req.q_max)])
    iaz_full = np.mean(data[:, c0:c1+1], axis=1) if c1 >= c0 else np.zeros(rows)
    ai0, ai1 = sorted([row_idx(req.az_min), row_idx(req.az_max)])
    if crop_mask is not None:
        peak_candidates = np.where(crop_mask[ai0:ai1+1])[0] + ai0
        if len(peak_candidates) == 0:
            az_pks = []
        else:
            iaz_crop = iaz_full[peak_candidates]
            pks, _ = find_peaks(iaz_crop, prominence=req.prominence, width=req.width)
            az_pks = [{"azimuth": float(azv[peak_candidates[i]]), "intensity": float(iaz_crop[i])} for i in pks]
    elif ai1 >= ai0:
        az_pks = []
        pks, _ = find_peaks(iaz_full[ai0:ai1+1], prominence=req.prominence, width=req.width)
        for i in pks:
            az_pks.append({"azimuth": float(azv[ai0+i]), "intensity": float(iaz_full[ai0+i])})
    else:
        az_pks = []

    return {"q_peaks": q_pks, "az_peaks": az_pks}


@router.post("/record-peaks")
def record_peaks(req: RecordPeaksReq):
    sess = int_store.require(req.session_id)
    q_range  = sess["q_range"]
    az_range = sess["az_range"]
    data     = sess["data"]
    rows, cols = data.shape

    for pk in req.peaks:
        px, py = _coords_to_pixel(pk["q"], pk["azimuth"], q_range, az_range, rows, cols)
        r, c = int(round(py)), int(round(px))
        intensity = float(data[r, c]) if (0 <= r < rows and 0 <= c < cols) else 0.0
        sess["records"].append({
            "q": pk["q"], "azimuth": pk["azimuth"], "intensity": intensity,
        })
    return {"records": sess["records"]}


@router.post("/delete-record")
def delete_record(req: DeleteReq):
    sess = int_store.require(req.session_id)
    idx = req.index
    if 0 <= idx < len(sess["records"]):
        sess["records"].pop(idx)
    return {"records": sess["records"]}


@router.post("/clear-records")
def clear_records(body: dict):
    sid = body.get("session_id", "")
    sess = int_store.require(sid)
    sess["records"].clear()
    return {"records": []}


@router.get("/export-csv/{session_id}")
def export_csv(session_id: str):
    sess = int_store.require(session_id)
    records = sess.get("records", [])

    def gen():
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["index", "q_A-1", "azimuth_deg", "intensity"])
        for i, r in enumerate(records):
            w.writerow([i+1, r["q"], r["azimuth"], r["intensity"]])
        yield buf.getvalue()

    return StreamingResponse(
        gen(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=integrated_peaks.csv"},
    )