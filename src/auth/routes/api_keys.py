from typing import Annotated

from fastapi import Body, Depends, Security, APIRouter

from ..depends.auth import get_current_user
from ..dtos import (
    CreateAPIKeyInput,
    CreateAPIKeyOutputSuccess,
)
from ..factories import ApiKeyService, getAPIKeyService
from ..services.users import AuthInfo

router = APIRouter(prefix="/api_keys", tags=["API keys"])


@router.post(
    "/",
    responses={
        200: {"model": CreateAPIKeyOutputSuccess},
    },
)
async def create_api_key(
    request: Annotated[CreateAPIKeyInput, Body()],
    auth_info: Annotated[AuthInfo, Security(get_current_user)],
    api_key_service: Annotated[ApiKeyService, Depends(getAPIKeyService)],
) -> CreateAPIKeyOutputSuccess:
    api_key = await api_key_service.create_api_key(
        auth_info["id"], request.permissions
    )
    return {"key": api_key.unwrap()}
