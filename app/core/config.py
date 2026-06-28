from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Stopcard API"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    docs_enabled: bool = True
    api_prefix: str = "/api"

    database_url: str = "postgresql+asyncpg://stopcard:stopcard@localhost:5432/stopcard"
    database_echo: bool = False

    telegram_bot_token: str = ""
    telegram_auth_max_age_seconds: int = Field(default=3600, ge=60)
    telegram_auth_future_skew_seconds: int = Field(default=30, ge=0)

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket: str = "stopcard"
    minio_region: str = "us-east-1"
    minio_public_url: str | None = None
    minio_presign_endpoint: str | None = None
    minio_presign_secure: bool | None = None
    photo_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)
    photo_url_expires_seconds: int = Field(default=3600, ge=60, le=604800)

    jwt_secret: str = "development-only-change-me"
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_access_token_minutes: int = Field(default=60, ge=5)

    cors_origins: list[str] = [
        "https://stop-card.kz",
        "https://stop-card-app.vercel.app",
    ]
    trusted_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]

    @model_validator(mode="after")
    def reject_unsafe_production_defaults(self) -> "Settings":
        if self.environment == "production":
            if not self.telegram_bot_token:
                raise ValueError("TELEGRAM_BOT_TOKEN is required in production")
            if self.jwt_secret == "development-only-change-me" or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must contain at least 32 characters in production")
            if self.minio_access_key == "minioadmin" or self.minio_secret_key == "minioadmin":
                raise ValueError("default MinIO credentials are forbidden in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
