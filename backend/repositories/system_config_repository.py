"""System runtime configuration repository."""
import sqlite3
import time


class SystemConfigRepository:
    """SQLite-backed system runtime configuration storage."""

    DEFAULT_MAX_JOBS = 1

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._cpu_count = max(1, __import__("os").cpu_count() or 1)
        self.DEFAULT_MAX_OMP_THREADS = self._cpu_count
        self.DEFAULT_DEFAULT_USER_RUN_LIMIT = 0
        self.DEFAULT_DEFAULT_USER_MAX_THREADS = min(4, self._cpu_count)
        self.DEFAULT_APPROVED_USER_RUN_LIMIT = 0
        self.DEFAULT_APPROVED_USER_MAX_THREADS = self._cpu_count
        self.ensure_initialized()

    def _ensure_column(self, conn: sqlite3.Connection, column_name: str, definition: str) -> None:
        rows = conn.execute("PRAGMA table_info(system_config)").fetchall()
        columns = {row[1] for row in rows}
        if column_name not in columns:
            conn.execute(f"ALTER TABLE system_config ADD COLUMN {column_name} {definition}")

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def ensure_initialized(self) -> None:
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    max_jobs INTEGER NOT NULL DEFAULT 1,
                    max_omp_threads INTEGER NOT NULL DEFAULT 1,
                    default_user_run_limit INTEGER NOT NULL DEFAULT 0,
                    default_user_max_threads INTEGER NOT NULL DEFAULT 4,
                    approved_user_run_limit INTEGER NOT NULL DEFAULT 0,
                    approved_user_max_threads INTEGER NOT NULL DEFAULT 1,
                    updated_at REAL NOT NULL,
                    updated_by TEXT
                )
            """)
            self._ensure_column(conn, "default_user_run_limit", f"INTEGER NOT NULL DEFAULT {self.DEFAULT_DEFAULT_USER_RUN_LIMIT}")
            self._ensure_column(conn, "default_user_max_threads", f"INTEGER NOT NULL DEFAULT {self.DEFAULT_DEFAULT_USER_MAX_THREADS}")
            self._ensure_column(conn, "approved_user_run_limit", f"INTEGER NOT NULL DEFAULT {self.DEFAULT_APPROVED_USER_RUN_LIMIT}")
            self._ensure_column(conn, "approved_user_max_threads", f"INTEGER NOT NULL DEFAULT {self.DEFAULT_APPROVED_USER_MAX_THREADS}")
            conn.execute(
                """INSERT OR IGNORE INTO system_config (
                    id, max_jobs, max_omp_threads, default_user_run_limit,
                    default_user_max_threads, approved_user_run_limit,
                    approved_user_max_threads, updated_at
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    self.DEFAULT_MAX_JOBS,
                    self.DEFAULT_MAX_OMP_THREADS,
                    self.DEFAULT_DEFAULT_USER_RUN_LIMIT,
                    self.DEFAULT_DEFAULT_USER_MAX_THREADS,
                    self.DEFAULT_APPROVED_USER_RUN_LIMIT,
                    self.DEFAULT_APPROVED_USER_MAX_THREADS,
                    time.time(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_runtime_config(self) -> dict:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM system_config WHERE id = 1").fetchone()
            if row:
                return {
                    "max_jobs": row["max_jobs"],
                    "max_omp_threads": row["max_omp_threads"],
                    "default_user_run_limit": row["default_user_run_limit"],
                    "default_user_max_threads": row["default_user_max_threads"],
                    "approved_user_run_limit": row["approved_user_run_limit"],
                    "approved_user_max_threads": row["approved_user_max_threads"],
                    "cpu_count": self._cpu_count,
                    "updated_at": row["updated_at"],
                    "updated_by": row["updated_by"],
                }
            return {
                "max_jobs": self.DEFAULT_MAX_JOBS,
                "max_omp_threads": self.DEFAULT_MAX_OMP_THREADS,
                "default_user_run_limit": self.DEFAULT_DEFAULT_USER_RUN_LIMIT,
                "default_user_max_threads": self.DEFAULT_DEFAULT_USER_MAX_THREADS,
                "approved_user_run_limit": self.DEFAULT_APPROVED_USER_RUN_LIMIT,
                "approved_user_max_threads": self.DEFAULT_APPROVED_USER_MAX_THREADS,
                "cpu_count": self._cpu_count,
                "updated_at": None,
                "updated_by": None,
            }
        finally:
            conn.close()

    def upsert_runtime_config(
        self,
        max_jobs: int,
        max_omp_threads: int,
        default_user_run_limit: int,
        default_user_max_threads: int,
        approved_user_run_limit: int,
        approved_user_max_threads: int,
        updated_by: str = None,
    ) -> dict:
        now = time.time()
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO system_config (
                       id, max_jobs, max_omp_threads, default_user_run_limit,
                       default_user_max_threads, approved_user_run_limit,
                       approved_user_max_threads, updated_at, updated_by
                   )
                   VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                        max_jobs = excluded.max_jobs,
                        max_omp_threads = excluded.max_omp_threads,
                        default_user_run_limit = excluded.default_user_run_limit,
                        default_user_max_threads = excluded.default_user_max_threads,
                        approved_user_run_limit = excluded.approved_user_run_limit,
                        approved_user_max_threads = excluded.approved_user_max_threads,
                        updated_at = excluded.updated_at,
                        updated_by = excluded.updated_by""",
                (
                    max_jobs,
                    max_omp_threads,
                    default_user_run_limit,
                    default_user_max_threads,
                    approved_user_run_limit,
                    approved_user_max_threads,
                    now,
                    updated_by,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return {
            "max_jobs": max_jobs,
            "max_omp_threads": max_omp_threads,
            "default_user_run_limit": default_user_run_limit,
            "default_user_max_threads": default_user_max_threads,
            "approved_user_run_limit": approved_user_run_limit,
            "approved_user_max_threads": approved_user_max_threads,
            "cpu_count": self._cpu_count,
            "updated_at": now,
            "updated_by": updated_by,
        }
