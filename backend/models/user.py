"""User data model."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """User data class for internal use."""
    username: str
    password_hash: str
    role: str = "user"
    display_name: Optional[str] = None
    school: Optional[str] = None
    organization: Optional[str] = None
    is_active: bool = True
    is_approved: bool = False
    run_count: int = 0
    run_limit_override: Optional[int] = None
    max_threads_override: Optional[int] = None
    created_at: Optional[str] = None
    id: Optional[int] = None

    def to_public_dict(self) -> dict:
        """Return public user info (for API responses)."""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "displayName": self.display_name or self.username,
            "school": self.school or "",
            "organization": self.organization or "",
            "isActive": self.is_active,
            "isApproved": self.is_approved,
            "runCount": self.run_count,
            "runLimitOverride": self.run_limit_override,
            "maxThreadsOverride": self.max_threads_override,
            "createdAt": self.created_at,
        }

    def to_db_dict(self) -> dict:
        """Return dict suitable for database insertion/update."""
        return {
            "username": self.username,
            "password_hash": self.password_hash,
            "role": self.role,
            "display_name": self.display_name,
            "school": self.school,
            "organization": self.organization,
            "is_active": 1 if self.is_active else 0,
            "is_approved": 1 if self.is_approved else 0,
            "run_count": self.run_count,
            "run_limit_override": self.run_limit_override,
            "max_threads_override": self.max_threads_override,
            "created_at": self.created_at,
        }
