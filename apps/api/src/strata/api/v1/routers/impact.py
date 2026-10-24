"""Verified Impact Ledger REST API Router.

Exposes lifecycle event recording, environmental impact calculations,
and mass balance summaries with auditable carbon factor lineage.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from strata.core.auth import AuthUser, get_current_user
from strata.db.session import get_db
from strata.domain.impact.service import ImpactLedgerService
from strata.schemas.common import MetaInfo, ResponseEnvelope
from strata.schemas.impact import (
    ImpactCalculation,
    ImpactCalculationRequest,
    ImpactMethodologyInfo,
    ImpactRecordCreate,
    ImpactRecordRead,
    ImpactSummaryRead,
)

router = APIRouter(prefix="/impact", tags=["Verified Impact Ledger"])


@router.post(
    "/record",
    response_model=ResponseEnvelope[ImpactRecordRead],
    status_code=status.HTTP_201_CREATED,
)
def record_impact_event(
    payload: ImpactRecordCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[ImpactRecordRead]:
    """Appends an immutable lifecycle event to the verified impact ledger with state checks."""
    service = ImpactLedgerService(db)
    record = service.record_lifecycle_impact_event(payload, actor_org_id=current_user.org_id)
    return ResponseEnvelope(data=record, meta=MetaInfo())


@router.get(
    "/summary",
    response_model=ResponseEnvelope[ImpactSummaryRead],
    status_code=status.HTTP_200_OK,
)
def get_impact_summary(
    facility_id: Optional[str] = Query(None, description="Optional facility UUID filter"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[ImpactSummaryRead]:
    """Retrieves facility or organization mass balance and realized environmental impact."""
    service = ImpactLedgerService(db)
    summary = service.get_mass_balance_and_summary(
        organization_id=current_user.org_id,
        facility_id=facility_id,
    )
    return ResponseEnvelope(data=summary, meta=MetaInfo())


@router.get(
    "/methods",
    response_model=ResponseEnvelope[List[ImpactMethodologyInfo]],
    status_code=status.HTTP_200_OK,
)
def get_supported_methods(
    db: Session = Depends(get_db),
) -> ResponseEnvelope[List[ImpactMethodologyInfo]]:
    """Returns documented carbon factor methodologies, uncertainty ratings, and boundary sources."""
    service = ImpactLedgerService(db)
    methods = service.get_supported_methodologies()
    return ResponseEnvelope(data=methods, meta=MetaInfo())


@router.post(
    "/calculate",
    response_model=ResponseEnvelope[ImpactCalculation],
    status_code=status.HTTP_200_OK,
)
def calculate_environmental_impact(
    payload: ImpactCalculationRequest,
    db: Session = Depends(get_db),
) -> ResponseEnvelope[ImpactCalculation]:
    """Computes instant landfill diversion and carbon abatement simulation for candidate materials."""
    service = ImpactLedgerService(db)
    calculation = service.calculate_environmental_impact(
        mass_kg=payload.mass_kg,
        material_category=payload.material_category,
        methodology_version=payload.methodology_version,
    )
    return ResponseEnvelope(data=calculation, meta=MetaInfo())
