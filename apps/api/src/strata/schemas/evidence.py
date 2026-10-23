import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceProvenance(str, Enum):
    """
    Provenance levels distinguishing the origin and certainty of evidence claims.
    Public claims are strictly differentiated from independently verified or outcome-confirmed claims.
    """
    PUBLICLY_STATED = "publicly_stated"
    USER_REPORTED = "user_reported"
    USER_SUPPLIED = "user_supplied"
    SOURCE_SUPPORTED = "source_supported"
    INFERRED = "inferred"
    ESTIMATED = "estimated"
    INDEPENDENTLY_VERIFIED = "independently_verified"
    VERIFIED = "verified"
    OUTCOME_CONFIRMED = "outcome_confirmed"
    SYNTHETIC_DEMO = "synthetic_demo"
    STALE = "stale"


class EvidenceVerificationState(str, Enum):
    """Authoritative state of verification for an evidence record."""
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    STALE = "stale"


class ExtractionMethod(str, Enum):
    """Method used to extract evidence from primary sources."""
    USER_UPLOAD = "user_upload"
    ERP_IMPORT = "erp_import"
    TINYFISH_FETCH = "tinyfish_fetch"
    MANUAL_ENTRY = "manual_entry"
    LAB_TEST = "lab_test"
    LLM_EXTRACT = "llm_extract"


# Backward-compatible alias for existing imports
EvidenceStatus = EvidenceProvenance


class EvidenceRecordCreate(BaseModel):
    """Payload for registering an evidence claim or supporting document."""
    claim_subject: str = Field(..., description="Subject domain: composition, hazard, moisture, specification, receiver_capability")
    claim_text: str = Field(..., min_length=1, description="Assertion or claim statement")
    lot_id: Optional[str] = Field(default=None, description="Optional target material lot UUID")
    source_url: Optional[str] = Field(default=None, description="External citation or primary document URL")
    source_title: Optional[str] = Field(default=None, description="Source or document title")
    source_type: str = Field(default="web", description="web, lab_report, sds, permit, invoice, manual")
    retrieved_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    extraction_method: ExtractionMethod = Field(default=ExtractionMethod.MANUAL_ENTRY)
    provenance: EvidenceProvenance = Field(default=EvidenceProvenance.USER_REPORTED)
    verification_state: EvidenceVerificationState = Field(default=EvidenceVerificationState.UNVERIFIED)
    supporting_passage: Optional[str] = Field(default=None, description="Primary excerpt or excerpt from source")
    content_hash: Optional[str] = Field(default=None, description="SHA-256 or document checksum reference")
    document_ref: Optional[str] = Field(default=None, description="Storage URI for raw artifact")
    verified_by: Optional[str] = Field(default=None, description="Identifier of verifying expert or auditor")

    @model_validator(mode="before")
    @classmethod
    def handle_evidence_status_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "evidence_status" in data and "provenance" not in data:
                data["provenance"] = data["evidence_status"]
        return data

    @property
    def evidence_status(self) -> EvidenceProvenance:
        return self.provenance


class EvidenceRecordRead(BaseModel):
    """Audit-grade evidence record returned to API clients."""
    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    lot_id: Optional[str] = None
    claim_subject: str
    claim_text: str
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    source_type: str = "web"
    retrieved_at: datetime
    extraction_method: ExtractionMethod
    provenance: EvidenceProvenance
    verification_state: EvidenceVerificationState
    supporting_passage: Optional[str] = None
    content_hash: Optional[str] = None
    document_ref: Optional[str] = None
    verified_by: Optional[str] = None
    contradicted_by: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    # Backward compatibility property for existing contract references
    @property
    def evidence_status(self) -> EvidenceProvenance:
        return self.provenance

    model_config = ConfigDict(from_attributes=True)

