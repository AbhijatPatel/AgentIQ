"""
Shared dependencies for the API layer.

This now delegates to app.database.repository, which persists
sessions in PostgreSQL instead of an in-memory dict (Module 16).
Kept as a thin re-export so route files don't need to change imports.
"""

from app.database.repository import create_session, get_session, update_session

__all__ = ["create_session", "get_session", "update_session"]