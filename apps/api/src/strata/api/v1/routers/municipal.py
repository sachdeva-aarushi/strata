"""Municipal & City Intelligence REST API Router.

Serves aggregate material-flow metrics, geographic density indicators,
and capacity deficit hotspot analysis to authorized municipal planners.

Strict Privacy & Security:
  * Only accessible by users with role 'municipal_planner' or 'admin'.
  * Enforces cohort threshold masking (minimum 3 facilities per zone).
  * Never leaks facility identities, commercial pricing, or individual lot records.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from strata.core.auth import AuthUser, require_role
from strata.db.session import get_db
from strata.domain.marketplace.municipal import MunicipalIntelligenceEngine
from strata.schemas.common import MetaInfo, ResponseEnvelope
from strata.schemas.municipal import (
    CapacityGapReport,
    MunicipalFlowReport,
    MunicipalGeographicSummary,
)

router = APIRouter(prefix="/municipal", tags=["Municipal Intelligence"])


@router.get(
    "/flows",
    response_model=ResponseEnvelope[MunicipalFlowReport],
    status_code=status.HTTP_200_OK,
)
def get_aggregate_flows(
    city_id: str = Query(..., min_length=1, description="Target city/metropolitan area identifier"),
    zone_id: Optional[str] = Query(None, description="Optional zone/ward filter"),
    material_category: Optional[str] = Query(None, description="Optional material category filter"),
    current_user: AuthUser = Depends(require_role(["municipal_planner", "admin"])),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[MunicipalFlowReport]:
    """Retrieves aggregate material flows across circularity lifecycle stages with cohort privacy masking."""
    engine = MunicipalIntelligenceEngine(db)
    report = engine.get_aggregate_material_flows(
        city_id=city_id,
        zone_id=zone_id,
        material_category=material_category,
    )
    return ResponseEnvelope(data=report, meta=MetaInfo())


@router.get(
    "/capacity-gaps",
    response_model=ResponseEnvelope[CapacityGapReport],
    status_code=status.HTTP_200_OK,
)
def get_capacity_gaps(
    city_id: str = Query(..., min_length=1, description="Target city/metropolitan area identifier"),
    current_user: AuthUser = Depends(require_role(["municipal_planner", "admin"])),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[CapacityGapReport]:
    """Analyzes byproduct generation against aggregate verified processing capacity per zone."""
    engine = MunicipalIntelligenceEngine(db)
    report = engine.get_capacity_gap_analysis(city_id=city_id)
    return ResponseEnvelope(data=report, meta=MetaInfo())


@router.get(
    "/indicators",
    response_model=ResponseEnvelope[MunicipalGeographicSummary],
    status_code=status.HTTP_200_OK,
)
def get_geographic_indicators(
    city_id: str = Query(..., min_length=1, description="Target city/metropolitan area identifier"),
    current_user: AuthUser = Depends(require_role(["municipal_planner", "admin"])),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[MunicipalGeographicSummary]:
    """Retrieves city-wide circularity geographic indicators and material density breakdown."""
    engine = MunicipalIntelligenceEngine(db)
    summary = engine.get_geographic_indicators(city_id=city_id)
    return ResponseEnvelope(data=summary, meta=MetaInfo())
