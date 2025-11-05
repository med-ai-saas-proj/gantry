from fastapi import APIRouter, Depends

from ..initialize import get_api_key_service
from ..depends.auth import get_current_user
from ..schemas.api_keys import CreateApiKeyRequest
from ..services.api_keys import ApiKeyService
from ..services.users import UserInfo

router = APIRouter(prefix="/api_keys")


@router.post("/")
async def create_api_key(
        request: CreateApiKeyRequest,
        user: UserInfo = Depends(get_current_user),
        api_key_service: ApiKeyService = Depends(get_api_key_service)
):
    api_key = await api_key_service.create_api_key(user["id"],
                                            request.permissions)
    return {"api_key": api_key}