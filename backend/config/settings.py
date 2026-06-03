"""Application configuration via Pydantic Settings.

All configuration is loaded from environment variables and/or a .env file.
Nested settings models keep each subsystem's config isolated.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ── Nested Configuration Models ──────────────────────────────────────────────


class DatabaseSettings(BaseModel):
    """PostgreSQL connection settings."""

    host: str = "localhost"
    port: int = 5432
    user: str = "artwork_user"
    password: SecretStr = SecretStr("artwork_secret")
    name: str = "artwork_automation"
    pool_size: int = 20
    max_overflow: int = 10

    @property
    def async_url(self) -> str:
        pwd = self.password.get_secret_value()
        return f"postgresql+asyncpg://{self.user}:{pwd}@{self.host}:{self.port}/{self.name}"

    @property
    def sync_url(self) -> str:
        pwd = self.password.get_secret_value()
        return f"postgresql+psycopg2://{self.user}:{pwd}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseModel):
    """Redis connection settings."""

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: SecretStr | None = None

    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class CelerySettings(BaseModel):
    """Celery task queue settings."""

    broker_url: str = "redis://localhost:6379/1"
    result_backend: str = "redis://localhost:6379/2"
    worker_concurrency: int = 4
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: list[str] = Field(default_factory=lambda: ["json"])
    task_track_started: bool = True
    task_acks_late: bool = True
    worker_prefetch_multiplier: int = 1


class JWTSettings(BaseModel):
    """JWT authentication settings."""

    secret_key: SecretStr = SecretStr("CHANGE-ME-generate-a-64-character-random-secret-key")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7


class GeminiSettings(BaseModel):
    """Google Gemini AI provider settings."""

    api_key: SecretStr = SecretStr("")
    model: str = "gemini-2.5-flash"
    max_retries: int = 3
    timeout: int = 60


class CloudinarySettings(BaseModel):
    """Cloudinary media storage settings."""

    cloud_name: str = ""
    api_key: str = ""
    api_secret: SecretStr = SecretStr("")
    upload_preset: str = ""


class InstagramSettings(BaseModel):
    """Instagram Graph API settings."""

    app_id: str = ""
    app_secret: SecretStr = SecretStr("")
    access_token: SecretStr = SecretStr("")
    business_account_id: str = ""


class YouTubeSettings(BaseModel):
    """YouTube Data API settings."""

    client_id: str = ""
    client_secret: SecretStr = SecretStr("")
    refresh_token: SecretStr = SecretStr("")
    channel_id: str = ""


class PinterestSettings(BaseModel):
    """Pinterest API settings."""

    app_id: str = ""
    app_secret: SecretStr = SecretStr("")
    access_token: SecretStr = SecretStr("")
    board_id: str = ""


class TikTokSettings(BaseModel):
    """TikTok API settings."""

    client_key: str = ""
    client_secret: SecretStr = SecretStr("")
    access_token: SecretStr = SecretStr("")


class StorageSettings(BaseModel):
    """File storage settings."""

    backend: str = "local"
    local_path: str = "./outputs"


class PromptSettings(BaseModel):
    """Prompt template settings."""

    directory: str = "backend/prompts"
    default_version: str = "v1"


class FeatureFlagSettings(BaseModel):
    """Feature flag settings controlling pipeline stages."""

    enable_instagram_publish: bool = False
    enable_youtube_publish: bool = False
    enable_pinterest_publish: bool = False
    enable_tiktok_publish: bool = False
    enable_reel_generation: bool = False
    enable_analytics_collection: bool = False
    workflow_version: str = "v1"


# ── Root Settings ────────────────────────────────────────────────────────────


class Settings(BaseSettings):
    """Root application settings aggregating all subsystem configurations."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "artwork-automation"
    app_env: str = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "INFO"
    app_log_json: bool = True
    app_cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    # Subsystem settings
    postgres: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    cloudinary: CloudinarySettings = Field(default_factory=CloudinarySettings)
    instagram: InstagramSettings = Field(default_factory=InstagramSettings)
    youtube: YouTubeSettings = Field(default_factory=YouTubeSettings)
    pinterest: PinterestSettings = Field(default_factory=PinterestSettings)
    tiktok: TikTokSettings = Field(default_factory=TikTokSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    prompts: PromptSettings = Field(default_factory=PromptSettings)
    feature_flags: FeatureFlagSettings = Field(default_factory=FeatureFlagSettings)

    @field_validator("app_env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production", "testing"}
        if v not in allowed:
            msg = f"app_env must be one of {allowed}, got '{v}'"
            raise ValueError(msg)
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
