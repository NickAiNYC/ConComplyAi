"""Application settings loaded from environment variables.

Uses ``pydantic-settings`` when available; otherwise falls back to
``os.environ`` parsing so the module works without extra dependencies.
"""

from __future__ import annotations

import functools
import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr

_PYDANTIC_SETTINGS_AVAILABLE = False
try:
    from pydantic_settings import BaseSettings as _BaseSettings  # type: ignore[import-untyped]

    _PYDANTIC_SETTINGS_AVAILABLE = True
except ImportError:
    _BaseSettings = None  # type: ignore[assignment,misc]


def _env(key: str, default: Any = None, cast: type = str) -> Any:
    """Read an environment variable with optional type coercion."""
    raw = os.environ.get(key, default)
    if raw is None:
        return raw
    if cast is bool:
        return str(raw).lower() in ("1", "true", "yes")
    return cast(raw)


if _PYDANTIC_SETTINGS_AVAILABLE:

    class Settings(_BaseSettings):  # type: ignore[misc]
        """Central configuration surface – all values overridable via env vars."""

        model_config = ConfigDict(
            env_prefix="CONCOMPLYAI_",
            frozen=True,
        )

        app_name: str = Field(default="ConComplyAi", description="Application display name.")
        version: str = Field(default="2.0.0", description="Semantic version of the deployment.")
        debug: bool = Field(default=False, description="Enable debug mode.")
        log_level: str = Field(default="INFO", description="Root logging level.")

        api_host: str = Field(default="0.0.0.0", description="HTTP bind address.")
        api_port: int = Field(default=8000, description="HTTP listen port.")

        auth_token: SecretStr = Field(
            default=SecretStr(""),
            description="Bearer token for API authentication.",
        )

        rate_limit_per_minute: int = Field(
            default=60,
            description="Maximum API requests per minute per client.",
        )
        risk_score_threshold: float = Field(
            default=0.7,
            description="Minimum risk score that triggers escalation.",
        )
        audit_retention_days: int = Field(
            default=2555,
            description="Days to retain audit records (default ≈ 7 years).",
        )

else:

    class Settings(BaseModel):  # type: ignore[no-redef]
        """Fallback settings parsed directly from ``os.environ``."""

        model_config = ConfigDict(frozen=True)

        app_name: str = "ConComplyAi"
        version: str = "2.0.0"
        debug: bool = False
        log_level: str = "INFO"

        api_host: str = "0.0.0.0"
        api_port: int = 8000

        auth_token: SecretStr = Field(default=SecretStr(""))

        rate_limit_per_minute: int = 60
        risk_score_threshold: float = 0.7
        audit_retention_days: int = 2555

        @classmethod
        def from_env(cls) -> Settings:
            """Build a ``Settings`` instance from environment variables."""
            return cls(
                app_name=_env("CONCOMPLYAI_APP_NAME", "ConComplyAi"),
                version=_env("CONCOMPLYAI_VERSION", "2.0.0"),
                debug=_env("CONCOMPLYAI_DEBUG", False, bool),
                log_level=_env("CONCOMPLYAI_LOG_LEVEL", "INFO"),
                api_host=_env("CONCOMPLYAI_API_HOST", "0.0.0.0"),
                api_port=_env("CONCOMPLYAI_API_PORT", 8000, int),
                auth_token=SecretStr(_env("CONCOMPLYAI_AUTH_TOKEN", "")),
                rate_limit_per_minute=_env("CONCOMPLYAI_RATE_LIMIT_PER_MINUTE", 60, int),
                risk_score_threshold=_env("CONCOMPLYAI_RISK_SCORE_THRESHOLD", 0.7, float),
                audit_retention_days=_env("CONCOMPLYAI_AUDIT_RETENTION_DAYS", 2555, int),
            )


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached, immutable ``Settings`` singleton.

    On first call the settings object is created (from env vars when
    ``pydantic-settings`` is unavailable) and cached for the process
    lifetime.
    """
    if _PYDANTIC_SETTINGS_AVAILABLE:
        return Settings()  # type: ignore[call-arg]
    return Settings.from_env()  # type: ignore[attr-error]
