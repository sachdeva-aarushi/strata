import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from strata.db.base import Base, TimestampMixin


class EvidenceRecord(Base, TimestampMixin):
    """Immutable audit-grade evidence claim or document supporting qualification and circularity claims."""
    __tablename__ = "evidence_records"

    evidence_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lot_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("material_lots.lot_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    claim_subject: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), default="web", nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    extraction_method: Mapped[str] = mapped_column(String(50), default="manual_entry", nullable=False)
    provenance: Mapped[str] = mapped_column(String(50), default="user_reported", nullable=False)
    verification_state: Mapped[str] = mapped_column(String(50), default="unverified", nullable=False)
    supporting_passage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    document_ref: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    verified_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contradicted_by: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)


class Investigation(Base, TimestampMixin):
    """Execution run for qualification assessments on a target material lot."""
    __tablename__ = "investigations"

    investigation_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    org_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.org_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lot_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("material_lots.lot_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    assessments: Mapped[List["QualificationAssessment"]] = relationship(
        "QualificationAssessment",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )


class QualificationAssessment(Base, TimestampMixin):
    """Deterministic evaluation outcome of a candidate circularity route for a material lot."""
    __tablename__ = "qualification_assessments"

    assessment_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    investigation_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("investigations.investigation_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    lot_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("material_lots.lot_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_route_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    hard_gate_results: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    blocking_conditions: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    missing_facts: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    next_action: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    investigation: Mapped[Optional["Investigation"]] = relationship("Investigation", back_populates="assessments")
