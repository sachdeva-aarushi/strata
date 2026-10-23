import os
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment flags
os.environ["APP_ENV"] = "testing"
os.environ["DEBUG"] = "true"
os.environ["MOCK_AUTH_ENABLED"] = "true"

from strata.db.base import Base
from strata.db.session import get_db
from strata.main import app

# In-memory SQLite for isolated, fast test execution
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all database schema tables once per test session."""
    import strata.domain.materials.models  # noqa: F401
    import strata.domain.qualification.models  # noqa: F401
    import strata.domain.marketplace.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Yields a transactional database session rolled back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Yields a TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def org_headers() -> dict:
    """Default authenticated tenant headers."""
    return {
        "X-Org-Id": "11111111-1111-1111-1111-111111111111",
        "X-User-Id": "22222222-2222-2222-2222-222222222222",
        "X-Role": "facility_operator",
    }


@pytest.fixture
def other_org_headers() -> dict:
    """Secondary tenant organization headers to test multi-tenant boundary isolation."""
    return {
        "X-Org-Id": "99999999-9999-9999-9999-999999999999",
        "X-User-Id": "88888888-8888-8888-8888-888888888888",
        "X-Role": "facility_operator",
    }
