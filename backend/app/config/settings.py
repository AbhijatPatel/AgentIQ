from pathlib import Path
from typing import Any
from pydantic import field_validator
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
    GROQ_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_FALLBACK_MODEL: str = "openai/gpt-oss-20b"

    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 2
    LLM_RETRY_BASE_DELAY_SECONDS: float = 1.0
    LLM_RATE_LIMIT_MAX_DELAY_SECONDS: float = 20.0
    LLM_CONCURRENCY_LIMIT: int = 4
    LLM_MIN_REQUEST_DELAY_SECONDS: float = 0.0
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_OUTPUT_TOKENS: int = 1024
    LLM_JSON_MAX_OUTPUT_TOKENS: int = 8192

    # Maximum number of evidence items passed to the Writer prompt.
    # 12 high-quality items provides optimal synthesis depth with maximum speed.
    MAX_EVIDENCE_FOR_WRITER: int = 12

    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Email / OTP Settings
    OTP_EXPIRE_MINUTES: int = 10
    OTP_REQUEST_COOLDOWN_SECONDS: int = 60
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = ""
    SENDGRID_API_KEY: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: int = 10
    SMTP_MAX_RETRIES: int = 2

    # Web & Media
    TAVILY_API_KEY: str = ""
    YOUTUBE_API_KEY: str = ""
    POLLINATIONS_IMAGE_URL: str = "https://image.pollinations.ai/prompt"

    # Database
    DATABASE_URL: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: Any) -> str:
        if isinstance(v, str):
            s = v.strip()
            # Render and Heroku provide postgres:// URLs which SQLAlchemy 1.4+ rejects
            if s.startswith("postgres://"):
                return "postgresql://" + s[len("postgres://"):]
            return s
        return ""

    @property
    def effective_llm_api_key(self) -> str:
        """Returns whichever API key is configured (OPENAI_API_KEY or GROQ_API_KEY)."""
        return (self.OPENAI_API_KEY or self.GROQ_API_KEY or "").strip()

    @property
    def sanitized_smtp_password(self) -> str:
        """Returns SMTP password with accidental spaces or wrapping quotes removed."""
        return self.SMTP_PASSWORD.replace(" ", "").replace('"', '').replace("'", "").strip()

    @property
    def effective_smtp_from_email(self) -> str:
        """Returns configured FROM email or falls back to SMTP username."""
        return (self.SMTP_FROM_EMAIL.strip() or self.SMTP_USERNAME.strip())

    @property
    def effective_resend_from_email(self) -> str:
        """Returns configured Resend from email, or defaults to onboarding@resend.dev."""
        if self.RESEND_FROM_EMAIL.strip():
            return self.RESEND_FROM_EMAIL.strip()
        if self.SMTP_FROM_EMAIL.strip() and "@" in self.SMTP_FROM_EMAIL and "gmail.com" not in self.SMTP_FROM_EMAIL.lower():
            return self.SMTP_FROM_EMAIL.strip()
        return "AgentIQ <onboarding@resend.dev>"

    @property
    def is_smtp_configured(self) -> bool:
        """Returns True if minimum required email settings (Resend API or SMTP) are present."""
        return bool(self.RESEND_API_KEY.strip() or (self.SMTP_HOST.strip() and (self.SMTP_FROM_EMAIL.strip() or self.SMTP_USERNAME.strip())))

    @property
    def active_email_provider(self) -> str:
        """Identifies which email delivery backend is active."""
        if self.RESEND_API_KEY.strip():
            return "resend_https"
        if self.SMTP_HOST.strip():
            return "smtp"
        return "mock"

    @property
    def is_llm_configured(self) -> bool:
        """Returns True if an LLM API key is present."""
        return bool(self.effective_llm_api_key)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


