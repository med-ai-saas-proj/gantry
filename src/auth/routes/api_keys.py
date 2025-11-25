from ..dtos import (
    ApiKeyResponse,
    CreateAPIKeyInput,
    CreateAPIKeyOutputSuccess,
    UpdateApiKeyInput,
)
from ..factories import ApiKeyService, getAPIKeyService
from ..depends.auth import get_current_user
from ..services.users import AuthInfo

from typing import Annotated

from fastapi import Body, Depends, Security, APIRouter


router = APIRouter(prefix="/api_keys", tags=["API keys"])


@router.post(
    "",
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


@router.get(
    "/",
    responses={
        200: {"model": list[ApiKeyResponse]},
    },
)
async def get_api_keys(
    user: Annotated[AuthInfo, Security(get_current_user)],
    api_key_service: Annotated[ApiKeyService, Depends(getAPIKeyService)],
) -> list[ApiKeyResponse]:
    keys = await api_key_service.get_user_api_keys(user["id"])
    return [
        {
            "id": str(key.id),
            "name": key.name,
            "is_active": key.is_active,
            "expiration_date": key.expiration_date,
            "created_at": key.created_at,
        }
        for key in keys
    ]


@router.put(
    "/{key_id}",
    responses={
        200: {"model": ApiKeyResponse},
    },
)
async def update_api_key(
    key_id: str,
    request: Annotated[UpdateApiKeyInput, Body()],
    user: Annotated[AuthInfo, Security(get_current_user)],
    api_key_service: Annotated[ApiKeyService, Depends(getAPIKeyService)],
) -> ApiKeyResponse:
    result = await api_key_service.update_api_key(
        user["id"], key_id, name=request.name, is_active=request.is_active
    )
    updated_key = result.unwrap()

    return {
        "id": str(updated_key.id),
        "name": updated_key.name,
        "is_active": updated_key.is_active,
        "expiration_date": updated_key.expiration_date,
        "created_at": updated_key.created_at,
    }


@router.delete(
    "/{key_id}",
    responses={
        204: {"model": None},
    },
)
async def delete_api_key(
    key_id: str,
    user: Annotated[AuthInfo, Security(get_current_user)],
    api_key_service: Annotated[ApiKeyService, Depends(getAPIKeyService)],
):
    result = await api_key_service.revoke_api_key(user["id"], key_id)

    return None
