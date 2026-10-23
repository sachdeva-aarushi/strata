"""
Integration tests for the waste-prevention service and API endpoint.

All tests use FakeLLMProvider and FakeDiscoveryProvider (no real network calls).
Live provider tests (TinyFish, OpenAI) are explicitly gated on environment flags.

Provider mode for each test is documented in the test docstring:
  - "Verified with: MOCK" — uses fake providers, no credentials required
  - "Verified with: LIVE"  — requires real credentials + env flag (skipped otherwise)
"""

import os
import pytest
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from strata.domain.materials.models import MaterialLot, Organization, Facility
from strata.domain.prevention.service import WastePreventionService
from strata.domain.qualification.models import EvidenceRecord, QualificationAssessment
from strata.integrations.llm import FakeLLMProvider
from strata.schemas.evidence import (
    EvidenceProvenance,
    EvidenceVerificationState,
    ExtractionMethod,
)
from strata.schemas.prevention import (
    RecommendationCategory,
    RecommendationConfidence,
)
from strata.schemas.qualification import QualificationOutcome


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ORG_ID = "11111111-1111-1111-1111-111111111111"
FACILITY_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
LOT_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


@pytest.fixture
def org(db_session: Session) -> Organization:
    o = Organization(org_id=ORG_ID, name="Test Org", org_type="manufacturer")
    db_session.add(o)
    db_session.flush()
    return o


@pytest.fixture
def facility(db_session: Session, org: Organization) -> Facility:
    f = Facility(
        facility_id=FACILITY_ID,
        org_id=ORG_ID,
        name="Test Plant",
        location_country="US",
    )
    db_session.add(f)
    db_session.flush()
    return f


@pytest.fixture
def aluminum_lot(db_session: Session, facility: Facility) -> MaterialLot:
    lot = MaterialLot(
        lot_id=LOT_ID,
        org_id=ORG_ID,
        facility_id=FACILITY_ID,
        material_type="aluminum-scrap",
        quantity=1500.0,
        unit="kg",
        status="active",
        availability_from=date(2026, 11, 1),
        declared_attributes={
            "is_hazardous": False,
            "oil_contamination_pct": 0.8,
            "contaminants": [],
        },
        provenance_label="user_supplied",
    )
    db_session.add(lot)
    db_session.flush()
    return lot


@pytest.fixture
def unknown_lot(db_session: Session, facility: Facility) -> MaterialLot:
    """A lot with a material type that has no pre-configured routes."""
    lot = MaterialLot(
        lot_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        org_id=ORG_ID,
        facility_id=FACILITY_ID,
        material_type="unregistered-exotic-material",
        quantity=100.0,
        unit="kg",
        status="active",
        availability_from=date(2026, 11, 1),
        declared_attributes={},
        provenance_label="user_supplied",
    )
    db_session.add(lot)
    db_session.flush()
    return lot


def _make_service(db: Session) -> WastePreventionService:
    return WastePreventionService(db=db, llm=FakeLLMProvider(), llm_label="fake", evidence_label="fake")


# ---------------------------------------------------------------------------
# Service-layer tests (Verified with: MOCK)
# ---------------------------------------------------------------------------


class TestWastePreventionServiceNoAssessments:
    """Tests when no ProofPath assessments exist. Verified with: MOCK."""

    def test_recommends_investigation_when_routes_exist(
        self, db_session: Session, aluminum_lot: MaterialLot
    ):
        """R4: No assessments + known material → recommend running investigation."""
        service = _make_service(db_session)
        result = service.get_recommendations(lot_id=LOT_ID, org_id=ORG_ID)

        assert result.lot_id == LOT_ID
        assert result.material_type == "aluminum-scrap"
        assert result.evidence_provider == "fake"
        assert result.llm_provider == "fake"

        categories = [r.category for r in result.recommendations]
        assert RecommendationCategory.ROUTE_OPTIMIZATION in categories, (
            "Expected route-optimization recommendation when no assessment exists"
        )

    def test_deferred_recommendation_for_unknown_material(
        self, db_session: Session, unknown_lot: MaterialLot
    ):
        """R3: No pre-configured routes for material type → deferred recommendation."""
        service = _make_service(db_session)
        result = service.get_recommendations(
            lot_id="cccccccc-cccc-cccc-cccc-cccccccccccc", org_id=ORG_ID
        )

        categories = [r.category for r in result.recommendations]
        assert RecommendationCategory.DEFERRED in categories

    def test_global_evidence_gap_when_no_evidence(
        self, db_session: Session, aluminum_lot: MaterialLot
    ):
        """R5: No verified evidence + candidate routes → lot-preparation recommendation."""
        service = _make_service(db_session)
        result = service.get_recommendations(lot_id=LOT_ID, org_id=ORG_ID)

        categories = [r.category for r in result.recommendations]
        assert RecommendationCategory.LOT_PREPARATION in categories

        prep_recs = [r for r in result.recommendations if r.category == RecommendationCategory.LOT_PREPARATION]
        assert prep_recs[0].confidence == RecommendationConfidence.LOW
        assert len(prep_recs[0].missing_information) > 0


