from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from strata.core.auth import AuthUser, get_current_user
from strata.db.session import get_db
from strata.domain.marketplace.qualification import ProofPathQualificationClient
from strata.domain.marketplace.schemas import (
    BuyerRequirementCreate,
    BuyerRequirementRead,
    ListingCreate,
    ListingRead,
    ListingStatusUpdateRequest,
    OfferCreate,
    OfferRead,
    QualificationResult,
    RFQCreate,
    RFQRead,
    StateTransitionRequest,
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
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponseEnvelope[ListingRead]:
    """Lists the caller's organization's own listings."""
    service = MarketplaceService(db)
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
