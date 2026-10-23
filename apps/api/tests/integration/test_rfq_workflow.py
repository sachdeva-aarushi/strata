import uuid
import pytest
from fastapi.testclient import TestClient

API = "/api/v1/marketplace"


def _headers(org_id: str, role: str = "facility_operator", user_id: str | None = None) -> dict:
    return {
        "X-Org-Id": org_id,
        "X-User-Id": user_id or str(uuid.uuid4()),
        "X-Role": role,
    }


def _register_lot_and_listing(client: TestClient, seller_headers: dict, facility_id: str) -> str:
    # 1. Register lot in materials domain
    lot_payload = {
        "material_type": "aluminum-scrap",
        "quantity": 1000.0,
        "unit": "kg",
        "facility_id": facility_id,
        "availability_from": "2026-11-01",
    }
    lot_resp = client.post("/api/v1/materials/lots", json=lot_payload, headers=seller_headers)
    assert lot_resp.status_code == 201, lot_resp.text
    lot_id = lot_resp.json()["data"]["lot_id"]

    # 2. Publish listing in marketplace domain
    listing_payload = {
        "material_lot_id": lot_id,
        "facility_id": facility_id,
        "visibility": "public",
        "asking_price_per_unit": 3.5,
        "currency": "USD",
        "available_quantity": 800.0,
        "unit": "kg",
        "status": "active",
    }
    listing_resp = client.post(f"{API}/listings", json=listing_payload, headers=seller_headers)
    assert listing_resp.status_code == 201, listing_resp.text
    return listing_resp.json()["data"]["id"]


