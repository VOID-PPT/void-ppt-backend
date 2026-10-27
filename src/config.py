from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_asyncpg_url(raw: str) -> str:
    """Convert a provider-issued Postgres URL into an asyncpg-compatible one.

    Neon/Supabase hand out libpq URLs (`postgresql://...?sslmode=require`).
    asyncpg does not understand `sslmode` or `channel_binding`, so they are
    translated/dropped here instead of leaking into the driver.
    """
    if not raw:
        return raw

    url = raw.strip().strip('"').strip("'")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))

    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    if sslmode and "ssl" not in query:
        # libpq -> asyncpg ssl argument
        query["ssl"] = "disable" if sslmode == "disable" else sslmode

    return urlunparse(parsed._replace(query=urlencode(query)))


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
    # Optional direct (non-pooler) URL for migrations. Falls back to DATABASE_URL.
    # Pooled endpoints (PgBouncer transaction mode) cannot run some DDL reliably.
    DATABASE_DIRECT_URL: str = ""
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_RECYCLE_SECONDS: int = 300

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

    @property
    def async_database_url(self) -> str:
        """Runtime URL (may be a pooler endpoint)."""
        return _normalize_asyncpg_url(self.DATABASE_URL)

    @property
    def async_direct_url(self) -> str:
        """Migration URL — prefers the direct endpoint when configured."""
        return _normalize_asyncpg_url(self.DATABASE_DIRECT_URL or self.DATABASE_URL)

    @property
    def database_is_pooled(self) -> bool:
        """True when the runtime endpoint is a PgBouncer-style pooler.

        Transaction-mode poolers cannot keep server-side prepared statements
        between checkouts, so the asyncpg statement cache must be disabled.
        """
        hostname = urlparse(self.async_database_url).hostname or ""
        return "pooler" in hostname


settings = AppSettings()
