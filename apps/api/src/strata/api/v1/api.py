from fastapi import APIRouter
from strata.api.v1.routers import health, marketplace, materials, prevention, qualification
from strata.api.v1.routers import exchange, health, marketplace, materials, prevention, qualification, municipal

api_v1_router = APIRouter()

# Include health router (accessible via /api/v1/health)
api_v1_router.include_router(health.router)

# Include materials router (accessible via /api/v1/materials)
api_v1_router.include_router(materials.router)

# Include qualification & evidence router (accessible via /api/v1)
api_v1_router.include_router(qualification.router)

# Include marketplace router (accessible via /api/v1/marketplace)
api_v1_router.include_router(marketplace.router)

# Include circular exchange router (accessible via /api/v1/exchange)
api_v1_router.include_router(exchange.router)

# Include cluster & city indicators router (accessible via /api/v1/cluster/indicators, /api/v1/city/indicators)
api_v1_router.include_router(exchange.cluster_router)

# Include waste-prevention intelligence router (accessible via /api/v1/lots/{lot_id}/prevention)
api_v1_router.include_router(prevention.router)

# Include municipal & city intelligence router (accessible via /api/v1/municipal)
api_v1_router.include_router(municipal.router)

