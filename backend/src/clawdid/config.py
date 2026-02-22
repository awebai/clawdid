from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "staging", "production"] = "development"

    log_json: bool = Field(default=False, validation_alias=AliasChoices("LOG_JSON"))
    log_level: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL"))
    trusted_proxy_headers: bool = Field(
        default=False,
        validation_alias=AliasChoices("TRUST_PROXY_HEADERS", "TRUSTED_PROXY_HEADERS"),
    )

    database_url: str = Field(default="postgresql://beadhub@localhost:5432/clawdid")
    database_pool_size: int = 10
    database_pool_overflow: int = 10

    auth_timestamp_skew_seconds: int = 300

    rate_limit_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "RATE_LIMIT_ENABLED", "CLAWDID_RATE_LIMIT_ENABLED"
        ),
    )
    rate_limit_backend: Literal["memory", "redis"] = Field(
        default="memory",
        validation_alias=AliasChoices(
            "RATE_LIMIT_BACKEND", "CLAWDID_RATE_LIMIT_BACKEND"
        ),
    )
    rate_limit_redis_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "REDIS_URL", "RATE_LIMIT_REDIS_URL", "CLAWDID_RATE_LIMIT_REDIS_URL"
        ),
    )

    # Per-endpoint buckets (fixed window).
    rate_limit_key_per_minute: int = Field(
        default=60,
        validation_alias=AliasChoices(
            "RATE_LIMIT_KEY_PER_MINUTE", "CLAWDID_RATE_LIMIT_KEY_PER_MINUTE"
        ),
    )
    rate_limit_log_per_minute: int = Field(
        default=30,
        validation_alias=AliasChoices(
            "RATE_LIMIT_LOG_PER_MINUTE", "CLAWDID_RATE_LIMIT_LOG_PER_MINUTE"
        ),
    )
    rate_limit_head_per_minute: int = Field(
        default=120,
        validation_alias=AliasChoices(
            "RATE_LIMIT_HEAD_PER_MINUTE", "CLAWDID_RATE_LIMIT_HEAD_PER_MINUTE"
        ),
    )
    rate_limit_register_per_hour: int = Field(
        default=10,
        validation_alias=AliasChoices(
            "RATE_LIMIT_REGISTER_PER_HOUR", "CLAWDID_RATE_LIMIT_REGISTER_PER_HOUR"
        ),
    )
    rate_limit_full_per_minute: int = Field(
        default=30,
        validation_alias=AliasChoices(
            "RATE_LIMIT_FULL_PER_MINUTE", "CLAWDID_RATE_LIMIT_FULL_PER_MINUTE"
        ),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
