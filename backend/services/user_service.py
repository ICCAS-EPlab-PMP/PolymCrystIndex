"""User business logic service."""
from typing import List, Optional

from core.config import settings
from core.security import get_password_hash, verify_password
from models.user import User
from repositories.user_repository import UserRepository


class UserService:
    """Handles user-related business logic."""

    VALID_ROLES = {"admin", "user"}

    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def create_user(
        self,
        username: str,
        password: str,
        role: str = "user",
        display_name: Optional[str] = None,
        school: Optional[str] = None,
        organization: Optional[str] = None,
        is_approved: bool = False,
    ) -> Optional[User]:
        """Register a new user with hashed password."""
        username = username.strip()
        if role not in self.VALID_ROLES:
            role = "user"
        password_hash = get_password_hash(password)
        user = await self.repository.create_user(
            username=username,
            password_hash=password_hash,
            role=role,
            display_name=display_name or username,
            school=school,
            organization=organization,
            is_approved=is_approved,
        )
        return user

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user by username and password. Returns None if failed."""
        user = await self.repository.get_user_by_username(username)
        if user is None:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    async def get_user(self, username: str) -> Optional[User]:
        """Get user by username."""
        return await self.repository.get_user_by_username(username)

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by id."""
        return await self.repository.get_user_by_id(user_id)

    async def list_users(self, include_inactive: bool = True) -> List[User]:
        """List all users (admin only). Can include inactive users when include_inactive=True."""
        return await self.repository.list_users(include_inactive=include_inactive)

    async def disable_user(self, user_id: int, operator_id: Optional[int] = None) -> bool:
        """Disable a user account.

        Args:
            user_id: User ID to disable
            operator_id: ID of the user performing the operation (optional)

        Returns:
            True if disabled, False if user not found

        Raises:
            ValueError: If trying to disable yourself
            ValueError: If trying to disable the last active admin
        """
        if operator_id is not None and operator_id == user_id:
            raise ValueError("Cannot disable yourself")
        user = await self.repository.get_user_by_id(user_id)
        if user and user.role == "admin":
            admin_count = await self.repository.count_active_admins()
            if admin_count <= 1:
                raise ValueError("Cannot disable the last active admin")
        return await self.repository.set_user_active(user_id, False)

    async def enable_user(self, user_id: int) -> bool:
        """Enable a user account."""
        return await self.repository.set_user_active(user_id, True)

    async def admin_create_user(
        self,
        username: str,
        password: str,
        role: str = "user",
        display_name: Optional[str] = None,
        school: Optional[str] = None,
        organization: Optional[str] = None,
        is_approved: bool = False,
    ) -> Optional[User]:
        """Admin creates a user with role validation.

        Args:
            username: Unique username
            password: Plain text password (will be hashed)
            role: Must be "admin" or "user"
            display_name: Optional display name

        Returns:
            Created User or None if username already exists

        Raises:
            ValueError: if role is not "admin" or "user"
        """
        if role not in self.VALID_ROLES:
            raise ValueError("Invalid role")
        existing = await self.repository.get_user_by_username(username)
        if existing is not None:
            return None
        return await self.create_user(
            username,
            password,
            role,
            display_name,
            school,
            organization,
            is_approved,
        )

    async def update_user(
        self,
        user_id: int,
        role: Optional[str] = None,
        display_name: Optional[str] = None,
        school: Optional[str] = None,
        organization: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_approved: Optional[bool] = None,
        run_limit_override: Optional[int] = None,
        max_threads_override: Optional[int] = None,
        operator_id: Optional[int] = None,
    ) -> bool:
        """Update user information at service layer with business rules.

        Args:
            user_id: User ID to update
            role: New role (optional), must be "admin" or "user"
            display_name: New display name (optional)
            is_active: New active status (optional)
            operator_id: ID of the user performing the operation (optional)

        Returns:
            True if updated, False if user not found

        Raises:
            ValueError: if role is not "admin" or "user"
            ValueError: if trying to change your own role
            ValueError: if trying to disable yourself
            ValueError: if demoting the last active admin to user role
            ValueError: if disabling the last active admin
        """
        if role is not None and role not in self.VALID_ROLES:
            raise ValueError("Invalid role")
        user = await self.repository.get_user_by_id(user_id)
        if user is None:
            return False
        is_self_operation = operator_id is not None and operator_id == user_id
        if is_self_operation:
            if role is not None and role != user.role:
                raise ValueError("Cannot change your own role")
            if is_active is False:
                raise ValueError("Cannot disable yourself")
        if user.role == "admin":
            admin_count = await self.repository.count_active_admins()
            is_demoting = role is not None and role != "admin"
            is_disabling = is_active is False
            if admin_count <= 1 and (is_demoting or is_disabling):
                raise ValueError("Cannot demote or disable the last active admin")
        updates = {}
        if role is not None:
            updates["role"] = role
        if display_name is not None:
            updates["display_name"] = display_name
        if school is not None:
            updates["school"] = school
        if organization is not None:
            updates["organization"] = organization
        if is_active is not None:
            updates["is_active"] = is_active
        if is_approved is not None:
            updates["is_approved"] = is_approved
        updates["run_limit_override"] = run_limit_override
        updates["max_threads_override"] = max_threads_override
        if not updates:
            raise ValueError("No valid fields to update")
        return await self.repository.update_user(user_id, **updates)

    async def increment_run_count(self, user_id: int) -> bool:
        """Increment analysis submission count for quota tracking."""
        return await self.repository.increment_run_count(user_id)

    async def ensure_admin_exists(self) -> None:
        """Ensure the default admin account exists. Creates it if missing.

        Admin credentials are read from settings.DEFAULT_ADMIN_USERNAME / DEFAULT_ADMIN_PASSWORD.
        """
        await self.repository.init_db()
        existing = await self.repository.get_user_by_username(settings.DEFAULT_ADMIN_USERNAME)
        if existing is None:
            await self.create_user(
                username=settings.DEFAULT_ADMIN_USERNAME,
                password=settings.DEFAULT_ADMIN_PASSWORD,
                role="admin",
                display_name="Administrator",
                is_approved=True,
            )

    async def ensure_local_user_exists(self) -> None:
        """Ensure the local single-user account exists when auth is disabled."""
        await self.repository.init_db()
        existing = await self.repository.get_user_by_username(settings.LOCAL_USERNAME)
        if existing is None:
            await self.create_user(
                username=settings.LOCAL_USERNAME,
                password="local-only",
                role="user",
                display_name=settings.LOCAL_DISPLAY_NAME,
                is_approved=True,
            )
