import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from strata.core.errors import ResourceNotFoundError
from strata.domain.materials.models import Facility, MaterialLot, Organization
from strata.domain.qualification.models import EvidenceRecord
from strata.schemas.evidence import EvidenceRecordCreate


class MaterialLotRepository:
    """Repository handling SQL persistence for material lots and facility references."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def ensure_organization_and_facility(self, org_id: str, facility_id: str) -> Facility:
        """Ensures the organization and facility records exist before attaching a lot."""
        org = self.db.execute(select(Organization).where(Organization.org_id == org_id)).scalar_one_or_none()
        if not org:
            org = Organization(org_id=org_id, name="Default Organization", org_type="manufacturer")
            self.db.add(org)
            self.db.flush()

        facility = self.db.execute(
            select(Facility).where(Facility.facility_id == facility_id, Facility.org_id == org_id)
        ).scalar_one_or_none()
        if not facility:
            facility = Facility(
                facility_id=facility_id,
                org_id=org_id,
                name="Main Production Site",
                location_country="US",
            )
            self.db.add(facility)
            self.db.flush()

        return facility

    def get_evidence_ids_for_lots(self, lot_ids: List[str], org_id: str) -> Dict[str, List[str]]:
        """Batches retrieval of attached evidence IDs for given lots within organization scope."""
        if not lot_ids:
            return {}
        stmt = (
            select(EvidenceRecord.lot_id, EvidenceRecord.evidence_id)
            .where(
                EvidenceRecord.lot_id.in_(lot_ids),
                EvidenceRecord.org_id == org_id,
            )
            .order_by(EvidenceRecord.retrieved_at.asc())
        )
        rows = self.db.execute(stmt).all()
        mapping: Dict[str, List[str]] = {lid: [] for lid in lot_ids}
        for lid, eid in rows:
            if lid in mapping:
                mapping[lid].append(eid)
        return mapping

    def create(self, lot: MaterialLot) -> MaterialLot:
        """Persists a new material lot."""
        self.db.add(lot)
        self.db.commit()
        self.db.refresh(lot)
        lot.evidence_ids = []
        return lot

    def update(self, lot: MaterialLot, update_data: Dict[str, Any]) -> MaterialLot:
        """
        Updates permitted mutable fields on an existing material lot.
        Preserves identifiers (lot_id, org_id, facility_id) and creation audit trail.
        """
        immutable_fields = {"lot_id", "org_id", "facility_id", "created_at"}
        for field, value in update_data.items():
            if hasattr(lot, field) and field not in immutable_fields:
                setattr(lot, field, value)
        lot.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(lot)

        ev_map = self.get_evidence_ids_for_lots([lot.lot_id], lot.org_id)
        lot.evidence_ids = ev_map.get(lot.lot_id, [])
        return lot

    def get_by_id(self, lot_id: str, org_id: str) -> Optional[MaterialLot]:
        """Retrieves a single lot constrained to the authenticated organization tenant."""
        stmt = select(MaterialLot).where(
            MaterialLot.lot_id == lot_id,
            MaterialLot.org_id == org_id,
        )
        lot = self.db.execute(stmt).scalar_one_or_none()
        if lot:
            ev_map = self.get_evidence_ids_for_lots([lot.lot_id], org_id)
            lot.evidence_ids = ev_map.get(lot.lot_id, [])
        return lot

    def list(
        self,
        org_id: str,
        status: Optional[str] = None,
        material_type: Optional[str] = None,
        facility_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[MaterialLot], int]:
        """Lists lots belonging to the tenant matching optional filters with total count."""
        base_query = select(MaterialLot).where(MaterialLot.org_id == org_id)
        count_query = select(func.count(MaterialLot.lot_id)).where(MaterialLot.org_id == org_id)

        if status:
            base_query = base_query.where(MaterialLot.status == status)
            count_query = count_query.where(MaterialLot.status == status)
        if material_type:
            base_query = base_query.where(MaterialLot.material_type == material_type)
            count_query = count_query.where(MaterialLot.material_type == material_type)
        if facility_id:
            base_query = base_query.where(MaterialLot.facility_id == facility_id)
            count_query = count_query.where(MaterialLot.facility_id == facility_id)

        total = self.db.execute(count_query).scalar() or 0
        lots = list(
            self.db.execute(
                base_query.order_by(MaterialLot.created_at.desc()).offset(skip).limit(limit)
            ).scalars().all()
        )

        if lots:
            lot_ids = [l.lot_id for l in lots]
            ev_map = self.get_evidence_ids_for_lots(lot_ids, org_id)
            for l in lots:
                l.evidence_ids = ev_map.get(l.lot_id, [])

        return lots, total

    def attach_evidence_to_lot(self, lot_id: str, org_id: str, evidence_ids: List[str]) -> List[str]:
        """
        Associates existing evidence records with a material lot.
        Preserves original evidence provenance and verification state.
        Guarantees tenant isolation.
        """
        if not evidence_ids:
            return []

        records = self.db.execute(
            select(EvidenceRecord).where(
                EvidenceRecord.evidence_id.in_(evidence_ids),
                EvidenceRecord.org_id == org_id,
            )
        ).scalars().all()

        found_ids = {r.evidence_id for r in records}
        missing = set(evidence_ids) - found_ids
        if missing:
            raise ResourceNotFoundError(
                f"Evidence record(s) not found in organization scope: {', '.join(sorted(missing))}",
                details={"missing_evidence_ids": list(missing)},
            )

        for record in records:
            record.lot_id = lot_id
            # NOTE: Preserves existing record.provenance and record.verification_state
        self.db.commit()
        return [r.evidence_id for r in records]

    def create_evidence_for_lot(self, lot_id: str, org_id: str, payload: EvidenceRecordCreate) -> EvidenceRecord:
        """
        Creates a new audit-grade evidence record linked directly to a material lot.
        Preserves requested provenance and verification state (defaults to unverified).
        """
        record = EvidenceRecord(
            evidence_id=str(uuid.uuid4()),
            org_id=org_id,
            lot_id=lot_id,
            claim_subject=payload.claim_subject,
            claim_text=payload.claim_text,
            source_url=payload.source_url,
            source_title=payload.source_title,
            source_type=payload.source_type,
            retrieved_at=payload.retrieved_at or datetime.now(timezone.utc),
            extraction_method=payload.extraction_method.value,
            provenance=payload.provenance.value,
            verification_state=payload.verification_state.value,
            supporting_passage=payload.supporting_passage,
            content_hash=payload.content_hash,
            document_ref=payload.document_ref,
            verified_by=payload.verified_by,
            contradicted_by=[],
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_evidence_for_lot(self, lot_id: str, org_id: str) -> List[EvidenceRecord]:
        """Retrieves all evidence records associated with a lot within organization scope."""
        stmt = (
            select(EvidenceRecord)
            .where(
                EvidenceRecord.lot_id == lot_id,
                EvidenceRecord.org_id == org_id,
            )
            .order_by(EvidenceRecord.retrieved_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

