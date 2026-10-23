from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from strata.core.auth import AuthUser, get_current_user
from strata.db.session import get_db
from strata.domain.marketplace.cluster import ClusterSynergyEngine
from strata.domain.marketplace.qualification import ProofPathQualificationClient
from strata.domain.marketplace.schemas import (
    AggregationProposal,
    BuyerRequirementCreate,
    BuyerRequirementMatchesResponse,
    BuyerRequirementRead,
    BuyerRequirementUpdate,
    CityIndicatorsResponse,
    ClusterIndicatorsResponse,
    ClusterSummary,
    FreightOption,
    ListingCreate,
    ListingRead,
    ListingStatusUpdateRequest,
    ListingUpdate,
    ListingVisibility,
    LogisticsComparisonRequest,
    LogisticsComparisonResponse,
    LogisticsEstimate,
    LogisticsEstimateRequest,
    MatchCandidateRead,
    OfferCreate,
    OfferRead,
    QualificationResult,
    RFQCreate,
    RFQRead,
    StateTransitionRequest,
    WorkflowEventCreate,
    WorkflowEventRead,
)
from strata.domain.marketplace.service import MarketplaceService
from strata.schemas.common import (
    MetaInfo,
    PaginatedResponseEnvelope,
    PaginationInfo,
    ResponseEnvelope,
)

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


