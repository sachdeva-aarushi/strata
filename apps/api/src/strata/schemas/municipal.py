"""Pydantic schemas for Municipal & City Intelligence APIs.

Enforces strict privacy boundaries:
  * No facility names
  * No individual lot records
  * No pricing or commercial details
  * Cohort threshold aggregation (>= 3 facilities per zone)
  * Explicit provenance labeling
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DataProvenanceLabel(str, Enum):
    """Provenance indicator for municipal circularity data."""
    REAL_VERIFIED = "real_verified"
    CURATED_PUBLIC = "curated_public"
    SYNTHETIC_DEMO = "synthetic_demo"


class LifecycleFlowBreakdown(BaseModel):
    """Aggregate material volumes across circularity pipeline stages in metric tonnes."""
    generated_tonnage: float = Field(0.0, description="Total byproduct generation volume")
    offered_tonnage: float = Field(0.0, description="Volume actively listed for exchange")
    shipped_tonnage: float = Field(0.0, description="Volume fulfilled and dispatched")
    accepted_tonnage: float = Field(0.0, description="Volume confirmed received by buyers")
    processed_tonnage: float = Field(0.0, description="Volume processed into secondary materials")
    verified_recovered_tonnage: float = Field(0.0, description="Volume with audit-verified recovery")
    by_material_category: Dict[str, float] = Field(
        default_factory=dict,
        description="Aggregate generated tonnage broken down by material category",
    )

    model_config = ConfigDict(from_attributes=True)


class MunicipalFlowReport(BaseModel):
    """City- or zone-level aggregate material flow report with cohort privacy masking."""
    city_id: str
    zone_id: Optional[str] = None
    material_category: Optional[str] = None
    facility_cohort_count: Optional[int] = Field(
        None,
        description="Number of contributing facilities (suppressed to None if < 3)",
    )
    cohort_suppressed: bool = Field(
        False,
        description="True if metrics were masked because fewer than 3 facilities operate in this zone",
    )
    suppression_reason: Optional[str] = None
    flows: Optional[LifecycleFlowBreakdown] = Field(
        None,
        description="Lifecycle stage volume breakdown (suppressed if cohort size < 3)",
    )
    provenance: DataProvenanceLabel = Field(
        default=DataProvenanceLabel.REAL_VERIFIED,
        description="Data provenance classification",
    )
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class ZoneGapIndicator(BaseModel):
    """Zone-level capacity balance comparison and bottleneck classification."""
    zone_id: str
    cohort_suppressed: bool = Field(
        False,
        description="True if metrics are masked because fewer than 3 facilities are in this zone",
    )
    facility_count: Optional[int] = Field(None, description="Facility count (masked if < 3)")
    generation_tonnage: Optional[float] = Field(None, description="Annualized byproduct generation (t)")
    processing_capacity_tonnage: Optional[float] = Field(None, description="Aggregate verified processing capacity (t)")
    net_balance_tonnage: Optional[float] = Field(None, description="Capacity - Generation (positive = surplus)")
    gap_status: str = Field(
        ...,
        description="'DEFICIT_HOTSPOT', 'BALANCED', 'SURPLUS_CAPACITY', or 'SUPPRESSED'",
    )
    top_deficit_categories: List[str] = Field(
        default_factory=list,
        description="Material categories with local processing capacity shortfall",
    )

    model_config = ConfigDict(from_attributes=True)


class CapacityGapReport(BaseModel):
    """City-wide material generation versus local processing capacity gap analysis."""
    city_id: str
    total_city_generation: float = Field(..., description="Total byproduct generation in city (tonnes)")
    total_city_capacity: float = Field(..., description="Total verified processing capacity in city (tonnes)")
    net_city_balance: float = Field(..., description="Total Capacity - Total Generation")
    overall_status: str = Field(..., description="'DEFICIT_HOTSPOT', 'BALANCED', or 'SURPLUS_CAPACITY'")
    zones: List[ZoneGapIndicator] = Field(default_factory=list, description="Zone-level gap indicators")
    provenance: DataProvenanceLabel = Field(default=DataProvenanceLabel.REAL_VERIFIED)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class ZoneGeographicIndicator(BaseModel):
    """Zone-level material density indicators with cohort privacy masking."""
    zone_id: str
    cohort_suppressed: bool = False
    active_facility_count: Optional[int] = None
    total_tonnage: Optional[float] = None
    top_categories: List[str] = Field(default_factory=list)
    tonnage_by_category: Dict[str, float] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class MunicipalGeographicSummary(BaseModel):
    """City-wide circularity geographic indicators and material density breakdown."""
    city_id: str
    total_active_zones: int
    total_city_facilities: int
    total_city_tonnage: float
    city_tonnage_by_category: Dict[str, float] = Field(default_factory=dict)
    zones: List[ZoneGeographicIndicator] = Field(default_factory=list)
    provenance: DataProvenanceLabel = Field(default=DataProvenanceLabel.REAL_VERIFIED)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)
