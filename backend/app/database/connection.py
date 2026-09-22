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
    "pool_reset_on_return": "rollback",
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


from sqlalchemy import inspect, text


def init_db() -> None:
    """Create all tables that don't already exist and ensure required columns exist. Safe to call repeatedly."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.warning("Base.metadata.create_all warning: %s", e)

    # Safe idempotent column additions for existing PostgreSQL databases
    if "postgresql" in settings.DATABASE_URL.lower():
        migrations = [
            "ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS title VARCHAR(255);",
            "ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);",
            "ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS tasks JSON DEFAULT '[]';",
            "ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS evidence_count INTEGER DEFAULT 0;",
            "ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS evidence JSON DEFAULT '[]';",
            "ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS images JSON DEFAULT '[]';",
            "ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS videos JSON DEFAULT '[]';",
            "ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS sources JSON DEFAULT '[]';",
            "ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS revision_count INTEGER DEFAULT 0;",
            "ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS final_report JSON;",
            "ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS critique JSON;",
            "ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS errors JSON DEFAULT '[]';",
            "ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS agent_events JSON DEFAULT '[]';",
            "ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;",
            "ALTER TABLE research_sessions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE;",
            "CREATE INDEX IF NOT EXISTS ix_research_sessions_user_id ON research_sessions (user_id);",
            "CREATE INDEX IF NOT EXISTS ix_research_sessions_created_at ON research_sessions (created_at);",
            "CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL, password_hash VARCHAR(255) NOT NULL, name VARCHAR(100) NOT NULL, created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW());",
            "CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);",
            "CREATE TABLE IF NOT EXISTS otp_challenges (id SERIAL PRIMARY KEY, email VARCHAR(255) NOT NULL, code_hash VARCHAR(128) NOT NULL, expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(), used BOOLEAN DEFAULT FALSE);",
            "CREATE INDEX IF NOT EXISTS ix_otp_challenges_email ON otp_challenges (email);",
        ]
        for sql in migrations:
            try:
                with engine.begin() as conn:
                    conn.execute(text(sql))
            except Exception as e:
                logger.debug("PostgreSQL migration step notice for %s: %s", sql[:50], e)
    elif "sqlite" in settings.DATABASE_URL.lower():
        # SQLite migrations for existing sqlite databases
        sqlite_cols = [
            ("title", "VARCHAR(255)"),
            ("user_id", "VARCHAR(255)"),
            ("tasks", "JSON"),
            ("evidence_count", "INTEGER DEFAULT 0"),
            ("evidence", "JSON"),
            ("images", "JSON"),
            ("videos", "JSON"),
            ("sources", "JSON"),
            ("revision_count", "INTEGER DEFAULT 0"),
            ("final_report", "JSON"),
            ("critique", "JSON"),
            ("errors", "JSON"),
            ("agent_events", "JSON"),
        ]
        for col_name, col_type in sqlite_cols:
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE research_sessions ADD COLUMN {col_name} {col_type};"))
            except Exception:
                pass

    logger.info("Database tables and columns initialized successfully.")


# Auto-run table initialization on module import to guarantee tables/columns exist immediately
try:
    init_db()
except Exception as exc:
    logger.warning("Automatic init_db on import warning: %s", exc)