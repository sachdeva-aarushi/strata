import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from strata.core.errors import ResourceNotFoundError, ValidationError
from strata.domain.materials.models import MaterialLot
from strata.domain.materials.repository import MaterialLotRepository
from strata.domain.materials.taxonomy import get_material_type
from strata.schemas.materials import (
    MaterialLotCreate,
    MaterialLotFilter,
    MaterialLotRead,
    MaterialLotStatus,
)


class MaterialService:
    """Domain service orchestrating material registry operations and business rules."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = MaterialLotRepository(db)

    def register_lot(self, payload: MaterialLotCreate, org_id: str) -> MaterialLotRead:
        """
        Registers a new material lot after validating taxonomy compatibility,
        measurement units, and temporal bounds.
        """
        # 1. Validate taxonomy type
        taxonomy_info = get_material_type(payload.material_type)
        if not taxonomy_info:
            raise ValidationError(
                f"Unknown material type '{payload.material_type}'. Must be a recognized taxonomy slug.",
                details={"material_type": payload.material_type},
            )

        # 2. Validate unit compatibility with material class
        cleaned_unit = payload.unit.strip().lower()
        if cleaned_unit not in taxonomy_info.standard_units:
            raise ValidationError(
                f"Unit '{payload.unit}' is not standard for material class '{payload.material_type}'. "
                f"Allowed units: {', '.join(taxonomy_info.standard_units)}",
                details={"unit": payload.unit, "allowed_units": taxonomy_info.standard_units},
            )

        # 3. Validate temporal window
        if payload.availability_to and payload.availability_to < payload.availability_from:
            raise ValidationError(
                "availability_to date cannot be earlier than availability_from date.",
                details={
                    "availability_from": str(payload.availability_from),
                    "availability_to": str(payload.availability_to),
                },
            )

        # 4. Ensure tenant references exist
        self.repository.ensure_organization_and_facility(org_id=org_id, facility_id=payload.facility_id)

        # 5. Create domain model
        lot = MaterialLot(
            lot_id=str(uuid.uuid4()),
            org_id=org_id,
            facility_id=payload.facility_id,
            material_type=payload.material_type,
            quantity=payload.quantity,
            unit=cleaned_unit,
            status=(payload.status or MaterialLotStatus.DRAFT).value,
            availability_from=payload.availability_from,
            availability_to=payload.availability_to,
            declared_attributes=payload.declared_attributes or {},
            provenance_label=payload.provenance_label.value,
        )

        saved = self.repository.create(lot)
        return MaterialLotRead.model_validate(saved)

    def get_lot(self, lot_id: str, org_id: str) -> MaterialLotRead:
        """Retrieves a single material lot, ensuring tenant boundary enforcement."""
        lot = self.repository.get_by_id(lot_id=lot_id, org_id=org_id)
        if not lot:
            raise ResourceNotFoundError(
                f"Material lot with ID '{lot_id}' was not found in your organization scope.",
                details={"lot_id": lot_id},
            )
        return MaterialLotRead.model_validate(lot)

    def list_lots(self, org_id: str, filters: MaterialLotFilter) -> Tuple[List[MaterialLotRead], int]:
        """Lists lots belonging to the tenant matching criteria with pagination."""
        skip = (filters.page - 1) * filters.page_size
        status_val = filters.status.value if filters.status else None
        lots, total = self.repository.list(
            org_id=org_id,
            status=status_val,
            material_type=filters.material_type,
            facility_id=filters.facility_id,
            skip=skip,
            limit=filters.page_size,
        )
        items = [MaterialLotRead.model_validate(item) for item in lots]
        return items, total
