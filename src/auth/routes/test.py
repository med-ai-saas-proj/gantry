"""Test routes for api key authentication and authorization."""

from src.auth.services.dtos import APIKeyInfo

from ..depends.auth import required_permission

from typing import Annotated

from fastapi import Security, APIRouter


router = APIRouter(prefix="/test")


@router.get("/")
async def test_endpoint(
    api_key_info: Annotated[
        APIKeyInfo, Security(required_permission(["test-permission-1"]))
    ],
):
    """A test endpoint that requires 'test-permission-1' permission."""
    return {
        "message": f"Test endpoint is working for user {api_key_info['user_id']} with test-permission-1"
    }


@router.get("/admin")
async def admin_endpoint(
    api_key_info: Annotated[
        APIKeyInfo,
        Security(
            required_permission(["test-permission-admin", "test-permission-1"])
        ),
    ],
):
    """A test endpoint that requires 'test-permission-admin' and 'test-permission-1' permissions."""
    return {
        "message": f"Admin endpoint is working for admin {api_key_info['user_id']} with admin-permission"
    }
