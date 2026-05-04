from fastapi import APIRouter, Depends
from pydantic import BaseModel

from dealflow.core.auth import TokenPayload
from dealflow.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class MeResponse(BaseModel):
    sub: str
    email: str | None = None
    name: str | None = None


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Current user identity",
    responses={
        401: {"description": "Missing or invalid token"},
    },
)
async def me(current_user: TokenPayload = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        sub=current_user.sub,
        email=current_user.email,
        name=current_user.name,
    )
