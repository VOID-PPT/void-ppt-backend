from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Void API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "local"  # local, staging, production
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    CORS_ORIGINS: list[str] = [
        "[FRONTEND_URL]"
    ]

    # Database connection (PostgreSQL + asyncpg)
    DATABASE_URL: str = ""
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5


settings = AppSettings()
