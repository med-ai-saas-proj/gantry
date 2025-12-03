"""API key management routes."""

from .dtos import (
    CreateAPIKeyRequest,
    CreateAPIKeySuccessResponse,
)
from ..depends.auth import get_current_user
from ..services.users import AuthInfo
from ..services.factories import ApiKeyService, getAPIKeyService

from typing import Annotated

from fastapi import Body, Depends, Security, APIRouter


router = APIRouter(prefix="/api_keys", tags=["API keys"])


@router.post(
    "/",
    responses={
        200: {"model": CreateAPIKeySuccessResponse},
    },
)
async def createApiKey(
    request: Annotated[CreateAPIKeyRequest, Body()],
    auth_info: Annotated[AuthInfo, Security(get_current_user)],
    api_key_service: Annotated[ApiKeyService, Depends(getAPIKeyService)],
) -> CreateAPIKeySuccessResponse:
    """Create a new API key with specified permissions for the authenticated user."""
    api_key = await api_key_service.createApiKey(
        auth_info["uid"], request.permissions
    )
    return {"key": api_key.unwrap()}
