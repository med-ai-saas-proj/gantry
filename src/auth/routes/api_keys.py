from fastapi import APIRouter, Security

from ..depends.auth import get_current_user
from ..initialize import api_key_service
from ..schemas.api_keys import CreateApiKeyRequest
from ..services.users import AuthInfo

router = APIRouter(prefix="/api_keys")


@router.post("/")
async def create_api_key(
    request: CreateApiKeyRequest,
    user: AuthInfo = Security(get_current_user),
):
    api_key = await api_key_service.create_api_key(
        user["id"], request.permissions
    )
    return {"api_key": api_key}
