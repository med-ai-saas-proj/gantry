from .dtos import ApiKeyOutput, CreateAPIKeyInput, CreateAPIKeyOutputSuccess
from .factories import ApiKeyService, getApiKeyService
from ..auth.dependencies import UserInfo, getUserInfo

from typing import Annotated

from fastapi import Body, Path, Depends, APIRouter


apikey_router = APIRouter(
    prefix="/api-keys",
    tags=["api-keys"],
    include_in_schema=True,
)


@apikey_router.post("", tags=["api-keys"])
async def createApiKey(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    input: Annotated[CreateAPIKeyInput, Body()],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
) -> CreateAPIKeyOutputSuccess:
    api_key_ = await apikey_service.createApiKey(
        user_info["id"], input.name, input.description, input.permissions
    )
    return api_key_.unwrap()


@apikey_router.get("", tags=["api-keys"])
async def getApiKeys(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
) -> list[ApiKeyOutput]:
    """Get all API keys for the current user."""
    result = await apikey_service.getApiKeys(user_info["id"])
    return result.unwrap()


@apikey_router.delete("/{key_id}", tags=["api-keys"])
async def deleteApiKey(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    key_id: Annotated[int, Path(title="The ID of the API key to delete")],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
):
    """Delete a specific API key by ID."""
    result = await apikey_service.deleteApiKey(user_info["id"], key_id)
    return result.unwrap()
