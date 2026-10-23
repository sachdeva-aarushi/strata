import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EvidenceStatus(str, Enum):
    """Canonical provenance labels for auditability and verification."""
    VERIFIED = "verified"
    SOURCE_SUPPORTED = "source_supported"
    USER_SUPPLIED = "user_supplied"
    INFERRED = "inferred"
    ESTIMATED = "estimated"
    SYNTHETIC_DEMO = "synthetic_demo"
    STALE = "stale"


class EvidenceRecordCreate(BaseModel):
    """Payload for registering an evidence claim or supporting document."""
    claim_text: str = Field(..., min_length=1, description="Assertion or claim statement")
    claim_subject: str = Field(..., description="Subject domain: composition, hazard, moisture, specification")
    source_url: Optional[str] = Field(default=None, description="External URL or citation")
    source_title: Optional[str] = Field(default=None, description="Source name or title")
    extraction_method: str = Field(
        default="user_upload",
        description="Method used: user_upload, erp_import, tinyfish_fetch, manual_entry",
    )
    evidence_status: EvidenceStatus = Field(default=EvidenceStatus.USER_SUPPLIED)
    supporting_passage: Optional[str] = Field(default=None, description="Extracted source excerpt")


class EvidenceRecordRead(BaseModel):
    """Audit-grade evidence record returned to API clients."""
    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    claim_text: str
    claim_subject: str
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    extraction_method: str
    evidence_status: EvidenceStatus
    supporting_passage: Optional[str] = None
    verified_by: Optional[str] = None
    contradicted_by: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
