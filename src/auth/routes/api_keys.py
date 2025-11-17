from fastapi import APIRouter, Depends, Security

from ..initialize import get_api_key_service
from ..depends.auth import get_current_user
from ..schemas.api_keys import CreateApiKeyRequest
from ..services.api_keys import ApiKeyService
from ..services.users import AuthInfo

router = APIRouter(prefix="/api_keys")


@router.post("/")
async def create_api_key(
    request: CreateApiKeyRequest,
    user: AuthInfo = Security(get_current_user),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    api_key = await api_key_service.create_api_key(
        user["id"], request.permissions
    )
    return {"api_key": api_key}
