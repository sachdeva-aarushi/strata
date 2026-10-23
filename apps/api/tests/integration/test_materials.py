from fastapi.testclient import TestClient


def test_get_material_types(client: TestClient, org_headers: dict):
    """Verifies that the material taxonomy endpoint returns the recognized catalog."""
    response = client.get("/api/v1/materials/types", headers=org_headers)
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert len(body["data"]) > 0

    type_ids = [item["type_id"] for item in body["data"]]
    assert "aluminum-scrap" in type_ids
    assert "spent-isopropanol" in type_ids


def test_create_and_get_material_lot(client: TestClient, org_headers: dict):
    """Verifies end-to-end creation and subsequent retrieval of a material lot."""
    payload = {
        "material_type": "aluminum-scrap",
        "quantity": 1250.5,
        "unit": "kg",
        "facility_id": "fac-00000000-0000-0000-0000-000000000001",
        "availability_from": "2026-11-01",
        "availability_to": "2026-12-01",
        "declared_attributes": {
            "alloy": "6061-T6",
            "physical_form": "stamping_offcuts",
            "oil_contamination_pct": 0.2,
        },
        "provenance_label": "user_supplied",
    }

    # 1. Create lot
    create_resp = client.post("/api/v1/materials/lots", json=payload, headers=org_headers)
    assert create_resp.status_code == 201
    create_body = create_resp.json()
    assert "data" in create_body
    lot_data = create_body["data"]
    lot_id = lot_data["lot_id"]

    assert lot_data["material_type"] == "aluminum-scrap"
    assert lot_data["quantity"] == 1250.5
    assert lot_data["unit"] == "kg"
    assert lot_data["status"] == "draft"
    assert lot_data["org_id"] == org_headers["X-Org-Id"]
    assert lot_data["facility_id"] == payload["facility_id"]
    assert lot_data["declared_attributes"]["alloy"] == "6061-T6"

    # 2. Retrieve lot
    get_resp = client.get(f"/api/v1/materials/lots/{lot_id}", headers=org_headers)
    assert get_resp.status_code == 200
    get_body = get_resp.json()
    assert get_body["data"]["lot_id"] == lot_id
    assert get_body["data"]["quantity"] == 1250.5


def test_list_material_lots_pagination(client: TestClient, org_headers: dict):
    """Verifies listing and pagination for tenant material lots."""
    facility_id = "fac-00000000-0000-0000-0000-000000000002"
    for i in range(3):
        client.post(
            "/api/v1/materials/lots",
            json={
                "material_type": "post-industrial-polypropylene",
                "quantity": 100.0 * (i + 1),
                "unit": "kg",
                "facility_id": facility_id,
                "availability_from": "2026-11-15",
            },
            headers=org_headers,
        )

    response = client.get(
        "/api/v1/materials/lots?page=1&page_size=2",
        headers=org_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "pagination" in body
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["page_size"] == 2
    assert body["pagination"]["total"] >= 3
    assert body["pagination"]["has_next"] is True
    assert len(body["data"]) == 2


def test_get_nonexistent_lot(client: TestClient, org_headers: dict):
    """Verifies 404 response for non-existent material lot IDs."""
    response = client.get(
        "/api/v1/materials/lots/00000000-0000-0000-0000-999999999999",
        headers=org_headers,
    )
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_create_lot_invalid_unit(client: TestClient, org_headers: dict):
    """Verifies that submitting an invalid unit returns validation error with standard envelope."""
    payload = {
        "material_type": "aluminum-scrap",
        "quantity": 50.0,
        "unit": "gallons",
        "facility_id": "fac-1",
        "availability_from": "2026-11-01",
    }
    response = client.post("/api/v1/materials/lots", json=payload, headers=org_headers)
    assert response.status_code in (400, 422)
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_create_lot_unknown_taxonomy_type(client: TestClient, org_headers: dict):
    """Verifies that submitting an unregistered taxonomy type returns validation error."""
    payload = {
        "material_type": "unobtanium-scrap",
        "quantity": 50.0,
        "unit": "kg",
        "facility_id": "fac-1",
        "availability_from": "2026-11-01",
    }
    response = client.post("/api/v1/materials/lots", json=payload, headers=org_headers)
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "Unknown material type" in body["error"]["message"]


def test_multi_tenant_isolation(client: TestClient, org_headers: dict, other_org_headers: dict):
    """Verifies that Tenant B cannot access a material lot created by Tenant A."""
    payload = {
        "material_type": "copper-swarf",
        "quantity": 300.0,
        "unit": "kg",
        "facility_id": "fac-tenant-a",
        "availability_from": "2026-11-01",
    }

    # Tenant A creates the lot
    create_resp = client.post("/api/v1/materials/lots", json=payload, headers=org_headers)
    assert create_resp.status_code == 201
    lot_id = create_resp.json()["data"]["lot_id"]

    # Tenant B attempts to read Tenant A's lot
    get_resp = client.get(f"/api/v1/materials/lots/{lot_id}", headers=other_org_headers)
    assert get_resp.status_code == 404
    assert get_resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
