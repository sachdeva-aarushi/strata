import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class WorkflowEventType(str, Enum):
    """Immutable audit trail event types tracking physical and commercial transitions."""
    LOT_REGISTERED = "lot_registered"
    LOT_UPDATED = "lot_updated"
    LOT_LISTED = "lot_listed"
    QUALIFICATION_STARTED = "qualification_started"
    QUALIFICATION_COMPLETED = "qualification_completed"
    RFQ_CREATED = "rfq_created"
    RFQ_APPROVED = "rfq_approved"
    RFQ_SENT = "rfq_sent"
    QUOTE_RECEIVED = "quote_received"
    QUOTE_ACCEPTED = "quote_accepted"
    ORDER_CONFIRMED = "order_confirmed"
    SHIPMENT_DISPATCHED = "shipment_dispatched"
    SHIPMENT_RECEIVED = "shipment_received"
    PROCESSING_CONFIRMED = "processing_confirmed"
    OUTCOME_RECORDED = "outcome_recorded"
    EVENT_CANCELLED = "event_cancelled"


class WorkflowEventCreate(BaseModel):
    """Payload for appending an event to the immutable operational log."""
    event_type: WorkflowEventType
    entity_id: str = Field(..., description="Target UUID of the lot, listing, RFQ, or shipment")
    entity_type: str = Field(..., description="Target type: lot, listing, rfq, order, shipment")
    quantity: Optional[float] = Field(default=None, gt=0)
    unit: Optional[str] = None
    document_ref: Optional[str] = Field(default=None, description="Storage key for bill of lading or manifest")
    notes: Optional[str] = None
    idempotency_key: str = Field(..., description="Unique client-generated key preventing duplicate submissions")
    occurred_at: Optional[datetime] = None


class WorkflowEventRead(BaseModel):
    """Immutable event record returned by the audit trail."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: WorkflowEventType
    entity_id: str
    entity_type: str
    actor_id: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    document_ref: Optional[str] = None
    notes: Optional[str] = None
    idempotency_key: str
    occurred_at: datetime
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)
