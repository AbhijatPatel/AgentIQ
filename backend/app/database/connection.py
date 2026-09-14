"""
Database connection setup.

Creates the SQLAlchemy engine and session factory used throughout the
app. This is the single place that knows how to connect to Postgres -
everything else imports SessionLocal or the Base class from here.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class every SQLAlchemy model inherits from."""
    pass


def get_db():
    """
    FastAPI dependency that provides a database session per request,
    and always closes it afterward - even if an error occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables that don't already exist. Safe to call repeatedly."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured (created if missing)")