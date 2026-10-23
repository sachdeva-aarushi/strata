"""Marketplace domain service: listings, buyer requirements and candidate matching.

Candidate filtering is pure (``matches_requirement`` / ``filter_candidates``).
``MarketplaceService`` wires it to persistence and to ProofPath. Qualification
is requested from ProofPath for each candidate and is never computed here.
Material lots and their canonical ``material_lot_id`` remain owned by the
materials registry.
"""

from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Tuple

from pydantic import BaseModel
from sqlalchemy.orm import Session

from strata.core.auth import AuthUser
from strata.core.errors import (
    ForbiddenError,
    InvalidStateTransitionError,
    ResourceNotFoundError,
    ValidationError,
)
from strata.domain.marketplace.models import (
    BuyerRequirement,
    Listing,
    OfferModel,
    RFQModel,
    WorkflowEventModel,
)
from strata.domain.marketplace.qualification import ProofPathQualificationClient
from strata.domain.marketplace.repository import MarketplaceRepository
from strata.domain.marketplace.schemas import (
    BuyerRequirementCreate,
    BuyerRequirementRead,
    ListingCreate,
    ListingRead,
    ListingStatus,
    ListingVisibility,
    OfferCreate,
    OfferRead,
    OfferStatus,
    QualificationResult,
    RFQCreate,
    RFQRead,
    RFQStatus,
    WorkflowEventRead,
    WorkflowEventType,
)
from strata.domain.materials.taxonomy import get_all_material_types, get_material_type

DEFAULT_VISIBILITY_LEVELS: FrozenSet[ListingVisibility] = frozenset(
    {ListingVisibility.PUBLIC, ListingVisibility.CLUSTER_ONLY}
)


class CandidateListing(BaseModel):
    """A listing paired with the material category of its lot.

    ``material_category`` is a snapshot taken from the materials registry by the
    caller; this module does not own or re-derive it.
    """
    listing: ListingRead
    material_category: str


def _normalise(value: str) -> str:
    return value.strip().lower()


def matches_requirement(
    candidate: CandidateListing,
    requirement: BuyerRequirementRead,
    visibility_levels: Optional[Iterable[ListingVisibility]] = None,
) -> bool:
    """True when a single listing satisfies every hard filter of the requirement.

    Filters:
      * status is ACTIVE (drafts, paused, sold-out and withdrawn listings are excluded)
      * visibility is within ``visibility_levels`` (default: public and cluster_only)
      * material category matches (case-insensitive)
      * unit matches (case-insensitive)
      * available quantity covers ``min_quantity``

    ``max_quantity`` is not a filter: a larger listing can still serve a buyer
    who takes at most ``max_quantity``.
    """
    levels = frozenset(visibility_levels) if visibility_levels is not None else DEFAULT_VISIBILITY_LEVELS
    listing = candidate.listing

    if listing.status != ListingStatus.ACTIVE:
        return False
    if listing.visibility not in levels:
        return False
    if _normalise(candidate.material_category) != _normalise(requirement.material_category):
        return False
    if _normalise(listing.unit) != _normalise(requirement.unit):
        return False
    if listing.available_quantity < requirement.min_quantity:
        return False
    return True


def filter_candidates(
    candidates: Iterable[CandidateListing],
    requirement: BuyerRequirementRead,
    visibility_levels: Optional[Iterable[ListingVisibility]] = None,
) -> List[CandidateListing]:
    """Return the listings that match the requirement, preserving input order."""
    return [
        c for c in candidates
        if matches_requirement(c, requirement, visibility_levels=visibility_levels)
    ]


