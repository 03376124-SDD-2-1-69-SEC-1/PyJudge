"""Application settings loaded from environment variables."""

from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration for the GReader application.

    Values are read from environment variables (and an optional ``.env`` file).
    Development defaults target a local PostgreSQL container.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    DATABASE_URL: str = ""
    POSTGRES_USER: str = "greader"
    POSTGRES_PASSWORD: str = "greader"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "greader"
    SECRET_KEY: str = "change-me-in-production"
    AI_PROVIDER: str = "demo"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"
    AI_REQUEST_TIMEOUT_SECONDS: int = 30

    @property
    def database_url(self) -> str:
        """Return explicit DATABASE_URL or build a PostgreSQL URL from parts."""
        if self.DATABASE_URL:
            return self.DATABASE_URL

        user = quote(self.POSTGRES_USER, safe="")
        password = quote(self.POSTGRES_PASSWORD, safe="")
        database = quote(self.POSTGRES_DB, safe="")
        return (
            f"postgresql+psycopg://{user}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{database}"
        )
