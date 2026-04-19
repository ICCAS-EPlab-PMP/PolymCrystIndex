"""Analysis task request and response models."""

from typing import Any, Optional, List
from pydantic import BaseModel, Field, model_validator


class GlideBatchParams(BaseModel):
    """One glide-shear batch item applied to the optimized cell."""

    label: str = Field(default="")
    nA: float = Field(default=0.0)
    nB: float = Field(default=0.0)
    l0: float

    @model_validator(mode="after")
    def validate_l0(self) -> "GlideBatchParams":
        if abs(self.l0) < 1e-12:
            raise ValueError("glide batch parameter l0 cannot be 0")
        return self


class AnalysisParams(BaseModel):
    """Analysis parameters matching API_DOC.md specification."""

    steps: int = Field(default=30, ge=1, le=10000)
    generations: int = Field(default=2000, ge=1, le=100000)
    liveRatio: int = Field(default=10, ge=0, le=100)
    exchangeRatio: int = Field(default=20, ge=0, le=100)
    mutateRatio: int = Field(default=50, ge=0, le=100)
    newRatio: int = Field(default=20, ge=0, le=100)

    aMin: float = Field(default=3.0, ge=0)
    aMax: float = Field(default=10.0, ge=0)
    bMin: float = Field(default=3.0, ge=0)
    bMax: float = Field(default=10.0, ge=0)
    cMin: float = Field(default=5.0, ge=0)
    cMax: float = Field(default=15.0, ge=0)

    alphaMin: float = Field(default=60.0, ge=0, le=180)
    alphaMax: float = Field(default=150.0, ge=0, le=180)
    betaMin: float = Field(default=60.0, ge=0, le=180)
    betaMax: float = Field(default=150.0, ge=0, le=180)
    gammaMin: float = Field(default=60.0, ge=0, le=180)
    gammaMax: float = Field(default=150.0, ge=0, le=180)

    e1: float = Field(default=1.0, ge=0)
    e2: float = Field(default=100.0, ge=0)
    e3: float = Field(default=500.0, ge=0)
    e4: float = Field(default=1.0, ge=0)

    wavelength: float = Field(default=1.542, gt=0)
    esym: float = Field(default=0.95, ge=0, le=1)
    lmMode: bool = True
    tiltCheck: bool = False
    pseuOrth: bool = False
    mergeNearbyEnabled: bool = False
    mergeTq: float = Field(default=0.2, ge=0)
    mergeTa: float = Field(default=2.0, ge=0)
    peakSymmetryEnabled: bool = False
    symmetryTq: float = Field(default=0.2, ge=0)
    symmetryTa: float = Field(default=2.0, ge=0)
    mergeGradientEnabled: bool = False
    mergeGradientThreshold: float = Field(default=0.0, ge=0)
    duplicate: bool = False

    @model_validator(mode="before")
    @classmethod
    def _backward_compat_peak_symmetry(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "mergeNearbyEnabled" in data and "peakSymmetryEnabled" not in data:
                data["peakSymmetryEnabled"] = data["mergeNearbyEnabled"]
            if "mergeTq" in data and "symmetryTq" not in data:
                data["symmetryTq"] = data["mergeTq"]
            if "mergeTa" in data and "symmetryTa" not in data:
                data["symmetryTa"] = data["mergeTa"]
        return data

    hklMode: str = Field(default="Default")
    custH: int = Field(default=5, ge=0)
    custK: int = Field(default=5, ge=0)
    custL: int = Field(default=0, ge=0)
    fixModeEnabled: bool = Field(default=False)
    fixedPeakText: str = Field(default="")
    ompThreads: int = Field(default=1, ge=1, le=1024)
    glideBatches: List[GlideBatchParams] = Field(default_factory=list)


class AnalysisRunRequest(BaseModel):
    """Request to start an analysis task."""

    dataFile: str
    params: AnalysisParams


class AnalysisRunResponse(BaseModel):
    """Response after starting an analysis task."""

    success: bool = True
    data: Optional[dict] = None
    message: Optional[str] = None


class AnalysisStatusResponse(BaseModel):
    """Analysis task status response."""

    success: bool = True
    data: Optional[dict] = None
    message: Optional[str] = None


class AnalysisLogsResponse(BaseModel):
    """Analysis logs response."""

    success: bool = True
    data: Optional[dict] = None
    message: Optional[str] = None


class ManualCellRequest(BaseModel):
    """Manual cell parameter request — generate FullMiller.txt from 6 params + wavelength."""

    a: float = Field(gt=0)
    b: float = Field(gt=0)
    c: float = Field(gt=0)
    alpha: float = Field(gt=0, le=180)
    beta: float = Field(gt=0, le=180)
    gamma: float = Field(gt=0, le=180)
    wavelength: float = Field(default=1.542, gt=0)


class ManualCellResponse(BaseModel):
    """Response for manual FullMiller generation."""

    success: bool = True
    data: Optional[dict] = None
    message: Optional[str] = None


class ManualBatchItem(BaseModel):
    """One item in a manual batch request."""

    label: str = Field(default="")
    a: float = Field(gt=0)
    b: float = Field(gt=0)
    c: float = Field(gt=0)
    alpha: float = Field(gt=0, le=180)
    beta: float = Field(gt=0, le=180)
    gamma: float = Field(gt=0, le=180)
    wavelength: float = Field(default=1.542, gt=0)


class ManualBatchRequest(BaseModel):
    """Batch manual cell request — multiple groups of 6 params + wavelength."""

    groups: List[ManualBatchItem] = Field(min_length=1)


class ManualBatchResponse(BaseModel):
    """Response for batch manual FullMiller generation."""

    success: bool = True
    data: Optional[List[dict]] = None
    message: Optional[str] = None


class GlideBatchRequest(BaseModel):
    """Independent GLIDE request — base cell + wavelength + multiple glide shear groups."""

    a: float = Field(gt=0)
    b: float = Field(gt=0)
    c: float = Field(gt=0)
    alpha: float = Field(gt=0, le=180)
    beta: float = Field(gt=0, le=180)
    gamma: float = Field(gt=0, le=180)
    wavelength: float = Field(default=1.542, gt=0)
    glideGroups: List[GlideBatchParams] = Field(min_length=1)


class GlideBatchResponse(BaseModel):
    """Response for independent GLIDE batch FullMiller generation."""

    success: bool = True
    data: Optional[dict] = None
    message: Optional[str] = None
