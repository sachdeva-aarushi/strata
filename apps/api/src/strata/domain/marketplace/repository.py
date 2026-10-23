from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from strata.domain.marketplace.models import (
    BuyerRequirement,
    Listing,
    OfferModel,
    RFQModel,
    WorkflowEventModel,
)
from strata.domain.marketplace.schemas import (
    ListingStatus,
    ListingVisibility,
    OfferStatus,
    RFQStatus,
)
from strata.domain.materials.models import MaterialLot


class MarketplaceRepository:
    """SQL persistence for listings, buyer requirements, RFQs, offers and audit events.

    Material lots are read here only to check tenant ownership and quantity.
    This repository never writes to the materials tables.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # -- material registry (read-only) -------------------------------------

    def get_lot_for_org(self, lot_id: str, org_id: str) -> Optional[MaterialLot]:
        stmt = select(MaterialLot).where(MaterialLot.lot_id == lot_id, MaterialLot.org_id == org_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_lots_by_ids(self, lot_ids: List[str]) -> dict:
        if not lot_ids:
            return {}
        rows = self.db.execute(select(MaterialLot).where(MaterialLot.lot_id.in_(lot_ids))).scalars().all()
        return {lot.lot_id: lot for lot in rows}

    # -- listings -----------------------------------------------------------

    def add_listing(self, listing: Listing) -> Listing:
        self.db.add(listing)
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def get_listing(self, listing_id: str, org_id: str) -> Optional[Listing]:
        stmt = select(Listing).where(Listing.id == listing_id, Listing.organization_id == org_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_listing_by_id(self, listing_id: str) -> Optional[Listing]:
        stmt = select(Listing).where(Listing.id == listing_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def update_listing_status(self, listing: Listing, new_status: ListingStatus) -> Listing:
        listing.status = new_status
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def list_listings(self, org_id: str, skip: int, limit: int) -> Tuple[List[Listing], int]:
        base = select(Listing).where(Listing.organization_id == org_id)
        count = select(func.count(Listing.id)).where(Listing.organization_id == org_id)
        total = self.db.execute(count).scalar() or 0
        rows = self.db.execute(
            base.order_by(Listing.created_at.desc()).offset(skip).limit(limit)
        ).scalars().all()
        return list(rows), total

    def list_discoverable_listings(
        self,
        exclude_org_id: str,
        visibility_levels: List[ListingVisibility],
    ) -> List[Listing]:
        """Active listings from other organizations that are visible at the given levels."""
        stmt = (
            select(Listing)
            .where(
                Listing.status == ListingStatus.ACTIVE,
                Listing.visibility.in_(visibility_levels),
                Listing.organization_id != exclude_org_id,
            )
            .order_by(Listing.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    # -- buyer requirements -------------------------------------------------

    def add_requirement(self, requirement: BuyerRequirement) -> BuyerRequirement:
        self.db.add(requirement)
        self.db.commit()
        self.db.refresh(requirement)
        return requirement

    def get_requirement(self, requirement_id: str, org_id: str) -> Optional[BuyerRequirement]:
        stmt = select(BuyerRequirement).where(
            BuyerRequirement.id == requirement_id,
            BuyerRequirement.organization_id == org_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    # -- RFQs ---------------------------------------------------------------

    def add_rfq(self, rfq: RFQModel) -> RFQModel:
        self.db.add(rfq)
        self.db.commit()
        self.db.refresh(rfq)
        return rfq

    def get_rfq(self, rfq_id: str, org_id: Optional[str] = None) -> Optional[RFQModel]:
        stmt = select(RFQModel).where(RFQModel.id == rfq_id)
        if org_id is not None:
            stmt = stmt.where(
                or_(
                    RFQModel.buyer_organization_id == org_id,
                    RFQModel.seller_organization_id == org_id,
                )
            )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_rfqs_for_org(
        self,
        org_id: str,
        as_buyer: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[RFQModel], int]:
        base = select(RFQModel)
        count_stmt = select(func.count(RFQModel.id))
        if as_buyer is True:
            cond = RFQModel.buyer_organization_id == org_id
        elif as_buyer is False:
            cond = RFQModel.seller_organization_id == org_id
        else:
            cond = or_(
                RFQModel.buyer_organization_id == org_id,
                RFQModel.seller_organization_id == org_id,
            )
        base = base.where(cond)
        count_stmt = count_stmt.where(cond)
        total = self.db.execute(count_stmt).scalar() or 0
        rows = self.db.execute(
            base.order_by(RFQModel.created_at.desc()).offset(skip).limit(limit)
        ).scalars().all()
        return list(rows), total

    def update_rfq_status(self, rfq: RFQModel, new_status: RFQStatus) -> RFQModel:
        rfq.status = new_status
        self.db.commit()
        self.db.refresh(rfq)
        return rfq

    # -- Offers -------------------------------------------------------------

    def add_offer(self, offer: OfferModel) -> OfferModel:
        self.db.add(offer)
        self.db.commit()
        self.db.refresh(offer)
        return offer

    def get_offer(self, offer_id: str) -> Optional[OfferModel]:
        stmt = select(OfferModel).where(OfferModel.id == offer_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_offers_for_rfq(self, rfq_id: str) -> List[OfferModel]:
        stmt = (
            select(OfferModel)
            .where(OfferModel.rfq_id == rfq_id)
            .order_by(OfferModel.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def update_offer_status(self, offer: OfferModel, new_status: OfferStatus) -> OfferModel:
        offer.status = new_status
        self.db.commit()
        self.db.refresh(offer)
        return offer

    # -- Workflow Events ----------------------------------------------------

    def add_workflow_event(self, event: WorkflowEventModel) -> WorkflowEventModel:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_workflow_events(self, entity_id: str) -> List[WorkflowEventModel]:
        stmt = (
            select(WorkflowEventModel)
            .where(WorkflowEventModel.entity_id == entity_id)
            .order_by(WorkflowEventModel.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())
