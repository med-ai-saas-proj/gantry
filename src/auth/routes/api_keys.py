from src.shared.dtos.error_output import problemDetailsFromRecoverableError

from ..dtos import (
    CrateAPIKeyInput,
    CrateAPIKeyOutputSuccess,
)
from ..factories import ApiKeyService, getAPIKeyService
from ..depends.auth import get_current_user
from ..services.users import AuthInfo

from typing import Annotated

from fastapi import Body, Depends, Security, APIRouter


router = APIRouter(prefix="/api_keys", tags=["API keys"])


@router.post(
    "/",
    responses={
        200: {"model": CrateAPIKeyOutputSuccess},
    },
)
async def create_api_key(
    request: Annotated[CrateAPIKeyInput, Body()],
    user: Annotated[AuthInfo, Security(get_current_user)],
    api_key_service: Annotated[ApiKeyService, Depends(getAPIKeyService)],
) -> CrateAPIKeyOutputSuccess:
    api_key = await api_key_service.create_api_key(
        user["id"], request.permissions
    )
    return {"key": api_key.unwrap()}
