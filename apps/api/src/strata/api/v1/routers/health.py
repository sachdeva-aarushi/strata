from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from strata.core.config import settings
from strata.db.session import get_db
from strata.schemas.common import MetaInfo, ResponseEnvelope

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=ResponseEnvelope[dict])
def check_health(db: Session = Depends(get_db)) -> ResponseEnvelope[dict]:
    """Liveness and readiness check testing API operational state and database connectivity."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unhealthy: {str(exc)}"

    payload = {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "0.1.0",
        "database": db_status,
    }
    return ResponseEnvelope(data=payload, meta=MetaInfo())
