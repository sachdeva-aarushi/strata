from fastapi.testclient import TestClient


def _create_test_lot(client: TestClient, org_headers: dict, material_type: str, attrs: dict, quantity: float = 2000.0) -> str:
    """Helper to create a material lot for qualification testing."""
    payload = {
        "material_type": material_type,
        "quantity": quantity,
        "unit": "kg",
        "facility_id": "fac-00000000-0000-0000-0000-000000000001",
        "availability_from": "2026-11-01",
        "availability_to": "2026-12-01",
        "declared_attributes": attrs,
        "provenance_label": "user_supplied",
    }
    resp = client.post("/api/v1/materials/lots", json=payload, headers=org_headers)
    assert resp.status_code == 201
    return resp.json()["data"]["lot_id"]


def test_evidence_registration_and_retrieval(client: TestClient, org_headers: dict):
    """
    Verifies registering evidence records with source reference, timestamps,
    supporting content, extraction method, provenance, and verification state.
    """
    lot_id = _create_test_lot(
        client,
        org_headers,
        material_type="aluminum-scrap",
        attrs={"alloy": "6061-T6"},
    )

    evidence_payload = {
        "lot_id": lot_id,
        "claim_subject": "moisture_level",
        "claim_text": "Moisture assay shows 0.02% water content.",
        "source_url": "https://lab.testing.org/cert/CERT-1092",
        "source_title": "Certified ASTM Moisture Assay",
        "source_type": "lab_report",
        "extraction_method": "lab_test",
        "provenance": "independently_verified",
        "verification_state": "verified",
        "supporting_passage": "Karl Fischer titration confirmed moisture at 0.02% by weight.",
        "content_hash": "sha256-112233445566778899aabbccddeeff00",
        "document_ref": "DOC-LAB-1092.pdf",
        "verified_by": "Dr. E. Vance, Lead Chemist",
    }

    # 1. Post evidence record
    post_resp = client.post("/api/v1/evidence", json=evidence_payload, headers=org_headers)
    assert post_resp.status_code == 201
    created_ev = post_resp.json()["data"]
    assert created_ev["evidence_id"] is not None
    assert created_ev["lot_id"] == lot_id
    assert created_ev["claim_subject"] == "moisture_level"
    assert created_ev["extraction_method"] == "lab_test"
    assert created_ev["provenance"] == "independently_verified"
    assert created_ev["verification_state"] == "verified"
    assert created_ev["retrieved_at"] is not None

    # 2. List evidence for lot
    list_resp = client.get(f"/api/v1/lots/{lot_id}/evidence", headers=org_headers)
    assert list_resp.status_code == 200
    evidence_list = list_resp.json()["data"]
    assert len(evidence_list) == 1
    assert evidence_list[0]["evidence_id"] == created_ev["evidence_id"]


