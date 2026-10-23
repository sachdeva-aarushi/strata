"""Pydantic contracts for the marketplace domain.

Three groups are kept deliberately separate:

* Marketplace listings      - what a supplier offers (ListingCreate / ListingRead)
* Buyer requirements        - what a buyer needs (BuyerRequirementCreate / BuyerRequirementRead)
* Qualification results     - read-only output of ProofPath (QualificationResult).
                              Owned by ProofPath; the marketplace never computes it.

Material registry data (and the canonical ``material_lot_id``) is owned by the
materials domain. Listings only reference the lot by its UUID string.
"""

import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from strata.schemas.qualification import AssessmentStatus, HardGateResult, MissingFact


def _validate_uuid_str(value: str) -> str:
    """Accept only canonical UUID strings and return them normalised."""
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError("must be a valid UUID string") from exc


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ListingVisibility(str, Enum):
    """Who may see a listing or buyer requirement."""
    PRIVATE = "private"
    CLUSTER_ONLY = "cluster_only"
    PUBLIC = "public"


class ListingStatus(str, Enum):
    """Marketplace listing lifecycle (distinct from the materials lot status)."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    SOLD_OUT = "sold_out"
    WITHDRAWN = "withdrawn"


class RFQStatus(str, Enum):
    """Commercial request for quotation lifecycle."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class OfferStatus(str, Enum):
    """Commercial offer / quote lifecycle."""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    REVISED = "revised"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class WorkflowEventType(str, Enum):
    """Auditable state machine event types."""
    RFQ_CREATED = "rfq_created"
    RFQ_SUBMITTED = "rfq_submitted"
    RFQ_APPROVED = "rfq_approved"
    RFQ_CANCELLED = "rfq_cancelled"
    OFFER_SUBMITTED = "offer_submitted"
    OFFER_REVIEWED = "offer_reviewed"
    OFFER_REVISED = "offer_revised"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_REJECTED = "offer_rejected"
    OFFER_WITHDRAWN = "offer_withdrawn"
    LISTING_CREATED = "listing_created"
    LISTING_PUBLISHED = "listing_published"
    LISTING_UPDATED = "listing_updated"
    LISTING_PAUSED = "listing_paused"
    LISTING_WITHDRAWN = "listing_withdrawn"
    REQUIREMENT_CREATED = "requirement_created"
    REQUIREMENT_UPDATED = "requirement_updated"
    REQUIREMENT_DELETED = "requirement_deleted"
    MATCH_EVALUATED = "match_evaluated"


# ---------------------------------------------------------------------------
# Marketplace listings (supplier side)
# ---------------------------------------------------------------------------

class ListingCreate(BaseModel):
    """Payload to publish a material lot to the marketplace."""
    material_lot_id: str = Field(..., description="Canonical lot UUID from the materials registry")
    facility_id: str
    visibility: ListingVisibility = ListingVisibility.PRIVATE
    asking_price_per_unit: float = Field(..., ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    available_quantity: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1, max_length=20)
    status: ListingStatus = ListingStatus.DRAFT

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("material_lot_id")
    @classmethod
    def _check_lot_id(cls, v: str) -> str:
        return _validate_uuid_str(v)

    @field_validator("currency")
    @classmethod
    def _upper_currency(cls, v: str) -> str:
        return v.upper()

    @field_validator("unit")
    @classmethod
    def _lower_unit(cls, v: str) -> str:
        return v.lower()


