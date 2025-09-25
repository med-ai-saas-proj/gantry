from src.dependencies.auth import get_current_user
from src.entities.user import User
from src.initialize.services import API_KEY_SERVICE
from src.dtos.api_key import (
    CreateApiKeyRequestDTO,
    CreateApiKeyResponseDTO,
    ApiKeyListResponseDTO,
    DeleteApiKeyRequestDTO,
)
from src.custom_types.responses import CErrorResponse

from fastapi import APIRouter, Depends, Response
from http import HTTPStatus

api_key_router = APIRouter(prefix="/api-key", tags=["API Key"])


@api_key_router.post(
    "/create",
    response_model=CreateApiKeyResponseDTO,
    status_code=HTTPStatus.CREATED,
)
async def create_api_key(
    request: CreateApiKeyRequestDTO,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new API key for the authenticated user.
    """
    api_key_data = await API_KEY_SERVICE.create_api_key(
        user_id=str(current_user["id"]),
        name=request.name,
        expires_in_days=request.expires_in_days,
    )

    return CreateApiKeyResponseDTO(
        id=api_key_data["id"],
        name=api_key_data["name"],
        api_key=api_key_data["api_key"],
        is_active=api_key_data["is_active"],
        expires_at=(
            api_key_data["expires_at"].isoformat()
            if api_key_data["expires_at"]
            else None
        ),
        created_at=api_key_data["created_at"].isoformat(),
    )


@api_key_router.get("/list", response_model=ApiKeyListResponseDTO)
async def list_api_keys(
    current_user: User = Depends(get_current_user),
):
    """
    List all API keys for the authenticated user.
    """
    api_keys_data = await API_KEY_SERVICE.get_user_api_keys(
        str(current_user["id"])
    )

    # Convert to DTOs
    api_keys = [
        {
            "id": key["id"],
            "name": key["name"],
            "is_active": key["is_active"],
            "last_used_at": (
                key["last_used_at"].isoformat() if key["last_used_at"] else None
            ),
            "expires_at": (
                key["expires_at"].isoformat() if key["expires_at"] else None
            ),
            "created_at": key["created_at"].isoformat(),
            "updated_at": key["updated_at"].isoformat(),
        }
        for key in api_keys_data
    ]

    return ApiKeyListResponseDTO(api_keys=api_keys, total_count=len(api_keys))
