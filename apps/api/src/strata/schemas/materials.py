from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from strata.schemas.evidence import EvidenceStatus


class MaterialLotStatus(str, Enum):
    """Lifecycle status states for a registered industrial material lot."""
    DRAFT = "draft"
    AVAILABLE = "available"
    UNDER_QUALIFICATION = "under_qualification"
    LISTED = "listed"
    MATCHED = "matched"
    RFQ_IN_PROGRESS = "rfq_in_progress"
    ORDER_CONFIRMED = "order_confirmed"
    DISPATCHED = "dispatched"
    RECEIVED = "received"
    OUTCOME_RECORDED = "outcome_recorded"
    WITHDRAWN = "withdrawn"


class MaterialTypeInfo(BaseModel):
    """Taxonomy descriptor for recognized material classes."""
    type_id: str = Field(..., description="Unique slug for the material type")
    name: str = Field(..., description="Common industrial name")
    category: str = Field(..., description="Broad category: metallics, polymers, chemicals, biomass, minerals, textiles, packaging")
    standard_units: List[str] = Field(..., description="Allowed measurement units")
    is_hazardous: bool = Field(default=False, description="Whether stream routinely triggers hazardous waste gate checks")
    description: str = Field(..., description="Engineering definition and scope")


class MaterialLotBase(BaseModel):
    material_type: str = Field(..., min_length=1, description="Material type slug from taxonomy")
    quantity: float = Field(..., gt=0, description="Measured quantity, must be greater than zero")
    unit: str = Field(..., description="Physical measurement unit: kg, tonne, litre, m3, unit")
    facility_id: str = Field(..., description="Originating manufacturing facility UUID")
    availability_from: date = Field(..., description="Earliest availability date (YYYY-MM-DD)")
    availability_to: Optional[date] = Field(default=None, description="Expiration or required evacuation date")
    declared_attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value specifications (composition, moisture_pct, contamination_notes, physical_form)",
    )
    provenance_label: EvidenceStatus = Field(
        default=EvidenceStatus.USER_SUPPLIED,
        description="Data provenance label describing evidence backing",
    )

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        allowed = {"kg", "tonne", "litre", "m3", "unit"}
        cleaned = v.strip().lower()
        if cleaned not in allowed:
            raise ValueError(f"Invalid unit '{v}'. Allowed units: {', '.join(sorted(allowed))}")
        return cleaned


class MaterialLotCreate(MaterialLotBase):
    """Request payload for registering a material lot."""
    status: Optional[MaterialLotStatus] = Field(
        default=MaterialLotStatus.DRAFT,
        description="Initial lifecycle status",
    )


class MaterialLotUpdate(BaseModel):
    """Request payload for updating an existing material lot."""
    material_type: Optional[str] = None
    quantity: Optional[float] = Field(default=None, gt=0)
    unit: Optional[str] = None
    status: Optional[MaterialLotStatus] = None
    availability_from: Optional[date] = None
    availability_to: Optional[date] = None
    declared_attributes: Optional[Dict[str, Any]] = None
    provenance_label: Optional[EvidenceStatus] = None


class MaterialLotRead(MaterialLotBase):
    """Canonical material lot representation returned by the API."""
    lot_id: str = Field(..., description="Unique Material Lot UUID")
    org_id: str = Field(..., description="Owning tenant organization UUID")
    status: MaterialLotStatus = Field(..., description="Current lifecycle status")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaterialLotFilter(BaseModel):
    """Query parameters for filtering material lot collections."""
    status: Optional[MaterialLotStatus] = None
    material_type: Optional[str] = None
    facility_id: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
