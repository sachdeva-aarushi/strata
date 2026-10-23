import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class MetaInfo(BaseModel):
    """Standard metadata included in all responses."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PaginationInfo(BaseModel):
    """Pagination metadata for collection endpoints."""
    total: int = Field(..., description="Total number of items matching query")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether subsequent pages exist")


class ResponseEnvelope(BaseModel, Generic[T]):
    """Standard success response envelope wrapping single entities or simple results."""
    data: T
    meta: MetaInfo = Field(default_factory=MetaInfo)


class PaginatedResponseEnvelope(BaseModel, Generic[T]):
    """Standard paginated collection envelope."""
    data: List[T]
    pagination: PaginationInfo
    meta: MetaInfo = Field(default_factory=MetaInfo)


class ErrorDetail(BaseModel):
    """Machine and human readable error information."""
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    """Standard error response envelope."""
    error: ErrorDetail
    meta: MetaInfo = Field(default_factory=MetaInfo)
