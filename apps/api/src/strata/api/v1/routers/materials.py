from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from strata.core.auth import AuthUser, get_current_user
from strata.db.session import get_db
from strata.domain.materials.service import MaterialService
from strata.domain.materials.taxonomy import get_all_material_types
from strata.schemas.common import (
    MetaInfo,
    PaginatedResponseEnvelope,
    PaginationInfo,
    ResponseEnvelope,
)
from strata.schemas.evidence import EvidenceRecordCreate, EvidenceRecordRead
from strata.schemas.materials import (
    EvidenceAttachRequest,
    MaterialLotCreate,
    MaterialLotFilter,
    MaterialLotRead,
    MaterialLotStatus,
    MaterialLotUpdate,
    MaterialTypeInfo,
)

router = APIRouter(prefix="/materials", tags=["Materials"])


@router.get("/types", response_model=ResponseEnvelope[List[MaterialTypeInfo]])
def list_material_types() -> ResponseEnvelope[List[MaterialTypeInfo]]:
    """Retrieves the authoritative taxonomy of circularity material categories and types."""
    types = get_all_material_types()
    return ResponseEnvelope(data=types, meta=MetaInfo())


@router.post(
    "/lots",
    response_model=ResponseEnvelope[MaterialLotRead],
    status_code=status.HTTP_201_CREATED,
)
def create_material_lot(
    payload: MaterialLotCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[MaterialLotRead]:
    """Registers a new industrial material lot scoped to the authenticated tenant organization."""
    service = MaterialService(db)
    created = service.register_lot(payload, org_id=current_user.org_id)
    return ResponseEnvelope(data=created, meta=MetaInfo())


@router.get("/lots/{lot_id}", response_model=ResponseEnvelope[MaterialLotRead])
def get_material_lot(
    lot_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[MaterialLotRead]:
    """Retrieves a single material lot by ID, strictly enforcing organization tenant boundaries."""
    service = MaterialService(db)
    lot = service.get_lot(lot_id=lot_id, org_id=current_user.org_id)
    return ResponseEnvelope(data=lot, meta=MetaInfo())


@router.get("/lots", response_model=PaginatedResponseEnvelope[MaterialLotRead])
def list_material_lots(
    status: Optional[MaterialLotStatus] = Query(None, description="Filter by lifecycle status"),
    material_type: Optional[str] = Query(None, description="Filter by taxonomy material type slug"),
    facility_id: Optional[str] = Query(None, description="Filter by facility UUID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponseEnvelope[MaterialLotRead]:
    """Lists registered material lots belonging to the authenticated tenant organization."""
    service = MaterialService(db)
    filters = MaterialLotFilter(
        status=status,
        material_type=material_type,
        facility_id=facility_id,
        page=page,
        page_size=page_size,
    )
    items, total = service.list_lots(org_id=current_user.org_id, filters=filters)
    has_next = (page * page_size) < total

    return PaginatedResponseEnvelope(
        data=items,
        pagination=PaginationInfo(
            total=total,
            page=page,
            page_size=page_size,
            has_next=has_next,
        ),
        meta=MetaInfo(),
    )


@router.patch("/lots/{lot_id}", response_model=ResponseEnvelope[MaterialLotRead])
@router.put("/lots/{lot_id}", response_model=ResponseEnvelope[MaterialLotRead])
def update_material_lot(
    lot_id: str,
    payload: MaterialLotUpdate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[MaterialLotRead]:
    """
    Updates permitted fields on an existing material lot.
    Preserves identifiers, creation timestamps, and tenant boundaries.
    """
    service = MaterialService(db)
    updated = service.update_lot(lot_id=lot_id, payload=payload, org_id=current_user.org_id)
    return ResponseEnvelope(data=updated, meta=MetaInfo())


@router.post(
    "/lots/{lot_id}/evidence",
    response_model=ResponseEnvelope[EvidenceRecordRead],
    status_code=status.HTTP_201_CREATED,
)
def create_lot_evidence(
    lot_id: str,
    payload: EvidenceRecordCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[EvidenceRecordRead]:
    """
    Creates and attaches an audit-grade evidence claim directly to a material lot.
    Preserves requested provenance and verification state without premature verification.
    """
    service = MaterialService(db)
    record = service.create_lot_evidence(lot_id=lot_id, payload=payload, org_id=current_user.org_id)
    return ResponseEnvelope(data=record, meta=MetaInfo())


@router.get("/lots/{lot_id}/evidence", response_model=ResponseEnvelope[List[EvidenceRecordRead]])
def list_lot_evidence(
    lot_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[List[EvidenceRecordRead]]:
    """Retrieves all evidence records associated with a specific material lot."""
    service = MaterialService(db)
    records = service.get_lot_evidence(lot_id=lot_id, org_id=current_user.org_id)
    return ResponseEnvelope(data=records, meta=MetaInfo())


@router.post("/lots/{lot_id}/evidence/attach", response_model=ResponseEnvelope[MaterialLotRead])
def attach_evidence_to_lot(
    lot_id: str,
    payload: EvidenceAttachRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[MaterialLotRead]:
    """
    Associates existing evidence records with a target material lot.
    Guarantees tenant isolation and preserves provenance without altering verification status.
    """
    service = MaterialService(db)
    updated = service.attach_evidence_to_lot(
        lot_id=lot_id,
        evidence_ids=payload.evidence_ids,
        org_id=current_user.org_id,
    )
    return ResponseEnvelope(data=updated, meta=MetaInfo())