class TestWastePreventionServiceWithAssessments:
    """Tests when ProofPath assessments exist. Verified with: MOCK."""

    def _add_assessment(
        self,
        db: Session,
        lot_id: str,
        status: str,
        missing_facts=None,
    ) -> QualificationAssessment:
        qa = QualificationAssessment(
            assessment_id=f"qa-{status}-{lot_id[:8]}",
            investigation_id=None,
            lot_id=lot_id,
            candidate_route_id="route-secondary-aluminum-smelter",
            status=status,
            hard_gate_results=[{"gate_id": "g1", "gate_name": "Hazardous Exclusion", "outcome": "pass", "blocking": False}],
            blocking_conditions=[],
            missing_facts=missing_facts or [],
            rationale="Test rationale",
            next_action="Test next action",
            evidence_refs=[],
            rule_version="1.0.0",
        )
        db.add(qa)
        db.flush()
        return qa

    def test_supported_assessment_triggers_exchange_listing(
        self, db_session: Session, aluminum_lot: MaterialLot
    ):
        """R1: Supported assessment → recommend exchange listing."""
        self._add_assessment(db_session, LOT_ID, QualificationOutcome.SUPPORTED.value)

        service = _make_service(db_session)
        result = service.get_recommendations(lot_id=LOT_ID, org_id=ORG_ID)

        exchange_recs = [r for r in result.recommendations if r.category == RecommendationCategory.EXCHANGE_LISTING]
        assert len(exchange_recs) >= 1
        assert exchange_recs[0].confidence == RecommendationConfidence.HIGH
        assert len(exchange_recs[0].next_steps) > 0

    def test_conditional_assessment_triggers_evidence_acquisition(
        self, db_session: Session, aluminum_lot: MaterialLot
    ):
        """R2: Conditional assessment → recommend acquiring missing facts."""
        missing = [
            {"fact_id": "fact-alloy-series", "description": "Alloy series required", "acquisition_method": "document", "is_critical": True},
            {"fact_id": "fact-moisture-level", "description": "Moisture assay required", "acquisition_method": "lab_test", "is_critical": True},
        ]
        self._add_assessment(db_session, LOT_ID, QualificationOutcome.CONDITIONAL.value, missing_facts=missing)

        service = _make_service(db_session)
        result = service.get_recommendations(lot_id=LOT_ID, org_id=ORG_ID)

        acq_recs = [r for r in result.recommendations if r.category == RecommendationCategory.EVIDENCE_ACQUISITION]
        assert len(acq_recs) >= 1
        missing_ids = [m.item_id for m in acq_recs[0].missing_information]
        assert "fact-alloy-series" in missing_ids
        assert "fact-moisture-level" in missing_ids

    def test_verified_evidence_suppresses_global_gap_recommendation(
        self, db_session: Session, aluminum_lot: MaterialLot
    ):
        """R5 is suppressed when verified evidence exists."""
        # Add a verified evidence record
        ev = EvidenceRecord(
            evidence_id="ev-verified-001",
            org_id=ORG_ID,
            lot_id=LOT_ID,
            claim_subject="moisture_level",
            claim_text="Moisture < 0.1%",
            source_type="lab_report",
            retrieved_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            extraction_method=ExtractionMethod.LAB_TEST.value,
            provenance=EvidenceProvenance.INDEPENDENTLY_VERIFIED.value,
            verification_state=EvidenceVerificationState.VERIFIED.value,
            contradicted_by=[],
        )
        db_session.add(ev)
        db_session.flush()

        service = _make_service(db_session)
        result = service.get_recommendations(lot_id=LOT_ID, org_id=ORG_ID)

        prep_recs = [r for r in result.recommendations if r.category == RecommendationCategory.LOT_PREPARATION]
        assert len(prep_recs) == 0, "Lot-preparation recommendation must not appear when verified evidence exists"

    def test_no_environmental_savings_in_recommendations(
        self, db_session: Session, aluminum_lot: MaterialLot
    ):
        """Architecture constraint: no unsupported environmental impact figures."""
        self._add_assessment(db_session, LOT_ID, QualificationOutcome.SUPPORTED.value)
        service = _make_service(db_session)
        result = service.get_recommendations(lot_id=LOT_ID, org_id=ORG_ID)

        forbidden_terms = ["tonnes CO2", "kg CO2", "carbon saved", "emissions reduced", "environmental savings"]
        for rec in result.recommendations:
            text = (rec.rationale + " " + rec.summary + " " + " ".join(rec.next_steps)).lower()
            for term in forbidden_terms:
                assert term.lower() not in text, (
                    f"Forbidden environmental claim '{term}' found in recommendation: {rec.recommendation_id}"
                )

    def test_lot_not_found_raises_error(self, db_session: Session):
        """Service raises ResourceNotFoundError for unknown lot in tenant scope."""
        from strata.core.errors import ResourceNotFoundError
        service = _make_service(db_session)
        with pytest.raises(ResourceNotFoundError):
            service.get_recommendations(lot_id="nonexistent-lot-id", org_id=ORG_ID)


