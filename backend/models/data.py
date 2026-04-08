"""Data validation and upload models."""
from typing import Optional
from pydantic import BaseModel


class DataCheckRequest(BaseModel):
    """Data validation request (raw text content)."""
    class Config:
        content_type = "text/plain"


class DataCheckResponse(BaseModel):
    """Data validation response."""
    success: bool = True
    data: Optional[dict] = None
    message: Optional[str] = None


class DataUploadResponse(BaseModel):
    """File upload response."""
    success: bool = True
    data: Optional[dict] = None
    message: Optional[str] = None
