"""Authentication request and response models."""
from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request payload."""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    """Registration request payload."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    school: Optional[str] = Field(default=None, max_length=100)
    organization: Optional[str] = Field(default=None, max_length=150)


class TokenResponse(BaseModel):
    """Token response after successful login."""
    success: bool = True
    data: Optional[dict] = None
    message: Optional[str] = None


class UserInfo(BaseModel):
    """User information stored in token."""
    username: str
    role: str = "user"
    displayName: Optional[str] = None
    school: Optional[str] = None
    organization: Optional[str] = None
    isApproved: Optional[bool] = None
    runCount: Optional[int] = None
