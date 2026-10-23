import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class QualificationOutcome(str, Enum):
    """
    Authoritative qualification outcome status evaluating route feasibility.
    - supported: All hard gates passed and all critical facts verified.
    - conditional: No hard gate failed, but one or more critical facts or verification items are missing.
    - unsupported: One or more hard constraints failed (inviolable block).
    """
    SUPPORTED = "supported"
    CONDITIONAL = "conditional"
    UNSUPPORTED = "unsupported"


class InvestigationExecutionStatus(str, Enum):
    """Execution state of the asynchronous or synchronous investigation job."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


# Backward-compatible alias
AssessmentStatus = QualificationOutcome


class HardGateResult(BaseModel):
    """Evaluation result for an inviolable regulatory, technical, or safety constraint."""
    gate_id: str
    gate_name: str
    outcome: str = Field(..., description="pass, fail, or unknown")
    material_value: Optional[Any] = None
    required_value: Optional[Any] = None
    evidence_ref_id: Optional[str] = None
    blocking: bool = Field(default=False, description="Whether this failure constitutes an inviolable block")


class MissingFact(BaseModel):
    """Specification gap preventing a route from achieving supported status."""
    fact_id: str
    description: str
    acquisition_method: str = Field(
        default="document",
        description="lab_test, document, user_confirmation, external_source",
    )
    is_critical: bool = Field(default=True, description="Whether missing this fact forces conditional status")


class QualificationAssessmentRead(BaseModel):
    """Audit-backed qualification assessment for a material lot and candidate route."""
    assessment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lot_id: str
    candidate_route_id: str
    status: QualificationOutcome
    hard_gate_results: List[HardGateResult] = Field(default_factory=list)
    blocking_conditions: List[str] = Field(default_factory=list, description="Explicit failure reasons for unsupported status")
    missing_facts: List[MissingFact] = Field(default_factory=list)
    rationale: str
    next_action: str
    evidence_refs: List[str] = Field(default_factory=list)
    rule_version: str = Field(default="1.0.0")
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class InvestigationCreate(BaseModel):
    """Request payload to initiate a qualification investigation for a material lot."""
    lot_id: str = Field(..., description="Material lot UUID to evaluate")
    candidate_route_ids: Optional[List[str]] = Field(default=None, description="Optional route IDs to constrain evaluation to")
    notes: Optional[str] = Field(default=None, description="Context or investigation directive")


class InvestigationRead(BaseModel):
    """Response payload representing an investigation execution run."""
    investigation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    lot_id: str
    status: InvestigationExecutionStatus
    assessments: List[QualificationAssessmentRead] = Field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

