import os
import uuid
from datetime import date, datetime, timezone
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from alembic import command
from alembic.config import Config

from strata.core.config import settings
from strata.domain.materials.models import Facility, MaterialLot, Organization
from strata.domain.qualification.models import EvidenceRecord


def test_alembic_migrations_execution(tmp_path):
    """Verify that Alembic migrations run cleanly to head on a clean database."""
    test_db_path = tmp_path / "migration_test.db"
    test_db_url = f"sqlite:///{test_db_path}"

    alembic_cfg = Config("apps/api/alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
    # Ensure prepend_sys_path resolves
    alembic_cfg.set_main_option("script_location", "apps/api/migrations")

    # Run upgrade to head
    command.upgrade(alembic_cfg, "head")

    # Verify tables were created by the migration
    engine = create_engine(test_db_url)
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('organizations', 'facilities', 'material_lots', 'evidence_records', 'investigations', 'qualification_assessments')")
        )
        table_names = {row[0] for row in result.fetchall()}
        assert "organizations" in table_names
        assert "facilities" in table_names
        assert "material_lots" in table_names
        assert "evidence_records" in table_names
        assert "investigations" in table_names
        assert "qualification_assessments" in table_names


def test_materials_and_evidence_persistence(db_session):
    """Verify material lots and evidence records persist across commits with valid relationships."""
    org_id = str(uuid.uuid4())
    fac_id = str(uuid.uuid4())
    lot_id = str(uuid.uuid4())
    evidence_id = str(uuid.uuid4())

    # 1. Create Organization & Facility
    org = Organization(org_id=org_id, name="Circularity Corp", org_type="manufacturer")
    fac = Facility(facility_id=fac_id, org_id=org_id, name="Main Smelter Plant", location_country="US")
    db_session.add(org)
    db_session.add(fac)
    db_session.commit()

    # 2. Persist MaterialLot
    lot = MaterialLot(
        lot_id=lot_id,
        org_id=org_id,
        facility_id=fac_id,
        material_type="aluminum-scrap",
        quantity=5000.0,
        unit="kg",
        status="active",
        availability_from=date(2026, 11, 1),
        declared_attributes={"alloy": "6061", "oil_contamination_pct": 0.5},
        provenance_label="facility_metered",
    )
    db_session.add(lot)
    db_session.commit()

    # 3. Persist Evidence linked to MaterialLot
    evidence = EvidenceRecord(
        evidence_id=evidence_id,
        org_id=org_id,
        lot_id=lot_id,
        claim_subject="alloy_series",
        claim_text="Spectrometry confirms 6061 aluminum alloy.",
        source_url="https://lab.cert/101",
        source_title="Certified Lab Assay",
        source_type="lab_report",
        extraction_method="lab_test",
        provenance="independently_verified",
        verification_state="verified",
        contradicted_by=[],
    )
    db_session.add(evidence)
    db_session.commit()

    # 4. Retrieve and verify relational integrity
    db_session.expire_all()

    fetched_lot = db_session.scalar(select(MaterialLot).where(MaterialLot.lot_id == lot_id))
    assert fetched_lot is not None
    assert fetched_lot.quantity == 5000.0
    assert fetched_lot.declared_attributes["alloy"] == "6061"

    fetched_evidence = db_session.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id))
    assert fetched_evidence is not None
    assert fetched_evidence.lot_id == lot_id
    assert fetched_evidence.verification_state == "verified"


def test_health_check_db_degraded_reporting(client):
    """Verify health endpoint reports degraded status when database execution fails."""
    # Create a mock session that fails on execute
    class FailingDBSession:
        def execute(self, statement):
            raise OperationalError("Connection refused to PostgreSQL host", params=None, orig=Exception())

        def rollback(self):
            pass

        def close(self):
            pass

    from strata.db.session import get_db
    from strata.main import app

    def failing_get_db():
        yield FailingDBSession()

    app.dependency_overrides[get_db] = failing_get_db
    try:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "degraded"
        assert "unhealthy" in data["database"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.skipif(
    not os.getenv("STRATA_TEST_LIVE_SUPABASE"),
    reason="Requires active Supabase project with valid credentials and STRATA_TEST_LIVE_SUPABASE=1",
)
def test_live_supabase_connectivity():
    """Live verification test against an active Supabase project.
    
    To execute:
    1. Set DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
    2. Set STRATA_TEST_LIVE_SUPABASE=1
    3. Run: pytest apps/api/tests/integration/test_persistence.py -k test_live_supabase_connectivity
    """
    from strata.db.session import engine

    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1
