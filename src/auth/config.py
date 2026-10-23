from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    JWT_SECRET: str = ""
    JWT_ALG: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14


auth_settings = AuthConfig()
