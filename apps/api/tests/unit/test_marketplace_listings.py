import json
import uuid

import httpx
import pytest
from pydantic import ValidationError

from strata.domain.marketplace.qualification import (
    ASSESS_PATH,
    ProofPathQualificationClient,
    QualificationServiceError,
)
from strata.domain.marketplace.schemas import (
    BuyerRequirementCreate,
    BuyerRequirementRead,
    ListingCreate,
    ListingRead,
    ListingStatus,
    ListingVisibility,
    QualificationResult,
)
from strata.domain.marketplace.service import CandidateListing, filter_candidates, matches_requirement

LOT_ID = str(uuid.uuid4())
REQ_ID = str(uuid.uuid4())
ORG_ID = str(uuid.uuid4())
FAC_ID = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_listing(**overrides) -> ListingRead:
    data = dict(
        id=str(uuid.uuid4()),
        material_lot_id=LOT_ID,
        organization_id=ORG_ID,
        facility_id=FAC_ID,
        visibility=ListingVisibility.PUBLIC,
        asking_price_per_unit=120.0,
        currency="USD",
        available_quantity=500.0,
        unit="kg",
        status=ListingStatus.ACTIVE,
    )
    data.update(overrides)
    return ListingRead(**data)


def make_requirement(**overrides) -> BuyerRequirementRead:
    data = dict(
        organization_id=ORG_ID,
        facility_id=FAC_ID,
        material_category="pet_flake",
        min_quantity=100.0,
        max_quantity=1000.0,
        unit="kg",
        target_price_per_unit=150.0,
        required_properties={"color": "clear"},
        prohibited_conditions=["contaminated_with_pvc"],
        visibility=ListingVisibility.PUBLIC,
    )
    data.update(overrides)
    organization_id = data.pop("organization_id")
    create = BuyerRequirementCreate(**data)
    return BuyerRequirementRead(**create.model_dump(), organization_id=organization_id)


def make_candidate(category: str = "pet_flake", **listing_overrides) -> CandidateListing:
    return CandidateListing(listing=make_listing(**listing_overrides), material_category=category)


PROOFPATH_OK = {
    "status": "supported",
    "rationale": "All hard gates passed.",
    "next_action": "Proceed to RFQ.",
    "rule_version": "2.3.1",
    "hard_gate_results": [
        {"gate_id": "G1", "gate_name": "Colour", "outcome": "pass"},
    ],
    "missing_facts": [],
    "evidence_refs": ["ev-1"],
}


