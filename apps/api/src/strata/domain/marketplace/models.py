"""SQLAlchemy persistence models for marketplace listings and buyer requirements.

Qualification results are not persisted here; ProofPath owns them.
Material lots are owned by ``strata.domain.materials``; ``material_lot_id`` is
a reference only and is not a foreign key, so this module does not depend on
the materials models.
"""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, JSON, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from strata.db.base import Base, TimestampMixin
from strata.domain.marketplace.schemas import (
    ListingStatus,
    ListingVisibility,
    OfferStatus,
    RFQStatus,
    WorkflowEventType,
)


def _new_id() -> str:
    return str(uuid.uuid4())


class Listing(Base, TimestampMixin):
    """Supplier offer for a material lot."""
    __tablename__ = "marketplace_listings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    material_lot_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    visibility: Mapped[ListingVisibility] = mapped_column(
        SAEnum(ListingVisibility, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e]),
        default=ListingVisibility.PRIVATE,
        nullable=False,
        index=True,
    )
    asking_price_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    available_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[ListingStatus] = mapped_column(
        SAEnum(ListingStatus, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e]),
        default=ListingStatus.DRAFT,
        nullable=False,
        index=True,
    )


class BuyerRequirement(Base, TimestampMixin):
    """Buyer demand specification used for candidate matching."""
    __tablename__ = "marketplace_buyer_requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    material_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    min_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    max_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    target_price_per_unit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    required_properties: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    prohibited_conditions: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    visibility: Mapped[ListingVisibility] = mapped_column(
        SAEnum(ListingVisibility, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e]),
        default=ListingVisibility.PRIVATE,
        nullable=False,
    )


class RFQModel(Base, TimestampMixin):
    """Commercial request for quotation initiated by a buyer."""
    __tablename__ = "marketplace_rfqs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    listing_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    buyer_requirement_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    buyer_organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    buyer_facility_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    seller_organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    seller_facility_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    requested_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    target_price_per_unit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[RFQStatus] = mapped_column(
        SAEnum(RFQStatus, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e]),
        default=RFQStatus.DRAFT,
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)


class OfferModel(Base, TimestampMixin):
    """Commercial offer / quote submitted by a seller against an RFQ."""
    __tablename__ = "marketplace_offers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    rfq_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    listing_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    seller_organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    seller_facility_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    offered_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    price_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[OfferStatus] = mapped_column(
        SAEnum(OfferStatus, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e]),
        default=OfferStatus.SUBMITTED,
        nullable=False,
        index=True,
    )
    terms: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)


class WorkflowEventModel(Base):
    """Auditable state transition event record."""
    __tablename__ = "marketplace_workflow_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    from_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_state: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_org_id: Mapped[str] = mapped_column(String(36), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    metadata_payload: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# Domain-level aliases
RFQ = RFQModel
Offer = OfferModel
WorkflowEventRecord = WorkflowEventModel
