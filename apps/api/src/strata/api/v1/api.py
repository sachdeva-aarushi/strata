from fastapi import APIRouter
from strata.api.v1.routers import health, materials

api_v1_router = APIRouter()

# Include health router (accessible via /api/v1/health)
api_v1_router.include_router(health.router)

# Include materials router (accessible via /api/v1/materials)
api_v1_router.include_router(materials.router)
