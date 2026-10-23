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


def test_create_lot_invalid_quantity(client: TestClient, org_headers: dict):
    """Verifies that non-positive quantities are rejected."""
    payload = {
        "material_type": "aluminum-scrap",
        "quantity": -10.0,
        "unit": "kg",
        "facility_id": "fac-1",
        "availability_from": "2026-11-01",
    }
    response = client.post("/api/v1/materials/lots", json=payload, headers=org_headers)
    assert response.status_code in (400, 422)
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_lot_invalid_date_window(client: TestClient, org_headers: dict):
    """Verifies that availability_to earlier than availability_from is rejected."""
    payload = {
        "material_type": "aluminum-scrap",
        "quantity": 100.0,
        "unit": "kg",
        "facility_id": "fac-1",
        "availability_from": "2026-12-01",
        "availability_to": "2026-11-01",
    }
    response = client.post("/api/v1/materials/lots", json=payload, headers=org_headers)
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "earlier than" in body["error"]["message"]


def test_update_material_lot_success(client: TestClient, org_headers: dict):
    """Verifies updating permitted mutable fields on an existing material lot."""
    # 1. Create lot
    create_resp = client.post(
        "/api/v1/materials/lots",
        json={
            "material_type": "spent-isopropanol",
            "quantity": 500.0,
            "unit": "litre",
            "facility_id": "fac-upd-1",
            "availability_from": "2026-11-01",
            "declared_attributes": {"purity_pct": 85.0},
        },
        headers=org_headers,
    )
    assert create_resp.status_code == 201
    created_lot = create_resp.json()["data"]
    lot_id = created_lot["lot_id"]
    initial_created_at = created_lot["created_at"]

    # 2. Update quantity, unit, status, and declared_attributes
    update_payload = {
        "quantity": 750.0,
        "status": "available",
        "declared_attributes": {"purity_pct": 88.5, "water_content_pct": 11.5},
    }
    update_resp = client.patch(f"/api/v1/materials/lots/{lot_id}", json=update_payload, headers=org_headers)
    assert update_resp.status_code == 200
    updated_lot = update_resp.json()["data"]

    assert updated_lot["lot_id"] == lot_id
    assert updated_lot["quantity"] == 750.0
    assert updated_lot["status"] == "available"
    assert updated_lot["declared_attributes"]["purity_pct"] == 88.5
    assert updated_lot["declared_attributes"]["water_content_pct"] == 11.5
    assert updated_lot["created_at"] == initial_created_at


