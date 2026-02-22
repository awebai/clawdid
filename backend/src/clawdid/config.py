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

    clawdid_method: str = Field(
        default="claw", description="Stable DID method name: claw|aw"
    )
    auth_timestamp_skew_seconds: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
