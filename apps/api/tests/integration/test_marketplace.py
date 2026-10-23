import uuid

import pytest
from fastapi.testclient import TestClient

from strata.api.v1.routers import marketplace as marketplace_router
from strata.domain.marketplace.qualification import ProofPathQualificationClient

API = "/api/v1/marketplace"


def _lot_payload(facility_id: str, **overrides) -> dict:
    data = {
        "material_type": "aluminum-scrap",
        "quantity": 1000.0,
        "unit": "kg",
        "facility_id": facility_id,
        "availability_from": "2026-11-01",
    }
    data.update(overrides)
    return data


def _register_lot(client: TestClient, headers: dict, facility_id: str, **overrides) -> str:
    resp = client.post("/api/v1/materials/lots", json=_lot_payload(facility_id, **overrides), headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["lot_id"]


def _listing_payload(lot_id: str, facility_id: str, **overrides) -> dict:
    data = {
        "material_lot_id": lot_id,
        "facility_id": facility_id,
        "visibility": "public",
        "asking_price_per_unit": 2.5,
        "currency": "USD",
        "available_quantity": 500,
        "unit": "kg",
        "status": "active",
    }
    data.update(overrides)
    return data


def _requirement_payload(facility_id: str, **overrides) -> dict:
    data = {
        "facility_id": facility_id,
        "material_category": "metallics",
        "min_quantity": 100,
        "max_quantity": 800,
        "unit": "kg",
        "target_price_per_unit": 3.0,
        "required_properties": {"alloy": "6061-T6"},
        "prohibited_conditions": ["contaminated_with_pvc"],
        "visibility": "public",
    }
    data.update(overrides)
    return data


def _new_facility() -> str:
    return f"fac-{uuid.uuid4()}"


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------

def test_create_listing_for_own_lot(client: TestClient, org_headers: dict):
    facility = _new_facility()
    lot_id = _register_lot(client, org_headers, facility)

    resp = client.post(f"{API}/listings", json=_listing_payload(lot_id, facility), headers=org_headers)

    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["material_lot_id"] == lot_id
    assert data["organization_id"] == org_headers["X-Org-Id"]
    assert data["status"] == "active"
    assert data["unit"] == "kg"
    assert data["available_quantity"] == 500


def test_create_listing_for_lot_of_another_org_is_not_found(
    client: TestClient, org_headers: dict, other_org_headers: dict
):
    facility = _new_facility()
    lot_id = _register_lot(client, org_headers, facility)

    resp = client.post(
        f"{API}/listings",
        json=_listing_payload(lot_id, facility),
        headers=other_org_headers,
    )

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_listing_with_wrong_facility_is_rejected(client: TestClient, org_headers: dict):
    facility = _new_facility()
    lot_id = _register_lot(client, org_headers, facility)

    resp = client.post(
        f"{API}/listings",
        json=_listing_payload(lot_id, _new_facility()),
        headers=org_headers,
    )

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_listing_with_mismatched_unit_is_rejected(client: TestClient, org_headers: dict):
    facility = _new_facility()
    lot_id = _register_lot(client, org_headers, facility)

    resp = client.post(
        f"{API}/listings",
        json=_listing_payload(lot_id, facility, unit="tonne"),
        headers=org_headers,
    )

    assert resp.status_code == 400


def test_listing_quantity_above_lot_quantity_is_rejected(client: TestClient, org_headers: dict):
    facility = _new_facility()
    lot_id = _register_lot(client, org_headers, facility, quantity=100)

    resp = client.post(
        f"{API}/listings",
        json=_listing_payload(lot_id, facility, available_quantity=101),
        headers=org_headers,
    )

    assert resp.status_code == 400


def test_get_listing_is_tenant_scoped(client: TestClient, org_headers: dict, other_org_headers: dict):
    facility = _new_facility()
    lot_id = _register_lot(client, org_headers, facility)
    created = client.post(f"{API}/listings", json=_listing_payload(lot_id, facility), headers=org_headers)
    listing_id = created.json()["data"]["id"]

    own = client.get(f"{API}/listings/{listing_id}", headers=org_headers)
    other = client.get(f"{API}/listings/{listing_id}", headers=other_org_headers)

    assert own.status_code == 200
    assert other.status_code == 404


def test_list_own_listings_is_paginated(client: TestClient, org_headers: dict):
    facility = _new_facility()
    lot_id = _register_lot(client, org_headers, facility)
    for _ in range(3):
        client.post(f"{API}/listings", json=_listing_payload(lot_id, facility), headers=org_headers)

    resp = client.get(f"{API}/listings?page=1&page_size=2", headers=org_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["pagination"]["total"] >= 3
    assert body["pagination"]["has_next"] is True


# ---------------------------------------------------------------------------
# Buyer requirements
# ---------------------------------------------------------------------------

def test_create_and_get_buyer_requirement(client: TestClient, org_headers: dict):
    resp = client.post(f"{API}/buyer-requirements", json=_requirement_payload(_new_facility()), headers=org_headers)

    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["organization_id"] == org_headers["X-Org-Id"]
    assert data["required_properties"] == {"alloy": "6061-T6"}

    get_resp = client.get(f"{API}/buyer-requirements/{data['id']}", headers=org_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["id"] == data["id"]


def test_requirement_with_unknown_category_is_rejected(client: TestClient, org_headers: dict):
    resp = client.post(
        f"{API}/buyer-requirements",
        json=_requirement_payload(_new_facility(), material_category="unobtainium"),
        headers=org_headers,
    )
    assert resp.status_code == 400


def test_requirement_max_below_min_is_rejected(client: TestClient, org_headers: dict):
    resp = client.post(
        f"{API}/buyer-requirements",
        json=_requirement_payload(_new_facility(), min_quantity=500, max_quantity=100),
        headers=org_headers,
    )
    assert resp.status_code == 422


def test_requirement_is_tenant_scoped(client: TestClient, org_headers: dict, other_org_headers: dict):
    created = client.post(
        f"{API}/buyer-requirements", json=_requirement_payload(_new_facility()), headers=org_headers
    ).json()["data"]

    resp = client.get(f"{API}/buyer-requirements/{created['id']}", headers=other_org_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Candidate matching
# ---------------------------------------------------------------------------

def test_candidates_include_other_org_active_public_listing_only(
    client: TestClient, org_headers: dict, other_org_headers: dict
):
    # Supplier (org A) publishes four listings of metallic material.
    supplier_fac = _new_facility()
    lot_id = _register_lot(client, org_headers, supplier_fac)

    def publish(**overrides) -> str:
        resp = client.post(
            f"{API}/listings",
            json=_listing_payload(lot_id, supplier_fac, **overrides),
            headers=org_headers,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()["data"]["id"]

    matching = publish()
    excluded = [
        publish(status="draft"),
        publish(visibility="private"),
        publish(available_quantity=50),
    ]

    # Buyer (org B) requires at least 100 kg of metallics.
    req = client.post(
        f"{API}/buyer-requirements",
        json=_requirement_payload(_new_facility()),
        headers=other_org_headers,
    ).json()["data"]

    resp = client.get(f"{API}/buyer-requirements/{req['id']}/candidates", headers=other_org_headers)

    assert resp.status_code == 200, resp.text
    ids = [c["id"] for c in resp.json()["data"]]
    assert matching in ids
    for listing_id in excluded:
        assert listing_id not in ids


def test_candidates_exclude_own_organization_listings(client: TestClient, org_headers: dict):
    facility = _new_facility()
    lot_id = _register_lot(client, org_headers, facility)
    client.post(f"{API}/listings", json=_listing_payload(lot_id, facility), headers=org_headers)

    req = client.post(
        f"{API}/buyer-requirements", json=_requirement_payload(_new_facility()), headers=org_headers
    ).json()["data"]

    resp = client.get(f"{API}/buyer-requirements/{req['id']}/candidates", headers=org_headers)

    assert resp.status_code == 200
    assert all(c["organization_id"] != org_headers["X-Org-Id"] for c in resp.json()["data"])


def test_candidates_for_unknown_requirement_return_404(client: TestClient, org_headers: dict):
    resp = client.get(f"{API}/buyer-requirements/{uuid.uuid4()}/candidates", headers=org_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Qualification endpoint (ProofPath client forced to mock_only: no network)
# ---------------------------------------------------------------------------

def test_qualifications_endpoint_returns_pending_mock_results(
    client: TestClient, org_headers: dict, other_org_headers: dict, monkeypatch
):
    monkeypatch.setattr(
        marketplace_router,
        "ProofPathQualificationClient",
        lambda: ProofPathQualificationClient(mock_only=True),
    )

    supplier_fac = _new_facility()
    lot_id = _register_lot(client, org_headers, supplier_fac)
    client.post(f"{API}/listings", json=_listing_payload(lot_id, supplier_fac), headers=org_headers)

    req = client.post(
        f"{API}/buyer-requirements", json=_requirement_payload(_new_facility()), headers=other_org_headers
    ).json()["data"]

    resp = client.get(f"{API}/buyer-requirements/{req['id']}/qualifications", headers=other_org_headers)

    assert resp.status_code == 200, resp.text
    results = resp.json()["data"]
    assert len(results) >= 1
    mine = [r for r in results if r["material_lot_id"] == lot_id]
    assert len(mine) == 1
    assert mine[0]["source"] == "mock"
    assert mine[0]["status"] == "pending"
    assert mine[0]["requirement_id"] == req["id"]


def test_qualifications_endpoint_returns_502_when_proofpath_down_and_no_fallback(
    client: TestClient, org_headers: dict, other_org_headers: dict, monkeypatch
):
    import httpx

    def refuse_connection(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("ProofPath is down")

    def failing_transport_client():
        return ProofPathQualificationClient(
            base_url="http://proofpath.test",
            mock_fallback=False,
            transport=httpx.MockTransport(refuse_connection),
        )

    monkeypatch.setattr(marketplace_router, "ProofPathQualificationClient", failing_transport_client)

    supplier_fac = _new_facility()
    lot_id = _register_lot(client, org_headers, supplier_fac)
    client.post(f"{API}/listings", json=_listing_payload(lot_id, supplier_fac), headers=org_headers)
    req = client.post(
        f"{API}/buyer-requirements", json=_requirement_payload(_new_facility()), headers=other_org_headers
    ).json()["data"]

    resp = client.get(f"{API}/buyer-requirements/{req['id']}/qualifications", headers=other_org_headers)

    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "QUALIFICATION_SERVICE_UNAVAILABLE"
