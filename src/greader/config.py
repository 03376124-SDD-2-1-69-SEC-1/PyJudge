"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration for the GReader application.

    Values are read from environment variables (and an optional ``.env``
    file).  Development defaults are provided so the app runs without any
    extra configuration out of the box.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./data/greader.db"
    SECRET_KEY: str = "change-me-in-production"
