from datetime import date
import json
import uuid
import pytest
from fastapi.testclient import TestClient

from strata.domain.marketplace.models import Listing
from strata.domain.marketplace.schemas import ListingStatus, ListingVisibility
from strata.domain.materials.models import Facility, MaterialLot, Organization

API = "/api/v1/municipal"


def _headers(role: str = "municipal_planner", org_id: str | None = None) -> dict:
    return {
        "X-Org-Id": org_id or str(uuid.uuid4()),
        "X-User-Id": str(uuid.uuid4()),
        "X-Role": role,
    }


@pytest.fixture
def municipal_fixture(db_session):
    city_id = f"metro-{uuid.uuid4()}"
    org_id = str(uuid.uuid4())
    db_session.add(Organization(org_id=org_id, name="Commercial Enterprise Inc", org_type="generator"))
    db_session.flush()

    # Proprietary naming to test strict privacy leaks
    secret_facility_names = [
        "Confidential Defense Chemical Plant",
        "Secret Semiconductor Fab #4",
        "Proprietary Textile Mill Beta",
    ]

    facs_zone_main = []
    for i, name in enumerate(secret_facility_names):
        f = Facility(
            facility_id=str(uuid.uuid4()),
            org_id=org_id,
            name=name,
            city_id=city_id,
            zone_id="industrial-zone-1",
            processing_capacity_tpa=150.0,
        )
        facs_zone_main.append(f)

    # Sub-threshold zone (<3 facilities)
    fac_zone_small = Facility(
        facility_id=str(uuid.uuid4()),
        org_id=org_id,
        name="Isolated Secret Facility",
        city_id=city_id,
        zone_id="rural-zone-9",
        processing_capacity_tpa=20.0,
    )

    db_session.add_all(facs_zone_main + [fac_zone_small])
    db_session.flush()

    lots = []
    for f in facs_zone_main:
        lot = MaterialLot(
            org_id=org_id,
            facility_id=f.facility_id,
            material_type="cotton-blend-offcuts",
            quantity=15000.0,
            unit="kg",
            status="available",
            availability_from=date(2026, 11, 1),
        )
        lots.append(lot)

    # Lot in small zone
    lot_small = MaterialLot(
        org_id=org_id,
        facility_id=fac_zone_small.facility_id,
        material_type="aluminum-scrap",
        quantity=5000.0,
        unit="kg",
        status="available",
        availability_from=date(2026, 11, 1),
    )
    lots.append(lot_small)

    db_session.add_all(lots)
    db_session.flush()

    # Commercial listing with confidential price
    secret_asking_price = 149.75
    listing = Listing(
        material_lot_id=lots[0].lot_id,
        organization_id=org_id,
        facility_id=facs_zone_main[0].facility_id,
        visibility=ListingVisibility.PUBLIC,
        asking_price_per_unit=secret_asking_price,
        currency="USD",
        available_quantity=15000.0,
        unit="kg",
        status=ListingStatus.ACTIVE,
    )
    db_session.add(listing)
    db_session.flush()

    return {
        "city_id": city_id,
        "secret_facility_names": secret_facility_names + ["Isolated Secret Facility"],
        "secret_asking_price": secret_asking_price,
        "facs_main": facs_zone_main,
        "fac_small": fac_zone_small,
    }


