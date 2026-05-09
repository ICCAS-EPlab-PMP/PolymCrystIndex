"""Update check API routes."""

from fastapi import APIRouter, Depends

from core.dependencies import get_update_service
from services.update_service import UpdateService

router = APIRouter(prefix="/update", tags=["Update"])


@router.get("/check")
async def check_for_updates(
    update_service: UpdateService = Depends(get_update_service),
):
    """Check latest published version with GitHub primary and Gitee fallback."""
    return update_service.check()
