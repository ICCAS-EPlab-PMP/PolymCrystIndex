"""Admin task audit API models."""
from typing import Optional, List

from pydantic import BaseModel, Field


class AdminTaskItem(BaseModel):
    id: str
    userId: str
    status: str
    currentStep: int
    totalSteps: int
    bestFitness: float
    errorMessage: Optional[str] = None
    createdAt: Optional[float] = None
    startedAt: Optional[float] = None
    completedAt: Optional[float] = None


class AdminTaskListResponse(BaseModel):
    success: bool = True
    data: List[AdminTaskItem] = Field(default_factory=list)
    message: Optional[str] = None


class AdminTaskDetailResponse(BaseModel):
    success: bool = True
    data: Optional[AdminTaskItem] = None
    message: Optional[str] = None


class AdminTaskLogsResponse(BaseModel):
    success: bool = True
    data: Optional[dict] = None
    message: Optional[str] = None


class AdminTaskActionResponse(BaseModel):
    success: bool = True
    message: str
