from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from strata.core.auth import AuthUser, get_current_user
from strata.db.session import get_db
from strata.domain.qualification.service import ProofPathQualificationService
from strata.schemas.common import (
    MetaInfo,
    PaginatedResponseEnvelope,
    PaginationInfo,
    ResponseEnvelope,
)
from strata.schemas.evidence import EvidenceRecordCreate, EvidenceRecordRead
from strata.schemas.qualification import (
    InvestigationCreate,
    InvestigationRead,
    LotDiscoveryResponse,
    QualificationAssessmentRead,
    QualificationAssessRequest,
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
    Optionally executes external discovery prior to deterministic evaluation.
    """
    service = ProofPathQualificationService(db)
    investigation = service.run_investigation(
        lot_id=payload.lot_id,
        org_id=current_user.org_id,
        candidate_route_ids=payload.candidate_route_ids,
        notes=payload.notes,
        run_discovery=payload.run_discovery,
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
    "/investigations",
    response_model=PaginatedResponseEnvelope[InvestigationRead],
)
def list_investigations(
    lot_id: Optional[str] = Query(None, description="Filter investigations by target lot UUID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponseEnvelope[InvestigationRead]:
    """Lists historical qualification investigation runs belonging to the tenant organization."""
    service = ProofPathQualificationService(db)
    skip = (page - 1) * page_size
    items, total = service.list_investigations(
        org_id=current_user.org_id,
        lot_id=lot_id,
        skip=skip,
        limit=page_size,
    )
    has_next = (page * page_size) < total

    return PaginatedResponseEnvelope(
        data=items,
        pagination=PaginationInfo(
            total=total,
            page=page,
            page_size=page_size,
            has_next=has_next,
        ),
        meta=MetaInfo(),
    )


@router.post(
    "/lots/{lot_id}/qualification/assess",
    response_model=ResponseEnvelope[InvestigationRead],
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/lots/{lot_id}/qualification",
    response_model=ResponseEnvelope[InvestigationRead],
    status_code=status.HTTP_201_CREATED,
)
def assess_material_lot_qualification(
    lot_id: str,
    payload: Optional[QualificationAssessRequest] = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[InvestigationRead]:
    """
    Requests a qualification assessment for a registered material lot.
    Retrieves relevant evidence, evaluates candidate circularity routes deterministically,
    persists audit assessments, and returns structured outcomes distinguishing
    supported, conditional, and unsupported results.
    """
    service = ProofPathQualificationService(db)
    req = payload or QualificationAssessRequest()
    investigation = service.run_investigation(
        lot_id=lot_id,
        org_id=current_user.org_id,
        candidate_route_ids=req.candidate_route_ids,
        notes=req.notes,
        run_discovery=req.run_discovery,
    )
    return ResponseEnvelope(data=investigation, meta=MetaInfo())


@router.get(
    "/lots/{lot_id}/qualification/assessments",
    response_model=ResponseEnvelope[List[QualificationAssessmentRead]],
)
@router.get(
    "/lots/{lot_id}/qualification",
    response_model=ResponseEnvelope[List[QualificationAssessmentRead]],
)
@router.get(
    "/lots/{lot_id}/routes",
    response_model=ResponseEnvelope[List[QualificationAssessmentRead]],
)
def get_lot_qualification_assessments(
    lot_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[List[QualificationAssessmentRead]]:
    """Retrieves authoritative candidate route assessments recorded for a material lot."""
    service = ProofPathQualificationService(db)
    assessments = service.get_route_assessments_for_lot(lot_id=lot_id, org_id=current_user.org_id)
    return ResponseEnvelope(data=assessments, meta=MetaInfo())


@router.get(
    "/qualification/assessments/{assessment_id}",
    response_model=ResponseEnvelope[QualificationAssessmentRead],
)
def get_qualification_assessment(
    assessment_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[QualificationAssessmentRead]:
    """Retrieves a single qualification assessment by ID, strictly enforcing organization tenant boundaries."""
    service = ProofPathQualificationService(db)
    assessment = service.get_assessment_by_id(assessment_id=assessment_id, org_id=current_user.org_id)
    return ResponseEnvelope(data=assessment, meta=MetaInfo())


@router.post(
    "/lots/{lot_id}/discovery",
    response_model=ResponseEnvelope[LotDiscoveryResponse],
    status_code=status.HTTP_200_OK,
)
@router.post(
    "/lots/{lot_id}/discover",
    response_model=ResponseEnvelope[LotDiscoveryResponse],
    status_code=status.HTTP_200_OK,
)
def run_lot_discovery(
    lot_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[LotDiscoveryResponse]:
    """
    Executes the discovery pipeline to identify relevant material recovery partners,
    processors, and reuse opportunities for a material lot.
    Extracts structured capability claims and stores them as PUBLICLY_STATED and UNVERIFIED
    evidence records connected to this lot for subsequent ProofPath assessments.
    """
    service = ProofPathQualificationService(db)
    result = service.discover_partners_and_evidence(lot_id=lot_id, org_id=current_user.org_id)
    return ResponseEnvelope(data=result, meta=MetaInfo())


@router.get(
    "/lots/{lot_id}/discovery",
    response_model=ResponseEnvelope[LotDiscoveryResponse],
)
def get_lot_discovery_results(
    lot_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[LotDiscoveryResponse]:
    """Retrieves discovered recovery partners and their public capability claims for a lot."""
    service = ProofPathQualificationService(db)
    result = service.get_discovered_opportunities(lot_id=lot_id, org_id=current_user.org_id)
    return ResponseEnvelope(data=result, meta=MetaInfo())


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

