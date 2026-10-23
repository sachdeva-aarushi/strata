"""SQLAlchemy persistence models for the Verified Impact Ledger.

Rigidly records lifecycle material flows and environmental outcomes (landfill diversion,
carbon abatement) with explicit factor sources, versioning, and uncertainty ratings.
"""

from datetime import datetime, timezone
import uuid
from typing import Optional

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from strata.db.base import Base, TimestampMixin


def _new_id() -> str:
    return str(uuid.uuid4())


class ImpactRecord(Base, TimestampMixin):
    """Immutable audit ledger record for material lifecycle and environmental impact."""
    __tablename__ = "impact_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    lot_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    mass_kg: Mapped[float] = mapped_column(Float, nullable=False)
    displaced_material_category: Mapped[str] = mapped_column(String(100), nullable=False)
    co2e_avoided_kg: Mapped[float] = mapped_column(Float, nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(20), default="v1.0", nullable=False)
    factor_source: Mapped[str] = mapped_column(String(255), nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(50), default="unverified", nullable=False, index=True
    )
    evidence_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    uncertainty_rating: Mapped[str] = mapped_column(String(20), default="LOW", nullable=False)
    boundary_assumptions: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
