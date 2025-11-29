"""API key management routes."""

from ..dtos import (
    CreateAPIKeyInput,
    CreateAPIKeyOutputSuccess,
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
        200: {"model": CreateAPIKeyOutputSuccess},
    },
)
async def createApiKey(
    request: Annotated[CreateAPIKeyInput, Body()],
    auth_info: Annotated[AuthInfo, Security(get_current_user)],
    api_key_service: Annotated[ApiKeyService, Depends(getAPIKeyService)],
) -> CreateAPIKeyOutputSuccess:
    """Create a new API key with specified permissions for the authenticated user."""
    api_key = await api_key_service.createApiKey(
        auth_info["id"], request.permissions
    )
    return {"key": api_key.unwrap()}
