from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from strata.domain.materials.models import Facility, MaterialLot, Organization


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

    def create(self, lot: MaterialLot) -> MaterialLot:
        """Persists a new material lot."""
        self.db.add(lot)
        self.db.commit()
        self.db.refresh(lot)
        return lot

    def get_by_id(self, lot_id: str, org_id: str) -> Optional[MaterialLot]:
        """Retrieves a single lot constrained to the authenticated organization tenant."""
        stmt = select(MaterialLot).where(
            MaterialLot.lot_id == lot_id,
            MaterialLot.org_id == org_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

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
        lots = self.db.execute(
            base_query.order_by(MaterialLot.created_at.desc()).offset(skip).limit(limit)
        ).scalars().all()

        return list(lots), total
