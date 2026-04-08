"""Admin user management API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.dependencies import get_user_service, require_permission
from core.dependencies import get_system_config_service
from core.permissions import PERM_USER_READ, PERM_USER_CREATE, PERM_USER_UPDATE, PERM_USER_DISABLE
from core.security import get_password_hash
from models.admin_user import (
    AdminUserItem,
    AdminUserListResponse,
    AdminCreateUserRequest,
    AdminUpdateUserRequest,
    AdminActionResponse,
)
from services.user_service import UserService
from services.system_config_service import SystemConfigService

router = APIRouter(prefix="/admin/users", tags=["Admin Users"])


def _user_to_item(user, system_config_service: SystemConfigService) -> AdminUserItem:
    """Convert User model to AdminUserItem."""
    limits = system_config_service.get_effective_user_limits(user)
    return AdminUserItem(
        id=user.id,
        username=user.username,
        role=user.role,
        displayName=user.display_name,
        school=user.school,
        organization=user.organization,
        isActive=user.is_active,
        isApproved=user.is_approved,
        runCount=user.run_count,
        runLimitOverride=user.run_limit_override,
        maxThreadsOverride=user.max_threads_override,
        effectiveRunLimit=limits["effective_run_limit"],
        effectiveMaxThreads=limits["effective_max_threads"],
        remainingRuns=limits["remaining_runs"],
        createdAt=user.created_at,
    )


@router.get("", response_model=AdminUserListResponse)
async def list_users(
    current_user: dict = Depends(require_permission(PERM_USER_READ)),
    user_service: UserService = Depends(get_user_service),
    system_config_service: SystemConfigService = Depends(get_system_config_service),
):
    """Get all users (admin only, includes inactive)."""
    users = await user_service.list_users(include_inactive=True)
    items = [_user_to_item(u, system_config_service) for u in users]
    return AdminUserListResponse(success=True, data=items)


@router.post("", response_model=AdminActionResponse)
async def create_user(
    request: AdminCreateUserRequest,
    current_user: dict = Depends(require_permission(PERM_USER_CREATE)),
    user_service: UserService = Depends(get_user_service),
    system_config_service: SystemConfigService = Depends(get_system_config_service),
):
    """Create a new user (admin only)."""
    try:
        user = await user_service.admin_create_user(
            username=request.username,
            password=request.password,
            role=request.role,
            display_name=request.displayName,
            school=request.school,
            organization=request.organization,
            is_approved=request.isApproved,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if user is None:
        raise HTTPException(status_code=409, detail="Username already exists")
    await user_service.update_user(
        user.id,
        run_limit_override=request.runLimitOverride,
        max_threads_override=request.maxThreadsOverride,
    )
    user = await user_service.get_user_by_id(user.id)
    item = _user_to_item(user, system_config_service)
    return AdminActionResponse(
        success=True,
        message="User created successfully",
        data=item.dict(),
    )


@router.patch("/{user_id}", response_model=AdminActionResponse)
async def update_user(
    user_id: int,
    request: AdminUpdateUserRequest,
    current_user: dict = Depends(require_permission(PERM_USER_UPDATE)),
    user_service: UserService = Depends(get_user_service),
    system_config_service: SystemConfigService = Depends(get_system_config_service),
):
    """Update user information (admin only).

    Business rules (enforced at service layer):
    - Cannot change own role (prevents losing admin access)
    - Cannot disable self
    - Cannot demote/disable the last active admin
    """
    try:
        result = await user_service.update_user(
            user_id=user_id,
            role=request.role,
            display_name=request.displayName,
            school=request.school,
            organization=request.organization,
            is_active=request.isActive,
            is_approved=request.isApproved,
            run_limit_override=request.runLimitOverride,
            max_threads_override=request.maxThreadsOverride,
            operator_id=current_user.get("id"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    user = await user_service.get_user_by_id(user_id)
    item = _user_to_item(user, system_config_service)
    return AdminActionResponse(
        success=True,
        message="User updated successfully",
        data=item.dict(),
    )


@router.post("/{user_id}/disable", response_model=AdminActionResponse)
async def disable_user(
    user_id: int,
    current_user: dict = Depends(require_permission(PERM_USER_DISABLE)),
    user_service: UserService = Depends(get_user_service),
):
    """Disable a user (admin only).

    Business rules (enforced at service layer):
    - Cannot disable yourself
    - Cannot disable the last active admin
    """
    try:
        result = await user_service.disable_user(user_id, operator_id=current_user.get("id"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return AdminActionResponse(success=True, message="User disabled successfully")


@router.post("/{user_id}/enable", response_model=AdminActionResponse)
async def enable_user(
    user_id: int,
    current_user: dict = Depends(require_permission(PERM_USER_UPDATE)),
    user_service: UserService = Depends(get_user_service),
):
    """Enable a user (admin only)."""
    result = await user_service.enable_user(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return AdminActionResponse(success=True, message="User enabled successfully")


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)


@router.post("/{user_id}/reset-password", response_model=AdminActionResponse)
async def reset_password(
    user_id: int,
    request: AdminResetPasswordRequest,
    current_user: dict = Depends(require_permission(PERM_USER_UPDATE)),
    user_service: UserService = Depends(get_user_service),
):
    """Reset a user's password (admin only). Cannot reset own password."""
    user = await user_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.get("id") == user_id:
        raise HTTPException(status_code=400, detail="Cannot reset your own password. Use the change password feature instead.")
    password_hash = get_password_hash(request.new_password)
    await user_service.repository.update_user(user_id, password_hash=password_hash)
    return AdminActionResponse(success=True, message="Password reset successfully")