# ---------------------------------------------------------------------------
# API endpoint integration tests (Verified with: MOCK)
# ---------------------------------------------------------------------------


class TestPreventionAPIEndpoint:
    """Tests the GET /api/v1/lots/{lot_id}/prevention/recommendations endpoint. Verified with: MOCK."""

    def test_returns_200_with_recommendations(
        self, client: TestClient, org_headers: dict, db_session: Session,
        aluminum_lot: MaterialLot
    ):
        response = client.get(
            f"/api/v1/lots/{LOT_ID}/prevention/recommendations",
            headers=org_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        data = body["data"]
        assert data["lot_id"] == LOT_ID
        assert data["material_type"] == "aluminum-scrap"
        assert isinstance(data["recommendations"], list)
        assert data["evidence_provider"] == "fake"
        assert data["llm_provider"] == "fake"

    def test_returns_404_for_unknown_lot(self, client: TestClient, org_headers: dict):
        response = client.get(
            "/api/v1/lots/nonexistent-lot-uuid/prevention/recommendations",
            headers=org_headers,
        )
        assert response.status_code == 404

    def test_returns_200_when_no_assessments(
        self, client: TestClient, org_headers: dict, aluminum_lot: MaterialLot
    ):
        """Endpoint always returns 200 with at least one advisory recommendation."""
        response = client.get(
            f"/api/v1/lots/{LOT_ID}/prevention/recommendations",
            headers=org_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["recommendations"]) >= 1

    def test_multi_tenant_isolation(
        self, client: TestClient, other_org_headers: dict, aluminum_lot: MaterialLot
    ):
        """Lot from org-A must not be accessible from org-B."""
        response = client.get(
            f"/api/v1/lots/{LOT_ID}/prevention/recommendations",
            headers=other_org_headers,
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Live provider smoke tests (Verified with: LIVE — skipped unless explicitly enabled)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("STRATA_TEST_LIVE_TINYFISH"),
    reason="Requires live TinyFish credentials. Set STRATA_TEST_LIVE_TINYFISH=1 to run.",
)
class TestTinyFishLiveIntegration:
    """
    Live smoke tests for the TinyFish adapter.
    Requires TINYFISH_API_KEY in the environment.
    These tests make real network calls and may incur API usage.
    Set STRATA_TEST_LIVE_TINYFISH=1 to enable.

    Verified with: LIVE
    """

    def test_live_search_returns_results(self):
        from strata.integrations.tinyfish import TinyFishAdapter
        adapter = TinyFishAdapter()
        results = adapter.search("aluminum scrap secondary smelter industrial recycling")
        assert isinstance(results, list)
        # We do not assert specific content — sources change over time
        print(f"\nLive TinyFish search: {len(results)} results returned")

    def test_live_search_normalize_evidence_provenance(self):
        from strata.integrations.tinyfish import TinyFishAdapter
        adapter = TinyFishAdapter()
        evidence = adapter.search_and_normalize_evidence(
            query="secondary aluminum recycler capability",
            claim_subject="receiver_capability",
        )
        if evidence:
            # All records must always be PUBLICLY_STATED / UNVERIFIED
            for rec in evidence:
                assert rec.provenance == EvidenceProvenance.PUBLICLY_STATED
                assert rec.verification_state == EvidenceVerificationState.UNVERIFIED


@pytest.mark.skipif(
    not os.environ.get("STRATA_TEST_LIVE_LLM"),
    reason="Requires live LLM credentials. Set STRATA_TEST_LIVE_LLM=1 to run.",
)
class TestOpenAILiveIntegration:
    """
    Live smoke tests for the OpenAI-compatible LLM adapter.
    Requires LLM_PROVIDER and LLM_API_KEY in the environment.
    Set STRATA_TEST_LIVE_LLM=1 to enable.

    Verified with: LIVE
    """

    def test_live_synthesize_explanation_returns_text(self):
        from strata.integrations.llm import OpenAICompatibleLLMAdapter
        adapter = OpenAICompatibleLLMAdapter()
        result = adapter.synthesize_explanation(
            route_name="Secondary Aluminum Smelter",
            status="conditional",
            passed_gates=["Hazardous Exclusion", "Oil Contamination Limit"],
            blocking_conditions=[],
            missing_facts=["Alloy series verification", "Moisture assay"],
        )
        assert isinstance(result, str)
        assert len(result) > 10
        print(f"\nLive LLM explanation:\n{result}")

    def test_live_suggest_next_action_returns_text(self):
        from strata.integrations.llm import OpenAICompatibleLLMAdapter
        adapter = OpenAICompatibleLLMAdapter()
        action = adapter.suggest_next_action(
            status="conditional",
            blocking_conditions=[],
            missing_facts=["Alloy series verification"],
        )
        assert isinstance(action, str)
        assert len(action) > 5
        print(f"\nLive LLM next action:\n{action}")
