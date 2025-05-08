from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import BaseModel, Field
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # .env loading is optional; ignore if dotenv is unavailable
    pass


class Settings(BaseModel):
    app_name: str = Field(default_factory=lambda: os.getenv("APP_NAME", "rt-collab"))
    app_version: str = Field(default_factory=lambda: os.getenv("APP_VERSION", "0.1.0"))

    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "mysql+aiomysql://root:password@localhost:3306/rt_collab",
        )
    )
    redis_url: str = Field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))

    allowed_origins: List[str] = Field(
        default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    )
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    snapshot_interval: int = Field(default_factory=lambda: int(os.getenv("SNAPSHOT_INTERVAL", "100")))


@lru_cache
def get_settings() -> Settings:
    return Settings()
