"""Typed application configuration, loaded from environment / .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Values are read from environment variables, falling back to a local .env file.
    Secrets are never committed; see .env.example for the expected keys.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    gemini_api_key: str = ""

    langchain_api_key: str = ""
    langchain_tracing_v2: bool = False
    langchain_project: str = "incident-triage-agent"

    # The deployed demo serves cached runs only; live investigation is disabled
    # so a public instance never spends the free-tier LLM quota.
    allow_live_runs: bool = False


def get_settings() -> Settings:
    """Return a fresh Settings instance."""
    return Settings()
