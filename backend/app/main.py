"""
Application entry point.

This file creates the FastAPI app, configures CORS (so the React
frontend running on a different port can call it), and wires up routers.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, documents, health, research
from app.config.settings import settings
from app.utils.error_handlers import register_error_handlers
from app.database.connection import init_db
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.utils.rate_limit import limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"{settings.APP_NAME} starting in {settings.ENVIRONMENT} mode")
    init_db()
    yield
    logger.info(f"{settings.APP_NAME} shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

register_error_handlers(app)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(research.router, prefix="/api", tags=["research"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(auth.router, prefix="/api")