class ListingUpdate(BaseModel):
    """Payload to update an existing marketplace listing."""
    asking_price_per_unit: Optional[float] = Field(default=None, ge=0)
    available_quantity: Optional[float] = Field(default=None, gt=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    visibility: Optional[ListingVisibility] = None
    status: Optional[ListingStatus] = None
    notes: Optional[str] = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("currency")
    @classmethod
    def _upper_currency(cls, v: Optional[str]) -> Optional[str]:
        return v.upper() if v else v


class ListingRead(BaseModel):
    """Marketplace listing as returned by the API."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    material_lot_id: str
    organization_id: str
    facility_id: str
    visibility: ListingVisibility
    asking_price_per_unit: float
    currency: str
    available_quantity: float
    unit: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: ListingStatus = ListingStatus.DRAFT

    # Enriched material lot and provenance information
    material_type: Optional[str] = None
    material_category: Optional[str] = None
    material_properties: Dict[str, Any] = Field(default_factory=dict)
    location: Optional[str] = None
    availability_from: Optional[date] = None
    availability_to: Optional[date] = None
    lot_quantity: Optional[float] = None
    supporting_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Buyer requirements (demand side)
# ---------------------------------------------------------------------------

class BuyerRequirementCreate(BaseModel):
    """Payload describing what a buyer needs."""
    facility_id: str
    material_category: str = Field(..., min_length=1, max_length=100)
    min_quantity: float = Field(..., ge=0)
    max_quantity: Optional[float] = Field(default=None, gt=0)
    unit: str = Field(..., min_length=1, max_length=20)
    target_price_per_unit: Optional[float] = Field(default=None, ge=0)
    required_properties: Dict[str, Any] = Field(default_factory=dict)
    prohibited_conditions: List[str] = Field(default_factory=list)
    visibility: ListingVisibility = ListingVisibility.PRIVATE
    location: Optional[str] = None
    delivery_requirements: Dict[str, Any] = Field(default_factory=dict)
    constraints: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("unit")
    @classmethod
    def _lower_unit(cls, v: str) -> str:
        return v.lower()

    @field_validator("max_quantity")
    @classmethod
    def _max_ge_min(cls, v: Optional[float], info) -> Optional[float]:
        min_q = info.data.get("min_quantity")
        if v is not None and min_q is not None and v < min_q:
            raise ValueError("max_quantity cannot be smaller than min_quantity")
        return v


class BuyerRequirementUpdate(BaseModel):
    """Payload to update an existing buyer requirement."""
    min_quantity: Optional[float] = Field(default=None, ge=0)
    max_quantity: Optional[float] = Field(default=None, gt=0)
    target_price_per_unit: Optional[float] = Field(default=None, ge=0)
    required_properties: Optional[Dict[str, Any]] = None
    prohibited_conditions: Optional[List[str]] = None
    visibility: Optional[ListingVisibility] = None
    location: Optional[str] = None
    delivery_requirements: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(str_strip_whitespace=True)


class BuyerRequirementRead(BuyerRequirementCreate):
    """Buyer requirement as returned by the API."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Qualification results (ProofPath output, read-only here)
# ---------------------------------------------------------------------------

class QualificationResult(BaseModel):
    """Result of a ProofPath assessment of one lot against one buyer requirement.

    This is a consumer-side contract. The marketplace stores and displays it,
    but never derives the status itself.
    """
    material_lot_id: str
    requirement_id: str
    status: AssessmentStatus
    hard_gate_results: List[HardGateResult] = Field(default_factory=list)
    missing_facts: List[MissingFact] = Field(default_factory=list)
    rationale: str = ""
    next_action: str = ""
    evidence_refs: List[str] = Field(default_factory=list)
    rule_version: str = "unknown"
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = Field(default="proofpath", description="proofpath or mock")

    model_config = ConfigDict(from_attributes=True)

    @field_validator("material_lot_id")
    @classmethod
    def _check_lot_id(cls, v: str) -> str:
        return _validate_uuid_str(v)


# ---------------------------------------------------------------------------
# Transition and Status Requests
# ---------------------------------------------------------------------------

class StateTransitionRequest(BaseModel):
    """Payload to request a state machine transition."""
    status: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(str_strip_whitespace=True)


class ListingStatusUpdateRequest(BaseModel):
    """Payload to alter a listing's lifecycle status."""
    status: ListingStatus
    notes: Optional[str] = None

    model_config = ConfigDict(str_strip_whitespace=True)


# ---------------------------------------------------------------------------
# RFQs (Request For Quotation)
# ---------------------------------------------------------------------------

class RFQCreate(BaseModel):
    """Payload to initiate a request for quotation against an active listing."""
    listing_id: str = Field(..., description="Target listing UUID")
    buyer_facility_id: str = Field(..., description="Facility of the buyer organization")
    buyer_requirement_id: Optional[str] = Field(default=None, description="Optional linked requirement UUID")
    requested_quantity: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1, max_length=20)
    target_price_per_unit: Optional[float] = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    notes: Optional[str] = None
    submit_for_approval: bool = Field(
        default=False,
        description="If True, moves directly to PENDING_APPROVAL; else DRAFT.",
    )

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("listing_id")
    @classmethod
    def _check_listing_id(cls, v: str) -> str:
        return _validate_uuid_str(v)

    @field_validator("buyer_requirement_id")
    @classmethod
    def _check_req_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_uuid_str(v)
        return v

    @field_validator("currency")
    @classmethod
    def _upper_currency(cls, v: str) -> str:
        return v.upper()

    @field_validator("unit")
    @classmethod
    def _lower_unit(cls, v: str) -> str:
        return v.lower()


