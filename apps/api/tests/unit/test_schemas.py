from datetime import date, datetime, timezone
import pytest
from pydantic import ValidationError

from strata.schemas.common import (
    ErrorDetail,
    ErrorEnvelope,
    MetaInfo,
    PaginatedResponseEnvelope,
    PaginationInfo,
    ResponseEnvelope,
)
from strata.schemas.evidence import (
    EvidenceRecordCreate,
    EvidenceRecordRead,
    EvidenceStatus,
)
from strata.schemas.impact import (
    ImpactCalculationRead,
    ImpactStage,
)
from strata.schemas.marketplace import (
    ExchangeListingRead,
    ListingStatus,
    OfferRead,
    RFQRead,
    RFQStatus,
)
from strata.schemas.materials import (
    MaterialLotCreate,
    MaterialLotRead,
    MaterialLotStatus,
)
from strata.schemas.organization import (
    FacilityRef,
    OrganizationRef,
)
from strata.schemas.qualification import (
    AssessmentStatus,
    HardGateResult,
    MissingFact,
    QualificationAssessmentRead,
)
from strata.schemas.workflow import (
    WorkflowEventCreate,
    WorkflowEventRead,
    WorkflowEventType,
)


def test_material_lot_create_validation_valid():
    """Verifies that a valid material lot payload parses and normalizes units correctly."""
    payload = MaterialLotCreate(
        material_type="aluminum-scrap",
        quantity=500.0,
        unit="KG",  # tests case-insensitivity
        facility_id="12345678-1234-5678-1234-567812345678",
        availability_from=date(2026, 11, 1),
        declared_attributes={"alloy": "6061", "form": "offcuts"},
    )
    assert payload.unit == "kg"
    assert payload.quantity == 500.0
    assert payload.status == MaterialLotStatus.DRAFT
    assert payload.provenance_label == EvidenceStatus.USER_SUPPLIED


def test_material_lot_create_invalid_unit():
    """Verifies that an unsupported measurement unit raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        MaterialLotCreate(
            material_type="aluminum-scrap",
            quantity=100.0,
            unit="lightyears",
            facility_id="12345678-1234-5678-1234-567812345678",
            availability_from=date(2026, 11, 1),
        )
    assert "Invalid unit" in str(exc_info.value)


def test_material_lot_create_invalid_quantity():
    """Verifies that non-positive quantities raise validation error."""
    with pytest.raises(ValidationError):
        MaterialLotCreate(
            material_type="aluminum-scrap",
            quantity=0.0,
            unit="kg",
            facility_id="12345678-1234-5678-1234-567812345678",
            availability_from=date(2026, 11, 1),
        )


def test_evidence_record_provenance_labels():
    """Verifies all evidence status labels conform to the canonical enum."""
    allowed = {
        "verified",
        "source_supported",
        "user_supplied",
        "inferred",
        "estimated",
        "synthetic_demo",
        "stale",
    }
    for status_str in allowed:
        assert EvidenceStatus(status_str) is not None

    record = EvidenceRecordCreate(
        claim_text="Moisture content under 5%",
        claim_subject="specification",
        evidence_status=EvidenceStatus.SOURCE_SUPPORTED,
    )
    assert record.evidence_status == EvidenceStatus.SOURCE_SUPPORTED


def test_qualification_assessment_contract():
    """Verifies qualification assessment schema serialization and hard gates."""
    assessment = QualificationAssessmentRead(
        lot_id="lot-1",
        candidate_route_id="route-1",
        status=AssessmentStatus.UNSUPPORTED,
        hard_gate_results=[
            HardGateResult(
                gate_id="gate-hazardous",
                gate_name="Hazardous Material Exclusion",
                outcome="fail",
                material_value=True,
                required_value=False,
            )
        ],
        missing_facts=[
            MissingFact(
                fact_id="fact-heavy-metals",
                description="Heavy metal assay lab report required",
            )
        ],
        rationale="Hazardous contamination exceeds threshold for municipal route.",
        next_action="Reroute to certified hazardous recovery facility.",
    )
    assert assessment.status == AssessmentStatus.UNSUPPORTED
    assert len(assessment.hard_gate_results) == 1
    assert assessment.hard_gate_results[0].outcome == "fail"


def test_marketplace_listing_and_rfq_contracts():
    """Verifies circular exchange listing and RFQ contract schemas."""
    listing = ExchangeListingRead(
        lot_id="lot-123",
        org_id="org-123",
        quantity=1200.0,
        unit="kg",
        status=ListingStatus.PUBLISHED,
        availability_from=date(2026, 11, 1),
    )
    assert listing.status == ListingStatus.PUBLISHED

    rfq = RFQRead(
        listing_id=listing.listing_id,
        lot_id=listing.lot_id,
        sender_org_id="org-buyer",
        recipient_org_id="org-123",
        status=RFQStatus.AWAITING_APPROVAL,
        quantity=600.0,
        unit="kg",
        idempotency_key="idempotency-key-1",
    )
    assert rfq.status == RFQStatus.AWAITING_APPROVAL


def test_workflow_event_contract():
    """Verifies operational audit log event schema."""
    event = WorkflowEventCreate(
        event_type=WorkflowEventType.LOT_REGISTERED,
        entity_id="lot-123",
        entity_type="lot",
        idempotency_key="key-abc",
    )
    assert event.event_type == WorkflowEventType.LOT_REGISTERED


def test_impact_calculation_contract():
    """Verifies impact calculation and rigid lifecycle stage segregation."""
    impact = ImpactCalculationRead(
        lot_id="lot-123",
        lifecycle_stage=ImpactStage.MATERIAL_CONFIRMED_PROCESSED,
        method_id="GHG-SCOPE3-CAT1",
        quantity=1000.0,
        unit="kg",
        metric_type="co2e_kg",
        metric_value=2450.5,
    )
    assert impact.lifecycle_stage == ImpactStage.MATERIAL_CONFIRMED_PROCESSED
    assert impact.metric_value == 2450.5


def test_standard_response_envelopes():
    """Verifies that success and error envelopes serialize properly."""
    success = ResponseEnvelope(data={"hello": "world"})
    json_data = success.model_dump()
    assert "data" in json_data
    assert "meta" in json_data
    assert "request_id" in json_data["meta"]
    assert "timestamp" in json_data["meta"]

    err = ErrorEnvelope(
        error=ErrorDetail(code="VALIDATION_ERROR", message="Bad request", details={"field": "unit"})
    )
    err_json = err.model_dump()
    assert err_json["error"]["code"] == "VALIDATION_ERROR"
