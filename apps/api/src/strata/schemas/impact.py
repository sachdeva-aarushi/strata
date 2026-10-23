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


class ImpactCalculationRead(BaseModel):
    """Versioned, auditable carbon, water, and landfill avoidance calculation."""
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
