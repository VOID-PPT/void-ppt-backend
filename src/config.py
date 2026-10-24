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

    CORS_ORIGINS: list[str] = ["[FRONTEND_URL]"]

    # Database connection (PostgreSQL + asyncpg)
    DATABASE_URL: str = ""
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5

    # Observability (unset = no-op exporters; local dev needs nothing)
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OTEL_EXPORTER_OTLP_HEADERS: str = ""
    LOG_LEVEL: str = "INFO"

    # AI providers (free-tier; swap by config, never code)
    AI_PROVIDER: str = "gemini"  # gemini | groq | cloudflare | ollama
    AI_API_KEY: str = ""
    AI_MODEL: str = "gemini-2.0-flash"
    AI_EMBEDDING_MODEL: str = "text-embedding-004"
    AI_TIMEOUT_SECONDS: float = 60.0
    AI_DAILY_USER_TOKEN_BUDGET: int = 100_000


settings = AppSettings()
