from datetime import date
import uuid
import pytest
from fastapi.testclient import TestClient

from strata.domain.marketplace.models import Listing
from strata.domain.marketplace.schemas import ListingStatus, ListingVisibility
from strata.domain.materials.models import Facility, MaterialLot, Organization

API = "/api/v1/marketplace"


def _headers(org_id: str, role: str = "facility_operator", user_id: str | None = None) -> dict:
    return {
        "X-Org-Id": org_id,
        "X-User-Id": user_id or str(uuid.uuid4()),
        "X-Role": role,
    }


class TestClusterSynergyIntegrationApi:
    """Integration test suite for Cluster Synergy & Aggregation REST endpoints."""

    def test_get_cluster_indicators_empty(self, client: TestClient, org_headers: dict):
        """Calling indicators on an empty/new cluster returns zero metrics."""
        cluster_id = f"cluster-{uuid.uuid4()}"
        resp = client.get(f"{API}/cluster/{cluster_id}/indicators", headers=org_headers)
        assert resp.status_code == 200, resp.text

        data = resp.json()["data"]
        assert data["cluster_id"] == cluster_id
        assert data["active_listings_count"] == 0
        assert data["total_available_tonnage"] == 0.0
        assert data["tonnage_by_category"] == {}
        assert data["potential_aggregation_opportunities"] == 0

    def test_get_cluster_indicators_with_active_listings(
        self, client: TestClient, db_session, org_headers: dict
    ):
        """Indicators aggregate active listings, tonnage by category, and opportunities."""
        cluster_id = f"cluster-{uuid.uuid4()}"
        seller_org_id = org_headers["X-Org-Id"]

        # Ensure seller facility in cluster
        facility = Facility(
            facility_id=str(uuid.uuid4()),
            org_id=seller_org_id,
            name="Alpha Textile Mill",
            cluster_id=cluster_id,
        )
        db_session.add(facility)
        db_session.flush()

        # Seed two textile lots + listings
        for qty in [300.0, 450.0]:
            lot = MaterialLot(
                org_id=seller_org_id,
                facility_id=facility.facility_id,
                material_type="cotton-blend-offcuts",
                quantity=qty,
                unit="kg",
                status="available",
                availability_from=date(2026, 11, 1),
            )
            db_session.add(lot)
            db_session.flush()

            listing = Listing(
                material_lot_id=lot.lot_id,
                organization_id=seller_org_id,
                facility_id=facility.facility_id,
                visibility=ListingVisibility.CLUSTER_ONLY,
                asking_price_per_unit=45.0,
                currency="INR",
                available_quantity=qty,
                unit="kg",
                status=ListingStatus.ACTIVE,
            )
            db_session.add(listing)

        # Seed an aluminum lot + listing
        metal_lot = MaterialLot(
            org_id=seller_org_id,
            facility_id=facility.facility_id,
            material_type="aluminum-scrap",
            quantity=1200.0,
            unit="kg",
            status="available",
            availability_from=date(2026, 11, 1),
        )
        db_session.add(metal_lot)
        db_session.flush()

        metal_listing = Listing(
            material_lot_id=metal_lot.lot_id,
            organization_id=seller_org_id,
            facility_id=facility.facility_id,
            visibility=ListingVisibility.PUBLIC,
            asking_price_per_unit=120.0,
            currency="INR",
            available_quantity=1200.0,
            unit="kg",
            status=ListingStatus.ACTIVE,
        )
        db_session.add(metal_listing)
        db_session.flush()

        resp = client.get(f"{API}/cluster/{cluster_id}/indicators", headers=org_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        assert data["cluster_id"] == cluster_id
        assert data["active_listings_count"] == 3
        # 300 kg + 450 kg = 0.75 tonne textiles; 1200 kg = 1.2 tonne metallics; total = 1.95 tonnes
        assert data["total_available_tonnage"] == 1.95
        assert data["tonnage_by_category"]["textiles"] == 0.75
        assert data["tonnage_by_category"]["metallics"] == 1.2
        # Textiles has 2 lots (>= 2 is an aggregation opportunity)
        assert data["potential_aggregation_opportunities"] >= 1

    def test_get_cluster_synergies_for_specific_requirement(
        self, client: TestClient, db_session
    ):
        """Synergy endpoint generates valid aggregation proposals meeting buyer volume thresholds."""
        cluster_id = f"cluster-{uuid.uuid4()}"
        buyer_org = str(uuid.uuid4())
        seller_org_1 = str(uuid.uuid4())
        seller_org_2 = str(uuid.uuid4())

        for oid, name in [
            (buyer_org, "Buyer Mills Ltd"),
            (seller_org_1, "Supplier Alpha"),
            (seller_org_2, "Supplier Beta"),
        ]:
            db_session.add(Organization(org_id=oid, name=name))
        db_session.flush()

        fac_buyer = Facility(
            facility_id=str(uuid.uuid4()),
            org_id=buyer_org,
            name="Buyer Central Processing",
            cluster_id=cluster_id,
        )
        fac_seller_1 = Facility(
            facility_id=str(uuid.uuid4()),
            org_id=seller_org_1,
            name="Supplier Alpha Plant",
            cluster_id=cluster_id,
        )
        fac_seller_2 = Facility(
            facility_id=str(uuid.uuid4()),
            org_id=seller_org_2,
            name="Supplier Beta Plant",
            cluster_id=cluster_id,
        )
        db_session.add_all([fac_buyer, fac_seller_1, fac_seller_2])
        db_session.flush()

        buyer_headers = _headers(buyer_org)

        # 1. Post buyer requirement (needs 500 kg textiles, min 500, max 1000)
        req_payload = {
            "facility_id": fac_buyer.facility_id,
            "material_category": "textiles",
            "min_quantity": 500.0,
            "max_quantity": 1000.0,
            "unit": "kg",
            "required_properties": {"fiber": "cotton"},
            "prohibited_conditions": ["pvc", "moisture_gt_15"],
            "visibility": "cluster_only",
        }
        req_resp = client.post(f"{API}/buyer-requirements", json=req_payload, headers=buyer_headers)
        assert req_resp.status_code == 201, req_resp.text
        requirement_id = req_resp.json()["data"]["id"]

        # 2. Add Supplier 1 lot (300 kg cotton offcuts, moisture 8%)
        lot1 = MaterialLot(
            org_id=seller_org_1,
            facility_id=fac_seller_1.facility_id,
            material_type="cotton-blend-offcuts",
            quantity=300.0,
            unit="kg",
            status="available",
            availability_from=date(2026, 11, 1),
            declared_attributes={"moisture_pct": 8.0, "cotton_pct": 85.0},
        )
        db_session.add(lot1)
        db_session.flush()

        listing1 = Listing(
            material_lot_id=lot1.lot_id,
            organization_id=seller_org_1,
            facility_id=fac_seller_1.facility_id,
            visibility=ListingVisibility.CLUSTER_ONLY,
            asking_price_per_unit=40.0,
            currency="INR",
            available_quantity=300.0,
            unit="kg",
            status=ListingStatus.ACTIVE,
        )
        db_session.add(listing1)

        # 3. Add Supplier 2 lot (350 kg cotton offcuts, moisture 12%)
        lot2 = MaterialLot(
            org_id=seller_org_2,
            facility_id=fac_seller_2.facility_id,
            material_type="cotton-blend-offcuts",
            quantity=350.0,
            unit="kg",
            status="available",
            availability_from=date(2026, 11, 1),
            declared_attributes={"moisture_pct": 12.0, "cotton_pct": 75.0},
        )
        db_session.add(lot2)
        db_session.flush()

        listing2 = Listing(
            material_lot_id=lot2.lot_id,
            organization_id=seller_org_2,
            facility_id=fac_seller_2.facility_id,
            visibility=ListingVisibility.PUBLIC,
            asking_price_per_unit=42.0,
            currency="INR",
            available_quantity=350.0,
            unit="kg",
            status=ListingStatus.ACTIVE,
        )
        db_session.add(listing2)
        db_session.flush()

        # 4. Fetch cluster synergies for this requirement
        synergy_resp = client.get(
            f"{API}/cluster/{cluster_id}/synergies?requirement_id={requirement_id}",
            headers=buyer_headers,
        )
        assert synergy_resp.status_code == 200, synergy_resp.text
        proposals = synergy_resp.json()["data"]

        assert len(proposals) >= 1
        p = proposals[0]
        assert p["requirement_id"] == requirement_id
        assert p["cluster_id"] == cluster_id
        assert p["total_quantity"] == 650.0  # 300 + 350
        assert p["total_quantity"] >= 500.0
        assert len(p["lots"]) == 2

        # Check composite attributes
        composite = p["composite_attributes"]
        assert "moisture_pct" in composite
        # Weighted moisture: (300*8 + 350*12) / 650 = 6600 / 650 = 10.15%
        assert composite["moisture_pct"] == 10.15

    def test_get_cluster_synergies_all_requirements(
        self, client: TestClient, db_session
    ):
        """Querying synergies without requirement_id iterates across active requirements."""
        cluster_id = f"cluster-{uuid.uuid4()}"
        buyer_org = str(uuid.uuid4())
        seller_org = str(uuid.uuid4())

        for oid, name in [(buyer_org, "Buyer Co"), (seller_org, "Seller Co")]:
            db_session.add(Organization(org_id=oid, name=name))
        db_session.flush()

        fac_buyer = Facility(
            facility_id=str(uuid.uuid4()),
            org_id=buyer_org,
            name="Buyer Plant",
            cluster_id=cluster_id,
        )
        fac_seller = Facility(
            facility_id=str(uuid.uuid4()),
            org_id=seller_org,
            name="Seller Plant",
            cluster_id=cluster_id,
        )
        db_session.add_all([fac_buyer, fac_seller])
        db_session.flush()

        buyer_headers = _headers(buyer_org)

        # Create buyer requirement
        req_payload = {
            "facility_id": fac_buyer.facility_id,
            "material_category": "textiles",
            "min_quantity": 100.0,
            "max_quantity": 500.0,
            "unit": "kg",
            "required_properties": {},
            "prohibited_conditions": [],
            "visibility": "public",
        }
        client.post(f"{API}/buyer-requirements", json=req_payload, headers=buyer_headers)

        # Create compatible listing
        lot = MaterialLot(
            org_id=seller_org,
            facility_id=fac_seller.facility_id,
            material_type="cotton-blend-offcuts",
            quantity=250.0,
            unit="kg",
            status="available",
            availability_from=date(2026, 11, 1),
        )
        db_session.add(lot)
        db_session.flush()

        listing = Listing(
            material_lot_id=lot.lot_id,
            organization_id=seller_org,
            facility_id=fac_seller.facility_id,
            visibility=ListingVisibility.PUBLIC,
            asking_price_per_unit=50.0,
            currency="INR",
            available_quantity=250.0,
            unit="kg",
            status=ListingStatus.ACTIVE,
        )
        db_session.add(listing)
        db_session.flush()

        # Query without requirement_id
        resp = client.get(f"{API}/cluster/{cluster_id}/synergies", headers=buyer_headers)
        assert resp.status_code == 200, resp.text
        proposals = resp.json()["data"]
        assert len(proposals) >= 1

    def test_get_cluster_synergies_nonexistent_requirement_404(
        self, client: TestClient, org_headers: dict
    ):
        """Querying synergies with a nonexistent requirement ID returns 404."""
        missing_id = str(uuid.uuid4())
        resp = client.get(
            f"{API}/cluster/cluster-test/synergies?requirement_id={missing_id}",
            headers=org_headers,
        )
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "RESOURCE_NOT_FOUND"

    def test_calculate_logistics_estimate_success(
        self, client: TestClient, db_session, org_headers: dict
    ):
        """Calculates indicative consolidation distance, transport tariff in INR, and CO2 emissions."""
        seller_org_id = org_headers["X-Org-Id"]
        destination_facility = str(uuid.uuid4())

        fac1 = Facility(facility_id=str(uuid.uuid4()), org_id=seller_org_id, name="Depot 1")
        fac2 = Facility(facility_id=str(uuid.uuid4()), org_id=seller_org_id, name="Depot 2")
        db_session.add_all([fac1, fac2])
        db_session.flush()

        # 2 lots: 5000 kg (5 t) at fac1, 3000 kg (3 t) at fac2 -> Total: 8 tonnes
        lot1 = MaterialLot(
            org_id=seller_org_id,
            facility_id=fac1.facility_id,
            material_type="aluminum-scrap",
            quantity=5000.0,
            unit="kg",
            status="available",
            availability_from=date(2026, 11, 1),
        )
        lot2 = MaterialLot(
            org_id=seller_org_id,
            facility_id=fac2.facility_id,
            material_type="aluminum-scrap",
            quantity=3000.0,
            unit="kg",
            status="available",
            availability_from=date(2026, 11, 1),
        )
        db_session.add_all([lot1, lot2])
        db_session.flush()

        payload = {
            "lot_ids": [lot1.lot_id, lot2.lot_id],
            "destination_facility_id": destination_facility,
            "rate_per_km_tonne": 15.0,
        }
        resp = client.post(f"{API}/cluster/logistics-estimate", json=payload, headers=org_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        # Expected:
        # total_tonnage: 8.0 tonnes
        # 2 facilities -> distance = (2-1)*30 + 45 = 75.0 km
        # cost = 8.0 * 75.0 * 15.0 = 9000.0 INR
        # emissions = 8.0 * 75.0 * 0.105 = 63.0 kg CO2e
        assert data["total_tonnage"] == 8.0
        assert data["total_distance_km"] == 75.0
        assert data["rate_per_km_tonne"] == 15.0
        assert data["estimated_transport_cost_inr"] == 9000.0
        assert data["estimated_transport_emissions_kg_co2e"] == 63.0
        assert data["currency"] == "INR"
        assert data["methodology"] == "indicative_milk_run_v1"

    def test_calculate_logistics_missing_lot_404(
        self, client: TestClient, org_headers: dict
    ):
        """Logistics estimation returns 404 when referenced lot is not found."""
        payload = {
            "lot_ids": [str(uuid.uuid4())],
            "destination_facility_id": str(uuid.uuid4()),
            "rate_per_km_tonne": 12.5,
        }
        resp = client.post(f"{API}/cluster/logistics-estimate", json=payload, headers=org_headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    def test_calculate_logistics_validation_failure(
        self, client: TestClient, org_headers: dict
    ):
        """Empty lot_ids list or non-positive rate fails validation."""
        # Empty lot_ids
        resp1 = client.post(
            f"{API}/cluster/logistics-estimate",
            json={"lot_ids": [], "destination_facility_id": "fac-123", "rate_per_km_tonne": 10.0},
            headers=org_headers,
        )
        assert resp1.status_code == 422

        # Non-positive rate
        resp2 = client.post(
            f"{API}/cluster/logistics-estimate",
            json={"lot_ids": ["lot-123"], "destination_facility_id": "fac-123", "rate_per_km_tonne": -5.0},
            headers=org_headers,
        )
        assert resp2.status_code == 422
