from .dtos import CreateAPIKeyInput, CreateAPIKeyOutputSuccess
from .factories import ApiKeyService, getApiKeyService
from ..auth.dependencies import UserInfo, getUserInfo

from typing import Annotated

from fastapi import Body, Depends, APIRouter


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
async def getApiKeys(user_info: Annotated[UserInfo, Depends(getUserInfo)]):
    return None


@apikey_router.delete("", tags=["api-keys"])
async def deleteApiKeys(user_info: Annotated[UserInfo, Depends(getUserInfo)]):
    return None
