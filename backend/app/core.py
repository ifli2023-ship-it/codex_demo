import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "Repo Health"
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "*")
    work_dir: str = os.getenv("WORK_DIR", "/tmp/repo-health-work")
    report_ttl_seconds: int = int(os.getenv("REPORT_TTL_SECONDS", str(7 * 24 * 3600)))
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", str(24 * 3600)))
    rate_limit_count: int = int(os.getenv("RATE_LIMIT_COUNT", "5"))
    rate_limit_window_seconds: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "3600"))
    max_scan_files: int = int(os.getenv("MAX_SCAN_FILES", "12000"))
    max_file_bytes: int = int(os.getenv("MAX_FILE_BYTES", str(1024 * 1024)))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")


settings = Settings()