def proofpath_transport(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


def json_handler(body, status_code: int = 200, seen: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status_code, json=body)
    return handler


def raising_handler(exc: Exception):
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc
    return handler


# ---------------------------------------------------------------------------
# Listing schema
# ---------------------------------------------------------------------------

class TestListingCreate:
    def _payload(self, **overrides):
        data = dict(
            material_lot_id=LOT_ID,
            facility_id=FAC_ID,
            visibility="cluster_only",
            asking_price_per_unit=99.5,
            currency="usd",
            available_quantity=250,
            unit="KG",
        )
        data.update(overrides)
        return data

    def test_accepts_valid_payload_and_normalises_fields(self):
        listing = ListingCreate(**self._payload())
        assert listing.visibility == ListingVisibility.CLUSTER_ONLY
        assert listing.currency == "USD"
        assert listing.unit == "kg"

    def test_rejects_non_uuid_material_lot_id(self):
        with pytest.raises(ValidationError):
            ListingCreate(**self._payload(material_lot_id="lot-123"))

    def test_rejects_zero_available_quantity(self):
        with pytest.raises(ValidationError):
            ListingCreate(**self._payload(available_quantity=0))

    def test_rejects_negative_price(self):
        with pytest.raises(ValidationError):
            ListingCreate(**self._payload(asking_price_per_unit=-1))

    def test_rejects_unknown_visibility(self):
        with pytest.raises(ValidationError):
            ListingCreate(**self._payload(visibility="global"))

    def test_visibility_defaults_to_private(self):
        payload = self._payload()
        payload.pop("visibility")
        assert ListingCreate(**payload).visibility == ListingVisibility.PRIVATE


class TestBuyerRequirementCreate:
    def test_max_below_min_is_rejected(self):
        with pytest.raises(ValidationError):
            BuyerRequirementCreate(
                facility_id=FAC_ID,
                material_category="pet_flake",
                min_quantity=200,
                max_quantity=100,
                unit="kg",
            )

    def test_list_and_json_fields_default_empty(self):
        req = BuyerRequirementCreate(
            facility_id=FAC_ID, material_category="pet_flake", min_quantity=1, unit="kg"
        )
        assert req.required_properties == {}
        assert req.prohibited_conditions == []


# ---------------------------------------------------------------------------
# Candidate filtering
# ---------------------------------------------------------------------------

class TestCandidateFiltering:
    def test_matching_listing_is_returned(self):
        candidate = make_candidate()
        assert matches_requirement(candidate, make_requirement())

    def test_filters_by_material_category_case_insensitively(self):
        assert not matches_requirement(make_candidate(category="hdpe_bale"), make_requirement())
        assert matches_requirement(make_candidate(category="PET_FLAKE"), make_requirement())

    def test_filters_by_available_quantity_against_min(self):
        assert not matches_requirement(make_candidate(available_quantity=99.9), make_requirement())
        assert matches_requirement(make_candidate(available_quantity=100), make_requirement())

    def test_max_quantity_is_not_a_filter(self):
        candidate = make_candidate(available_quantity=5000)
        assert matches_requirement(candidate, make_requirement(max_quantity=1000))

    def test_filters_by_unit(self):
        assert not matches_requirement(make_candidate(unit="tonne"), make_requirement(unit="kg"))

    def test_default_visibility_excludes_private(self):
        assert not matches_requirement(make_candidate(visibility=ListingVisibility.PRIVATE), make_requirement())

    def test_default_visibility_includes_cluster_and_public(self):
        assert matches_requirement(make_candidate(visibility=ListingVisibility.CLUSTER_ONLY), make_requirement())
        assert matches_requirement(make_candidate(visibility=ListingVisibility.PUBLIC), make_requirement())

    def test_explicit_visibility_levels_are_respected(self):
        candidate = make_candidate(visibility=ListingVisibility.CLUSTER_ONLY)
        assert not matches_requirement(
            candidate, make_requirement(), visibility_levels=[ListingVisibility.PUBLIC]
        )
        private = make_candidate(visibility=ListingVisibility.PRIVATE)
        assert matches_requirement(
            private, make_requirement(), visibility_levels=[ListingVisibility.PRIVATE]
        )

    def test_only_active_listings_are_candidates(self):
        for status in (ListingStatus.DRAFT, ListingStatus.PAUSED, ListingStatus.SOLD_OUT, ListingStatus.WITHDRAWN):
            assert not matches_requirement(make_candidate(status=status), make_requirement())

    def test_filter_candidates_keeps_order_and_drops_non_matches(self):
        keep_a = make_candidate()
        drop_category = make_candidate(category="hdpe_bale")
        keep_b = make_candidate(available_quantity=800)
        drop_qty = make_candidate(available_quantity=1)

        result = filter_candidates([keep_a, drop_category, keep_b, drop_qty], make_requirement())

        assert result == [keep_a, keep_b]


# ---------------------------------------------------------------------------
# ProofPath client
# ---------------------------------------------------------------------------

class TestProofPathClient:
    async def test_success_returns_validated_result_and_calls_assess_endpoint(self):
        seen: list = []
        client = ProofPathQualificationClient(
            base_url="http://proofpath.test",
            mock_fallback=False,
            transport=proofpath_transport(json_handler(PROOFPATH_OK, seen=seen)),
        )

        result = await client.assess_lot_qualification(LOT_ID, REQ_ID)

        assert len(seen) == 1
        assert seen[0].url.path == ASSESS_PATH
        assert json.loads(seen[0].content) == {"material_lot_id": LOT_ID, "requirement_id": REQ_ID}
        assert result["status"] == "supported"
        assert result["source"] == "proofpath"
        assert result["material_lot_id"] == LOT_ID
        assert result["requirement_id"] == REQ_ID
        QualificationResult.model_validate(result)

    async def test_timeout_raises_typed_error_without_fallback(self):
        client = ProofPathQualificationClient(
            base_url="http://proofpath.test",
            mock_fallback=False,
            transport=proofpath_transport(raising_handler(httpx.ReadTimeout("slow"))),
        )
        with pytest.raises(QualificationServiceError) as info:
            await client.assess_lot_qualification(LOT_ID, REQ_ID)
        assert info.value.reason == "timeout"
        assert info.value.status_code == 502

    async def test_connection_error_raises_without_fallback(self):
        client = ProofPathQualificationClient(
            base_url="http://proofpath.test",
            mock_fallback=False,
            transport=proofpath_transport(raising_handler(httpx.ConnectError("refused"))),
        )
        with pytest.raises(QualificationServiceError) as info:
            await client.assess_lot_qualification(LOT_ID, REQ_ID)
        assert info.value.reason == "connection"

    async def test_server_error_raises_with_http_status_reason(self):
        client = ProofPathQualificationClient(
            base_url="http://proofpath.test",
            mock_fallback=False,
            transport=proofpath_transport(json_handler({"detail": "boom"}, status_code=503)),
        )
        with pytest.raises(QualificationServiceError) as info:
            await client.assess_lot_qualification(LOT_ID, REQ_ID)
        assert info.value.reason == "http_status"
        assert info.value.details["status_code"] == 503

    async def test_schema_violation_raises_schema_error(self):
        bad = {"status": "approved-ish", "rationale": "x", "next_action": "y"}
        client = ProofPathQualificationClient(
            base_url="http://proofpath.test",
            mock_fallback=False,
            transport=proofpath_transport(json_handler(bad)),
        )
        with pytest.raises(QualificationServiceError) as info:
            await client.assess_lot_qualification(LOT_ID, REQ_ID)
        assert info.value.reason == "schema"

    async def test_non_json_response_raises_schema_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"<html>oops</html>")

        client = ProofPathQualificationClient(
            base_url="http://proofpath.test",
            mock_fallback=False,
            transport=proofpath_transport(handler),
        )
        with pytest.raises(QualificationServiceError) as info:
            await client.assess_lot_qualification(LOT_ID, REQ_ID)
        assert info.value.reason == "schema"

    async def test_mismatched_identifiers_are_rejected(self):
        body = {**PROOFPATH_OK, "material_lot_id": str(uuid.uuid4())}
        client = ProofPathQualificationClient(
            base_url="http://proofpath.test",
            mock_fallback=False,
            transport=proofpath_transport(json_handler(body)),
        )
        with pytest.raises(QualificationServiceError) as info:
            await client.assess_lot_qualification(LOT_ID, REQ_ID)
        assert info.value.reason == "schema"

    async def test_fallback_returns_pending_mock_on_timeout(self):
        client = ProofPathQualificationClient(
            base_url="http://proofpath.test",
            mock_fallback=True,
            transport=proofpath_transport(raising_handler(httpx.ReadTimeout("slow"))),
        )
        result = await client.assess_lot_qualification(LOT_ID, REQ_ID)
        assert result["source"] == "mock"
        assert result["status"] == "pending"
        assert "MOCK" in result["rationale"]
        assert result["material_lot_id"] == LOT_ID

    async def test_fallback_returns_mock_on_schema_failure(self):
        client = ProofPathQualificationClient(
            base_url="http://proofpath.test",
            mock_fallback=True,
            transport=proofpath_transport(json_handler({"nope": True})),
        )
        result = await client.assess_lot_qualification(LOT_ID, REQ_ID)
        assert result["source"] == "mock"

    async def test_mock_only_never_touches_network(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("network must not be called in mock_only mode")

        client = ProofPathQualificationClient(
            base_url="http://proofpath.test",
            mock_only=True,
            transport=proofpath_transport(handler),
        )
        result = await client.assess_lot_qualification(LOT_ID, REQ_ID)
        assert result["source"] == "mock"
        assert result["status"] == "pending"

    def test_base_url_trailing_slash_is_stripped(self):
        client = ProofPathQualificationClient(base_url="http://proofpath.test/", mock_fallback=False)
        assert client.base_url == "http://proofpath.test"
