import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from strata.core.errors import ResourceNotFoundError, ValidationError
from strata.domain.materials.models import MaterialLot
from strata.domain.materials.repository import MaterialLotRepository
from strata.domain.materials.taxonomy import get_material_type
from strata.schemas.evidence import EvidenceRecordCreate, EvidenceRecordRead
from strata.schemas.materials import (
    MaterialLotCreate,
    MaterialLotFilter,
    MaterialLotRead,
    MaterialLotStatus,
    MaterialLotUpdate,
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

        # 3. Validate quantity
        if payload.quantity <= 0:
            raise ValidationError(
                "Quantity must be greater than zero.",
                details={"quantity": payload.quantity},
            )

        # 4. Validate temporal window
        if payload.availability_to and payload.availability_to < payload.availability_from:
            raise ValidationError(
                "availability_to date cannot be earlier than availability_from date.",
                details={
                    "availability_from": str(payload.availability_from),
                    "availability_to": str(payload.availability_to),
                },
            )

        # 5. Ensure tenant references exist
        self.repository.ensure_organization_and_facility(org_id=org_id, facility_id=payload.facility_id)

        # 6. Create domain model
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

        # 7. Attach existing evidence records if supplied
        if payload.evidence_ids:
            attached = self.repository.attach_evidence_to_lot(
                lot_id=saved.lot_id,
                org_id=org_id,
                evidence_ids=payload.evidence_ids,
            )
            saved.evidence_ids = attached

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

    def update_lot(self, lot_id: str, payload: MaterialLotUpdate, org_id: str) -> MaterialLotRead:
        """
        Updates permitted fields on an existing material lot.
        Preserves identifiers, creation timestamps, and tenant boundaries.
        """
        lot = self.repository.get_by_id(lot_id=lot_id, org_id=org_id)
        if not lot:
            raise ResourceNotFoundError(
                f"Material lot with ID '{lot_id}' was not found in your organization scope.",
                details={"lot_id": lot_id},
            )

        # 1. Validate taxonomy and unit compatibility if updated
        target_material_type = payload.material_type or lot.material_type
        taxonomy_info = get_material_type(target_material_type)
        if not taxonomy_info:
            raise ValidationError(
                f"Unknown material type '{target_material_type}'. Must be a recognized taxonomy slug.",
                details={"material_type": target_material_type},
            )

        if payload.unit is not None or payload.material_type is not None:
            effective_unit = (payload.unit.strip().lower() if payload.unit else lot.unit)
            if effective_unit not in taxonomy_info.standard_units:
                raise ValidationError(
                    f"Unit '{effective_unit}' is not standard for material class '{target_material_type}'. "
                    f"Allowed units: {', '.join(taxonomy_info.standard_units)}",
                    details={"unit": effective_unit, "allowed_units": taxonomy_info.standard_units},
                )

        # 2. Validate quantity if provided
        if payload.quantity is not None and payload.quantity <= 0:
            raise ValidationError(
                "Quantity must be greater than zero.",
                details={"quantity": payload.quantity},
            )

        # 3. Validate temporal window
        effective_from = payload.availability_from if payload.availability_from is not None else lot.availability_from
        effective_to = payload.availability_to if payload.availability_to is not None else lot.availability_to
        if effective_to and effective_to < effective_from:
            raise ValidationError(
                "availability_to date cannot be earlier than availability_from date.",
                details={
                    "availability_from": str(effective_from),
                    "availability_to": str(effective_to),
                },
            )

        # 4. Construct update payload for permitted mutable fields
        update_data = {}
        if payload.material_type is not None:
            update_data["material_type"] = payload.material_type
        if payload.quantity is not None:
            update_data["quantity"] = payload.quantity
        if payload.unit is not None:
            update_data["unit"] = payload.unit.strip().lower()
        if payload.status is not None:
            update_data["status"] = payload.status.value
        if payload.availability_from is not None:
            update_data["availability_from"] = payload.availability_from
        if payload.availability_to is not None:
            update_data["availability_to"] = payload.availability_to
        if payload.declared_attributes is not None:
            current_attrs = dict(lot.declared_attributes or {})
            current_attrs.update(payload.declared_attributes)
            update_data["declared_attributes"] = current_attrs
        if payload.provenance_label is not None:
            update_data["provenance_label"] = payload.provenance_label.value

        updated = self.repository.update(lot, update_data)

        # 5. Handle evidence attachment if requested
        if payload.evidence_ids is not None:
            self.repository.attach_evidence_to_lot(lot_id=lot_id, org_id=org_id, evidence_ids=payload.evidence_ids)
            ev_map = self.repository.get_evidence_ids_for_lots([lot_id], org_id)
            updated.evidence_ids = ev_map.get(lot_id, [])

        return MaterialLotRead.model_validate(updated)

    def get_lot_evidence(self, lot_id: str, org_id: str) -> List[EvidenceRecordRead]:
        """Retrieves all evidence records associated with a specific material lot."""
        lot = self.repository.get_by_id(lot_id=lot_id, org_id=org_id)
        if not lot:
            raise ResourceNotFoundError(
                f"Material lot with ID '{lot_id}' was not found in your organization scope.",
                details={"lot_id": lot_id},
            )
        records = self.repository.get_evidence_for_lot(lot_id=lot_id, org_id=org_id)
        return [EvidenceRecordRead.model_validate(r) for r in records]

    def create_lot_evidence(self, lot_id: str, payload: EvidenceRecordCreate, org_id: str) -> EvidenceRecordRead:
        """
        Creates a new audit-grade evidence record linked directly to a material lot.
        Preserves original verification state and provenance.
        """
        lot = self.repository.get_by_id(lot_id=lot_id, org_id=org_id)
        if not lot:
            raise ResourceNotFoundError(
                f"Material lot with ID '{lot_id}' was not found in your organization scope.",
                details={"lot_id": lot_id},
            )
        record = self.repository.create_evidence_for_lot(lot_id=lot_id, org_id=org_id, payload=payload)
        return EvidenceRecordRead.model_validate(record)

    def attach_evidence_to_lot(self, lot_id: str, evidence_ids: List[str], org_id: str) -> MaterialLotRead:
        """Associates existing evidence records with a material lot."""
        lot = self.repository.get_by_id(lot_id=lot_id, org_id=org_id)
        if not lot:
            raise ResourceNotFoundError(
                f"Material lot with ID '{lot_id}' was not found in your organization scope.",
                details={"lot_id": lot_id},
            )
        self.repository.attach_evidence_to_lot(lot_id=lot_id, org_id=org_id, evidence_ids=evidence_ids)
        refreshed = self.repository.get_by_id(lot_id=lot_id, org_id=org_id)
        return MaterialLotRead.model_validate(refreshed)

