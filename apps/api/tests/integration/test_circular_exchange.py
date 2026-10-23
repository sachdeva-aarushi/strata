import uuid
import pytest
from fastapi.testclient import TestClient

EXCHANGE_API = "/api/v1/exchange"
CLUSTER_API = "/api/v1"


def _headers(org_id: str, role: str = "facility_operator", user_id: str | None = None) -> dict:
    return {
        "X-Org-Id": org_id,
        "X-User-Id": user_id or str(uuid.uuid4()),
        "X-Role": role,
    }


def _create_facility(client: TestClient, headers: dict, postal_code: str = "77001", name: str = "Houston Plant") -> str:
    facility_id = f"fac-{uuid.uuid4()}"
    return facility_id


def _register_lot(client: TestClient, headers: dict, facility_id: str, **overrides) -> str:
    payload = {
        "material_type": "aluminum-scrap",
        "quantity": 2500.0,
        "unit": "kg",
        "facility_id": facility_id,
        "availability_from": "2026-11-01",
        "declared_attributes": {
            "aluminum": 0.95,
            "magnesium": 0.04,
            "iron": 0.01,
            "tensile_strength_mpa": 310,
            "form": "chips",
        },
    }
    payload.update(overrides)
    resp = client.post("/api/v1/materials/lots", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["lot_id"]


class TestCircularExchangeListings:
    def test_create_and_enrich_exchange_listing(self, client: TestClient):
        seller_org = str(uuid.uuid4())
        headers = _headers(seller_org, role="facility_operator")
        facility_id = _create_facility(client, headers)
        lot_id = _register_lot(client, headers, facility_id)

        # 1. Create exchange listing
        create_payload = {
            "material_lot_id": lot_id,
            "facility_id": facility_id,
            "visibility": "public",
            "asking_price_per_unit": 4.25,
            "currency": "USD",
            "available_quantity": 2000.0,
            "unit": "kg",
            "status": "active",
        }
        resp = client.post(f"{EXCHANGE_API}/listings", json=create_payload, headers=headers)
        assert resp.status_code == 201, resp.text
        listing_data = resp.json()["data"]
        listing_id = listing_data["id"]

        assert listing_data["material_lot_id"] == lot_id
        assert listing_data["organization_id"] == seller_org
        assert listing_data["available_quantity"] == 2000.0
        assert listing_data["status"] == "active"

        # 2. Get listing with enrichment
        get_resp = client.get(f"{EXCHANGE_API}/listings/{listing_id}", headers=headers)
        assert get_resp.status_code == 200, get_resp.text
        enriched = get_resp.json()["data"]
        assert enriched["material_type"] == "aluminum-scrap"
        assert enriched["material_category"] == "metallics"
        assert "aluminum" in enriched["material_properties"]
        assert enriched["lot_quantity"] == 2500.0

        # 3. Update listing commercial terms
        update_resp = client.patch(
            f"{EXCHANGE_API}/listings/{listing_id}",
            json={"asking_price_per_unit": 3.95, "available_quantity": 1800.0},
            headers=headers,
        )
        assert update_resp.status_code == 200, update_resp.text
        updated = update_resp.json()["data"]
        assert updated["asking_price_per_unit"] == 3.95
        assert updated["available_quantity"] == 1800.0

        # 4. Search listings
        search_resp = client.get(
            f"{EXCHANGE_API}/listings?category=metallics&material_type=aluminum-scrap&min_quantity=1000",
            headers=headers,
        )
        assert search_resp.status_code == 200
        found_ids = [item["id"] for item in search_resp.json()["data"]]
        assert listing_id in found_ids

        # 5. Check listing history
        history_resp = client.get(f"{EXCHANGE_API}/listings/{listing_id}/history", headers=headers)
        assert history_resp.status_code == 200
        events = history_resp.json()["data"]
        assert len(events) >= 1
        event_types = [e["event_type"].lower() for e in events]
        assert "listing_created" in event_types


class TestCircularExchangeBuyerRequirements:
    def test_crud_buyer_requirements(self, client: TestClient):
        buyer_org = str(uuid.uuid4())
        headers = _headers(buyer_org, role="buyer_admin")
        facility_id = _create_facility(client, headers)

        req_payload = {
            "facility_id": facility_id,
            "material_category": "metallics",
            "material_type": "aluminum-scrap",
            "min_quantity": 500.0,
            "max_quantity": 3000.0,
            "unit": "kg",
            "target_price_per_unit": 4.5,
            "location": "Houston, TX",
            "delivery_requirements": {"max_lead_time_days": 14, "preferred_transport": "truck"},
            "constraints": {"min_purity_percent": 90.0, "max_moisture_percent": 2.0},
            "required_properties": {"grade": "aerospace"},
            "prohibited_conditions": ["radioactive", "hazardous_waste"],
            "visibility": "public",
        }

        # 1. Create requirement
        create_resp = client.post(f"{EXCHANGE_API}/buyer-requirements", json=req_payload, headers=headers)
        assert create_resp.status_code == 201, create_resp.text
        req_data = create_resp.json()["data"]
        req_id = req_data["id"]
        assert req_data["location"] == "Houston, TX"
        assert req_data["delivery_requirements"]["max_lead_time_days"] == 14
        assert req_data["constraints"]["min_purity_percent"] == 90.0

        # 2. List requirements
        list_resp = client.get(f"{EXCHANGE_API}/buyer-requirements", headers=headers)
        assert list_resp.status_code == 200
        req_ids = [r["id"] for r in list_resp.json()["data"]]
        assert req_id in req_ids

        # 3. Update requirement
        update_resp = client.patch(
            f"{EXCHANGE_API}/buyer-requirements/{req_id}",
            json={"target_price_per_unit": 4.75, "min_quantity": 600.0},
            headers=headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["data"]["target_price_per_unit"] == 4.75
        assert update_resp.json()["data"]["min_quantity"] == 600.0

        # 4. Get requirement
        get_resp = client.get(f"{EXCHANGE_API}/buyer-requirements/{req_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["min_quantity"] == 600.0

        # 5. Delete requirement
        del_resp = client.delete(f"{EXCHANGE_API}/buyer-requirements/{req_id}", headers=headers)
        assert del_resp.status_code == 200

        # Verify not found after delete
        get_deleted = client.get(f"{EXCHANGE_API}/buyer-requirements/{req_id}", headers=headers)
        assert get_deleted.status_code == 404


class TestCircularExchangeMatching:
    def test_matching_with_proofpath_qualification_and_inviolable_constraints(self, client: TestClient):
        seller_org = str(uuid.uuid4())
        buyer_org = str(uuid.uuid4())

        seller_headers = _headers(seller_org, role="facility_operator")
        buyer_headers = _headers(buyer_org, role="buyer_admin")

        seller_fac = _create_facility(client, seller_headers)
        buyer_fac = _create_facility(client, buyer_headers)

        # 1. Register compatible lot (Clean aluminum chips)
        lot_clean = _register_lot(
            client,
            seller_headers,
            seller_fac,
            material_type="aluminum-scrap",
            declared_attributes={"aluminum": 0.98, "copper": 0.01, "grade": "clean"},
        )
        resp_clean = client.post(
            f"{EXCHANGE_API}/listings",
            json={
                "material_lot_id": lot_clean,
                "facility_id": seller_fac,
                "visibility": "public",
                "asking_price_per_unit": 3.8,
                "currency": "USD",
                "available_quantity": 1500.0,
                "unit": "kg",
                "status": "active",
            },
            headers=seller_headers,
        )
        clean_listing_id = resp_clean.json()["data"]["id"]

        # 2. Register contaminated lot (Contains prohibited condition "pvc_coating")
        lot_incompatible = _register_lot(
            client,
            seller_headers,
            seller_fac,
            material_type="aluminum-scrap",
            declared_attributes={"aluminum": 0.85, "pvc_coating": True, "contamination": "pvc_coating"},
        )
        resp_incompatible = client.post(
            f"{EXCHANGE_API}/listings",
            json={
                "material_lot_id": lot_incompatible,
                "facility_id": seller_fac,
                "visibility": "public",
                "asking_price_per_unit": 2.0,
                "currency": "USD",
                "available_quantity": 1000.0,
                "unit": "kg",
                "status": "active",
            },
            headers=seller_headers,
        )
        incompatible_listing_id = resp_incompatible.json()["data"]["id"]

        # 3. Buyer creates requirement strictly prohibiting pvc_coating
        req_resp = client.post(
            f"{EXCHANGE_API}/buyer-requirements",
            json={
                "facility_id": buyer_fac,
                "material_category": "metallics",
                "material_type": "aluminum-scrap",
                "min_quantity": 500.0,
                "max_quantity": 2000.0,
                "unit": "kg",
                "target_price_per_unit": 4.0,
                "prohibited_conditions": ["pvc_coating", "hazardous_waste"],
                "visibility": "public",
            },
            headers=buyer_headers,
        )
        req_id = req_resp.json()["data"]["id"]

        # 4. Perform matching
        match_resp = client.get(f"{EXCHANGE_API}/buyer-requirements/{req_id}/matches", headers=buyer_headers)
        assert match_resp.status_code == 200, match_resp.text
        match_data = match_resp.json()["data"]

        # Must have matches
        candidates = match_data["matches"]
        assert len(candidates) >= 2

        clean_candidate = next((c for c in candidates if c["listing"]["id"] == clean_listing_id), None)
        incompat_candidate = next((c for c in candidates if c["listing"]["id"] == incompatible_listing_id), None)

        assert clean_candidate is not None
        assert incompat_candidate is not None

        # Clean candidate should be eligible or conditional (not ineligible) and have a positive match score
        assert clean_candidate["eligibility"] in ["eligible", "conditional"]
        assert clean_candidate["match_score"] > 0.0

        # CRITICAL CONSTRAINT TEST:
        # Incompatible candidate MUST be marked ineligible
        # Incompatible candidate match score MUST NOT override hard incompatibility -> pinned to 0.0
        assert incompat_candidate["eligibility"] == "ineligible"
        assert incompat_candidate["match_score"] == 0.0
        assert len(incompat_candidate["incompatibilities"]) > 0
        assert any("pvc_coating" in inc for inc in incompat_candidate["incompatibilities"])


class TestCircularExchangeRFQsAndOffers:
    def test_offer_review_and_withdrawal_workflow(self, client: TestClient):
        seller_org = str(uuid.uuid4())
        buyer_org = str(uuid.uuid4())

        seller_headers = _headers(seller_org, role="facility_operator")
        buyer_operator = _headers(buyer_org, role="facility_operator")
        buyer_manager = _headers(buyer_org, role="facility_manager")

        seller_fac = _create_facility(client, seller_headers)
        buyer_fac = _create_facility(client, buyer_operator)

        # 1. Setup active listing
        lot_id = _register_lot(client, seller_headers, seller_fac)
        listing_resp = client.post(
            f"{EXCHANGE_API}/listings",
            json={
                "material_lot_id": lot_id,
                "facility_id": seller_fac,
                "visibility": "public",
                "asking_price_per_unit": 5.0,
                "currency": "USD",
                "available_quantity": 1000.0,
                "unit": "kg",
                "status": "active",
            },
            headers=seller_headers,
        )
        listing_id = listing_resp.json()["data"]["id"]

        # 2. Buyer creates and submits RFQ
        rfq_resp = client.post(
            f"{EXCHANGE_API}/rfqs",
            json={
                "listing_id": listing_id,
                "buyer_facility_id": buyer_fac,
                "requested_quantity": 500.0,
                "unit": "kg",
                "target_price_per_unit": 4.8,
            },
            headers=buyer_operator,
        )
        rfq_id = rfq_resp.json()["data"]["id"]
        assert rfq_resp.json()["data"]["status"] == "draft"

        client.post(f"{EXCHANGE_API}/rfqs/{rfq_id}/submit", headers=buyer_operator)

        # 3. Buyer manager approves RFQ -> OPEN
        approve_resp = client.post(f"{EXCHANGE_API}/rfqs/{rfq_id}/approve", headers=buyer_manager)
        assert approve_resp.status_code == 200
        assert approve_resp.json()["data"]["status"] == "open"
        assert approve_resp.json()["data"]["approved_by"] is not None

        # 4. Seller submits Offer
        offer_resp = client.post(
            f"{EXCHANGE_API}/rfqs/{rfq_id}/offers",
            json={
                "offered_quantity": 500.0,
                "unit": "kg",
                "price_per_unit": 4.9,
                "currency": "USD",
                "lead_time_days": 7,
                "notes": "Fast track freight available",
            },
            headers=seller_headers,
        )
        assert offer_resp.status_code == 201, offer_resp.text
        offer_id = offer_resp.json()["data"]["id"]
        assert offer_resp.json()["data"]["status"] == "submitted"

        # 5. Buyer puts offer under review
        review_resp = client.post(
            f"{EXCHANGE_API}/offers/{offer_id}/review",
            json={"notes": "Evaluating technical composition"},
            headers=buyer_manager,
        )
        assert review_resp.status_code == 200
        assert review_resp.json()["data"]["status"] == "under_review"
        assert review_resp.json()["data"]["reviewed_by"] is not None

        # 6. Seller withdraws offer
        withdraw_resp = client.post(
            f"{EXCHANGE_API}/offers/{offer_id}/withdraw",
            json={"notes": "Allocated to internal remelt"},
            headers=seller_headers,
        )
        assert withdraw_resp.status_code == 200
        assert withdraw_resp.json()["data"]["status"] == "withdrawn"

        # 7. Invalid state transition: Buyer cannot accept a withdrawn offer (returns 422 InvalidStateTransition)
        buyer_admin = _headers(buyer_org, role="buyer_admin")
        invalid_accept = client.post(f"{EXCHANGE_API}/offers/{offer_id}/accept", headers=buyer_admin)
        assert invalid_accept.status_code == 422
        assert invalid_accept.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


class TestCircularExchangeLogisticsAndIndicators:
    def test_logistics_comparison(self, client: TestClient):
        # Freight transport comparison across diesel, electric, and rail
        resp = client.get(
            f"{EXCHANGE_API}/logistics/compare?origin_location=Houston,TX&destination_location=Dallas,TX&quantity=5000&unit=kg&material_type=aluminum-scrap"
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        assert data["distance_km"] > 0
        assert data["is_distance_estimated"] is True
        assert len(data["options"]) == 3

        modes = [opt["mode"] for opt in data["options"]]
        assert "road_standard_diesel" in modes
        assert "road_electric_truck" in modes
        assert "rail_intermodal" in modes

        # Ensure values are clearly labeled as estimated
        for opt in data["options"]:
            assert opt["is_estimated"] is True
            assert opt["estimated_cost_usd"] > 0
            assert opt["estimated_emissions_kg_co2e"] > 0

    def test_cluster_and_city_indicators(self, client: TestClient):
        # 1. Cluster indicators using persisted data
        cluster_resp = client.get(f"{CLUSTER_API}/cluster/indicators")
        assert cluster_resp.status_code == 200, cluster_resp.text
        cluster_data = cluster_resp.json()["data"]

        assert "total_active_listings" in cluster_data
        assert "total_active_buyer_requirements" in cluster_data
        assert cluster_data["is_estimated"] is False

        # 2. City indicators
        city_resp = client.get(f"{CLUSTER_API}/city/indicators")
        assert city_resp.status_code == 200, city_resp.text
        city_data = city_resp.json()["data"]

        assert "diverted_material_tonnes" in city_data
        assert "participating_facilities_count" in city_data
        assert city_data["is_estimated"] is True
