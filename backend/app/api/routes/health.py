from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _mask_host(host: str) -> str:
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) >= 2:
        return f"{parts[0][0]}***.{'.'.join(parts[1:])}"
    return "***"


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/diagnostics")
def health_diagnostics(db: Session = Depends(get_db)) -> dict[str, Any]:
    # Check database
    db_status = "unconfigured"
    if settings.DATABASE_URL:
        try:
            db.execute(text("SELECT 1"))
            db_status = "healthy"
        except Exception as exc:
            logger.warning("Health diagnostics: database check failed: %s", type(exc).__name__)
            db_status = "unreachable"

    # LLM diagnostics
    llm_key = settings.effective_llm_api_key
    provider = "unconfigured"
    if llm_key:
        if "groq" in settings.LLM_BASE_URL.lower() or llm_key.startswith("gsk_"):
            provider = "Groq"
        elif "openrouter" in settings.LLM_BASE_URL.lower() or llm_key.startswith("sk-or-"):
            provider = "OpenRouter"
        else:
            provider = "OpenAI"

    # SMTP diagnostics
    ssl_mode = "None"
    if settings.SMTP_USE_SSL or settings.SMTP_PORT == 465:
        ssl_mode = "SSL"
    elif settings.SMTP_USE_TLS:
        ssl_mode = "STARTTLS"

    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "integrations": {
            "database": {
                "status": db_status,
            },
            "llm": {
                "configured": bool(llm_key),
                "provider": provider,
                "model": settings.LLM_MODEL,
                "fallback_model": settings.LLM_FALLBACK_MODEL,
            },
            "email": {
                "configured": settings.is_smtp_configured,
                "provider": settings.active_email_provider,
                "resend_active": bool(settings.RESEND_API_KEY.strip()),
                "smtp_host": _mask_host(settings.SMTP_HOST) if settings.SMTP_HOST else None,
                "smtp_port": settings.SMTP_PORT if settings.SMTP_HOST else None,
                "smtp_mode": ssl_mode if settings.SMTP_HOST else None,
            },
            "smtp": {
                "configured": settings.is_smtp_configured,
                "host": _mask_host(settings.SMTP_HOST),
                "port": settings.SMTP_PORT,
                "mode": ssl_mode,
            },
            "search": {
                "tavily_configured": bool(settings.TAVILY_API_KEY.strip()),
                "pexels_configured": bool(settings.PEXELS_API_KEY.strip()),
            },
        },
    }
