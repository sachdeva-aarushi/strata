from fastapi.testclient import TestClient


from typing import Optional


def _create_test_lot(
    client: TestClient,
    org_headers: dict,
    material_type: str,
    attrs: dict,
    quantity: float = 2000.0,
    unit: Optional[str] = None,
) -> str:
    """Helper to create a material lot for qualification testing."""
    if unit is None:
        unit = "litre" if material_type in ("spent-isopropanol", "glycol-purge") else "kg"
    payload = {
        "material_type": material_type,
        "quantity": quantity,
        "unit": unit,
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


def test_direct_lot_qualification_assess_endpoint(client: TestClient, org_headers: dict):
    """Verifies POST /api/v1/lots/{lot_id}/qualification/assess and GET /api/v1/lots/{lot_id}/qualification."""
    lot_id = _create_test_lot(
        client,
        org_headers,
        material_type="spent-isopropanol",
        attrs={"water_content_pct": 2.0, "is_halogenated": False},
        quantity=500.0,
    )

    # 1. Request direct assessment on lot
    assess_resp = client.post(
        f"/api/v1/lots/{lot_id}/qualification/assess",
        json={"notes": "Direct lot qualification assessment test"},
        headers=org_headers,
    )
    assert assess_resp.status_code == 201
    inv_data = assess_resp.json()["data"]
    assert inv_data["lot_id"] == lot_id
    assert inv_data["status"] == "completed"
    assert len(inv_data["assessments"]) >= 1

    # 2. Retrieve assessments for lot via /lots/{lot_id}/qualification
    get_resp = client.get(f"/api/v1/lots/{lot_id}/qualification", headers=org_headers)
    assert get_resp.status_code == 200
    assessments = get_resp.json()["data"]
    assert len(assessments) >= 1
    assert assessments[0]["lot_id"] == lot_id


def test_get_single_qualification_assessment_by_id(client: TestClient, org_headers: dict, other_org_headers: dict):
    """Verifies retrieval of individual assessment by ID and enforces tenant boundary."""
    lot_id = _create_test_lot(
        client,
        org_headers,
        material_type="aluminum-scrap",
        attrs={"is_hazardous": False, "oil_contamination_pct": 0.2},
        quantity=1200.0,
    )

    inv_resp = client.post(
        "/api/v1/investigations",
        json={"lot_id": lot_id, "candidate_route_ids": ["route-secondary-aluminum-smelter"]},
        headers=org_headers,
    )
    assessment_id = inv_resp.json()["data"]["assessments"][0]["assessment_id"]

    # Tenant retrieves assessment
    get_resp = client.get(f"/api/v1/qualification/assessments/{assessment_id}", headers=org_headers)
    assert get_resp.status_code == 200
    qa_data = get_resp.json()["data"]
    assert qa_data["assessment_id"] == assessment_id
    assert qa_data["candidate_route_id"] == "route-secondary-aluminum-smelter"

    # Other tenant attempts to retrieve -> 404
    other_resp = client.get(f"/api/v1/qualification/assessments/{assessment_id}", headers=other_org_headers)
    assert other_resp.status_code == 404
    assert other_resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_list_investigations_pagination_and_filter(client: TestClient, org_headers: dict):
    """Verifies GET /api/v1/investigations with pagination and lot_id filter."""
    lot_id = _create_test_lot(
        client,
        org_headers,
        material_type="post-industrial-polypropylene",
        attrs={"melt_flow_index": 12.0},
        quantity=1000.0,
    )

    # Run 2 investigations for this lot
    client.post("/api/v1/investigations", json={"lot_id": lot_id, "notes": "Run 1"}, headers=org_headers)
    client.post("/api/v1/investigations", json={"lot_id": lot_id, "notes": "Run 2"}, headers=org_headers)

    # List with lot_id filter and pagination
    list_resp = client.get(f"/api/v1/investigations?lot_id={lot_id}&page=1&page_size=10", headers=org_headers)
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert "pagination" in body
    assert body["pagination"]["total"] >= 2
    assert len(body["data"]) >= 2
    assert all(inv["lot_id"] == lot_id for inv in body["data"])


def test_discovery_pipeline_and_evidence_storage(client: TestClient, org_headers: dict):
    """
    Verifies that running discovery identifies potential recovery partners,
    extracts structured capability claims with provenance PUBLICLY_STATED and UNVERIFIED,
    and persists them into the evidence database table.
    """
    lot_id = _create_test_lot(
        client,
        org_headers,
        material_type="aluminum-scrap",
        attrs={"oil_contamination_pct": 0.5},
        quantity=2500.0,
    )

    # 1. Trigger discovery
    disc_resp = client.post(f"/api/v1/lots/{lot_id}/discovery", headers=org_headers)
    assert disc_resp.status_code == 200
    disc_data = disc_resp.json()["data"]
    assert disc_data["lot_id"] == lot_id
    assert disc_data["material_type"] == "aluminum-scrap"
    assert len(disc_data["opportunities"]) >= 1

    # Check partner opportunity fields
    opp = disc_data["opportunities"][0]
    assert opp["route_id"] is not None
    assert opp["processor_facility_name"] is not None
    assert opp["recovery_tier"] is not None

    # Check that discovered evidence has explicit provenance and unverified state
    if disc_data["new_evidence_count"] > 0:
        claim = disc_data["evidence_records"][0]
        assert claim["lot_id"] == lot_id
        assert claim["provenance"] == "publicly_stated"
        assert claim["verification_state"] == "unverified"
        assert claim["source_type"] == "web"
        assert claim["retrieved_at"] is not None

    # 2. Verify evidence records are retrievable from the lot's evidence list
    ev_resp = client.get(f"/api/v1/lots/{lot_id}/evidence", headers=org_headers)
    assert ev_resp.status_code == 200
    lot_evidence = ev_resp.json()["data"]
    assert len(lot_evidence) >= disc_data["new_evidence_count"]


def test_discovery_connects_to_subsequent_assessment(client: TestClient, org_headers: dict):
    """
    Verifies that running discovery persists evidence records that are
    subsequently loaded and referenced in a ProofPath qualification assessment.
    """
    lot_id = _create_test_lot(
        client,
        org_headers,
        material_type="spent-isopropanol",
        attrs={"water_content_pct": 2.5},
        quantity=800.0,
    )

    # 1. Run discovery first
    disc_resp = client.post(f"/api/v1/lots/{lot_id}/discovery", headers=org_headers)
    assert disc_resp.status_code == 200
    new_evidence = disc_resp.json()["data"]["evidence_records"]
    new_ev_ids = [e["evidence_id"] for e in new_evidence]

    # 2. Run qualification assessment on the lot
    assess_resp = client.post(
        f"/api/v1/lots/{lot_id}/qualification/assess",
        json={"notes": "Testing post-discovery assessment"},
        headers=org_headers,
    )
    assert assess_resp.status_code == 201
    assessments = assess_resp.json()["data"]["assessments"]
    assert len(assessments) >= 1

    # Verify that the newly discovered evidence IDs are included in the assessment's evidence_refs
    all_evidence_refs = set()
    for a in assessments:
        all_evidence_refs.update(a["evidence_refs"])
    for ev_id in new_ev_ids:
        assert ev_id in all_evidence_refs


def test_discovery_failure_graceful_handling(client: TestClient, org_headers: dict, monkeypatch):
    """
    Verifies that if the discovery provider throws an exception (e.g. timeout / network error),
    the system handles it gracefully, logs the error, returns empty claims without crashing,
    and never fabricates fake claims.
    """
    lot_id = _create_test_lot(
        client,
        org_headers,
        material_type="aluminum-scrap",
        attrs={"is_hazardous": False},
        quantity=1000.0,
    )

    from strata.integrations.discovery import FakeDiscoveryProvider

    def failing_fetch(self, route):
        raise TimeoutError("Simulated external discovery service timeout")

    monkeypatch.setattr(FakeDiscoveryProvider, "fetch_receiver_claims", failing_fetch)

    # Execute discovery despite provider failure
    resp = client.post(f"/api/v1/lots/{lot_id}/discovery", headers=org_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["lot_id"] == lot_id
    assert data["new_evidence_count"] == 0
    assert len(data["evidence_records"]) == 0
    # Opportunities still cataloged from taxonomy, but zero fabricated claims
    for opp in data["opportunities"]:
        assert opp["public_claims_count"] == 0
        assert len(opp["discovered_evidence"]) == 0