class RFQRead(BaseModel):
    """RFQ presentation model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    listing_id: str
    buyer_requirement_id: Optional[str] = None
    buyer_organization_id: str
    buyer_facility_id: str
    seller_organization_id: str
    seller_facility_id: str
    requested_quantity: float
    unit: str
    target_price_per_unit: Optional[float] = None
    currency: str = "USD"
    status: RFQStatus
    notes: Optional[str] = None
    created_by: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Offers / Quotes (Seller Responses)
# ---------------------------------------------------------------------------

class OfferCreate(BaseModel):
    """Payload from a seller submitting or revising a quote for an RFQ."""
    offered_quantity: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1, max_length=20)
    price_per_unit: float = Field(..., ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    terms: Optional[str] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("currency")
    @classmethod
    def _upper_currency(cls, v: str) -> str:
        return v.upper()

    @field_validator("unit")
    @classmethod
    def _lower_unit(cls, v: str) -> str:
        return v.lower()


class OfferRead(BaseModel):
    """Offer presentation model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rfq_id: str
    listing_id: str
    seller_organization_id: str
    seller_facility_id: str
    offered_quantity: float
    unit: str
    price_per_unit: float
    currency: str = "USD"
    status: OfferStatus
    terms: Optional[str] = None
    valid_until: Optional[datetime] = None
    created_by: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Workflow Audit Events
# ---------------------------------------------------------------------------

class WorkflowEventCreate(BaseModel):
    """Payload to record an auditable workflow event."""
    entity_type: str = Field(..., description="listing, rfq, offer, requirement, or match")
    entity_id: str
    event_type: WorkflowEventType
    from_state: Optional[str] = None
    to_state: str
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(str_strip_whitespace=True)


