from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from strata.core.auth import AuthUser, get_current_user
from strata.db.session import get_db
from strata.domain.prevention.service import WastePreventionService
from strata.integrations.llm import get_llm_provider
from strata.schemas.common import MetaInfo, ResponseEnvelope
from strata.schemas.prevention import PreventionRecommendationsResponse

router = APIRouter(tags=["Waste Prevention Intelligence"])


@router.get(
    "/lots/{lot_id}/prevention/recommendations",
    response_model=ResponseEnvelope[PreventionRecommendationsResponse],
    status_code=status.HTTP_200_OK,
)
def get_prevention_recommendations(
    lot_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResponseEnvelope[PreventionRecommendationsResponse]:
    """
    Generates evidence-grounded waste-prevention recommendations for a material lot.

    Recommendations are advisory. Confidence reflects evidence completeness.
    No environmental savings figures are generated or reported.

    The ``evidence_provider`` and ``llm_provider`` fields in the response
    identify which backend was used (``'tinyfish'`` / ``'openai'`` vs ``'fake'``).
    """
    from strata.core.config import settings

    # Select providers based on configuration
    llm = get_llm_provider()
    llm_label = settings.LLM_PROVIDER if settings.llm_configured else "fake"
    evidence_label = "tinyfish" if settings.tinyfish_configured else "fake"

    service = WastePreventionService(
        db=db,
        llm=llm,
        llm_label=llm_label,
        evidence_label=evidence_label,
    )
    result = service.get_recommendations(lot_id=lot_id, org_id=current_user.org_id)
    return ResponseEnvelope(data=result, meta=MetaInfo())
