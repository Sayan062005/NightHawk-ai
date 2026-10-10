"""SentinelWeb AI — Application Configuration."""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ───
    app_name: str = "SentinelWeb AI"
    app_env: str = "development"
    app_debug: bool = False
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_secret_key: str = secrets.token_urlsafe(48)
    app_cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("app_cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [s.strip() for s in v.split(",")]
        return v

    # ─── Database ───
    database_url: str = "sqlite+aiosqlite:///./sentinelweb.db"

    # ─── Auth ───
    jwt_secret_key: str = secrets.token_urlsafe(48)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # ─── NVIDIA AI ───
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "meta/llama-3.1-70b-instruct"
    nvidia_timeout_seconds: int = 60
    nvidia_max_retries: int = 3
    nvidia_max_tokens: int = 4096

    # ─── AI Provider ───
    ai_provider: str = "fallback"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"

    # ─── Redis ───
    redis_url: str = ""

    # ─── Assessment Limits ───
    max_concurrent_scans: int = 3
    max_scan_duration_seconds: int = 3600
    max_requests_per_host: int = 1000
    max_assessment_iterations: int = 100
    max_tokens_per_assessment: int = 100000
    rate_limit_requests_per_second: int = 10

    # ─── Logging ───
    log_level: str = "INFO"
    log_format: str = "json"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent


def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
