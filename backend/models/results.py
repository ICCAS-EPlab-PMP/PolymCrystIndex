"""Results response models."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class CellParams(BaseModel):
    """Unit cell parameters."""
    a: float
    b: float
    c: float
    alpha: float
    beta: float
    gamma: float


class MillerDataPoint(BaseModel):
    """Miller indices with diffraction data."""
    h: int
    k: int
    l: int
    q: float
    psi: float


class MaxDeviationPoint(BaseModel):
    """Point with maximum deviation."""
    h: int
    k: int
    l: int
    q: float


class QualityMetrics(BaseModel):
    """Quality metrics for fitting results."""
    rFactor: float
    maxDeviation: float
    maxDeviationPoint: MaxDeviationPoint


class FilesInfo(BaseModel):
    """Output file information."""
    cellFile: str
    millerFile: str
    fullMillerFile: str


class ResultsResponse(BaseModel):
    """Full analysis results response."""
    success: bool = True
    data: Optional[dict] = None
    message: Optional[str] = None
