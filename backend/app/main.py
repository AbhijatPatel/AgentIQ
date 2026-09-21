"""
Application entry point.

This file creates the FastAPI app, configures CORS,
registers middleware, initializes the database, and wires
up API routers.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import auth, documents, health, research
from app.config.settings import settings
from app.utils.error_handlers import register_error_handlers
from app.utils.logger import get_logger
from app.utils.rate_limit import limiter


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"{settings.APP_NAME} starting "
        f"in {settings.ENVIRONMENT} mode"
    )

    # Safe startup diagnostics (no secrets printed)
    llm_key = settings.effective_llm_api_key
    llm_provider = "Groq" if "groq" in settings.LLM_BASE_URL.lower() or llm_key.startswith("gsk_") else ("OpenRouter" if "openrouter" in settings.LLM_BASE_URL.lower() else "OpenAI")
    logger.info("Startup Check: LLM configured: %s (provider=%s, model=%s)", bool(llm_key), llm_provider if llm_key else "none", settings.LLM_MODEL)
    logger.info("Startup Check: Database configured: %s", bool(settings.DATABASE_URL.strip()))
    logger.info("Startup Check: SMTP configured: %s (host=%s, port=%d)", settings.is_smtp_configured, settings.SMTP_HOST or "none", settings.SMTP_PORT)
    logger.info("Startup Check: Web Search configured: %s", bool(settings.TAVILY_API_KEY.strip()))

    yield

    logger.info(
        f"{settings.APP_NAME} shutting down"
    )


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)


# ---------------------------------------------------------
# Error handling
# ---------------------------------------------------------

register_error_handlers(app)


# ---------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

origins = [
    settings.FRONTEND_ORIGIN,
    "https://agent-iq-mfsi.vercel.app",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# API routes
# ---------------------------------------------------------

app.include_router(
    health.router,
    prefix="/api",
    tags=["health"],
)

app.include_router(
    research.router,
    prefix="/api",
    tags=["research"],
)

app.include_router(
    documents.router,
    prefix="/api",
    tags=["documents"],
)

app.include_router(
    auth.router,
    prefix="/api",
    tags=["auth"],
)
