"""Application configuration via Pydantic Settings.

All configuration is loaded from environment variables and/or a .env file.
Nested settings models keep each subsystem's config isolated.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

# Explicitly load .env variables into os.environ
load_dotenv()

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
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
    url: str | None = None

    @model_validator(mode="before")
    @classmethod
    def parse_database_url(cls, data: Any) -> Any:
        import os
        if not isinstance(data, dict):
            return data
        
        url_val = data.get("url") or os.getenv("DATABASE_URL")
        if url_val:
            from urllib.parse import urlparse
            parsed = urlparse(url_val)
            if parsed.scheme.startswith("postgres"):
                data["host"] = parsed.hostname or data.get("host", "localhost")
                data["port"] = parsed.port or data.get("port", 5432)
                data["user"] = parsed.username or data.get("user", "artwork_user")
                data["password"] = parsed.password or data.get("password", "artwork_secret")
                db_name = parsed.path.lstrip("/")
                data["name"] = db_name or data.get("name", "artwork_automation")
                data["url"] = url_val
        return data

    @property
    def async_url(self) -> str:
        if self.url:
            url_str = self.url
            if url_str.startswith("postgresql://"):
                return url_str.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url_str.startswith("postgres://"):
                return url_str.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url_str.startswith("postgresql+asyncpg://"):
                return url_str
        pwd = self.password.get_secret_value()
        return f"postgresql+asyncpg://{self.user}:{pwd}@{self.host}:{self.port}/{self.name}"

    @property
    def sync_url(self) -> str:
        if self.url:
            url_str = self.url
            if url_str.startswith("postgresql://"):
                return url_str.replace("postgresql://", "postgresql+psycopg2://", 1)
            elif url_str.startswith("postgres://"):
                return url_str.replace("postgres://", "postgresql+psycopg2://", 1)
            elif url_str.startswith("postgresql+psycopg2://"):
                return url_str
        pwd = self.password.get_secret_value()
        return f"postgresql+psycopg2://{self.user}:{pwd}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseModel):
    """Redis connection settings."""

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: SecretStr | None = None
    url_override: str | None = None

    @model_validator(mode="before")
    @classmethod
    def parse_redis_url(cls, data: Any) -> Any:
        import os
        if not isinstance(data, dict):
            return data
        
        url_val = data.get("url") or os.getenv("REDIS_URL")
        if url_val:
            from urllib.parse import urlparse
            parsed = urlparse(url_val)
            data["host"] = parsed.hostname or data.get("host", "localhost")
            data["port"] = parsed.port or data.get("port", 6379)
            if parsed.password:
                data["password"] = parsed.password
            db_path = parsed.path.lstrip("/")
            data["db"] = int(db_path) if db_path.isdigit() else data.get("db", 0)
            data["url_override"] = url_val
        return data

    @property
    def url(self) -> str:
        if self.url_override:
            return self.url_override
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
    account_id: str = ""

    @model_validator(mode="after")
    def populate_account_ids(self) -> InstagramSettings:
        import os
        # Prioritize INSTAGRAM_ACCOUNT_ID env var, then fallback
        env_acct = os.getenv("INSTAGRAM_ACCOUNT_ID") or os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        if env_acct:
            self.account_id = env_acct
        
        if not self.account_id and self.business_account_id:
            self.account_id = self.business_account_id
        elif not self.business_account_id and self.account_id:
            self.business_account_id = self.account_id
            
        return self


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

    # AI Provider Settings
    ai_provider: str = "gemini"
    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "llama-3.3-70b-versatile"

    # Webhook Authentication (Phase 7)
    webhook_api_key: str = ""

    # Subsystem settings
    postgres: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    cloudinary: CloudinarySettings = Field(default_factory=CloudinarySettings)
    instagram: InstagramSettings = Field(default_factory=InstagramSettings)
    instagram_acc2: InstagramSettings = Field(default_factory=InstagramSettings)
    youtube: YouTubeSettings = Field(default_factory=YouTubeSettings)
    pinterest: PinterestSettings = Field(default_factory=PinterestSettings)
    tiktok: TikTokSettings = Field(default_factory=TikTokSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    prompts: PromptSettings = Field(default_factory=PromptSettings)
    feature_flags: FeatureFlagSettings = Field(default_factory=FeatureFlagSettings)

    @model_validator(mode="after")
    def configure_celery_urls(self) -> Settings:
        import os
        redis_url = self.redis.url
        if os.getenv("REDIS_URL") or self.redis.host != "localhost":
            if "localhost" in self.celery.broker_url:
                base_url = redis_url.rstrip("/")
                from urllib.parse import urlparse
                parsed = urlparse(base_url)
                if parsed.path and parsed.path != "/":
                    base_url = base_url.rsplit("/", 1)[0]
                self.celery.broker_url = f"{base_url}/1"
            if "localhost" in self.celery.result_backend:
                base_url = redis_url.rstrip("/")
                from urllib.parse import urlparse
                parsed = urlparse(base_url)
                if parsed.path and parsed.path != "/":
                    base_url = base_url.rsplit("/", 1)[0]
                self.celery.result_backend = f"{base_url}/2"
        return self

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
