"""Application configuration settings."""

import os
import platform
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).parent.parent
_PROJECT_ROOT = BACKEND_DIR.parent
_IS_WIN = platform.system() == "Windows"
_RUNTIME_DATA_ROOT_ENV = os.getenv("POLYCRYINDEX_RUNTIME_DATA_DIR", "").strip()
_RUNTIME_DATA_ROOT = Path(_RUNTIME_DATA_ROOT_ENV) if _RUNTIME_DATA_ROOT_ENV else None


def _runtime_data_path(relative_name: str, fallback_root: Path) -> str:
    root = _RUNTIME_DATA_ROOT or fallback_root
    return str(root / relative_name)


def _default_fortran_executable() -> str:
    name = "lm_opt2.exe" if _IS_WIN else "lm_opt2"
    return str(_PROJECT_ROOT / "fortrancode" / name)


def _default_postprocess_executable() -> str:
    name = "lm_postprocess.exe" if _IS_WIN else "lm_postprocess"
    return str(_PROJECT_ROOT / "fortrancode" / name)


def _resolve_profile() -> str:
    profile = (
        os.getenv("APP_PROFILE", "").strip().lower()
        or os.getenv("PROFILE", "").strip().lower()
    )
    if profile in ("local", "cloud"):
        return profile

    app_env = os.getenv("APP_ENV", "").strip().lower()
    if app_env in ("beta", "production"):
        return "cloud"
    return "local"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Profile defaults (local): AUTH_DISABLED=True, ENABLE_DOCS=True, HOST=127.0.0.1
    Profile defaults (cloud): AUTH_DISABLED=False, ENABLE_DOCS=False, HOST=0.0.0.0
    """

    PROJECT_NAME: str = "PolymCrystIndex API"
    VERSION: str = "1.8.4"
    API_PREFIX: str = "/api"
    OFFICIAL_DOWNLOAD_URL: str = "http://www.polymcrystal.com/download/PolymCrystindexsetup.zip"
    GITHUB_RELEASES_API_URL: str = "https://api.github.com/repos/ICCAS-EPlab-PMP/PolymCrystalIndex/releases/latest"
    GITHUB_RELEASES_PAGE_URL: str = "https://github.com/ICCAS-EPlab-PMP/PolymCrystalIndex/releases"
    GITHUB_LATEST_RELEASE_URL: str = "https://github.com/ICCAS-EPlab-PMP/PolymCrystalIndex/releases/latest"
    GITEE_TAGS_API_URL: str = ""
    GITEE_RELEASES_PAGE_URL: str = ""
    UPDATE_CHECK_TIMEOUT_SECONDS: int = 5
    UPDATE_CHECK_CACHE_TTL_SECONDS: int = 600

    # --- Profile ---
    APP_PROFILE: str = ""
    PROFILE: str = ""
    APP_ENV: str = ""

    # --- Auth & Security ---
    AUTH_DISABLED: bool = True
    LOCAL_USERNAME: str = "localuser"
    LOCAL_DISPLAY_NAME: str = "Local Researcher"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # --- Server ---
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    LOG_LEVEL: str = "info"
    ENABLE_DOCS: bool = True

    # --- CORS ---
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    # --- Database ---
    USER_DB_PATH: str = _runtime_data_path("users.db", BACKEND_DIR)

    # --- Admin ---
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"

    # --- Directories ---
    UPLOAD_DIR: str = _runtime_data_path("temp", BACKEND_DIR)
    RESULT_DIR: str = _runtime_data_path("result", BACKEND_DIR)
    HDF5_DIR: str = _runtime_data_path("hdf5", BACKEND_DIR)
    USER_RESULT_DIR: str = _runtime_data_path("userresult", BACKEND_DIR)

    # --- Limits ---
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024
    MAX_JOBS: int = 1
    MAX_OMP_THREADS: int = 1
    OMP_NUM_THREADS: int = 0

    # --- Fortran ---
    FORTRAN_EXECUTABLE: str = _default_fortran_executable()
    FORTRAN_POSTPROCESS_EXECUTABLE: str = _default_postprocess_executable()
    WORKING_DIR: str = _runtime_data_path("workdir", BACKEND_DIR)

    class Config:
        env_file = ".env"
        case_sensitive = True


def get_settings() -> Settings:
    """Get application settings with profile defaults applied."""
    s = Settings()
    profile = (s.APP_PROFILE or s.PROFILE or _resolve_profile()).strip().lower()
    if profile not in ("local", "cloud"):
        profile = _resolve_profile()

    s.PROFILE = profile
    s.APP_PROFILE = profile

    # Derive APP_ENV for backward compatibility
    if profile == "cloud":
        s.APP_ENV = s.APP_ENV or "beta"
    else:
        s.APP_ENV = s.APP_ENV or "local"

    if profile == "local":
        s.AUTH_DISABLED = True
        if s.ENABLE_DOCS is not False:
            s.ENABLE_DOCS = True
        if s.HOST == "0.0.0.0":
            s.HOST = "127.0.0.1"
        if s.LOG_LEVEL == "warning":
            s.LOG_LEVEL = "info"
    elif profile == "cloud":
        if s.AUTH_DISABLED is not False:
            s.AUTH_DISABLED = False
        if s.ENABLE_DOCS is not False:
            s.ENABLE_DOCS = False
        if s.HOST == "127.0.0.1":
            s.HOST = "0.0.0.0"
        if s.LOG_LEVEL == "info":
            s.LOG_LEVEL = "warning"

    return s


settings = get_settings()


def ensure_directories() -> None:
    """Ensure all required directories exist."""
    for dir_path in [
        settings.UPLOAD_DIR,
        settings.RESULT_DIR,
        settings.HDF5_DIR,
        settings.WORKING_DIR,
        settings.USER_RESULT_DIR,
    ]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
