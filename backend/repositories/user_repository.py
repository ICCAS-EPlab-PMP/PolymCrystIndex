"""User repository for SQLite database operations."""
import aiosqlite
from datetime import datetime
from typing import List, Optional

from models.user import User


class UserRepository:
    """Handles all user-related SQLite database operations."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def _ensure_column(self, db: aiosqlite.Connection, column_name: str, definition: str) -> None:
        async with db.execute("PRAGMA table_info(users)") as cursor:
            rows = await cursor.fetchall()
        columns = {row[1] for row in rows}
        if column_name not in columns:
            await db.execute(f"ALTER TABLE users ADD COLUMN {column_name} {definition}")

    async def init_db(self) -> None:
        """Create the users table if it does not exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    display_name TEXT,
                    school TEXT DEFAULT '',
                    organization TEXT DEFAULT '',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    is_approved INTEGER NOT NULL DEFAULT 0,
                    run_count INTEGER NOT NULL DEFAULT 0,
                    run_limit_override INTEGER,
                    max_threads_override INTEGER,
                    created_at TEXT NOT NULL
                )
            """)
            await self._ensure_column(db, "school", "TEXT DEFAULT ''")
            await self._ensure_column(db, "organization", "TEXT DEFAULT ''")
            await self._ensure_column(db, "is_approved", "INTEGER NOT NULL DEFAULT 0")
            await self._ensure_column(db, "run_count", "INTEGER NOT NULL DEFAULT 0")
            await self._ensure_column(db, "run_limit_override", "INTEGER")
            await self._ensure_column(db, "max_threads_override", "INTEGER")
            await db.commit()

    async def create_user(
        self,
        username: str,
        password_hash: str,
        role: str = "user",
        display_name: Optional[str] = None,
        school: Optional[str] = None,
        organization: Optional[str] = None,
        is_approved: bool = False,
    ) -> Optional[User]:
        """Create a new user. Returns None if username already exists."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO users (
                        username, password_hash, role, display_name, school, organization,
                        is_active, is_approved, run_count, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?, 0, ?)
                    """,
                    (
                        username,
                        password_hash,
                        role,
                        display_name or username,
                        school or "",
                        organization or "",
                        1 if is_approved else 0,
                        datetime.utcnow().isoformat(),
                    ),
                )
                await db.commit()
            return await self.get_user_by_username(username)
        except aiosqlite.IntegrityError:
            return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieve a user by username."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    return None
                return self._row_to_user(row)

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Retrieve a user by id."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    return None
                return self._row_to_user(row)

    async def list_users(self, include_inactive: bool = False) -> List[User]:
        """List all users. Optionally include inactive users.

        Returns users ordered by created_at DESC for consistent listing order.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM users"
            if not include_inactive:
                query += " WHERE is_active = 1"
            query += " ORDER BY created_at DESC"
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_user(row) for row in rows]

    async def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user fields. Returns True if user exists and was updated.

        Note: This is a data layer method with no business validation.
        All business logic (e.g. role changes, password resets) should be
        enforced at the service layer before calling this method.
        """
        allowed_fields = {
            "username", "password_hash", "role", "display_name", "school", "organization",
            "is_active", "is_approved", "run_count", "run_limit_override", "max_threads_override"
        }
        sets = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                if key == "is_active":
                    value = 1 if value else 0
                if key == "is_approved":
                    value = 1 if value else 0
                sets.append(f"{key} = ?")
                values.append(value)
        if not sets:
            return False
        values.append(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"UPDATE users SET {', '.join(sets)} WHERE id = ?", values
            )
            await db.commit()
            return cursor.rowcount > 0

    async def set_user_active(self, user_id: int, is_active: bool) -> bool:
        """Enable or disable a user account."""
        return await self.update_user(user_id, is_active=is_active)

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user by id. Returns True if deleted."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM users WHERE id = ?", (user_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def count_active_admins(self) -> int:
        """Count the number of active admin users."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1"
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def increment_run_count(self, user_id: int) -> bool:
        """Increment the successful submission counter for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE users SET run_count = COALESCE(run_count, 0) + 1 WHERE id = ?",
                (user_id,),
            )
            await db.commit()
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_user(row: aiosqlite.Row) -> User:
        """Convert a database row to a User object."""
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=row["role"],
            display_name=row["display_name"],
            school=row["school"] if "school" in row.keys() else "",
            organization=row["organization"] if "organization" in row.keys() else "",
            is_active=bool(row["is_active"]),
            is_approved=bool(row["is_approved"]) if "is_approved" in row.keys() else False,
            run_count=row["run_count"] if "run_count" in row.keys() and row["run_count"] is not None else 0,
            run_limit_override=row["run_limit_override"] if "run_limit_override" in row.keys() else None,
            max_threads_override=row["max_threads_override"] if "max_threads_override" in row.keys() else None,
            created_at=row["created_at"],
        )
