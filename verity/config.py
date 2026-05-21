"""Verity runtime configuration.

Loaded from environment variables (and an optional `.env` file) via
pydantic-settings. All `VERITY_*` env vars are mapped here; provider
API keys are loaded by their canonical names (OPENAI_API_KEY, etc.).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Env = Literal["development", "staging", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class Settings(BaseSettings):
    """Application settings.

    Threshold semantics:
      overall_score >= accept_threshold  -> ACCEPT
      refine_threshold <= overall_score < accept_threshold -> REFINE
      overall_score < refine_threshold   -> REJECT
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    env: Env = Field(default="development", alias="VERITY_ENV")
    log_level: LogLevel = Field(default="INFO", alias="VERITY_LOG_LEVEL")
    api_host: str = Field(default="0.0.0.0", alias="VERITY_API_HOST")
    api_port: int = Field(default=8080, alias="VERITY_API_PORT")

    # Provider keys
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    perplexity_api_key: SecretStr | None = Field(default=None, alias="PERPLEXITY_API_KEY")
    grok_api_key: SecretStr | None = Field(default=None, alias="GROK_API_KEY")

    # Scoring thresholds
    accept_threshold: float = Field(default=0.80, alias="VERITY_ACCEPT_THRESHOLD", ge=0.0, le=1.0)
    refine_threshold: float = Field(default=0.55, alias="VERITY_REFINE_THRESHOLD", ge=0.0, le=1.0)

    # Risk classifier
    healthcare_mode: bool = Field(default=True, alias="VERITY_HEALTHCARE_MODE")
    phi_detection: bool = Field(default=True, alias="VERITY_PHI_DETECTION")

    # Observability
    langsmith_api_key: SecretStr | None = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="verity", alias="LANGSMITH_PROJECT")
    otel_endpoint: str | None = Field(default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT")

    # Audit log
    audit_log_path: Path = Field(default=Path("./logs/audit.jsonl"), alias="VERITY_AUDIT_LOG_PATH")
    audit_retention_days: int = Field(default=90, alias="VERITY_AUDIT_RETENTION_DAYS", ge=1)

    @field_validator("refine_threshold")
    @classmethod
    def _refine_below_accept(cls, v: float, info: ValidationInfo) -> float:
        accept = info.data.get("accept_threshold")
        if accept is not None and v >= accept:
            raise ValueError(
                f"refine_threshold ({v}) must be strictly less than accept_threshold ({accept})"
            )
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor — single source of truth per process."""
    return Settings()


# Module-level instance for convenience imports (e.g. `from verity.config import settings`).
settings = get_settings()
