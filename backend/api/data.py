"""Data validation and upload API routes."""
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends, Request

from core.dependencies import get_current_user
from models.data import DataCheckResponse, DataUploadResponse
from services.file_service import FileService

# BOM signatures for encoding detection
_BOM_UTF16_LE = b'\xff\xfe'
_BOM_UTF16_BE = b'\xfe\xff'


def _decode_bytes(content: bytes) -> str:
    """Decode bytes to string with BOM-based encoding detection.
    
    Uses Python's 'utf-16' codec which auto-detects BOM and strips it.
    Falls back to 'utf-8' for files without BOM.
    """
    if content.startswith(_BOM_UTF16_LE) or content.startswith(_BOM_UTF16_BE):
        return content.decode('utf-16')
    return content.decode('utf-8')

router = APIRouter(prefix="/data", tags=["Data"])


@router.post("/check", response_model=DataCheckResponse)
async def check_data(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Validate diffraction data format.
    
    Request body should contain raw text with format: q psi intensity (one per line)
    """
    content = await request.body()
    
    try:
        text_content = _decode_bytes(content)
    except UnicodeDecodeError:
        return DataCheckResponse(
            success=False,
            data={"valid": False},
            message="Invalid text encoding (expected UTF-8 or UTF-16 with BOM)"
        )
    
    is_valid, count, message = FileService.validate_diffraction_data(text_content)
    
    if not is_valid:
        return DataCheckResponse(
            success=False,
            data={"valid": False},
            message=message
        )
    
    return DataCheckResponse(
        success=True,
        data={
            "valid": True,
            "count": count,
            "message": message
        }
    )


@router.post("/upload", response_model=DataUploadResponse)
async def upload_data(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload diffraction data file.
    
    Accepts multipart/form-data with 'file' field containing the diffraction data.
    """
    if not file.filename:
        return DataUploadResponse(
            success=False,
            message="No filename provided"
        )
    
    try:
        content = await file.read()
        
        text_content = _decode_bytes(content)
        is_valid, count, message = FileService.validate_diffraction_data(text_content)
        
        if not is_valid:
            return DataUploadResponse(
                success=False,
                message=f"Invalid file format: {message}"
            )
        
        utf8_bytes = text_content.encode('utf-8')
        saved_path = FileService.save_uploaded_file(
            utf8_bytes,
            file.filename,
            subdir=current_user["username"]
        )
        
        file_size = FileService.get_file_size(saved_path)
        
        return DataUploadResponse(
            success=True,
            data={
                "filename": file.filename,
                "size": file_size,
                "pointCount": count,
                "path": saved_path
            }
        )
        
    except Exception as e:
        return DataUploadResponse(
            success=False,
            message=f"Upload failed: {str(e)}"
        )
