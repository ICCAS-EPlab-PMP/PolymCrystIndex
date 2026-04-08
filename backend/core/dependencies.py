"""FastAPI dependencies for dependency injection."""
from typing import TYPE_CHECKING, Dict, Optional, Callable

from fastapi import Depends, HTTPException, Request, status

from .config import settings
from .permissions import has_permission, ROLE_ADMIN
from repositories.user_repository import UserRepository
from services.auth_service import AuthService
from services.indexing_service import IndexingService
from services.task_manager import TaskManager
from services.user_service import UserService

if TYPE_CHECKING:
    from repositories.system_config_repository import SystemConfigRepository
    from services.system_config_service import SystemConfigService


_task_manager: Optional[TaskManager] = None
_indexing_service: Optional[IndexingService] = None
_user_repository: Optional[UserRepository] = None
_user_service: Optional[UserService] = None
_auth_service: Optional[AuthService] = None
_system_config_repository: Optional["SystemConfigRepository"] = None
_system_config_service: Optional["SystemConfigService"] = None


def get_user_repository() -> UserRepository:
    """Get the global UserRepository instance."""
    global _user_repository
    if _user_repository is None:
        _user_repository = UserRepository(settings.USER_DB_PATH)
    return _user_repository


def get_user_service() -> UserService:
    """Get the global UserService instance."""
    global _user_service
    if _user_service is None:
        _user_service = UserService(get_user_repository())
    return _user_service


def get_auth_service() -> AuthService:
    """Get the global AuthService instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService(get_user_service())
    return _auth_service


def get_task_manager() -> TaskManager:
    """Get the global task manager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager(max_jobs=settings.MAX_JOBS)
    return _task_manager


def get_indexing_service() -> IndexingService:
    """Get the global indexing service instance."""
    global _indexing_service
    if _indexing_service is None:
        _indexing_service = IndexingService(get_task_manager())
    return _indexing_service


def get_system_config_repository() -> "SystemConfigRepository":
    """Get the global system config repository instance."""
    global _system_config_repository
    if _system_config_repository is None:
        from repositories.system_config_repository import SystemConfigRepository
        _system_config_repository = SystemConfigRepository(settings.USER_DB_PATH)
    return _system_config_repository


def get_system_config_service() -> "SystemConfigService":
    """Get the global system config service instance."""
    global _system_config_service
    if _system_config_service is None:
        from services.system_config_service import SystemConfigService
        _system_config_service = SystemConfigService(get_system_config_repository())
    return _system_config_service


async def get_current_user(request: Request) -> Dict[str, str]:
    """Dependency to get the current authenticated user from JWT token.

    When AUTH_DISABLED is True (local profile), returns a fixed local user
    without requiring any token.
    """

    if settings.AUTH_DISABLED:
        user_service = get_user_service()
        user = await user_service.get_user(settings.LOCAL_USERNAME)
        if user is None:
            await user_service.ensure_local_user_exists()
            user = await user_service.get_user(settings.LOCAL_USERNAME)
        if user is None:
            return {
                "id": 0,
                "username": settings.LOCAL_USERNAME,
                "role": "user",
                "displayName": settings.LOCAL_DISPLAY_NAME,
                "school": "",
                "organization": "",
                "isActive": True,
                "isApproved": True,
                "runCount": 0,
                "runLimitOverride": None,
                "maxThreadsOverride": None,
                "createdAt": None,
            }
        return user.to_public_dict()

    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header[len("Bearer "):]
    auth_service = get_auth_service()
    user = await auth_service.get_current_user(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(role: str) -> Callable:
    """Dependency factory: check if current user has the required role.

    Args:
        role: Required role name

    Returns:
        FastAPI dependency that validates role and returns current_user
    """
    async def dependency(
        current_user: Dict[str, str] = Depends(get_current_user)
    ) -> Dict[str, str]:
        if current_user.get("role") != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        return current_user
    return dependency


def require_permission(permission: str) -> Callable:
    """Dependency factory: check if current user has the required permission.

    Args:
        permission: Required permission string (e.g., "user:read")

    Returns:
        FastAPI dependency that validates permission and returns current_user
    """
    async def dependency(
        current_user: Dict[str, str] = Depends(get_current_user)
    ) -> Dict[str, str]:
        if not has_permission(current_user.get("role"), permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        return current_user
    return dependency


get_admin_user = require_role(ROLE_ADMIN)


async def get_optional_user(request: Request) -> Optional[Dict[str, str]]:
    """Optional user dependency that returns None if not authenticated."""

    if settings.AUTH_DISABLED:
        return await get_current_user(request)

    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header[len("Bearer "):]
    auth_service = get_auth_service()
    return await auth_service.get_current_user(token)
