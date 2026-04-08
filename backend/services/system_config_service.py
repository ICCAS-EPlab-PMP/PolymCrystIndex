"""System runtime configuration service."""
from typing import Optional

from repositories.system_config_repository import SystemConfigRepository


class SystemConfigService:
    """Service layer for system runtime configuration."""

    MIN_MAX_JOBS = 1
    MAX_MAX_JOBS = 32
    MIN_MAX_OMP_THREADS = 1
    MIN_RUN_LIMIT = 0

    def __init__(self, repository: SystemConfigRepository):
        self._repository = repository
        self._cpu_count = repository.get_runtime_config()["cpu_count"]

    def get_runtime_config(self) -> dict:
        return self._repository.get_runtime_config()

    def update_runtime_config(
        self,
        max_jobs: int,
        max_omp_threads: int,
        default_user_run_limit: int,
        default_user_max_threads: int,
        approved_user_run_limit: int,
        approved_user_max_threads: int,
        operator: str = None,
    ) -> dict:
        max_jobs = max(self.MIN_MAX_JOBS, min(max_jobs, self.MAX_MAX_JOBS))
        max_omp_threads = max(self.MIN_MAX_OMP_THREADS, min(max_omp_threads, self._cpu_count))
        default_user_run_limit = max(self.MIN_RUN_LIMIT, default_user_run_limit)
        default_user_max_threads = max(self.MIN_MAX_OMP_THREADS, min(default_user_max_threads, max_omp_threads))
        approved_user_run_limit = max(self.MIN_RUN_LIMIT, approved_user_run_limit)
        approved_user_max_threads = max(self.MIN_MAX_OMP_THREADS, min(approved_user_max_threads, max_omp_threads))
        return self._repository.upsert_runtime_config(
            max_jobs,
            max_omp_threads,
            default_user_run_limit,
            default_user_max_threads,
            approved_user_run_limit,
            approved_user_max_threads,
            operator,
        )

    def get_max_jobs(self) -> int:
        config = self._repository.get_runtime_config()
        return config["max_jobs"]

    def get_max_omp_threads(self) -> int:
        config = self._repository.get_runtime_config()
        return config["max_omp_threads"]

    def get_effective_user_limits(self, user) -> dict:
        config = self._repository.get_runtime_config()
        base_run_limit = config["approved_user_run_limit"] if user.is_approved else config["default_user_run_limit"]
        base_max_threads = config["approved_user_max_threads"] if user.is_approved else config["default_user_max_threads"]

        effective_run_limit = user.run_limit_override if user.run_limit_override is not None else base_run_limit
        effective_max_threads = user.max_threads_override if user.max_threads_override is not None else base_max_threads
        effective_max_threads = max(1, min(effective_max_threads, config["max_omp_threads"]))
        remaining_runs = -1 if effective_run_limit == 0 else max(0, effective_run_limit - (user.run_count or 0))

        return {
            "effective_run_limit": effective_run_limit,
            "effective_max_threads": effective_max_threads,
            "remaining_runs": remaining_runs,
            "server_max_omp_threads": config["max_omp_threads"],
        }
