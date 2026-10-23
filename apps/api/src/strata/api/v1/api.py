from fastapi import APIRouter
from strata.api.v1.routers import health, materials, qualification

api_v1_router = APIRouter()

# Include health router (accessible via /api/v1/health)
api_v1_router.include_router(health.router)

# Include materials router (accessible via /api/v1/materials)
api_v1_router.include_router(materials.router)

# Include qualification & evidence router (accessible via /api/v1)
api_v1_router.include_router(qualification.router)
