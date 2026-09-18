"""
Global FastAPI exception handlers.

Ensures every error - expected or unexpected - returns a consistent
JSON shape to the frontend, and is logged server-side with enough
detail to debug, without leaking internals to the client in production.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.settings import settings
from app.utils.exceptions import classify_exception
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _error_response(
    status_code: int,
    error_code: str,
    message: str,
    detail: str | None = None,
) -> JSONResponse:
    body: dict[str, str] = {
        "error": error_code,
        "message": message,
    }

    if detail and settings.DEBUG:
        body["detail"] = detail

    return JSONResponse(
        status_code=status_code,
        content=body,
    )

def register_error_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to the FastAPI app."""

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
        return _error_response(
            422,
            "validation_error",
            "The request was invalid.",
            detail=str(exc.errors()),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # Preserves intentional HTTPExceptions (404s, 400s from routes) as-is,
        # just wraps them in our consistent shape.
        return _error_response(
            exc.status_code,
            "http_error",
            str(exc.detail),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        status_code, error_code, message = classify_exception(exc)

        if status_code >= 500:
            logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
        else:
            logger.warning(f"Handled error on {request.url.path}: {exc}")

        return _error_response(status_code, error_code, message, detail=str(exc))