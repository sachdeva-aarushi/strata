from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from strata.api.v1.api import api_v1_router
from strata.api.v1.routers.health import check_health
from strata.core.config import settings
from strata.core.errors import register_error_handlers
from strata.core.logging import get_logger, setup_logging
from strata.db.session import init_db

logger = get_logger("strata.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for application startup and shutdown."""
    setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
    logger.info("Starting STRATA API", extra={"environment": settings.APP_ENV})

    # Automatically ensure database tables exist (e.g. for SQLite or initial setup)
    init_db()

    yield

    logger.info("Shutting down STRATA API")


def create_app() -> FastAPI:
    """Application factory for STRATA FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="STRATA — Industrial Circularity Operating System API",
        version="0.1.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # Register standardized error handlers
    register_error_handlers(app)

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root /health endpoint alias
    app.add_api_route("/health", check_health, methods=["GET"], tags=["Health"])

    # Include API v1 router under /api/v1
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "strata.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
