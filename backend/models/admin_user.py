"""Admin user management API models."""
from typing import Optional, List

from pydantic import BaseModel, Field


class AdminUserItem(BaseModel):
    id: int
    username: str
    role: str
    displayName: Optional[str] = None
    school: Optional[str] = None
    organization: Optional[str] = None
    isActive: bool
    isApproved: bool = False
    runCount: int = 0
    runLimitOverride: Optional[int] = None
    maxThreadsOverride: Optional[int] = None
    effectiveRunLimit: int = 0
    effectiveMaxThreads: int = 1
    remainingRuns: int = -1
    createdAt: str


class AdminUserListResponse(BaseModel):
    success: bool = True
    data: List[AdminUserItem] = Field(default_factory=list)
    message: Optional[str] = None


class AdminCreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    role: str = Field(default="user")
    displayName: Optional[str] = None
    school: Optional[str] = None
    organization: Optional[str] = None
    isApproved: bool = False
    runLimitOverride: Optional[int] = Field(default=None, ge=0, le=1000000)
    maxThreadsOverride: Optional[int] = Field(default=None, ge=1, le=1024)


class AdminUpdateUserRequest(BaseModel):
    role: Optional[str] = None
    displayName: Optional[str] = None
    school: Optional[str] = None
    organization: Optional[str] = None
    isActive: Optional[bool] = None
    isApproved: Optional[bool] = None
    runLimitOverride: Optional[int] = Field(default=None, ge=0, le=1000000)
    maxThreadsOverride: Optional[int] = Field(default=None, ge=1, le=1024)


class AdminActionResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[dict] = None