@router.post(
    "/listings",
    response_model=ResponseEnvelope[ListingRead],
    status_code=status.HTTP_201_CREATED,
)
def create_listing(
    payload: ListingCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[ListingRead]:
    """Publishes a material lot owned by the caller's organization to the marketplace."""
    service = MarketplaceService(db)
    created = service.create_listing(payload, org_id=current_user.org_id)
    return ResponseEnvelope(data=created, meta=MetaInfo())


@router.get("/listings", response_model=PaginatedResponseEnvelope[ListingRead])
def list_listings(
    view: str = Query("own", description="'own' to list own listings, 'exchange' or 'all' to search discoverable active listings"),
    category: Optional[str] = Query(None, description="Filter by material category"),
    material_type: Optional[str] = Query(None, description="Filter by material type"),
    unit: Optional[str] = Query(None, description="Filter by unit"),
    min_quantity: Optional[float] = Query(None, description="Minimum available quantity"),
    max_price: Optional[float] = Query(None, description="Maximum asking price per unit"),
    visibility: Optional[ListingVisibility] = Query(None, description="Visibility filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponseEnvelope[ListingRead]:
    """Lists listings (own organization's listings or circular exchange search)."""
    service = MarketplaceService(db)
    if view in ("exchange", "all"):
        items, total = service.search_exchange_listings(
            actor=current_user,
            category=category,
            material_type=material_type,
            unit=unit,
            min_quantity=min_quantity,
            max_price=max_price,
            visibility=visibility,
            page=page,
            page_size=page_size,
        )
    else:
        items, total = service.list_listings(org_id=current_user.org_id, page=page, page_size=page_size)
    return PaginatedResponseEnvelope(
        data=items,
        pagination=PaginationInfo(
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        ),
        meta=MetaInfo(),
    )


@router.get("/listings/{listing_id}", response_model=ResponseEnvelope[ListingRead])
def get_listing(
    listing_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[ListingRead]:
    """Retrieves one of the caller's organization's listings."""
    service = MarketplaceService(db)
    listing = service.get_listing(listing_id=listing_id, org_id=current_user.org_id)
    return ResponseEnvelope(data=listing, meta=MetaInfo())


@router.patch("/listings/{listing_id}", response_model=ResponseEnvelope[ListingRead])
@router.put("/listings/{listing_id}", response_model=ResponseEnvelope[ListingRead])
def update_listing(
    listing_id: str,
    payload: ListingUpdate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[ListingRead]:
    """Updates listing commercial terms, availability, visibility, or status."""
    service = MarketplaceService(db)
    updated = service.update_listing(listing_id=listing_id, payload=payload, actor=current_user)
    return ResponseEnvelope(data=updated, meta=MetaInfo())


@router.get("/listings/{listing_id}/history", response_model=ResponseEnvelope[List[WorkflowEventRead]])
def get_listing_workflow_history(
    listing_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[List[WorkflowEventRead]]:
    """Returns the chronological audit event timeline for a listing."""
    service = MarketplaceService(db)
    events = service.get_workflow_history(entity_id=listing_id, actor=current_user)
    return ResponseEnvelope(data=events, meta=MetaInfo())


@router.post(
    "/buyer-requirements",
    response_model=ResponseEnvelope[BuyerRequirementRead],
    status_code=status.HTTP_201_CREATED,
)
def create_buyer_requirement(
    payload: BuyerRequirementCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[BuyerRequirementRead]:
    """Records a buyer requirement for the caller's organization."""
    service = MarketplaceService(db)
    created = service.create_requirement(payload, org_id=current_user.org_id)
    return ResponseEnvelope(data=created, meta=MetaInfo())


@router.get("/buyer-requirements", response_model=PaginatedResponseEnvelope[BuyerRequirementRead])
def list_buyer_requirements(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponseEnvelope[BuyerRequirementRead]:
    """Lists the caller's organization's buyer requirements."""
    service = MarketplaceService(db)
    items, total = service.list_requirements(org_id=current_user.org_id, page=page, page_size=page_size)
    return PaginatedResponseEnvelope(
        data=items,
        pagination=PaginationInfo(
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        ),
        meta=MetaInfo(),
    )


@router.get(
    "/buyer-requirements/{requirement_id}",
    response_model=ResponseEnvelope[BuyerRequirementRead],
)
def get_buyer_requirement(
    requirement_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[BuyerRequirementRead]:
    """Retrieves one of the caller's organization's buyer requirements."""
    service = MarketplaceService(db)
    requirement = service.get_requirement(requirement_id=requirement_id, org_id=current_user.org_id)
    return ResponseEnvelope(data=requirement, meta=MetaInfo())


@router.patch("/buyer-requirements/{requirement_id}", response_model=ResponseEnvelope[BuyerRequirementRead])
@router.put("/buyer-requirements/{requirement_id}", response_model=ResponseEnvelope[BuyerRequirementRead])
def update_buyer_requirement(
    requirement_id: str,
    payload: BuyerRequirementUpdate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[BuyerRequirementRead]:
    """Updates a buyer requirement."""
    service = MarketplaceService(db)
    updated = service.update_requirement(requirement_id=requirement_id, payload=payload, actor=current_user)
    return ResponseEnvelope(data=updated, meta=MetaInfo())


@router.delete("/buyer-requirements/{requirement_id}", response_model=ResponseEnvelope[dict])
def delete_buyer_requirement(
    requirement_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[dict]:
    """Deletes a buyer requirement."""
    service = MarketplaceService(db)
    service.delete_requirement(requirement_id=requirement_id, actor=current_user)
    return ResponseEnvelope(data={"deleted": True, "id": requirement_id}, meta=MetaInfo())


@router.get(
    "/buyer-requirements/{requirement_id}/matches",
    response_model=ResponseEnvelope[BuyerRequirementMatchesResponse],
)
@router.post(
    "/buyer-requirements/{requirement_id}/matches",
    response_model=ResponseEnvelope[BuyerRequirementMatchesResponse],
)
def match_requirement_candidates(
    requirement_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[BuyerRequirementMatchesResponse]:
    """Matches listings against a buyer requirement with authoritative ProofPath qualification and logistics estimates."""
    service = MarketplaceService(db)
    result = service.match_candidates_with_qualification(requirement_id=requirement_id, org_id=current_user.org_id)
    return ResponseEnvelope(data=result, meta=MetaInfo())


@router.get(
    "/buyer-requirements/{requirement_id}/candidates",
    response_model=ResponseEnvelope[List[ListingRead]],
)
def list_requirement_candidates(
    requirement_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[List[ListingRead]]:
    """Returns other organizations' active listings that meet the requirement's hard filters."""
    service = MarketplaceService(db)
    candidates = service.find_candidates(requirement_id=requirement_id, org_id=current_user.org_id)
    return ResponseEnvelope(data=candidates, meta=MetaInfo())


@router.get(
    "/buyer-requirements/{requirement_id}/qualifications",
    response_model=ResponseEnvelope[List[QualificationResult]],
)
async def qualify_requirement_candidates(
    requirement_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[List[QualificationResult]]:
    """Requests ProofPath qualification for each candidate. Results are ProofPath's, not computed here."""
    service = MarketplaceService(db)
    client = ProofPathQualificationClient()
    results = await service.qualify_candidates(
        requirement_id=requirement_id,
        org_id=current_user.org_id,
        client=client,
    )
    return ResponseEnvelope(data=results, meta=MetaInfo())


# ---------------------------------------------------------------------------
# Listing Lifecycle State Transitions
# ---------------------------------------------------------------------------

@router.post(
    "/listings/{listing_id}/status",
    response_model=ResponseEnvelope[ListingRead],
)
def update_listing_status(
    listing_id: str,
    payload: ListingStatusUpdateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[ListingRead]:
    """Pauses, withdraws, or publishes a listing owned by the caller's organization."""
    service = MarketplaceService(db)
    updated = service.update_listing_status(
        listing_id=listing_id,
        new_status=payload.status,
        actor=current_user,
        notes=payload.notes,
    )
    return ResponseEnvelope(data=updated, meta=MetaInfo())


# ---------------------------------------------------------------------------
# RFQ Workflows
# ---------------------------------------------------------------------------

@router.post(
    "/rfqs",
    response_model=ResponseEnvelope[RFQRead],
    status_code=status.HTTP_201_CREATED,
)
def create_rfq(
    payload: RFQCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[RFQRead]:
    """Initiates a request for quotation against an active listing."""
    service = MarketplaceService(db)
    created = service.create_rfq(payload=payload, actor=current_user)
    return ResponseEnvelope(data=created, meta=MetaInfo())


@router.post(
    "/rfqs/{rfq_id}/submit",
    response_model=ResponseEnvelope[RFQRead],
)
def submit_rfq(
    rfq_id: str,
    payload: Optional[StateTransitionRequest] = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[RFQRead]:
    """Submits a DRAFT RFQ for human approval."""
    service = MarketplaceService(db)
    updated = service.submit_rfq_for_approval(
        rfq_id=rfq_id,
        actor=current_user,
        notes=payload.notes if payload else None,
    )
    return ResponseEnvelope(data=updated, meta=MetaInfo())


@router.post(
    "/rfqs/{rfq_id}/approve",
    response_model=ResponseEnvelope[RFQRead],
)
def approve_rfq(
    rfq_id: str,
    payload: Optional[StateTransitionRequest] = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[RFQRead]:
    """Human approval gate: facility_manager or admin approves the RFQ to open it for offers."""
    service = MarketplaceService(db)
    approved = service.approve_rfq(
        rfq_id=rfq_id,
        actor=current_user,
        notes=payload.notes if payload else None,
    )
    return ResponseEnvelope(data=approved, meta=MetaInfo())


@router.post(
    "/rfqs/{rfq_id}/cancel",
    response_model=ResponseEnvelope[RFQRead],
)
def cancel_rfq(
    rfq_id: str,
    payload: Optional[StateTransitionRequest] = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[RFQRead]:
    """Cancels an RFQ."""
    service = MarketplaceService(db)
    cancelled = service.cancel_rfq(
        rfq_id=rfq_id,
        actor=current_user,
        notes=payload.notes if payload else None,
    )
    return ResponseEnvelope(data=cancelled, meta=MetaInfo())


@router.get(
    "/rfqs",
    response_model=PaginatedResponseEnvelope[RFQRead],
)
def list_rfqs(
    as_buyer: Optional[bool] = Query(None, description="Filter as buyer or seller"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponseEnvelope[RFQRead]:
    """Lists RFQs involving the caller's organization."""
    service = MarketplaceService(db)
    items, total = service.list_rfqs(
        actor=current_user,
        as_buyer=as_buyer,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponseEnvelope(
        data=items,
        pagination=PaginationInfo(
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        ),
        meta=MetaInfo(),
    )


@router.get(
    "/rfqs/{rfq_id}",
    response_model=ResponseEnvelope[RFQRead],
)
def get_rfq(
    rfq_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[RFQRead]:
    """Retrieves an RFQ."""
    service = MarketplaceService(db)
    rfq = service.get_rfq(rfq_id=rfq_id, actor=current_user)
    return ResponseEnvelope(data=rfq, meta=MetaInfo())


@router.get(
    "/rfqs/{rfq_id}/history",
    response_model=ResponseEnvelope[List[WorkflowEventRead]],
)
def get_rfq_workflow_history(
    rfq_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[List[WorkflowEventRead]]:
    """Returns the chronological audit event timeline for an RFQ."""
    service = MarketplaceService(db)
    events = service.get_workflow_history(entity_id=rfq_id, actor=current_user)
    return ResponseEnvelope(data=events, meta=MetaInfo())


# ---------------------------------------------------------------------------
# Offer / Quote Workflows
# ---------------------------------------------------------------------------

@router.post(
    "/rfqs/{rfq_id}/offers",
    response_model=ResponseEnvelope[OfferRead],
    status_code=status.HTTP_201_CREATED,
)
def submit_offer(
    rfq_id: str,
    payload: OfferCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[OfferRead]:
    """Seller submits a commercial offer/quote against an OPEN RFQ."""
    service = MarketplaceService(db)
    created = service.submit_offer(rfq_id=rfq_id, payload=payload, actor=current_user)
    return ResponseEnvelope(data=created, meta=MetaInfo())


@router.get(
    "/rfqs/{rfq_id}/offers",
    response_model=ResponseEnvelope[List[OfferRead]],
)
def list_rfq_offers(
    rfq_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[List[OfferRead]]:
    """Lists offers submitted for an RFQ."""
    service = MarketplaceService(db)
    offers = service.list_offers_for_rfq(rfq_id=rfq_id, actor=current_user)
    return ResponseEnvelope(data=offers, meta=MetaInfo())


@router.post(
    "/offers/{offer_id}/accept",
    response_model=ResponseEnvelope[OfferRead],
)
def accept_offer(
    offer_id: str,
    payload: Optional[StateTransitionRequest] = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[OfferRead]:
    """Human approval gate: buyer_admin or admin accepts a binding commercial offer."""
    service = MarketplaceService(db)
    accepted = service.accept_offer(
        offer_id=offer_id,
        actor=current_user,
        notes=payload.notes if payload else None,
    )
    return ResponseEnvelope(data=accepted, meta=MetaInfo())


@router.post(
    "/offers/{offer_id}/reject",
    response_model=ResponseEnvelope[OfferRead],
)
def reject_offer(
    offer_id: str,
    payload: Optional[StateTransitionRequest] = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[OfferRead]:
    """Buyer rejects an offer."""
    service = MarketplaceService(db)
    rejected = service.reject_offer(
        offer_id=offer_id,
        actor=current_user,
        notes=payload.notes if payload else None,
    )
    return ResponseEnvelope(data=rejected, meta=MetaInfo())


# ---------------------------------------------------------------------------
# Cluster Synergy and Batch Aggregation (Hitendra)
# ---------------------------------------------------------------------------

@router.get(
    "/cluster/{cluster_id}/synergies",
    response_model=ResponseEnvelope[List[AggregationProposal]],
)
def get_cluster_synergies(
    cluster_id: str,
    requirement_id: Optional[str] = Query(None, description="Optional target buyer requirement UUID"),
    max_lots_per_batch: int = Query(5, ge=1, le=10, description="Max lots to aggregate into a batch proposal"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[List[AggregationProposal]]:
    """Identifies multi-lot aggregation proposals meeting buyer volume thresholds within the cluster."""
    engine = ClusterSynergyEngine(db)
    if requirement_id:
        proposals = engine.generate_aggregation_proposals(
            requirement_id=requirement_id,
            cluster_id=cluster_id,
            max_lots_per_batch=max_lots_per_batch,
        )
    else:
        # Retrieve all active buyer requirements accessible
        all_reqs = engine.repository.list_all_requirements()
        proposals = []
        for req in all_reqs:
            p = engine.generate_aggregation_proposals(
                requirement_id=req.id,
                cluster_id=cluster_id,
                max_lots_per_batch=max_lots_per_batch,
            )
            proposals.extend(p)
    return ResponseEnvelope(data=proposals, meta=MetaInfo())


@router.post(
    "/cluster/logistics-estimate",
    response_model=ResponseEnvelope[LogisticsEstimate],
)
def calculate_cluster_logistics(
    payload: LogisticsEstimateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[LogisticsEstimate]:
    """Calculates indicative consolidation route distance, transport cost (INR), and transport emissions."""
    engine = ClusterSynergyEngine(db)
    estimate = engine.calculate_indicative_logistics(
        lot_ids=payload.lot_ids,
        destination_facility_id=payload.destination_facility_id,
        rate_per_km_tonne=payload.rate_per_km_tonne,
    )
    return ResponseEnvelope(data=estimate, meta=MetaInfo())


@router.get(
    "/cluster/{cluster_id}/indicators",
    response_model=ResponseEnvelope[ClusterSummary],
)
def get_cluster_synergy_indicators(
    cluster_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[ClusterSummary]:
    """Returns aggregated cluster circularity metrics, material tonnage breakdown, and synergy opportunities."""
    engine = ClusterSynergyEngine(db)
    summary = engine.get_cluster_indicators(cluster_id=cluster_id)
    return ResponseEnvelope(data=summary, meta=MetaInfo())


# ---------------------------------------------------------------------------
# Offer Review / Withdraw (Aarushi - Circular Exchange)
# ---------------------------------------------------------------------------

@router.post(
    "/offers/{offer_id}/review",
    response_model=ResponseEnvelope[OfferRead],
)
def review_offer(
    offer_id: str,
    payload: Optional[StateTransitionRequest] = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[OfferRead]:
    """Buyer marks an offer as under review."""
    service = MarketplaceService(db)
    reviewed = service.review_offer(
        offer_id=offer_id,
        actor=current_user,
        notes=payload.notes if payload else None,
    )
    return ResponseEnvelope(data=reviewed, meta=MetaInfo())


@router.post(
    "/offers/{offer_id}/withdraw",
    response_model=ResponseEnvelope[OfferRead],
)
def withdraw_offer(
    offer_id: str,
    payload: Optional[StateTransitionRequest] = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[OfferRead]:
    """Seller withdraws their commercial offer."""
    service = MarketplaceService(db)
    withdrawn = service.withdraw_offer(
        offer_id=offer_id,
        actor=current_user,
        notes=payload.notes if payload else None,
    )
    return ResponseEnvelope(data=withdrawn, meta=MetaInfo())


# ---------------------------------------------------------------------------
# Workflow Events API (Aarushi - Circular Exchange)
# ---------------------------------------------------------------------------

@router.post(
    "/events",
    response_model=ResponseEnvelope[WorkflowEventRead],
    status_code=status.HTTP_201_CREATED,
)
def record_workflow_event(
    payload: WorkflowEventCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[WorkflowEventRead]:
    """Records an auditable workflow event."""
    service = MarketplaceService(db)
    event = service.record_custom_event(payload=payload, actor=current_user)
    return ResponseEnvelope(data=event, meta=MetaInfo())


@router.get(
    "/events",
    response_model=PaginatedResponseEnvelope[WorkflowEventRead],
)
def list_workflow_events(
    entity_type: Optional[str] = Query(None, description="Filter by entity type (listing, rfq, offer, requirement)"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponseEnvelope[WorkflowEventRead]:
    """Lists auditable workflow events for the organization."""
    service = MarketplaceService(db)
    items, total = service.list_workflow_events(
        actor=current_user,
        entity_type=entity_type,
        entity_id=entity_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponseEnvelope(
        data=items,
        pagination=PaginationInfo(
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        ),
        meta=MetaInfo(),
    )


@router.get(
    "/events/{entity_id}",
    response_model=ResponseEnvelope[List[WorkflowEventRead]],
)
def get_entity_workflow_history(
    entity_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[List[WorkflowEventRead]]:
    """Retrieves the full workflow history for any entity (listing, rfq, etc.)."""
    service = MarketplaceService(db)
    events = service.get_workflow_history(entity_id=entity_id, actor=current_user)
    return ResponseEnvelope(data=events, meta=MetaInfo())


# ---------------------------------------------------------------------------
# Logistics Comparison and Exchange Indicators (Aarushi - Circular Exchange)
# ---------------------------------------------------------------------------

@router.post(
    "/logistics/compare",
    response_model=ResponseEnvelope[LogisticsComparisonResponse],
)
@router.get(
    "/logistics/compare",
    response_model=ResponseEnvelope[LogisticsComparisonResponse],
)
def compare_logistics(
    origin_facility_id: Optional[str] = Query(None),
    destination_facility_id: Optional[str] = Query(None),
    origin_location: Optional[str] = Query(None),
    destination_location: Optional[str] = Query(None),
    quantity: float = Query(1000.0, gt=0),
    unit: str = Query("kg"),
    material_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[LogisticsComparisonResponse]:
    """Compares freight transport options across diesel, electric, and rail."""
    service = MarketplaceService(db)
    req = LogisticsComparisonRequest(
        origin_facility_id=origin_facility_id,
        destination_facility_id=destination_facility_id,
        origin_location=origin_location,
        destination_location=destination_location,
        quantity=quantity,
        unit=unit,
        material_type=material_type,
    )
    result = service.compare_logistics(req)
    return ResponseEnvelope(data=result, meta=MetaInfo())


@router.get(
    "/cluster/indicators",
    response_model=ResponseEnvelope[ClusterIndicatorsResponse],
)
def get_cluster_indicators(
    cluster_id: Optional[str] = Query(None, description="Cluster UUID"),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[ClusterIndicatorsResponse]:
    """Exposes cluster-level circular exchange indicators aggregated from persisted records."""
    service = MarketplaceService(db)
    indicators = service.get_cluster_indicators(cluster_id=cluster_id)
    return ResponseEnvelope(data=indicators, meta=MetaInfo())


@router.get(
    "/city/indicators",
    response_model=ResponseEnvelope[CityIndicatorsResponse],
)
def get_city_indicators(
    db: Session = Depends(get_db),
) -> ResponseEnvelope[CityIndicatorsResponse]:
    """Exposes city-level material prevention and diversion indicators."""
    service = MarketplaceService(db)
    indicators = service.get_city_indicators()
    return ResponseEnvelope(data=indicators, meta=MetaInfo())