class TestRFQAndOfferIntegrationWorkflow:
    def test_complete_rfq_and_offer_lifecycle(self, client: TestClient):
        seller_org = str(uuid.uuid4())
        buyer_org = str(uuid.uuid4())
        seller_facility = str(uuid.uuid4())
        buyer_facility = str(uuid.uuid4())

        seller_op = _headers(seller_org, role="facility_operator")
        buyer_op = _headers(buyer_org, role="facility_operator")
        buyer_mgr = _headers(buyer_org, role="facility_manager")
        buyer_adm = _headers(buyer_org, role="buyer_admin")

        # 1. Seller sets up listing
        listing_id = _register_lot_and_listing(client, seller_op, seller_facility)

        # 2. Seller pauses then unpauses listing
        pause_resp = client.post(
            f"{API}/listings/{listing_id}/status",
            json={"status": "paused", "notes": "Paused for stock counting"},
            headers=seller_op,
        )
        assert pause_resp.status_code == 200
        assert pause_resp.json()["data"]["status"] == "paused"

        resume_resp = client.post(
            f"{API}/listings/{listing_id}/status",
            json={"status": "active", "notes": "Stock counted; resumed"},
            headers=seller_op,
        )
        assert resume_resp.status_code == 200
        assert resume_resp.json()["data"]["status"] == "active"

        # 3. Buyer creates RFQ (DRAFT)
        rfq_payload = {
            "listing_id": listing_id,
            "buyer_facility_id": buyer_facility,
            "requested_quantity": 250.0,
            "unit": "kg",
            "target_price_per_unit": 3.2,
            "notes": "Urgent procurement batch",
        }
        create_rfq_resp = client.post(f"{API}/rfqs", json=rfq_payload, headers=buyer_op)
        assert create_rfq_resp.status_code == 201, create_rfq_resp.text
        rfq_data = create_rfq_resp.json()["data"]
        rfq_id = rfq_data["id"]
        assert rfq_data["status"] == "draft"

        # 4. Buyer submits RFQ for approval
        submit_resp = client.post(f"{API}/rfqs/{rfq_id}/submit", headers=buyer_op)
        assert submit_resp.status_code == 200
        assert submit_resp.json()["data"]["status"] == "pending_approval"

        # 5. Non-manager fails approval gate
        gate_fail_resp = client.post(f"{API}/rfqs/{rfq_id}/approve", headers=buyer_op)
        assert gate_fail_resp.status_code == 403

        # 6. Facility manager approves RFQ
        approve_resp = client.post(f"{API}/rfqs/{rfq_id}/approve", headers=buyer_mgr)
        assert approve_resp.status_code == 200
        assert approve_resp.json()["data"]["status"] == "open"

        # 7. Seller submits an Offer
        offer_payload = {
            "offered_quantity": 250.0,
            "unit": "kg",
            "price_per_unit": 3.4,
            "currency": "USD",
            "terms": "Net 30, pickup by buyer",
        }
        offer_resp = client.post(f"{API}/rfqs/{rfq_id}/offers", json=offer_payload, headers=seller_op)
        assert offer_resp.status_code == 201, offer_resp.text
        offer_id = offer_resp.json()["data"]["id"]
        assert offer_resp.json()["data"]["status"] == "submitted"

        # 8. List offers for the RFQ
        list_offers_resp = client.get(f"{API}/rfqs/{rfq_id}/offers", headers=buyer_op)
        assert list_offers_resp.status_code == 200
        assert len(list_offers_resp.json()["data"]) == 1

        # 9. Non-buyer-admin fails acceptance gate
        accept_fail_resp = client.post(f"{API}/offers/{offer_id}/accept", headers=buyer_mgr)
        assert accept_fail_resp.status_code == 403

        # 10. Buyer admin accepts the binding offer
        accept_resp = client.post(
            f"{API}/offers/{offer_id}/accept",
            json={"notes": "Commercial terms accepted by procurement director"},
            headers=buyer_adm,
        )
        assert accept_resp.status_code == 200
        assert accept_resp.json()["data"]["status"] == "accepted"

        # 11. RFQ status should now be closed
        rfq_check_resp = client.get(f"{API}/rfqs/{rfq_id}", headers=buyer_op)
        assert rfq_check_resp.status_code == 200
        assert rfq_check_resp.json()["data"]["status"] == "closed"

        # 12. Verify audit event timeline
        history_resp = client.get(f"{API}/rfqs/{rfq_id}/history", headers=buyer_op)
        assert history_resp.status_code == 200
        events = history_resp.json()["data"]
        event_types = [e["event_type"] for e in events]
        assert "rfq_created" in event_types
        assert "rfq_submitted" in event_types
        assert "rfq_approved" in event_types
        assert "rfq_cancelled" in event_types # closure transition

    def test_invalid_state_transitions_return_422(self, client: TestClient):
        seller_org = str(uuid.uuid4())
        buyer_org = str(uuid.uuid4())
        seller_facility = str(uuid.uuid4())
        buyer_facility = str(uuid.uuid4())

        seller_op = _headers(seller_org, role="facility_operator")
        buyer_op = _headers(buyer_org, role="facility_operator")

        listing_id = _register_lot_and_listing(client, seller_op, seller_facility)

        # Create DRAFT RFQ
        rfq_payload = {
            "listing_id": listing_id,
            "buyer_facility_id": buyer_facility,
            "requested_quantity": 100.0,
            "unit": "kg",
            "submit_for_approval": False,
        }
        create_resp = client.post(f"{API}/rfqs", json=rfq_payload, headers=buyer_op)
        assert create_resp.status_code == 201
        rfq_id = create_resp.json()["data"]["id"]

        # Attempting to submit offer on DRAFT RFQ -> 422
        offer_payload = {"offered_quantity": 100.0, "unit": "kg", "price_per_unit": 4.0}
        offer_resp = client.post(f"{API}/rfqs/{rfq_id}/offers", json=offer_payload, headers=seller_op)
        assert offer_resp.status_code == 422
        assert offer_resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

        # Cancel RFQ
        cancel_resp = client.post(f"{API}/rfqs/{rfq_id}/cancel", headers=buyer_op)
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["data"]["status"] == "cancelled"

        # Attempting to cancel an already cancelled RFQ -> 422
        cancel_again = client.post(f"{API}/rfqs/{rfq_id}/cancel", headers=buyer_op)
        assert cancel_again.status_code == 422

    def test_listing_status_transition_rules(self, client: TestClient):
        seller_org = str(uuid.uuid4())
        seller_facility = str(uuid.uuid4())
        seller_op = _headers(seller_org, role="facility_operator")

        listing_id = _register_lot_and_listing(client, seller_op, seller_facility)

        # ACTIVE -> WITHDRAWN
        withdraw_resp = client.post(
            f"{API}/listings/{listing_id}/status",
            json={"status": "withdrawn"},
            headers=seller_op,
        )
        assert withdraw_resp.status_code == 200
        assert withdraw_resp.json()["data"]["status"] == "withdrawn"

        # WITHDRAWN -> ACTIVE -> Invalid (422)
        invalid_resp = client.post(
            f"{API}/listings/{listing_id}/status",
            json={"status": "active"},
            headers=seller_op,
        )
        assert invalid_resp.status_code == 422
        assert invalid_resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
