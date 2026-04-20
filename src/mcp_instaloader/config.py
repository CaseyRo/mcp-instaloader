"""Configuration loaded from environment variables."""

from __future__ import annotations

from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Rate limiting
    rate_limit_requests: int = 10
    rate_limit_window: int = 60

    # Instaloader session
    cookie_file: str | None = None

    # Server transport
    transport: Literal["stdio", "http"] = "http"
    host: str = "127.0.0.1"
    mcp_port: int = 3336

    # Bearer token auth for MCP Portal
    mcp_api_key: SecretStr = SecretStr("")

    model_config = {"env_prefix": "", "case_sensitive": False}

    @field_validator("rate_limit_requests", "rate_limit_window")
    @classmethod
    def positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("must be >= 1")
        return v

    @model_validator(mode="after")
    def require_api_key_for_http(self) -> Settings:
        if self.transport == "http" and not self.mcp_api_key.get_secret_value():
            raise ValueError(
                "MCP_API_KEY is required when TRANSPORT=http. "
                "Refusing to start an unauthenticated server."
            )
        return self


settings = Settings()
