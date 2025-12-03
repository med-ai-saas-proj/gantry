"""Auth routes module."""

from src.auth.services.dtos import AuthInfo

from .dtos import (
    LoginRequest,
    LogoutRequest,
    LoginSuccessResponse,
    RefreshAccessTokenRequest,
    RefreshAccessTokenSuccessResponse,
)
from ..depends.auth import get_current_user
from ..services.factories import UserService, getUserService

from typing import Annotated

from fastapi import Body, Depends, APIRouter
from fastapi.params import Security


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    responses={
        200: {"model": LoginSuccessResponse},
    },
)
async def login(
    credential: Annotated[LoginRequest, Body()],
    user_service: Annotated[UserService, Depends(getUserService)],
) -> LoginSuccessResponse:
    """Login with email and password."""
    token = (
        await user_service.emailLogin(
            str(credential.username), credential.password.get_secret_value()
        )
    ).unwrap()

    return {
        "token_type": "Bearer",
        "access_token": token["access_token"],
        "expire_in": token["expires_in"],
        "refresh_token": token["refresh_token"],
        "refresh_token_expires_in": token["refresh_token_expires_in"],
    }


@router.post(
    "/refresh-token",
    responses={
        200: {"model": RefreshAccessTokenSuccessResponse},
    },
)
async def refreshToken(
    request: Annotated[RefreshAccessTokenRequest, Body()],
    user_service: Annotated[UserService, Depends(getUserService)],
) -> RefreshAccessTokenSuccessResponse:
    """Refresh access token using a valid refresh token."""
    token = (
        await user_service.refreshAccessToken(
            refresh_token=request.refresh_token
        )
    ).unwrap()

    return RefreshAccessTokenSuccessResponse(
        access_token=token["access_token"],
        token_type=token["token_type"],
        expires_in=token["expires_in"],
    )


@router.post(
    "/logout",
    responses={
        200: {"description": "Logout successful"},
    },
)
async def logout(
    request: Annotated[LogoutRequest, Body()],
    user_service: Annotated[UserService, Depends(getUserService)],
    auth_info: Annotated[AuthInfo, Security(get_current_user)],
):
    """Logout the current user by invalidating the refresh token."""
    await user_service.logout(auth_info, request.refresh_token)
