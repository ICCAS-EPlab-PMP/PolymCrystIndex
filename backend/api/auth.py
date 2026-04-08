"""Authentication API routes."""
from fastapi import APIRouter, Depends

from core.dependencies import get_auth_service, get_current_user
from models.auth import LoginRequest, RegisterRequest, TokenResponse, UserInfo
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_auth_svc() -> AuthService:
    """Dependency to get AuthService instance."""
    return get_auth_service()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, auth_service: AuthService = Depends(get_auth_svc)):
    """User login endpoint. Returns JWT token on success."""
    return await auth_service.login(request.username, request.password)


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, auth_service: AuthService = Depends(get_auth_svc)):
    """User registration endpoint. Creates a new user account."""
    return await auth_service.register(
        request.username,
        request.password,
        request.school,
        request.organization,
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
):
    """Get current authenticated user information."""
    return current_user
