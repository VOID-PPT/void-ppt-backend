from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    JWT_SECRET: str = ""
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, gt=0)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=14, gt=0)

    @field_validator("JWT_SECRET")
    @classmethod
    def _require_secret_in_runtime(cls, value: str) -> str:
        """Fail fast outside tests: a blank secret means unverifiable tokens.

        Tests may run without it (they construct their own tokens), but a real
        deployment must never start with an empty signing key.
        """
        import os

        if not value and os.getenv("ENVIRONMENT") not in {"test"}:
            msg = "AUTH_JWT_SECRET is required. Generate one with: openssl rand -hex 32"
            raise ValueError(msg)
        return value

    @field_validator("JWT_ALG")
    @classmethod
    def _require_alg(cls, value: str) -> str:
        if not value:
            msg = "AUTH_JWT_ALG must not be empty (use HS256)"
            raise ValueError(msg)
        return value


auth_settings = AuthConfig()
