from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from strata.core.auth import AuthUser, get_current_user
from strata.db.session import get_db
from strata.domain.qualification.service import ProofPathQualificationService
from strata.schemas.common import MetaInfo, ResponseEnvelope
from strata.schemas.evidence import EvidenceRecordCreate, EvidenceRecordRead
from strata.schemas.qualification import (
    InvestigationCreate,
    InvestigationRead,
    QualificationAssessmentRead,
)

router = APIRouter(tags=["ProofPath Qualification & Evidence"])


@router.post(
    "/investigations",
    response_model=ResponseEnvelope[InvestigationRead],
    status_code=status.HTTP_201_CREATED,
)
def create_investigation(
    payload: InvestigationCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[InvestigationRead]:
    """
    Initiates an investigation on a material lot, evaluating all eligible candidate
    recovery routes against deterministic technical and regulatory hard constraints.
    """
    service = ProofPathQualificationService(db)
    investigation = service.run_investigation(
        lot_id=payload.lot_id,
        org_id=current_user.org_id,
        candidate_route_ids=payload.candidate_route_ids,
        notes=payload.notes,
    )
    return ResponseEnvelope(data=investigation, meta=MetaInfo())


@router.get(
    "/investigations/{investigation_id}",
    response_model=ResponseEnvelope[InvestigationRead],
)
def get_investigation(
    investigation_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[InvestigationRead]:
    """Retrieves an investigation run and its structured route assessments."""
    service = ProofPathQualificationService(db)
    investigation = service.get_investigation(investigation_id, org_id=current_user.org_id)
    return ResponseEnvelope(data=investigation, meta=MetaInfo())


@router.get(
    "/lots/{lot_id}/routes",
    response_model=ResponseEnvelope[List[QualificationAssessmentRead]],
)
def get_lot_qualification_routes(
    lot_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[List[QualificationAssessmentRead]]:
    """Retrieves authoritative candidate route assessments recorded for a material lot."""
    service = ProofPathQualificationService(db)
    assessments = service.get_route_assessments_for_lot(lot_id=lot_id, org_id=current_user.org_id)
    return ResponseEnvelope(data=assessments, meta=MetaInfo())


@router.post(
    "/evidence",
    response_model=ResponseEnvelope[EvidenceRecordRead],
    status_code=status.HTTP_201_CREATED,
)
def create_evidence_record(
    payload: EvidenceRecordCreate,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[EvidenceRecordRead]:
    """Registers an audit-grade evidence record linked to a claim or lot."""
    service = ProofPathQualificationService(db)
    record = service.add_evidence(payload, org_id=current_user.org_id)
    return ResponseEnvelope(data=record, meta=MetaInfo())


@router.get(
    "/lots/{lot_id}/evidence",
    response_model=ResponseEnvelope[List[EvidenceRecordRead]],
)
def list_lot_evidence(
    lot_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[List[EvidenceRecordRead]]:
    """Lists all evidence records registered for a specific material lot."""
    service = ProofPathQualificationService(db)
    records = service.get_evidence_for_lot(lot_id, org_id=current_user.org_id)
    return ResponseEnvelope(data=records, meta=MetaInfo())
