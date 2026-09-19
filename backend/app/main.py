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
from app.database.connection import init_db
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

    init_db()

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_ORIGIN,
    ],
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
    ],
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