import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.core.auth import TokenPayload, decode_jwt
from dealflow.core.rbac import RequestContext, resolve_context
from dealflow.db.session import get_session

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> TokenPayload:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_token", "message": "Authorization header required"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    settings = request.app.state.settings
    return await decode_jwt(
        credentials.credentials,
        settings.auth0_domain,
        settings.auth0_audience,
    )


async def get_tenant_id(
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
) -> uuid.UUID:
    if x_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "missing_tenant", "message": "X-Tenant-ID header required"},
        )
    try:
        return uuid.UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_tenant", "message": "X-Tenant-ID must be a valid UUID"},
        )


async def get_tenant_context(
    token: Annotated[TokenPayload, Depends(get_current_user)],
    tenant_id: Annotated[uuid.UUID, Depends(get_tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RequestContext:
    try:
        return await resolve_context(token.sub, tenant_id, session)
    except ValueError as exc:
        code = str(exc)
        if code == "user_not_found":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "user_not_found", "message": "Authenticated user not registered"},
            )
        if code == "membership_expired":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "membership_expired", "message": "Tenant membership has expired"},
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "not_a_member", "message": "User is not a member of this tenant"},
        )


def require_permission(permission: str):
    """Dependency factory. Usage: `Depends(require_permission("leads:read"))`."""

    async def _check(
        ctx: Annotated[RequestContext, Depends(get_tenant_context)],
    ) -> RequestContext:
        if not ctx.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "forbidden",
                    "message": f"Permission '{permission}' required",
                },
            )
        return ctx

    return _check
