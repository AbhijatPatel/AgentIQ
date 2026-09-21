"""
ASGI application entry point for uvicorn.
Enables running `uvicorn main:app` directly inside the backend directory.
"""
from app.main import app

__all__ = ["app"]
