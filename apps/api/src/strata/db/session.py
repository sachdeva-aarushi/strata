from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from strata.core.config import settings
from strata.db.base import Base

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

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
    """Creates database tables defined in metadata if they don't already exist."""
    # Ensure all ORM models are registered on Base
    import strata.domain.materials.models  # noqa: F401
    import strata.domain.qualification.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