def test_investigation_supported_outcome(client: TestClient, org_headers: dict):
    """
    Verifies that a lot satisfying all candidate route gates and possessing
    verified facts produces a completed investigation with a 'supported' route assessment.
    """
    lot_id = _create_test_lot(
        client,
        org_headers,
        material_type="aluminum-scrap",
        attrs={
            "is_hazardous": False,
            "oil_contamination_pct": 0.3,
            "contaminants": [],
            "alloy_series": "6061",
        },
        quantity=3000.0,
    )

    # Attach verified moisture evidence
    client.post(
        "/api/v1/evidence",
        json={
            "lot_id": lot_id,
            "claim_subject": "moisture_level",
            "claim_text": "moisture_level dry assay 0.01%",
            "source_url": "https://lab.testing.org/cert/101",
            "source_type": "lab_report",
            "extraction_method": "lab_test",
            "provenance": "independently_verified",
            "verification_state": "verified",
        },
        headers=org_headers,
    )

    # Run investigation
    inv_payload = {
        "lot_id": lot_id,
        "candidate_route_ids": ["route-secondary-aluminum-smelter"],
        "notes": "Testing high-purity aluminum scrap circularity path",
    }
    resp = client.post("/api/v1/investigations", json=inv_payload, headers=org_headers)
    assert resp.status_code == 201
    body = resp.json()["data"]

    # Verify execution state vs qualification outcome separation
    assert body["status"] == "completed"
    assert len(body["assessments"]) == 1

    assessment = body["assessments"][0]
    assert assessment["candidate_route_id"] == "route-secondary-aluminum-smelter"
    assert assessment["status"] == "supported"
    assert len(assessment["blocking_conditions"]) == 0
    assert len(assessment["missing_facts"]) == 0
    assert assessment["rule_version"] == "1.0.0"
    assert len(assessment["evidence_refs"]) >= 1

    # Fetch investigation by ID
    inv_id = body["investigation_id"]
    get_resp = client.get(f"/api/v1/investigations/{inv_id}", headers=org_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["investigation_id"] == inv_id


def test_investigation_hard_incompatibility_unsupported(client: TestClient, org_headers: dict):
    """
    Verifies that a hard gate failure produces 'unsupported' with explicit blocking conditions.
    """
    lot_id = _create_test_lot(
        client,
        org_headers,
        material_type="aluminum-scrap",
        attrs={
            "is_hazardous": False,
            "oil_contamination_pct": 3.5,  # Exceeds max 1.5%
            "contaminants": ["lead"],      # Prohibited contaminant
            "alloy_series": "6061",
        },
        quantity=2000.0,
    )

    inv_payload = {
        "lot_id": lot_id,
        "candidate_route_ids": ["route-secondary-aluminum-smelter"],
    }
    resp = client.post("/api/v1/investigations", json=inv_payload, headers=org_headers)
    assert resp.status_code == 201
    body = resp.json()["data"]

    assert body["status"] == "completed"
    assessment = body["assessments"][0]
    assert assessment["status"] == "unsupported"
    assert len(assessment["blocking_conditions"]) >= 2
    assert any("oil" in cond.lower() for cond in assessment["blocking_conditions"])
    assert any("lead" in cond.lower() or "prohibited" in cond.lower() for cond in assessment["blocking_conditions"])


def test_investigation_missing_critical_facts_conditional(client: TestClient, org_headers: dict):
    """
    Verifies that missing critical facts produce 'conditional' outcome.
    """
    lot_id = _create_test_lot(
        client,
        org_headers,
        material_type="aluminum-scrap",
        attrs={
            "is_hazardous": False,
            "oil_contamination_pct": 0.4,
            "contaminants": [],
            # Missing alloy_series and moisture test
        },
        quantity=1500.0,
    )

    resp = client.post(
        "/api/v1/investigations",
        json={"lot_id": lot_id, "candidate_route_ids": ["route-secondary-aluminum-smelter"]},
        headers=org_headers,
    )
    assert resp.status_code == 201
    body = resp.json()["data"]

    assessment = body["assessments"][0]
    assert assessment["status"] == "conditional"
    assert len(assessment["blocking_conditions"]) == 0
    assert len(assessment["missing_facts"]) >= 2
    missing_ids = [f["fact_id"] for f in assessment["missing_facts"]]
    assert "fact-alloy-series" in missing_ids
    assert "fact-moisture-level" in missing_ids


def test_get_lot_qualification_routes(client: TestClient, org_headers: dict):
    """
    Verifies GET /api/v1/lots/{lot_id}/routes returns all evaluated candidate routes for the lot.
    """
    lot_id = _create_test_lot(
        client,
        org_headers,
        material_type="aluminum-scrap",
        attrs={"is_hazardous": False},
        quantity=1000.0,
    )

    # Run investigation
    client.post(
        "/api/v1/investigations",
        json={"lot_id": lot_id, "candidate_route_ids": ["route-secondary-aluminum-smelter"]},
        headers=org_headers,
    )

    # Query routes
    routes_resp = client.get(f"/api/v1/lots/{lot_id}/routes", headers=org_headers)
    assert routes_resp.status_code == 200
    assessments = routes_resp.json()["data"]
    assert len(assessments) >= 1
    assert assessments[0]["candidate_route_id"] == "route-secondary-aluminum-smelter"
    assert assessments[0]["lot_id"] == lot_id


def test_investigation_tenant_isolation(client: TestClient, org_headers: dict, other_org_headers: dict):
    """
    Verifies that an investigation cannot be launched or viewed across tenant organization boundaries.
    """
    lot_id = _create_test_lot(
        client,
        org_headers,
        material_type="aluminum-scrap",
        attrs={"is_hazardous": False},
    )

    # Attempt to run investigation using other org's credentials
    resp = client.post(
        "/api/v1/investigations",
        json={"lot_id": lot_id},
        headers=other_org_headers,
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["error"]["message"].lower()