def test_update_material_lot_immutability(client: TestClient, org_headers: dict, other_org_headers: dict):
    """Verifies that lot_id, org_id, and facility_id cannot be overwritten through updates."""
    create_resp = client.post(
        "/api/v1/materials/lots",
        json={
            "material_type": "post-industrial-polypropylene",
            "quantity": 250.0,
            "unit": "kg",
            "facility_id": "fac-orig",
            "availability_from": "2026-11-01",
        },
        headers=org_headers,
    )
    lot_id = create_resp.json()["data"]["lot_id"]

    # Attempt to tamper with org_id and lot_id via update
    patch_resp = client.patch(
        f"/api/v1/materials/lots/{lot_id}",
        json={
            "quantity": 300.0,
            "lot_id": "tampered-lot-id",
            "org_id": other_org_headers["X-Org-Id"],
            "facility_id": "tampered-fac",
        },
        headers=org_headers,
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()["data"]
    assert data["lot_id"] == lot_id
    assert data["org_id"] == org_headers["X-Org-Id"]
    assert data["facility_id"] == "fac-orig"


def test_update_material_lot_invalid_unit(client: TestClient, org_headers: dict):
    """Verifies that updating to an incompatible unit returns validation error."""
    create_resp = client.post(
        "/api/v1/materials/lots",
        json={
            "material_type": "aluminum-scrap",
            "quantity": 100.0,
            "unit": "kg",
            "facility_id": "fac-1",
            "availability_from": "2026-11-01",
        },
        headers=org_headers,
    )
    lot_id = create_resp.json()["data"]["lot_id"]

    # Aluminum scrap does not support litres
    patch_resp = client.patch(
        f"/api/v1/materials/lots/{lot_id}",
        json={"unit": "litre"},
        headers=org_headers,
    )
    assert patch_resp.status_code == 400
    assert patch_resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_update_material_lot_invalid_dates(client: TestClient, org_headers: dict):
    """Verifies that updating to an invalid temporal window returns validation error."""
    create_resp = client.post(
        "/api/v1/materials/lots",
        json={
            "material_type": "aluminum-scrap",
            "quantity": 100.0,
            "unit": "kg",
            "facility_id": "fac-1",
            "availability_from": "2026-11-10",
            "availability_to": "2026-11-20",
        },
        headers=org_headers,
    )
    lot_id = create_resp.json()["data"]["lot_id"]

    patch_resp = client.patch(
        f"/api/v1/materials/lots/{lot_id}",
        json={"availability_to": "2026-11-05"},
        headers=org_headers,
    )
    assert patch_resp.status_code == 400
    assert patch_resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_update_nonexistent_lot(client: TestClient, org_headers: dict):
    """Verifies 404 when updating non-existent material lot."""
    patch_resp = client.patch(
        "/api/v1/materials/lots/00000000-0000-0000-0000-999999999999",
        json={"quantity": 100.0},
        headers=org_headers,
    )
    assert patch_resp.status_code == 404
    assert patch_resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_create_and_list_lot_evidence(client: TestClient, org_headers: dict):
    """Verifies creating an evidence record linked directly to a material lot."""
    # 1. Create lot
    create_resp = client.post(
        "/api/v1/materials/lots",
        json={
            "material_type": "copper-swarf",
            "quantity": 400.0,
            "unit": "kg",
            "facility_id": "fac-ev-1",
            "availability_from": "2026-11-01",
        },
        headers=org_headers,
    )
    lot_id = create_resp.json()["data"]["lot_id"]

    # 2. Add evidence via POST /materials/lots/{lot_id}/evidence
    ev_payload = {
        "claim_subject": "composition",
        "claim_text": "Copper content is 99.2% pure electrolytic copper.",
        "source_title": "Internal Mill Spec Sheet",
        "source_type": "lab_report",
        "extraction_method": "lab_test",
        "provenance": "user_reported",
        "verification_state": "unverified",
    }
    ev_resp = client.post(f"/api/v1/materials/lots/{lot_id}/evidence", json=ev_payload, headers=org_headers)
    assert ev_resp.status_code == 201
    ev_data = ev_resp.json()["data"]
    assert ev_data["lot_id"] == lot_id
    assert ev_data["claim_subject"] == "composition"
    assert ev_data["provenance"] == "user_reported"
    assert ev_data["verification_state"] == "unverified"
    ev_id = ev_data["evidence_id"]

    # 3. Retrieve evidence via GET /materials/lots/{lot_id}/evidence
    list_ev_resp = client.get(f"/api/v1/materials/lots/{lot_id}/evidence", headers=org_headers)
    assert list_ev_resp.status_code == 200
    ev_list = list_ev_resp.json()["data"]
    assert len(ev_list) >= 1
    assert any(e["evidence_id"] == ev_id for e in ev_list)

    # 4. Verify lot read returns the evidence ID
    lot_resp = client.get(f"/api/v1/materials/lots/{lot_id}", headers=org_headers)
    assert ev_id in lot_resp.json()["data"]["evidence_ids"]


def test_attach_existing_evidence_to_lot(client: TestClient, org_headers: dict):
    """Verifies associating an existing evidence record with a lot via attach endpoint."""
    # 1. Create unattached evidence record via qualification endpoint
    ev_create_resp = client.post(
        "/api/v1/evidence",
        json={
            "claim_subject": "sds",
            "claim_text": "SDS confirms non-hazardous flashpoint > 60C.",
            "source_type": "sds",
            "provenance": "user_supplied",
            "verification_state": "unverified",
        },
        headers=org_headers,
    )
    assert ev_create_resp.status_code == 201
    evidence_id = ev_create_resp.json()["data"]["evidence_id"]

    # 2. Create lot
    lot_resp = client.post(
        "/api/v1/materials/lots",
        json={
            "material_type": "spent-isopropanol",
            "quantity": 200.0,
            "unit": "litre",
            "facility_id": "fac-ev-2",
            "availability_from": "2026-11-01",
        },
        headers=org_headers,
    )
    lot_id = lot_resp.json()["data"]["lot_id"]

    # 3. Attach evidence to lot
    attach_resp = client.post(
        f"/api/v1/materials/lots/{lot_id}/evidence/attach",
        json={"evidence_ids": [evidence_id]},
        headers=org_headers,
    )
    assert attach_resp.status_code == 200
    assert evidence_id in attach_resp.json()["data"]["evidence_ids"]

    # 4. Verify evidence record retains unverified state (NOT elevated merely by attachment)
    evidence_list_resp = client.get(f"/api/v1/materials/lots/{lot_id}/evidence", headers=org_headers)
    attached_ev = next(e for e in evidence_list_resp.json()["data"] if e["evidence_id"] == evidence_id)
    assert attached_ev["verification_state"] == "unverified"
    assert attached_ev["provenance"] == "user_supplied"


def test_cross_tenant_evidence_isolation(client: TestClient, org_headers: dict, other_org_headers: dict):
    """Verifies Tenant B cannot attach or view Tenant A's evidence."""
    # Tenant A creates evidence
    ev_resp = client.post(
        "/api/v1/evidence",
        json={
            "claim_subject": "moisture",
            "claim_text": "Moisture content 4.2%",
            "source_type": "lab_report",
            "provenance": "user_reported",
        },
        headers=org_headers,
    )
    tenant_a_evidence_id = ev_resp.json()["data"]["evidence_id"]

    # Tenant B creates lot
    lot_resp = client.post(
        "/api/v1/materials/lots",
        json={
            "material_type": "aluminum-scrap",
            "quantity": 100.0,
            "unit": "kg",
            "facility_id": "fac-b",
            "availability_from": "2026-11-01",
        },
        headers=other_org_headers,
    )
    tenant_b_lot_id = lot_resp.json()["data"]["lot_id"]

    # Tenant B attempts to attach Tenant A's evidence -> 404
    attach_resp = client.post(
        f"/api/v1/materials/lots/{tenant_b_lot_id}/evidence/attach",
        json={"evidence_ids": [tenant_a_evidence_id]},
        headers=other_org_headers,
    )
    assert attach_resp.status_code == 404
    assert attach_resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_attach_nonexistent_evidence_returns_404(client: TestClient, org_headers: dict):
    """Verifies 404 when attempting to attach a non-existent evidence ID."""
    lot_resp = client.post(
        "/api/v1/materials/lots",
        json={
            "material_type": "aluminum-scrap",
            "quantity": 100.0,
            "unit": "kg",
            "facility_id": "fac-1",
            "availability_from": "2026-11-01",
        },
        headers=org_headers,
    )
    lot_id = lot_resp.json()["data"]["lot_id"]

    attach_resp = client.post(
        f"/api/v1/materials/lots/{lot_id}/evidence/attach",
        json={"evidence_ids": ["00000000-0000-0000-0000-888888888888"]},
        headers=org_headers,
    )
    assert attach_resp.status_code == 404
    assert attach_resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_list_material_lots_filters(client: TestClient, org_headers: dict):
    """Verifies filtering material lots by status, material_type, and facility_id."""
    fac_a = "fac-filt-a"
    fac_b = "fac-filt-b"

    client.post(
        "/api/v1/materials/lots",
        json={
            "material_type": "aluminum-scrap",
            "quantity": 100.0,
            "unit": "kg",
            "status": "available",
            "facility_id": fac_a,
            "availability_from": "2026-11-01",
        },
        headers=org_headers,
    )
    client.post(
        "/api/v1/materials/lots",
        json={
            "material_type": "spent-isopropanol",
            "quantity": 50.0,
            "unit": "litre",
            "status": "draft",
            "facility_id": fac_b,
            "availability_from": "2026-11-01",
        },
        headers=org_headers,
    )

    # Filter by material_type
    resp_type = client.get("/api/v1/materials/lots?material_type=spent-isopropanol", headers=org_headers)
    assert resp_type.status_code == 200
    for item in resp_type.json()["data"]:
        assert item["material_type"] == "spent-isopropanol"

    # Filter by status
    resp_status = client.get("/api/v1/materials/lots?status=available", headers=org_headers)
    assert resp_status.status_code == 200
    for item in resp_status.json()["data"]:
        assert item["status"] == "available"

    # Filter by facility_id
    resp_fac = client.get(f"/api/v1/materials/lots?facility_id={fac_a}", headers=org_headers)
    assert resp_fac.status_code == 200
    for item in resp_fac.json()["data"]:
        assert item["facility_id"] == fac_a

