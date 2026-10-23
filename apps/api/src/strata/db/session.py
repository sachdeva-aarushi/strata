import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from strata.core.config import settings
from strata.db.base import Base

logger = logging.getLogger("strata.db")


def create_app_engine(database_url: str | None = None):
    """Creates a configured SQLAlchemy engine supporting SQLite and Supabase PostgreSQL."""
    url = database_url or settings.effective_database_url
    connect_args = {}
    engine_kwargs: dict = {
        "pool_pre_ping": True,
        "echo": False,
    }

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        # PostgreSQL / Supabase
        if url.startswith("postgresql://"):
            try:
                import psycopg  # noqa: F401
            except Exception:
                url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        connect_args["connect_timeout"] = settings.DATABASE_CONNECT_TIMEOUT
        # Enforce SSL requirement for remote Supabase connections if not specified in URL
        if ("supabase.co" in url or "pooler.supabase.com" in url) and "sslmode" not in url:
            connect_args["sslmode"] = "require"
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20
        engine_kwargs["pool_recycle"] = 300

    return create_engine(url, connect_args=connect_args, **engine_kwargs)


engine = create_app_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for request-scoped database sessions."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Creates database tables defined in metadata if they don't already exist.
    
    Strictly persists to the configured target database. Never silently falls back
    to in-memory storage if the configured database is unavailable.
    """
    import strata.domain.materials.models  # noqa: F401
    import strata.domain.qualification.models  # noqa: F401
    import strata.domain.marketplace.models  # noqa: F401

    url = settings.effective_database_url
    target_summary = url.split("@")[-1] if "@" in url else url
    logger.info("Synchronizing database schema to target: %s", target_summary)
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema synchronized successfully.")
    except Exception as exc:
        logger.error(
            "CRITICAL: Failed to connect to or initialize database at %s: %s",
            target_summary,
            str(exc),
        )
        # Inviolable architecture constraint: Do NOT silently fall back to in-memory persistence.
        raise
