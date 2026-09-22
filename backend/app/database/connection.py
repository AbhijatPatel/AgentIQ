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

engine_kwargs = {
    "pool_pre_ping": True,
}

if settings.DATABASE_URL.startswith("postgresql"):
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 300,
        "connect_args": {"connect_timeout": 10},
    })

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

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


from sqlalchemy import text


def init_db() -> None:
    """Create all tables that don't already exist and ensure required columns exist. Safe to call repeatedly."""
    Base.metadata.create_all(bind=engine)
    try:
        with engine.begin() as conn:
            # Safe migration for existing deployments: ensure `title` column exists
            conn.execute(
                text(
                    "ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS title VARCHAR(255);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_research_sessions_user_id ON research_sessions (user_id);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_research_sessions_created_at ON research_sessions (created_at);"
                )
            )
    except Exception as e:
        logger.warning("Optional schema migration skipped or failed: %s", e)
    logger.info("Database tables ensured (created if missing)")