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
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_FALLBACK_MODEL: str = "openai/gpt-oss-20b"

    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 2
    LLM_RETRY_BASE_DELAY_SECONDS: float = 2.0
    LLM_RATE_LIMIT_MAX_DELAY_SECONDS: float = 30.0
    LLM_CONCURRENCY_LIMIT: int = 1
    LLM_MIN_REQUEST_DELAY_SECONDS: float = 2.0
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_OUTPUT_TOKENS: int = 1024
    LLM_JSON_MAX_OUTPUT_TOKENS: int = 8192

    # Maximum number of evidence items passed to the Writer prompt.
    # This prevents HTTP 413 (request too large) on the small fallback model
    # (openai/gpt-oss-20b, 8 000 TPM limit). Evidence is ranked by confidence
    # (high → medium → low) so the highest-quality items are always kept.
    # Override with MAX_EVIDENCE_FOR_WRITER=N in your .env file.
    MAX_EVIDENCE_FOR_WRITER: int = 20

    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    OTP_EXPIRE_MINUTES: int = 10
    OTP_REQUEST_COOLDOWN_SECONDS: int = 60
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True

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
