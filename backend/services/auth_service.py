"""Authentication service handling JWT token lifecycle."""
from datetime import timedelta
from typing import Optional

from core.config import settings
from core.security import create_access_token, verify_token
from core.permissions import get_permissions_for_role
from models.auth import TokenResponse
from models.user import User
from services.user_service import UserService


class AuthService:
    """Handles authentication and JWT token management."""

    def __init__(self, user_service: UserService):
        self.user_service = user_service

    def create_access_token(self, user: User) -> str:
        """Generate a JWT token for the given user."""
        return create_access_token(
            data={
                "sub": user.username,
                "role": user.role,
            },
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

    async def login(self, username: str, password: str) -> TokenResponse:
        """Authenticate user and return token response."""
        user = await self.user_service.authenticate(username, password)
        if user is None:
            return TokenResponse(
                success=False,
                message="Invalid username or password",
            )
        token = self.create_access_token(user)
        permissions = list(get_permissions_for_role(user.role))
        return TokenResponse(
            success=True,
            data={
                "token": token,
                "user": user.to_public_dict(),
                "permissions": permissions,
            },
        )

    async def register(self, username: str, password: str, school: Optional[str], organization: Optional[str]) -> TokenResponse:
        """Register a new user account."""
        school = (school or "").strip()
        organization = (organization or "").strip()
        if not school and not organization:
            return TokenResponse(
                success=False,
                message="Please fill in either school or organization",
            )
        existing = await self.user_service.get_user(username)
        if existing is not None:
            return TokenResponse(
                success=False,
                message="Username already exists",
            )
        user = await self.user_service.create_user(
            username=username,
            password=password,
            role="user",
            school=school,
            organization=organization,
        )
        if user is None:
            return TokenResponse(
                success=False,
                message="Registration failed",
            )
        return TokenResponse(
            success=True,
            message="Registration successful",
        )

    async def get_current_user(self, token: str) -> Optional[dict]:
        """Validate token and return current user info from database."""
        payload = verify_token(token)
        if payload is None:
            return None
        username: str = payload.get("sub")
        if username is None:
            return None
        user = await self.user_service.get_user(username)
        if user is None:
            return None
        if not user.is_active:
            return None
        return user.to_public_dict()
