import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ImpactStage(str, Enum):
    """Rigidly segregated lifecycle stages for environmental and circular accounting."""
    MATERIAL_LISTED = "material_listed"
    MATERIAL_MATCHED = "material_matched"
    MATERIAL_OFFERED = "material_offered"
    MATERIAL_DISPATCHED = "material_dispatched"
    MATERIAL_RECEIVED = "material_received"
    MATERIAL_CONFIRMED_PROCESSED = "material_confirmed_processed"
    ENVIRONMENTAL_BENEFIT_ESTIMATED = "environmental_benefit_estimated"
    ENVIRONMENTAL_BENEFIT_VERIFIED = "environmental_benefit_verified"


class LifecycleEventType(str, Enum):
    """Canonical lifecycle events in the material circularity chain."""
    GENERATED = "generated"
    OFFERED = "offered"
    SHIPPED = "shipped"
    ACCEPTED = "accepted"
    PROCESSED = "processed"
    VERIFIED_RECOVERED = "verified_recovered"


class VerificationStatus(str, Enum):
    """Audit verification tier for recorded impact outcomes."""
    UNVERIFIED = "unverified"
    EVIDENCE_ATTACHED = "evidence_attached"
    VERIFIED_RECOVERED = "verified_recovered"


class UncertaintyRating(str, Enum):
    """Data quality and factor uncertainty classification."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ImpactCalculationRequest(BaseModel):
    """Payload to simulate environmental savings for a material lot."""
    mass_kg: float = Field(..., gt=0, description="Material mass in kilograms")
    material_category: str = Field(..., min_length=1, description="Material category slug, e.g. textiles, metallics")
    methodology_version: str = Field(default="v1.0", description="Impact factor methodology version")

    model_config = ConfigDict(str_strip_whitespace=True)


class ImpactCalculation(BaseModel):
    """Environmental impact avoidance estimate."""
    mass_kg: float
    material_category: str
    landfill_avoided_kg: float
    co2e_avoided_kg: float
    factor_used: float
    factor_source: str
    methodology_version: str
    uncertainty_rating: UncertaintyRating
    boundary_assumptions: str
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class ImpactCalculationRead(BaseModel):
    """Versioned, auditable carbon, water, and landfill avoidance calculation (legacy compatibility)."""
    calculation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lot_id: str
    linked_event_ids: List[str] = Field(default_factory=list)
    lifecycle_stage: ImpactStage
    method_id: str = Field(..., description="Methodology identifier, e.g. GHG-SCOPE3-CAT1")
    method_version: str = Field(default="1.0.0")
    quantity: float
    unit: str
    metric_type: str = Field(..., description="co2e_kg, water_litres, disposal_kg_avoided")
    metric_value: float
    assumptions: Dict[str, Any] = Field(default_factory=dict)
    uncertainty_pct: Optional[float] = None
    verification_state: str = Field(default="estimated", description="estimated or verified")
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class ImpactRecordCreate(BaseModel):
    """Payload to append a lifecycle event to the verified impact ledger."""
    lot_id: str = Field(..., description="Target material lot UUID")
    organization_id: Optional[str] = Field(None, description="Optional tenant org UUID (defaults to auth context)")
    facility_id: str = Field(..., description="Facility UUID where event occurred")
    event_type: str = Field(
        ...,
        description="'generated', 'offered', 'shipped', 'accepted', 'processed', or 'verified_recovered'",
    )
    mass_kg: float = Field(..., gt=0, description="Mass in kilograms for this lifecycle event")
    displaced_material_category: str = Field(..., description="Taxonomy material category, e.g. textiles")
    evidence_id: Optional[str] = Field(None, description="Optional ProofPath evidence record UUID")
    methodology_version: str = Field(default="v1.0", description="Methodology version")

    model_config = ConfigDict(str_strip_whitespace=True)


class ImpactRecordRead(BaseModel):
    """Immutable audit record from the verified impact ledger."""
    id: str
    lot_id: str
    organization_id: str
    facility_id: str
    event_type: str
    mass_kg: float
    displaced_material_category: str
    co2e_avoided_kg: float
    methodology_version: str
    factor_source: str
    verification_status: str
    evidence_id: Optional[str] = None
    uncertainty_rating: str
    boundary_assumptions: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MassBalanceReport(BaseModel):
    """Segregated mass balance across lifecycle stages to guarantee non-double-counting."""
    organization_id: str
    facility_id: Optional[str] = None
    total_generated_kg: float = 0.0
    total_offered_kg: float = 0.0
    total_shipped_kg: float = 0.0
    total_accepted_kg: float = 0.0
    total_processed_kg: float = 0.0
    total_verified_recovered_kg: float = 0.0
    total_landfill_avoided_kg: float = 0.0
    total_co2e_avoided_kg: float = 0.0
    net_in_pipeline_kg: float = 0.0
    stage_counts: Dict[str, int] = Field(default_factory=dict)
    category_breakdown: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class ImpactSummaryRead(BaseModel):
    """Facility or organization aggregate impact metrics and event ledger."""
    organization_id: str
    facility_id: Optional[str] = None
    mass_balance: MassBalanceReport
    records: List[ImpactRecordRead] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class ImpactMethodologyInfo(BaseModel):
    """Documented carbon abatement and landfill displacement factor sources."""
    methodology_version: str
    name: str
    description: str
    factors_by_category: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)
