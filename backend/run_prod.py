import os

_entry_profile = (os.getenv("APP_PROFILE") or os.getenv("PROFILE") or "").strip()
if _entry_profile:
    os.environ["APP_PROFILE"] = _entry_profile
    os.environ["PROFILE"] = _entry_profile

import uvicorn
from core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level=settings.LOG_LEVEL,
    )