class WorkflowEventRead(BaseModel):
    """Auditable state transition event."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str
    entity_id: str
    event_type: str
    from_state: Optional[str] = None
    to_state: str
    actor_id: str
    actor_role: str
    actor_org_id: str
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _resolve_metadata(cls, data: Any) -> Any:
        if hasattr(data, "metadata_payload"):
            return {
                "id": data.id,
                "entity_type": data.entity_type,
                "entity_id": data.entity_id,
                "event_type": data.event_type.value if hasattr(data.event_type, "value") else str(data.event_type),
                "from_state": data.from_state,
                "to_state": data.to_state,
                "actor_id": data.actor_id,
                "actor_role": data.actor_role,
                "actor_org_id": data.actor_org_id,
                "notes": data.notes,
                "metadata": getattr(data, "metadata_payload", None) or {},
                "created_at": data.created_at,
            }
        if isinstance(data, dict):
            if "metadata" not in data and "metadata_payload" in data:
                data["metadata"] = data["metadata_payload"]
        return data


# ---------------------------------------------------------------------------
# Cluster Synergy and Batch Aggregation (Hitendra)
# ---------------------------------------------------------------------------

class LotContribution(BaseModel):
    """A constituent material lot proposed as part of an aggregated batch."""
    lot_id: str
    listing_id: Optional[str] = None
    organization_id: str
    facility_id: str
    quantity: float
    unit: str
    material_type: str
    material_category: str
    declared_attributes: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class AggregationProposal(BaseModel):
    """A proposed combination of compatible lots meeting buyer volume thresholds."""
    proposal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    requirement_id: str
    cluster_id: str
    lots: List[LotContribution]
    total_quantity: float
    unit: str
    target_min_quantity: float
    composite_attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Weighted averages of composition, moisture, purity, etc.",
    )
    quality_variance_warnings: List[str] = Field(
        default_factory=list,
        description="Flags when individual lot attributes deviate significantly from the mean",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class LogisticsEstimateRequest(BaseModel):
    """Payload to calculate indicative multi-stop transport metrics."""
    lot_ids: List[str] = Field(..., min_length=1, description="List of lot UUIDs to collect")
    destination_facility_id: str = Field(..., description="Destination processing facility UUID")
    rate_per_km_tonne: float = Field(default=12.5, gt=0, description="Transport tariff in INR per tonne-km")

    model_config = ConfigDict(str_strip_whitespace=True)


class LogisticsEstimate(BaseModel):
    """Indicative transport routing, cost and emissions estimates."""
    lot_ids: List[str]
    destination_facility_id: str
    total_tonnage: float
    total_distance_km: float
    rate_per_km_tonne: float
    estimated_transport_cost_inr: float
    estimated_transport_emissions_kg_co2e: float
    currency: str = "INR"
    methodology: str = "indicative_milk_run_v1"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class ClusterSummary(BaseModel):
    """Aggregated cluster circularity indicators."""
    cluster_id: str
    active_listings_count: int
    total_available_tonnage: float
    tonnage_by_category: Dict[str, float] = Field(default_factory=dict)
    potential_aggregation_opportunities: int
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Matching and Compatibility Contracts (Aarushi - Circular Exchange)
# ---------------------------------------------------------------------------

class MatchEligibility(str, Enum):
    """Technical and commercial candidate eligibility status."""
    ELIGIBLE = "eligible"
    CONDITIONAL = "conditional"
    INELIGIBLE = "ineligible"


class MatchCandidateRead(BaseModel):
    """A matched listing candidate with compatibility score and ProofPath qualification."""
    listing: ListingRead
    match_score: float = Field(..., ge=0.0, le=100.0, description="Compatibility score (0-100). Hard gates cap this at 0.0.")
    eligibility: MatchEligibility
    compatibility_reasons: List[str] = Field(default_factory=list)
    incompatibilities: List[str] = Field(default_factory=list, description="Violated hard constraints or hard gates")
    missing_information: List[str] = Field(default_factory=list, description="Missing tests, certifications, or properties")
    distance_km: Optional[float] = None
    logistics_summary: Optional[Dict[str, Any]] = None
    qualification_details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class BuyerRequirementMatchesResponse(BaseModel):
    """Structured candidate matching response for a buyer requirement."""
    requirement_id: str
    total_candidates_evaluated: int
    eligible_count: int
    conditional_count: int
    ineligible_count: int
    matches: List[MatchCandidateRead]


# ---------------------------------------------------------------------------
# Logistics Comparison Contracts (Aarushi - Circular Exchange)
# ---------------------------------------------------------------------------

class FreightOption(BaseModel):
    """A transport option comparison breakdown."""
    mode: str
    mode_name: str
    estimated_cost_usd: float
    cost_per_unit: float
    estimated_duration_days: float
    estimated_emissions_kg_co2e: float
    is_estimated: bool = True
    disclaimer: str = "Indicative estimate based on regional freight averages. Confirm with carrier."


class LogisticsComparisonRequest(BaseModel):
    """Request to compare freight transport options."""
    origin_facility_id: Optional[str] = None
    destination_facility_id: Optional[str] = None
    origin_location: Optional[str] = None
    destination_location: Optional[str] = None
    quantity: float = Field(..., gt=0)
    unit: str = "kg"
    material_type: Optional[str] = None

    model_config = ConfigDict(str_strip_whitespace=True)


class LogisticsComparisonResponse(BaseModel):
    """Freight comparison results across available modes."""
    distance_km: float
    is_distance_estimated: bool = True
    quantity: float
    unit: str
    options: List[FreightOption]
    summary: str
    methodology: str = "indicative_freight_emissions_and_cost_model"


# ---------------------------------------------------------------------------
# Cluster and City Indicators Contracts (Aarushi - Circular Exchange)
# ---------------------------------------------------------------------------

class MaterialCategoryVolume(BaseModel):
    """Aggregated volume and listings for a material category."""
    category: str
    active_listings_count: int
    total_quantity: float
    unit: str


class ClusterIndicatorsResponse(BaseModel):
    """Aggregated circularity and exchange indicators across the industrial cluster."""
    cluster_id: Optional[str] = None
    as_of: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_estimated: bool = False
    source: str = "persisted_marketplace_records"
    total_active_listings: int
    total_active_buyer_requirements: int
    total_active_rfqs: int
    completed_exchanges_count: int
    supply_by_category: List[MaterialCategoryVolume]
    demand_by_category: List[MaterialCategoryVolume]
    top_materials: List[Dict[str, Any]]
    circularity_rate_pct: Optional[float] = None


class CityIndicatorsResponse(BaseModel):
    """Aggregated municipal-level material prevention and circularity indicators."""
    city: str = "Greater Industrial Metro"
    as_of: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    participating_facilities_count: int
    diverted_material_tonnes: float
    active_recovery_routes_count: int
    landfill_diversion_rate_pct: float
    is_estimated: bool = True
    methodology: str = "facility_reporting_and_exchange_aggregated_metrics"


# Re-export municipal intelligence schemas
from strata.schemas.municipal import (  # noqa: E402
    CapacityGapReport,
    DataProvenanceLabel,
    LifecycleFlowBreakdown,
    MunicipalFlowReport,
    MunicipalGeographicSummary,
    ZoneGapIndicator,
    ZoneGeographicIndicator,
)

