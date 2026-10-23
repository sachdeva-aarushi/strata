import uuid
from datetime import date
from typing import Any, Dict, Optional
from sqlalchemy import Date, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from strata.db.base import Base, TimestampMixin


class Organization(Base, TimestampMixin):
    """Tenant organization entity."""
    __tablename__ = "organizations"

    org_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    org_type: Mapped[str] = mapped_column(String(50), default="manufacturer", nullable=False)

    facilities: Mapped[list["Facility"]] = relationship(
        "Facility",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    material_lots: Mapped[list["MaterialLot"]] = relationship(
        "MaterialLot",
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class Facility(Base, TimestampMixin):
    """Manufacturing or processing site owned by an organization."""
    __tablename__ = "facilities"

    facility_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    org_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_country: Mapped[str] = mapped_column(String(2), default="US", nullable=False)
    location_postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    cluster_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    city_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    zone_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    processing_capacity_tpa: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True)
    facility_type: Mapped[Optional[str]] = mapped_column(String(50), default="generator", nullable=True)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="facilities")
    material_lots: Mapped[list["MaterialLot"]] = relationship("MaterialLot", back_populates="facility")


class MaterialLot(Base, TimestampMixin):
    """Canonical material lot registered by a facility."""
    __tablename__ = "material_lots"

    lot_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    org_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    facility_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("facilities.facility_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False, index=True)
    availability_from: Mapped[date] = mapped_column(Date, nullable=False)
    availability_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    declared_attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    provenance_label: Mapped[str] = mapped_column(String(50), default="user_supplied", nullable=False)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="material_lots")
    facility: Mapped["Facility"] = relationship("Facility", back_populates="material_lots")
