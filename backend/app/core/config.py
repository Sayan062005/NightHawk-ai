"""NightHawk AI — Application Configuration."""

from __future__ import annotations

import json
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "NightHawk AI"
    app_env: str = "development"
    app_debug: bool = False
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_secret_key: str = secrets.token_urlsafe(48)
    app_cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("app_cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    # Database
    database_url: str = "sqlite+aiosqlite:///./nighthawk.db"

    # Authentication
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 14
    admin_bootstrap_token: str = ""
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"

    # NVIDIA AI
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "meta/llama-3.1-70b-instruct"
    nvidia_timeout_seconds: int = 60
    nvidia_max_retries: int = 3
    nvidia_max_tokens: int = 4096

    # AI Provider
    ai_provider: str = "fallback"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"

    # Redis
    redis_url: str = ""

    # Assessment Limits
    max_concurrent_scans: int = 3
    max_scan_duration_seconds: int = 3600
    max_requests_per_host: int = 1000
    max_assessment_iterations: int = 100
    max_tokens_per_assessment: int = 100000
    rate_limit_requests_per_second: int = 10

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> "Settings":
        env = self.app_env.lower()
        if not self.jwt_secret_key:
            if env in {"production", "prod"}:
                raise ValueError("JWT_SECRET_KEY must be configured in production")
            self.jwt_secret_key = secrets.token_urlsafe(48)

        if len(self.jwt_secret_key.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 bytes")
        if any(marker in self.jwt_secret_key.lower() for marker in ("change_me", "replace_me", "your_secret")):
            raise ValueError("JWT_SECRET_KEY still contains a placeholder value")
        if self.jwt_algorithm != "HS256":
            raise ValueError("Only HS256 is supported by this application")
        if self.jwt_access_token_expire_minutes < 5 or self.jwt_access_token_expire_minutes > 60:
            raise ValueError("JWT access-token lifetime must be between 5 and 60 minutes")
        if self.jwt_refresh_token_expire_days < 1 or self.jwt_refresh_token_expire_days > 30:
            raise ValueError("JWT refresh-token lifetime must be between 1 and 30 days")
        if self.auth_cookie_samesite.lower() not in {"lax", "strict", "none"}:
            raise ValueError("AUTH_COOKIE_SAMESITE must be lax, strict, or none")
        if self.auth_cookie_samesite.lower() == "none" and not self.auth_cookie_secure:
            raise ValueError("AUTH_COOKIE_SECURE must be true when SameSite=None")
        if env in {"production", "prod"} and not self.auth_cookie_secure:
            raise ValueError("AUTH_COOKIE_SECURE must be true in production")
        return self

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one stable settings object for the lifetime of this process."""
    return Settings()
