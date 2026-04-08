"""System runtime configuration models."""
from typing import Optional
from pydantic import BaseModel, Field


class RuntimeConfigData(BaseModel):
    maxJobs: int
    maxOmpThreads: int
    defaultUserRunLimit: int
    defaultUserMaxThreads: int
    approvedUserRunLimit: int
    approvedUserMaxThreads: int
    cpuCount: int
    updatedAt: Optional[float] = None
    updatedBy: Optional[str] = None


class RuntimeConfigResponse(BaseModel):
    success: bool = True
    data: Optional[RuntimeConfigData] = None
    message: Optional[str] = None


class RuntimeConfigUpdateRequest(BaseModel):
    maxJobs: int = Field(..., ge=1, le=32)
    maxOmpThreads: int = Field(..., ge=1, le=1024)
    defaultUserRunLimit: int = Field(..., ge=0, le=1000000)
    defaultUserMaxThreads: int = Field(..., ge=1, le=1024)
    approvedUserRunLimit: int = Field(..., ge=0, le=1000000)
    approvedUserMaxThreads: int = Field(..., ge=1, le=1024)


class RuntimeConfigUpdateResponse(BaseModel):
    success: bool = True
    data: Optional[RuntimeConfigData] = None
    message: Optional[str] = None
