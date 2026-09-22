"""
Shared dependencies for the API layer.

Includes:
- Database session dependency
- JWT authentication dependency (supporting Bearer headers and query token for SSE EventStreams)
"""

from __future__ import annotations

from typing import Generator, Optional

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.database.repository import (
    clear_all_sessions,
    create_session,
    delete_session,
    get_session,
    list_sessions,
    rename_session,
    update_session,
)
from app.database.user_repository import get_user_by_id
from app.utils.auth import decode_access_token

security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    token_query: Optional[str] = Query(None, alias="token"),
    db: Session = Depends(get_db),
):
    """
    Authenticate the user via Bearer token in Authorization header,
    or via ?token= query parameter (for browser EventSource SSE connections).
    """
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    elif token_query:
        token = token_query

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


__all__ = [
    "create_session",
    "get_session",
    "update_session",
    "rename_session",
    "delete_session",
    "clear_all_sessions",
    "list_sessions",
    "get_db",
    "get_current_user",
]