import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AssessmentStatus(str, Enum):
    """Authoritative outcome status of a ProofPath qualification run."""
    SUPPORTED = "supported"
    CONDITIONAL = "conditional"
    UNSUPPORTED = "unsupported"
    PENDING = "pending"
    FAILED = "failed"


class HardGateResult(BaseModel):
    """Evaluation result for an inviolable regulatory, technical, or safety constraint."""
    gate_id: str
    gate_name: str
    outcome: str = Field(..., description="pass, fail, or unknown")
    material_value: Optional[Any] = None
    required_value: Optional[Any] = None
    evidence_ref_id: Optional[str] = None


class MissingFact(BaseModel):
    """Specification gap preventing a route from achieving supported status."""
    fact_id: str
    description: str
    acquisition_method: str = Field(
        default="document",
        description="lab_test, document, user_confirmation, external_source",
    )


class QualificationAssessmentRead(BaseModel):
    """Audit-backed qualification assessment for a material lot and candidate route."""
    assessment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lot_id: str
    candidate_route_id: str
    status: AssessmentStatus
    hard_gate_results: List[HardGateResult] = Field(default_factory=list)
    missing_facts: List[MissingFact] = Field(default_factory=list)
    rationale: str
    next_action: str
    evidence_refs: List[str] = Field(default_factory=list)
    rule_version: str = Field(default="1.0.0")
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)
