import uuid
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.core.auth import TokenPayload, decode_jwt
from dealflow.core.rbac import RequestContext, resolve_context
from dealflow.db.session import get_session

_bearer = HTTPBearer(auto_error=False)

# Fixed identity used when DEV_MODE=true. Matches the user seeded in migration 0008.
_DEV_TOKEN = TokenPayload(
    sub="dev|local",
    aud="dev",
    iss="https://dev.local/",
    email="dev@local.dev",
    name="Local Dev",
)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> TokenPayload:
    settings = request.app.state.settings
    if settings.dev_mode:
        return _DEV_TOKEN
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_token", "message": "Authorization header required"},
            headers={"WWW-Authenticate": "Bearer"},
        )
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
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_tenant", "message": "X-Tenant-ID must be a valid UUID"},
        ) from exc


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
            ) from exc
        if code == "membership_expired":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "membership_expired", "message": "Tenant membership has expired"},
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "not_a_member", "message": "User is not a member of this tenant"},
        ) from exc


def require_permission(
    permission: str,
) -> Callable[[RequestContext], Coroutine[Any, Any, RequestContext]]:
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
