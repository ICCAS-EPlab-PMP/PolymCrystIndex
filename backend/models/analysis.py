"""Analysis task request and response models."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


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
    duplicate: bool = False
    
    hklMode: str = Field(default="Default")
    custH: int = Field(default=5, ge=0)
    custK: int = Field(default=5, ge=0)
    custL: int = Field(default=0, ge=0)
    ompThreads: int = Field(default=1, ge=1, le=1024)


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
