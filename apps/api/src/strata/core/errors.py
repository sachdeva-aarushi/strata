import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError


class StrataError(Exception):
    """Base class for all application errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class ResourceNotFoundError(StrataError):
    """Raised when a requested resource does not exist in the tenant scope."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ValidationError(StrataError):
    """Raised when request payload or business validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class UnauthorizedError(StrataError):
    """Raised when an unauthenticated request is received."""

    def __init__(self, message: str = "Authentication required.", details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class ForbiddenError(StrataError):
    """Raised when the authenticated actor lacks permissions for the action."""

    def __init__(self, message: str = "Access forbidden.", details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ConflictError(StrataError):
    """Raised when a state conflict or duplicate idempotency key occurs."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="DUPLICATE_EVENT",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class QualificationHardBlockError(StrataError):
    """Raised when a marketplace action violates a hard qualification constraint."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="QUALIFICATION_HARD_BLOCK",
            status_code=422,
            details=details,
        )


def make_error_envelope(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "meta": {
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


def register_error_handlers(app: FastAPI) -> None:
    """Registers standard exception handlers on the FastAPI app."""

    @app.exception_handler(StrataError)
    async def strata_error_handler(request: Request, exc: StrataError) -> JSONResponse:
        content = make_error_envelope(
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        content = make_error_envelope(
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            details={"errors": jsonable_encoder(exc.errors())},
        )
        return JSONResponse(status_code=422, content=content)

    @app.exception_handler(PydanticValidationError)
    async def pydantic_error_handler(request: Request, exc: PydanticValidationError) -> JSONResponse:
        content = make_error_envelope(
            code="VALIDATION_ERROR",
            message="Data validation failed.",
            details={"errors": jsonable_encoder(exc.errors())},
        )
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=content)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        content = make_error_envelope(
            code="INTERNAL_ERROR",
            message="An unexpected server error occurred.",
            details={"detail": str(exc)} if app.debug else {},
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=content)
