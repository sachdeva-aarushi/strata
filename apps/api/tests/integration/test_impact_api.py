import uuid
import pytest
from fastapi.testclient import TestClient

from strata.domain.materials.models import Facility, Organization

API = "/api/v1/impact"


def _headers(org_id: str | None = None) -> dict:
    return {
        "X-Org-Id": org_id or str(uuid.uuid4()),
        "X-User-Id": str(uuid.uuid4()),
        "X-Role": "facility_operator",
    }


@pytest.fixture
def test_facility(db_session, org_headers):
    org_id = org_headers["X-Org-Id"]
    fac_id = str(uuid.uuid4())
    org = Organization(org_id=org_id, name="Test Circular Mill")
    fac = Facility(facility_id=fac_id, org_id=org_id, name="Depot Zero")
    db_session.add_all([org, fac])
    db_session.flush()
    return fac_id


class TestImpactIntegrationApi:
    """Integration test suite for Verified Impact Ledger REST endpoints."""

    def test_record_impact_lifecycle_event_api(self, client: TestClient, org_headers: dict, test_facility: str):
        """POST /api/v1/impact/record creates an immutable lifecycle impact record."""
        lot_id = f"lot-{uuid.uuid4()}"
        payload = {
            "lot_id": lot_id,
            "facility_id": test_facility,
            "event_type": "generated",
            "mass_kg": 1500.0,
            "displaced_material_category": "textiles",
            "methodology_version": "v1.0",
        }

        resp = client.post(f"{API}/record", json=payload, headers=org_headers)
        assert resp.status_code == 201, resp.text

        body = resp.json()
        assert "data" in body
        data = body["data"]
        assert data["lot_id"] == lot_id
        assert data["facility_id"] == test_facility
        assert data["event_type"] == "generated"
        assert data["mass_kg"] == 1500.0
        assert data["co2e_avoided_kg"] == 21300.0  # 1500 * 14.2
        assert "EPA WARM" in data["factor_source"]
        assert data["verification_status"] == "unverified"
        assert "meta" in body
        assert "request_id" in body["meta"]

    def test_record_duplicate_event_returns_409(self, client: TestClient, org_headers: dict, test_facility: str):
        """Duplicate event for the same lot triggers 409 Conflict to prevent double-counting."""
        lot_id = f"lot-{uuid.uuid4()}"
        payload = {
            "lot_id": lot_id,
            "facility_id": test_facility,
            "event_type": "generated",
            "mass_kg": 2000.0,
            "displaced_material_category": "metallics",
        }

        # First recording succeeds
        r1 = client.post(f"{API}/record", json=payload, headers=org_headers)
        assert r1.status_code == 201

        # Second recording fails
        r2 = client.post(f"{API}/record", json=payload, headers=org_headers)
        assert r2.status_code == 409
        body = r2.json()
        assert "error" in body
        assert body["error"]["code"] == "DUPLICATE_EVENT"
        assert "Double-counting is strictly prevented" in body["error"]["message"]

    def test_record_invalid_state_transition_returns_422(
        self, client: TestClient, org_headers: dict, test_facility: str
    ):
        """Skipping necessary receipt confirmation before verified_recovered returns 422."""
        lot_id = f"lot-{uuid.uuid4()}"

        # Register generation first
        client.post(
            f"{API}/record",
            json={
                "lot_id": lot_id,
                "facility_id": test_facility,
                "event_type": "generated",
                "mass_kg": 1000.0,
                "displaced_material_category": "chemicals",
            },
            headers=org_headers,
        )

        # Directly attempt verified_recovered without accepted/processed
        resp = client.post(
            f"{API}/record",
            json={
                "lot_id": lot_id,
                "facility_id": test_facility,
                "event_type": "verified_recovered",
                "mass_kg": 1000.0,
                "displaced_material_category": "chemicals",
            },
            headers=org_headers,
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "INVALID_STATE_TRANSITION"
        assert "accepted" in body["error"]["message"]

    def test_get_impact_summary_and_mass_balance_api(
        self, client: TestClient, org_headers: dict, test_facility: str
    ):
        """GET /api/v1/impact/summary returns segregated mass balance and historical records."""
        lot_id = f"lot-{uuid.uuid4()}"
        evidence_id = str(uuid.uuid4())

        # Progression: generated -> shipped -> accepted -> verified_recovered
        flow = [
            ("generated", None),
            ("shipped", None),
            ("accepted", None),
            ("verified_recovered", evidence_id),
        ]

        for step, ev in flow:
            client.post(
                f"{API}/record",
                json={
                    "lot_id": lot_id,
                    "facility_id": test_facility,
                    "event_type": step,
                    "mass_kg": 3000.0,
                    "displaced_material_category": "textiles",
                    "evidence_id": ev,
                },
                headers=org_headers,
            )

        resp = client.get(f"{API}/summary?facility_id={test_facility}", headers=org_headers)
        assert resp.status_code == 200, resp.text

        body = resp.json()
        data = body["data"]
        mb = data["mass_balance"]

        assert mb["total_generated_kg"] == 3000.0
        assert mb["total_shipped_kg"] == 3000.0
        assert mb["total_accepted_kg"] == 3000.0
        assert mb["total_verified_recovered_kg"] == 3000.0
        assert mb["total_landfill_avoided_kg"] == 3000.0
        assert mb["total_co2e_avoided_kg"] == 42600.0  # 3000 * 14.2
        assert mb["net_in_pipeline_kg"] == 0.0
        assert len(data["records"]) == 4

    def test_get_supported_methods_api(self, client: TestClient):
        """GET /api/v1/impact/methods returns versioned emission factor methodologies."""
        resp = client.get(f"{API}/methods")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert len(data) >= 1
        assert data[0]["methodology_version"] == "v1.0"
        assert "textiles" in data[0]["factors_by_category"]

    def test_calculate_environmental_impact_api(self, client: TestClient):
        """POST /api/v1/impact/calculate computes instant abatement without mutating database."""
        payload = {
            "mass_kg": 5000.0,
            "material_category": "metallics",
            "methodology_version": "v1.0",
        }
        resp = client.post(f"{API}/calculate", json=payload)
        assert resp.status_code == 200, resp.text

        data = resp.json()["data"]
        assert data["mass_kg"] == 5000.0
        assert data["landfill_avoided_kg"] == 5000.0
        assert data["co2e_avoided_kg"] == 42500.0  # 5000 * 8.5
        assert data["factor_used"] == 8.5
        assert data["uncertainty_rating"] == "LOW"
