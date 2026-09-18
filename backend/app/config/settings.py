from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # General app info
    APP_NAME: str = "AgentIQ"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # LLM configuration
    OPENAI_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 2
    LLM_TEMPERATURE: float = 0.2

    # Web Search
    TAVILY_API_KEY: str = ""

    # Database
    DATABASE_URL: str = ""

    # Video Search
    PEXELS_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()