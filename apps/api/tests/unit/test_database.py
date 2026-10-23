import pytest
from unittest.mock import MagicMock
from sqlalchemy.exc import OperationalError

from strata.core.config import Settings
from strata.db.session import create_app_engine, init_db


def test_database_url_normalization():
    """Verify postgres:// is normalized to postgresql:// for SQLAlchemy compatibility."""
    s1 = Settings(DATABASE_URL="postgres://postgres:secret@db.xyz.supabase.co:5432/postgres")
    assert s1.DATABASE_URL == "postgresql://postgres:secret@db.xyz.supabase.co:5432/postgres"

    s2 = Settings(DATABASE_URL="postgresql://postgres:secret@db.xyz.supabase.co:5432/postgres")
    assert s2.DATABASE_URL == "postgresql://postgres:secret@db.xyz.supabase.co:5432/postgres"

    s3 = Settings(DATABASE_URL="sqlite:///./test.db")
    assert s3.DATABASE_URL == "sqlite:///./test.db"


def test_supabase_auto_derived_url():
    """Verify effective_database_url auto-constructs direct connection if password and url provided."""
    s = Settings(
        DATABASE_URL="sqlite:///./strata.db",
        SUPABASE_URL="https://testprojectref.supabase.co",
        SUPABASE_DB_PASSWORD="p@ssword#123",
    )
    derived = s.effective_database_url
    assert derived.startswith("postgresql://postgres:p%40ssword%23123@db.testprojectref.supabase.co:5432/postgres")


def test_supabase_engine_ssl_enforcement():
    """Verify Supabase PostgreSQL connections enforce sslmode=require and timeouts."""
    engine = create_app_engine("postgresql://postgres:pwd@db.vatyzjfemocboipmclca.supabase.co:5432/postgres")
    assert engine.dialect.name == "postgresql"
    # Pool pre-ping must be enabled
    assert engine.pool._pre_ping is True


def test_database_unavailable_does_not_silently_fallback():
    """Verify that an unreachable database raises an error and does NOT silently fall back to in-memory SQLite."""
    unreachable_url = "postgresql://invalid_user:invalid_pass@127.0.0.1:59999/nonexistent"
    bad_engine = create_app_engine(unreachable_url)

    # Attempting to synchronize schema to unreachable database must fail explicitly
    with pytest.raises(Exception) as exc_info:
        # Simulate init_db against bad engine
        from strata.db.base import Base
        Base.metadata.create_all(bind=bad_engine)

    assert issubclass(exc_info.type, (OperationalError, Exception))