class MarketplaceService:
    """Orchestrates marketplace persistence, candidate matching and qualification."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = MarketplaceRepository(db)

    # -- listings -----------------------------------------------------------

    def create_listing(self, payload: ListingCreate, org_id: str) -> ListingRead:
        """Publishes a lot the caller's organization owns, after checking it against the registry."""
        lot = self.repository.get_lot_for_org(lot_id=payload.material_lot_id, org_id=org_id)
        if not lot:
            raise ResourceNotFoundError(
                f"Material lot '{payload.material_lot_id}' was not found in your organization scope.",
                details={"material_lot_id": payload.material_lot_id},
            )
        if lot.facility_id != payload.facility_id:
            raise ValidationError(
                "facility_id does not match the facility that registered this lot.",
                details={"facility_id": payload.facility_id, "lot_facility_id": lot.facility_id},
            )
        if _normalise(payload.unit) != _normalise(lot.unit):
            raise ValidationError(
                f"Listing unit '{payload.unit}' must match the lot unit '{lot.unit}'.",
                details={"unit": payload.unit, "lot_unit": lot.unit},
            )
        if payload.available_quantity > lot.quantity:
            raise ValidationError(
                "available_quantity cannot exceed the quantity registered for this lot.",
                details={"available_quantity": payload.available_quantity, "lot_quantity": lot.quantity},
            )

        listing = Listing(
            material_lot_id=lot.lot_id,
            organization_id=org_id,
            facility_id=lot.facility_id,
            visibility=payload.visibility,
            asking_price_per_unit=payload.asking_price_per_unit,
            currency=payload.currency,
            available_quantity=payload.available_quantity,
            unit=lot.unit,
            status=payload.status,
        )
        saved = self.repository.add_listing(listing)
        return ListingRead.model_validate(saved)

    def get_listing(self, listing_id: str, org_id: str) -> ListingRead:
        listing = self.repository.get_listing(listing_id=listing_id, org_id=org_id)
        if not listing:
            raise ResourceNotFoundError(
                f"Listing '{listing_id}' was not found in your organization scope.",
                details={"listing_id": listing_id},
            )
        return ListingRead.model_validate(listing)

    def list_listings(self, org_id: str, page: int, page_size: int) -> Tuple[List[ListingRead], int]:
        skip = (page - 1) * page_size
        rows, total = self.repository.list_listings(org_id=org_id, skip=skip, limit=page_size)
        return [ListingRead.model_validate(r) for r in rows], total

    # -- buyer requirements -------------------------------------------------

    def create_requirement(self, payload: BuyerRequirementCreate, org_id: str) -> BuyerRequirementRead:
        valid_categories = {t.category for t in get_all_material_types()}
        if payload.material_category not in valid_categories:
            raise ValidationError(
                f"Unknown material category '{payload.material_category}'.",
                details={"material_category": payload.material_category, "allowed": sorted(valid_categories)},
            )
        requirement = BuyerRequirement(
            organization_id=org_id,
            facility_id=payload.facility_id,
            material_category=payload.material_category,
            min_quantity=payload.min_quantity,
            max_quantity=payload.max_quantity,
            unit=payload.unit,
            target_price_per_unit=payload.target_price_per_unit,
            required_properties=payload.required_properties,
            prohibited_conditions=payload.prohibited_conditions,
            visibility=payload.visibility,
        )
        saved = self.repository.add_requirement(requirement)
        return BuyerRequirementRead.model_validate(saved)

    def get_requirement(self, requirement_id: str, org_id: str) -> BuyerRequirementRead:
        requirement = self.repository.get_requirement(requirement_id=requirement_id, org_id=org_id)
        if not requirement:
            raise ResourceNotFoundError(
                f"Buyer requirement '{requirement_id}' was not found in your organization scope.",
                details={"requirement_id": requirement_id},
            )
        return BuyerRequirementRead.model_validate(requirement)

    # -- matching and qualification ----------------------------------------

    def find_candidates(self, requirement_id: str, org_id: str) -> List[ListingRead]:
        """Active listings from other organizations that satisfy the requirement's hard filters."""
        requirement = self.get_requirement(requirement_id=requirement_id, org_id=org_id)
        listings = self.repository.list_discoverable_listings(
            exclude_org_id=org_id,
            visibility_levels=sorted(DEFAULT_VISIBILITY_LEVELS, key=lambda v: v.value),
        )
        lots = self.repository.get_lots_by_ids([l.material_lot_id for l in listings])

        candidates: List[CandidateListing] = []
        for listing in listings:
            lot = lots.get(listing.material_lot_id)
            if lot is None:
                continue
            taxonomy = get_material_type(lot.material_type)
            if taxonomy is None:
                continue
            candidates.append(
                CandidateListing(
                    listing=ListingRead.model_validate(listing),
                    material_category=taxonomy.category,
                )
            )

        matched = filter_candidates(candidates, requirement)
        return [c.listing for c in matched]

    async def qualify_candidates(
        self,
        requirement_id: str,
        org_id: str,
        client: ProofPathQualificationClient,
    ) -> List[QualificationResult]:
        """Asks ProofPath to assess each candidate lot against the requirement."""
        candidates = self.find_candidates(requirement_id=requirement_id, org_id=org_id)
        results: List[QualificationResult] = []
        for listing in candidates:
            raw = await client.assess_lot_qualification(listing.material_lot_id, requirement_id)
            results.append(QualificationResult.model_validate(raw))
        return results

    # -- workflow event recording -------------------------------------------

    def _record_event(
        self,
        entity_type: str,
        entity_id: str,
        event_type: WorkflowEventType,
        from_state: Optional[str],
        to_state: str,
        actor: AuthUser,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowEventModel:
        event = WorkflowEventModel(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type.value,
            from_state=from_state,
            to_state=to_state,
            actor_id=actor.user_id,
            actor_role=actor.role,
            actor_org_id=actor.org_id,
            notes=notes,
            metadata_payload=metadata or {},
        )
        return self.repository.add_workflow_event(event)

    # -- listing lifecycle state transitions --------------------------------

    def update_listing_status(
        self,
        listing_id: str,
        new_status: ListingStatus,
        actor: AuthUser,
        notes: Optional[str] = None,
    ) -> ListingRead:
        """Transitions a listing's lifecycle state (publish, pause, withdraw)."""
        listing = self.repository.get_listing(listing_id=listing_id, org_id=actor.org_id)
        if not listing:
            raise ResourceNotFoundError(
                f"Listing '{listing_id}' was not found in your organization scope.",
                details={"listing_id": listing_id},
            )

        if listing.status == new_status:
            return ListingRead.model_validate(listing)

        # Explicit transition rules:
        valid_transitions = {
            ListingStatus.DRAFT: {ListingStatus.ACTIVE, ListingStatus.WITHDRAWN},
            ListingStatus.ACTIVE: {ListingStatus.PAUSED, ListingStatus.WITHDRAWN, ListingStatus.SOLD_OUT},
            ListingStatus.PAUSED: {ListingStatus.ACTIVE, ListingStatus.WITHDRAWN},
        }

        allowed = valid_transitions.get(listing.status, set())
        if new_status not in allowed:
            raise InvalidStateTransitionError(
                f"Cannot transition listing from '{listing.status.value}' to '{new_status.value}'.",
                details={
                    "current_status": listing.status.value,
                    "target_status": new_status.value,
                    "allowed_transitions": [s.value for s in allowed],
                },
            )

        old_status = listing.status
        updated = self.repository.update_listing_status(listing, new_status)

        if new_status == ListingStatus.ACTIVE:
            event_type = WorkflowEventType.LISTING_PUBLISHED
        elif new_status == ListingStatus.PAUSED:
            event_type = WorkflowEventType.LISTING_PAUSED
        elif new_status == ListingStatus.WITHDRAWN:
            event_type = WorkflowEventType.LISTING_WITHDRAWN
        else:
            event_type = WorkflowEventType.LISTING_PAUSED

        self._record_event(
            entity_type="listing",
            entity_id=updated.id,
            event_type=event_type,
            from_state=old_status.value,
            to_state=new_status.value,
            actor=actor,
            notes=notes,
        )

        return ListingRead.model_validate(updated)

    # -- RFQ lifecycle and state transitions --------------------------------

    def create_rfq(self, payload: RFQCreate, actor: AuthUser) -> RFQRead:
        """Creates an RFQ against an active listing."""
        listing = self.repository.get_listing_by_id(payload.listing_id)
        if not listing:
            raise ResourceNotFoundError(
                f"Target listing '{payload.listing_id}' not found.",
                details={"listing_id": payload.listing_id},
            )

        if listing.status != ListingStatus.ACTIVE:
            raise InvalidStateTransitionError(
                f"Cannot create RFQ for listing '{payload.listing_id}' with status '{listing.status.value}'. Listing must be active.",
                details={"listing_status": listing.status.value},
            )

        if listing.organization_id == actor.org_id:
            raise ValidationError(
                "An organization cannot submit an RFQ against its own listing.",
                details={"listing_id": listing.id, "organization_id": actor.org_id},
            )

        if payload.buyer_requirement_id:
            req = self.repository.get_requirement(
                requirement_id=payload.buyer_requirement_id,
                org_id=actor.org_id,
            )
            if not req:
                raise ResourceNotFoundError(
                    f"Buyer requirement '{payload.buyer_requirement_id}' was not found in your organization scope.",
                    details={"buyer_requirement_id": payload.buyer_requirement_id},
                )

        if _normalise(payload.unit) != _normalise(listing.unit):
            raise ValidationError(
                f"Requested unit '{payload.unit}' does not match listing unit '{listing.unit}'.",
                details={"requested_unit": payload.unit, "listing_unit": listing.unit},
            )

        initial_status = RFQStatus.PENDING_APPROVAL if payload.submit_for_approval else RFQStatus.DRAFT

        rfq = RFQModel(
            listing_id=listing.id,
            buyer_requirement_id=payload.buyer_requirement_id,
            buyer_organization_id=actor.org_id,
            buyer_facility_id=payload.buyer_facility_id,
            seller_organization_id=listing.organization_id,
            seller_facility_id=listing.facility_id,
            requested_quantity=payload.requested_quantity,
            unit=listing.unit,
            target_price_per_unit=payload.target_price_per_unit,
            currency=payload.currency,
            status=initial_status,
            notes=payload.notes,
            created_by=actor.user_id,
        )
        saved = self.repository.add_rfq(rfq)

        self._record_event(
            entity_type="rfq",
            entity_id=saved.id,
            event_type=WorkflowEventType.RFQ_CREATED,
            from_state=None,
            to_state=initial_status.value,
            actor=actor,
            notes=payload.notes,
        )

        if initial_status == RFQStatus.PENDING_APPROVAL:
            self._record_event(
                entity_type="rfq",
                entity_id=saved.id,
                event_type=WorkflowEventType.RFQ_SUBMITTED,
                from_state=RFQStatus.DRAFT.value,
                to_state=RFQStatus.PENDING_APPROVAL.value,
                actor=actor,
                notes="Directly submitted for human approval upon creation.",
            )

        return RFQRead.model_validate(saved)

    def submit_rfq_for_approval(
        self,
        rfq_id: str,
        actor: AuthUser,
        notes: Optional[str] = None,
    ) -> RFQRead:
        """Transitions a DRAFT RFQ to PENDING_APPROVAL."""
        rfq = self.repository.get_rfq(rfq_id=rfq_id)
        if not rfq or (actor.role != "admin" and rfq.buyer_organization_id != actor.org_id):
            raise ResourceNotFoundError(
                f"RFQ '{rfq_id}' was not found in your organization scope.",
                details={"rfq_id": rfq_id},
            )

        if rfq.status != RFQStatus.DRAFT:
            raise InvalidStateTransitionError(
                f"Cannot submit RFQ with status '{rfq.status.value}' for approval. Only DRAFT RFQs can be submitted.",
                details={"current_status": rfq.status.value},
            )

        updated = self.repository.update_rfq_status(rfq, RFQStatus.PENDING_APPROVAL)
        self._record_event(
            entity_type="rfq",
            entity_id=updated.id,
            event_type=WorkflowEventType.RFQ_SUBMITTED,
            from_state=RFQStatus.DRAFT.value,
            to_state=RFQStatus.PENDING_APPROVAL.value,
            actor=actor,
            notes=notes,
        )
        return RFQRead.model_validate(updated)

    def approve_rfq(
        self,
        rfq_id: str,
        actor: AuthUser,
        notes: Optional[str] = None,
    ) -> RFQRead:
        """Human approval gate: opens an RFQ for external seller offers.

        Requires: actor.role in ['facility_manager', 'admin'].
        """
        if actor.role not in ["facility_manager", "admin"]:
            raise ForbiddenError(
                f"Role '{actor.role}' is not authorized to approve RFQs. Required: facility_manager or admin.",
                details={"required_roles": ["facility_manager", "admin"], "current_role": actor.role},
            )

        rfq = self.repository.get_rfq(rfq_id=rfq_id)
        if not rfq:
            raise ResourceNotFoundError(
                f"RFQ '{rfq_id}' was not found.",
                details={"rfq_id": rfq_id},
            )

        if actor.role != "admin" and rfq.buyer_organization_id != actor.org_id:
            raise ResourceNotFoundError(
                f"RFQ '{rfq_id}' was not found in your organization scope.",
                details={"rfq_id": rfq_id},
            )

        if rfq.status not in [RFQStatus.PENDING_APPROVAL, RFQStatus.DRAFT]:
            raise InvalidStateTransitionError(
                f"Cannot approve RFQ with status '{rfq.status.value}'.",
                details={"current_status": rfq.status.value},
            )

        old_status = rfq.status
        updated = self.repository.update_rfq_status(rfq, RFQStatus.OPEN)

        self._record_event(
            entity_type="rfq",
            entity_id=updated.id,
            event_type=WorkflowEventType.RFQ_APPROVED,
            from_state=old_status.value,
            to_state=RFQStatus.OPEN.value,
            actor=actor,
            notes=notes,
        )
        return RFQRead.model_validate(updated)

    def cancel_rfq(
        self,
        rfq_id: str,
        actor: AuthUser,
        notes: Optional[str] = None,
    ) -> RFQRead:
        """Cancels an RFQ."""
        rfq = self.repository.get_rfq(rfq_id=rfq_id)
        if not rfq:
            raise ResourceNotFoundError(f"RFQ '{rfq_id}' was not found.")

        if actor.role != "admin" and actor.org_id not in [rfq.buyer_organization_id, rfq.seller_organization_id]:
            raise ResourceNotFoundError(f"RFQ '{rfq_id}' was not found in your organization scope.")

        if rfq.status in [RFQStatus.CLOSED, RFQStatus.CANCELLED]:
            raise InvalidStateTransitionError(
                f"Cannot cancel RFQ with status '{rfq.status.value}'.",
                details={"current_status": rfq.status.value},
            )

        old_status = rfq.status
        updated = self.repository.update_rfq_status(rfq, RFQStatus.CANCELLED)
        self._record_event(
            entity_type="rfq",
            entity_id=updated.id,
            event_type=WorkflowEventType.RFQ_CANCELLED,
            from_state=old_status.value,
            to_state=RFQStatus.CANCELLED.value,
            actor=actor,
            notes=notes,
        )
        return RFQRead.model_validate(updated)

    def get_rfq(self, rfq_id: str, actor: AuthUser) -> RFQRead:
        rfq = self.repository.get_rfq(rfq_id=rfq_id)
        if not rfq:
            raise ResourceNotFoundError(f"RFQ '{rfq_id}' was not found.")
        if actor.role != "admin" and actor.org_id not in [rfq.buyer_organization_id, rfq.seller_organization_id]:
            raise ResourceNotFoundError(f"RFQ '{rfq_id}' was not found in your organization scope.")
        return RFQRead.model_validate(rfq)

    def list_rfqs(
        self,
        actor: AuthUser,
        as_buyer: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[RFQRead], int]:
        skip = (page - 1) * page_size
        rows, total = self.repository.list_rfqs_for_org(
            org_id=actor.org_id,
            as_buyer=as_buyer,
            skip=skip,
            limit=page_size,
        )
        return [RFQRead.model_validate(r) for r in rows], total

    # -- Offer lifecycle and state transitions ------------------------------

    def submit_offer(
        self,
        rfq_id: str,
        payload: OfferCreate,
        actor: AuthUser,
    ) -> OfferRead:
        """Seller submits a commercial offer/quote against an OPEN RFQ."""
        rfq = self.repository.get_rfq(rfq_id=rfq_id)
        if not rfq:
            raise ResourceNotFoundError(
                f"RFQ '{rfq_id}' was not found.",
                details={"rfq_id": rfq_id},
            )

        if rfq.status != RFQStatus.OPEN:
            raise InvalidStateTransitionError(
                f"Cannot submit offer for RFQ with status '{rfq.status.value}'. RFQ must be OPEN.",
                details={"rfq_id": rfq_id, "rfq_status": rfq.status.value},
            )

        if actor.role != "admin" and rfq.seller_organization_id != actor.org_id:
            raise ForbiddenError(
                "Only the seller organization can submit an offer for this RFQ.",
                details={"rfq_seller_org": rfq.seller_organization_id, "actor_org": actor.org_id},
            )

        if _normalise(payload.unit) != _normalise(rfq.unit):
            raise ValidationError(
                f"Offered unit '{payload.unit}' must match RFQ unit '{rfq.unit}'.",
                details={"offered_unit": payload.unit, "rfq_unit": rfq.unit},
            )

        offer = OfferModel(
            rfq_id=rfq.id,
            listing_id=rfq.listing_id,
            seller_organization_id=rfq.seller_organization_id,
            seller_facility_id=rfq.seller_facility_id,
            offered_quantity=payload.offered_quantity,
            unit=rfq.unit,
            price_per_unit=payload.price_per_unit,
            currency=payload.currency,
            status=OfferStatus.SUBMITTED,
            terms=payload.terms,
            valid_until=payload.valid_until,
            created_by=actor.user_id,
        )
        saved = self.repository.add_offer(offer)

        self._record_event(
            entity_type="offer",
            entity_id=saved.id,
            event_type=WorkflowEventType.OFFER_SUBMITTED,
            from_state=None,
            to_state=OfferStatus.SUBMITTED.value,
            actor=actor,
            notes=payload.notes,
            metadata={
                "rfq_id": rfq.id,
                "price_per_unit": saved.price_per_unit,
                "offered_quantity": saved.offered_quantity,
            },
        )
        return OfferRead.model_validate(saved)

    def revise_offer(
        self,
        offer_id: str,
        payload: OfferCreate,
        actor: AuthUser,
    ) -> OfferRead:
        """Seller revises an active offer."""
        offer = self.repository.get_offer(offer_id=offer_id)
        if not offer:
            raise ResourceNotFoundError(
                f"Offer '{offer_id}' was not found.",
                details={"offer_id": offer_id},
            )

        if actor.role != "admin" and offer.seller_organization_id != actor.org_id:
            raise ForbiddenError(
                "Only the seller organization may revise this offer.",
                details={"seller_org": offer.seller_organization_id, "actor_org": actor.org_id},
            )

        rfq = self.repository.get_rfq(offer.rfq_id)
        if not rfq or rfq.status != RFQStatus.OPEN:
            raise InvalidStateTransitionError(
                "Cannot revise offer when the linked RFQ is not OPEN.",
                details={"rfq_status": rfq.status.value if rfq else None},
            )

        if offer.status in [OfferStatus.ACCEPTED, OfferStatus.REJECTED, OfferStatus.WITHDRAWN]:
            raise InvalidStateTransitionError(
                f"Cannot revise offer with status '{offer.status.value}'.",
                details={"offer_status": offer.status.value},
            )

        old_status = offer.status
        offer.offered_quantity = payload.offered_quantity
        offer.price_per_unit = payload.price_per_unit
        offer.currency = payload.currency
        offer.terms = payload.terms
        offer.valid_until = payload.valid_until
        updated = self.repository.update_offer_status(offer, OfferStatus.REVISED)

        self._record_event(
            entity_type="offer",
            entity_id=updated.id,
            event_type=WorkflowEventType.OFFER_REVISED,
            from_state=old_status.value,
            to_state=OfferStatus.REVISED.value,
            actor=actor,
            notes=payload.notes,
        )
        return OfferRead.model_validate(updated)

    def accept_offer(
        self,
        offer_id: str,
        actor: AuthUser,
        notes: Optional[str] = None,
    ) -> OfferRead:
        """Human approval gate: buyer accepts a binding offer.

        Requires: actor.role in ['buyer_admin', 'admin'].
        Closes the RFQ and automatically marks other open offers as REJECTED.
        """
        if actor.role not in ["buyer_admin", "admin"]:
            raise ForbiddenError(
                f"Role '{actor.role}' is not authorized to accept binding offers. Required: buyer_admin or admin.",
                details={"required_roles": ["buyer_admin", "admin"], "current_role": actor.role},
            )

        offer = self.repository.get_offer(offer_id=offer_id)
        if not offer:
            raise ResourceNotFoundError(
                f"Offer '{offer_id}' was not found.",
                details={"offer_id": offer_id},
            )

        rfq = self.repository.get_rfq(rfq_id=offer.rfq_id)
        if not rfq:
            raise ResourceNotFoundError(f"Linked RFQ '{offer.rfq_id}' was not found.")

        if actor.role != "admin" and rfq.buyer_organization_id != actor.org_id:
            raise ForbiddenError(
                "Only the buyer organization can accept an offer for this RFQ.",
                details={"buyer_organization_id": rfq.buyer_organization_id, "actor_org": actor.org_id},
            )

        if rfq.status != RFQStatus.OPEN:
            raise InvalidStateTransitionError(
                f"Cannot accept offer for RFQ with status '{rfq.status.value}'. RFQ must be OPEN.",
                details={"rfq_status": rfq.status.value},
            )

        if offer.status not in [OfferStatus.SUBMITTED, OfferStatus.UNDER_REVIEW, OfferStatus.REVISED]:
            raise InvalidStateTransitionError(
                f"Cannot accept offer with status '{offer.status.value}'.",
                details={"offer_status": offer.status.value},
            )

        old_offer_status = offer.status
        accepted_offer = self.repository.update_offer_status(offer, OfferStatus.ACCEPTED)

        # Transition RFQ to CLOSED
        self.repository.update_rfq_status(rfq, RFQStatus.CLOSED)

        # Record events
        self._record_event(
            entity_type="offer",
            entity_id=accepted_offer.id,
            event_type=WorkflowEventType.OFFER_ACCEPTED,
            from_state=old_offer_status.value,
            to_state=OfferStatus.ACCEPTED.value,
            actor=actor,
            notes=notes,
            metadata={"rfq_id": rfq.id},
        )

        self._record_event(
            entity_type="rfq",
            entity_id=rfq.id,
            event_type=WorkflowEventType.RFQ_CANCELLED,
            from_state=RFQStatus.OPEN.value,
            to_state=RFQStatus.CLOSED.value,
            actor=actor,
            notes=f"Closed upon acceptance of offer {accepted_offer.id}.",
        )

        # Auto-reject other open offers on this RFQ
        other_offers = self.repository.list_offers_for_rfq(rfq.id)
        for other in other_offers:
            if other.id != accepted_offer.id and other.status in [
                OfferStatus.SUBMITTED,
                OfferStatus.UNDER_REVIEW,
                OfferStatus.REVISED,
            ]:
                old_st = other.status
                self.repository.update_offer_status(other, OfferStatus.REJECTED)
                self._record_event(
                    entity_type="offer",
                    entity_id=other.id,
                    event_type=WorkflowEventType.OFFER_REJECTED,
                    from_state=old_st.value,
                    to_state=OfferStatus.REJECTED.value,
                    actor=actor,
                    notes="Auto-rejected because another offer was accepted.",
                )

        return OfferRead.model_validate(accepted_offer)

    def reject_offer(
        self,
        offer_id: str,
        actor: AuthUser,
        notes: Optional[str] = None,
    ) -> OfferRead:
        """Buyer rejects an offer."""
        offer = self.repository.get_offer(offer_id=offer_id)
        if not offer:
            raise ResourceNotFoundError(
                f"Offer '{offer_id}' was not found.",
                details={"offer_id": offer_id},
            )

        rfq = self.repository.get_rfq(offer.rfq_id)
        if not rfq:
            raise ResourceNotFoundError(f"Linked RFQ '{offer.rfq_id}' was not found.")

        if actor.role != "admin" and rfq.buyer_organization_id != actor.org_id:
            raise ForbiddenError(
                "Only the buyer organization can reject an offer for this RFQ.",
                details={"buyer_organization_id": rfq.buyer_organization_id, "actor_org": actor.org_id},
            )

        if offer.status in [OfferStatus.ACCEPTED, OfferStatus.REJECTED, OfferStatus.WITHDRAWN]:
            raise InvalidStateTransitionError(
                f"Cannot reject offer with status '{offer.status.value}'.",
                details={"offer_status": offer.status.value},
            )

        old_status = offer.status
        updated = self.repository.update_offer_status(offer, OfferStatus.REJECTED)

        self._record_event(
            entity_type="offer",
            entity_id=updated.id,
            event_type=WorkflowEventType.OFFER_REJECTED,
            from_state=old_status.value,
            to_state=OfferStatus.REJECTED.value,
            actor=actor,
            notes=notes,
        )
        return OfferRead.model_validate(updated)

    def list_offers_for_rfq(self, rfq_id: str, actor: AuthUser) -> List[OfferRead]:
        rfq = self.repository.get_rfq(rfq_id=rfq_id)
        if not rfq:
            raise ResourceNotFoundError(f"RFQ '{rfq_id}' was not found.")
        if actor.role != "admin" and actor.org_id not in [rfq.buyer_organization_id, rfq.seller_organization_id]:
            raise ResourceNotFoundError(f"RFQ '{rfq_id}' was not found in your organization scope.")
        offers = self.repository.list_offers_for_rfq(rfq_id=rfq.id)
        return [OfferRead.model_validate(o) for o in offers]

    def get_workflow_history(self, entity_id: str, actor: AuthUser) -> List[WorkflowEventRead]:
        """Returns the chronological audit event timeline for an entity."""
        rfq = self.repository.get_rfq(entity_id)
        if rfq:
            if actor.role != "admin" and actor.org_id not in [rfq.buyer_organization_id, rfq.seller_organization_id]:
                raise ResourceNotFoundError(f"Entity '{entity_id}' not found in your organization scope.")
        else:
            listing = self.repository.get_listing_by_id(entity_id)
            if listing and actor.role != "admin" and listing.organization_id != actor.org_id:
                raise ResourceNotFoundError(f"Entity '{entity_id}' not found in your organization scope.")

        events = self.repository.get_workflow_events(entity_id=entity_id)
        return [WorkflowEventRead.model_validate(e) for e in events]
