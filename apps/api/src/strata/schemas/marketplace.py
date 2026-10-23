import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class ListingStatus(str, Enum):
    """Circular exchange listing lifecycle states."""
    DRAFT = "draft"
    PUBLISHED = "published"
    UNDER_QUALIFICATION = "under_qualification"
    QUALIFIED_CANDIDATE = "qualified_candidate"
    NEEDS_EVIDENCE = "needs_evidence"
    NOT_SUITABLE = "not_suitable"
    RFQ_PREPARED = "rfq_prepared"
    AWAITING_APPROVAL = "awaiting_approval"
    RFQ_SENT = "rfq_sent"
    QUOTE_RECEIVED = "quote_received"
    QUOTE_REVIEWED = "quote_reviewed"
    ORDER_APPROVED = "order_approved"
    DISPATCHED = "dispatched"
    RECEIVED = "received"
    PROCESSING_CONFIRMED = "processing_confirmed"
    OUTCOME_RECORDED = "outcome_recorded"
    CANCELLED = "cancelled"


class RFQStatus(str, Enum):
    """Request for Quotation lifecycle states."""
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    SENT = "sent"
    QUOTE_RECEIVED = "quote_received"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class ExchangeListingRead(BaseModel):
    """Exchange listing contract for published or matched material lots."""
    listing_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lot_id: str
    org_id: str
    quantity: float
    unit: str
    status: ListingStatus
    visibility: str = Field(default="cluster", description="private, cluster, public")
    commercial_terms: Dict[str, Any] = Field(default_factory=dict)
    availability_from: date
    availability_to: Optional[date] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class RFQRead(BaseModel):
    """Request for Quotation between buyer and supplier organizations."""
    rfq_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    listing_id: str
    lot_id: str
    sender_org_id: str
    recipient_org_id: str
    status: RFQStatus
    quantity: float
    unit: str
    message: Optional[str] = None
    idempotency_key: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class OfferRead(BaseModel):
    """Commercial response or proposal against an RFQ or listing."""
    offer_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rfq_id: str
    seller_org_id: str
    buyer_org_id: str
    price_per_unit: float
    currency: str = "USD"
    logistics_terms: str = "ex_works"
    valid_until: datetime
    status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)
