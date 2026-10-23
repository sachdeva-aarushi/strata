import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from strata.core.config import settings
from strata.core.errors import ForbiddenError, UnauthorizedError

security = HTTPBearer(auto_error=False)


class AuthUser(BaseModel):
    """Authenticated user context with tenant scope."""

    user_id: str = Field(..., description="Subject user UUID")
    org_id: str = Field(..., description="Organization tenant UUID")
    role: str = Field(default="facility_operator", description="Role enum value")
    cluster_ids: List[str] = Field(default_factory=list, description="Associated cluster UUIDs")


def create_access_token(
    user_id: str,
    org_id: str,
    role: str = "facility_operator",
    cluster_ids: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Creates a signed JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": user_id,
        "org_id": org_id,
        "role": role,
        "cluster_ids": cluster_ids or [],
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> AuthUser:
    """Decodes and validates a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: str = payload.get("sub")
        org_id: str = payload.get("org_id")
        role: str = payload.get("role", "facility_operator")
        cluster_ids: List[str] = payload.get("cluster_ids", [])

        if not user_id or not org_id:
            raise UnauthorizedError("Invalid token payload: missing sub or org_id")

        return AuthUser(
            user_id=user_id,
            org_id=org_id,
            role=role,
            cluster_ids=cluster_ids,
        )
    except JWTError as e:
        raise UnauthorizedError(f"Token validation failed: {str(e)}")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_org_id: Optional[str] = Header(None, alias="X-Org-Id"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_role: Optional[str] = Header(None, alias="X-Role"),
) -> AuthUser:
    """
    FastAPI dependency for resolving authenticated tenant context.
    If Bearer token is provided, it validates the JWT.
    If mock auth is enabled and explicit headers or default dev credentials are supplied,
    it returns the mock tenant user.
    """
    if credentials and credentials.scheme.lower() == "bearer":
        return decode_access_token(credentials.credentials)

    # In dev/test mode with mock auth enabled:
    if settings.MOCK_AUTH_ENABLED:
        mock_org = x_org_id or "00000000-0000-0000-0000-000000000001"
        mock_user = x_user_id or "00000000-0000-0000-0000-000000000002"
        mock_role = x_role or "facility_operator"
        return AuthUser(
            user_id=mock_user,
            org_id=mock_org,
            role=mock_role,
            cluster_ids=["00000000-0000-0000-0000-000000000003"],
        )

    raise UnauthorizedError("Missing or invalid authentication credentials")


def require_role(allowed_roles: List[str]):
    """Returns a dependency enforcing specific user roles."""

    async def role_checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in allowed_roles:
            raise ForbiddenError(f"Role '{user.role}' is not authorized for this operation.")
        return user

    return role_checker
