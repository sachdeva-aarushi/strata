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
from strata.schemas.materials import (
    MaterialLotCreate,
    MaterialLotFilter,
    MaterialLotRead,
    MaterialLotStatus,
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