class TestMunicipalApiSecurityAndPrivacy:
    """Verifies strict privacy guarantees, role-based authorization, and cohort suppression."""

    def test_unauthorized_roles_are_forbidden(self, client: TestClient, municipal_fixture):
        """Standard tenant roles cannot access municipal planner endpoints."""
        city_id = municipal_fixture["city_id"]

        for forbidden_role in ["facility_operator", "facility_manager", "buyer_admin"]:
            headers = _headers(role=forbidden_role)

            r1 = client.get(f"{API}/flows?city_id={city_id}", headers=headers)
            assert r1.status_code == 403, f"Role {forbidden_role} should be forbidden on /flows"

            r2 = client.get(f"{API}/capacity-gaps?city_id={city_id}", headers=headers)
            assert r2.status_code == 403, f"Role {forbidden_role} should be forbidden on /capacity-gaps"

            r3 = client.get(f"{API}/indicators?city_id={city_id}", headers=headers)
            assert r3.status_code == 403, f"Role {forbidden_role} should be forbidden on /indicators"

    def test_authorized_roles_allowed(self, client: TestClient, municipal_fixture):
        """Users with 'municipal_planner' or 'admin' roles successfully access endpoints."""
        city_id = municipal_fixture["city_id"]

        for allowed_role in ["municipal_planner", "admin"]:
            headers = _headers(role=allowed_role)
            resp = client.get(f"{API}/flows?city_id={city_id}", headers=headers)
            assert resp.status_code == 200, f"Role {allowed_role} failed to access /flows"

    def test_strict_privacy_enforcement_never_leaks_facility_names_or_prices(
        self, client: TestClient, municipal_fixture
    ):
        """Ensures that confidential facility names, commercial prices, and facility IDs never leak."""
        city_id = municipal_fixture["city_id"]
        headers = _headers(role="municipal_planner")

        endpoints = [
            f"{API}/flows?city_id={city_id}",
            f"{API}/flows?city_id={city_id}&zone_id=industrial-zone-1",
            f"{API}/capacity-gaps?city_id={city_id}",
            f"{API}/indicators?city_id={city_id}",
        ]

        for url in endpoints:
            resp = client.get(url, headers=headers)
            assert resp.status_code == 200, resp.text
            raw_text = resp.text

            # 1. Assert confidential facility names never appear anywhere in the body
            for name in municipal_fixture["secret_facility_names"]:
                assert name not in raw_text, f"Privacy violation: '{name}' was leaked in {url}"

            # 2. Assert commercial asking price never appears
            price_str = str(municipal_fixture["secret_asking_price"])
            assert price_str not in raw_text, f"Privacy violation: asking price '{price_str}' was leaked in {url}"

            # 3. Assert facility UUIDs never appear in response data
            for fac in municipal_fixture["facs_main"]:
                assert fac.facility_id not in raw_text, f"Privacy violation: facility_id '{fac.facility_id}' leaked"

    def test_cohort_masking_in_flows_endpoint(self, client: TestClient, municipal_fixture):
        """Querying a sub-threshold zone (<3 facilities) suppresses metrics and masks cohort size."""
        city_id = municipal_fixture["city_id"]
        headers = _headers(role="municipal_planner")

        # rural-zone-9 has only 1 facility
        resp = client.get(f"{API}/flows?city_id={city_id}&zone_id=rural-zone-9", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert data["cohort_suppressed"] is True
        assert data["facility_cohort_count"] is None
        assert data["flows"] is None
        assert "fewer than 3" in data["suppression_reason"]

    def test_cohort_disclosure_in_valid_zone(self, client: TestClient, municipal_fixture):
        """Querying a valid zone (>=3 facilities) discloses aggregated volumes."""
        city_id = municipal_fixture["city_id"]
        headers = _headers(role="municipal_planner")

        resp = client.get(f"{API}/flows?city_id={city_id}&zone_id=industrial-zone-1", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert data["cohort_suppressed"] is False
        assert data["facility_cohort_count"] == 3
        assert data["flows"] is not None
        assert data["flows"]["generated_tonnage"] == 45.0  # 3 * 15 tonnes
        assert data["flows"]["offered_tonnage"] == 15.0  # 1 active listing of 15 tonnes

    def test_capacity_gaps_endpoint(self, client: TestClient, municipal_fixture):
        """Capacity gaps endpoint returns net balances and suppresses sub-threshold zones."""
        city_id = municipal_fixture["city_id"]
        headers = _headers(role="municipal_planner")

        resp = client.get(f"{API}/capacity-gaps?city_id={city_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert data["city_id"] == city_id
        assert data["total_city_generation"] == 50.0  # 45t in zone 1 + 5t in rural zone
        assert data["total_city_capacity"] == 470.0  # 3*150 + 20
        assert data["overall_status"] == "SURPLUS_CAPACITY"

        zones = {z["zone_id"]: z for z in data["zones"]}
        # Sub-threshold zone is masked
        assert zones["rural-zone-9"]["cohort_suppressed"] is True
        assert zones["rural-zone-9"]["facility_count"] is None
        assert zones["rural-zone-9"]["gap_status"] == "SUPPRESSED"

        # Valid zone is disclosed
        assert zones["industrial-zone-1"]["cohort_suppressed"] is False
        assert zones["industrial-zone-1"]["facility_count"] == 3
        assert zones["industrial-zone-1"]["generation_tonnage"] == 45.0
        assert zones["industrial-zone-1"]["processing_capacity_tonnage"] == 450.0
        assert zones["industrial-zone-1"]["gap_status"] == "SURPLUS_CAPACITY"

    def test_missing_city_id_validation_error(self, client: TestClient):
        """Missing required city_id query parameter returns 422 Unprocessable Entity."""
        headers = _headers(role="municipal_planner")
        resp = client.get(f"{API}/flows", headers=headers)
        assert resp.status_code == 422
