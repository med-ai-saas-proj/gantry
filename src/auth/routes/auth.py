"""Auth routes module."""

from ..dtos import (
    LoginInput,
    LogoutRequest,
    LoginOutputSuccess,
    RefreshAccessTokenInput,
    RefreshAccessTokenOutputSuccess,
)
from ..factories import UserService, getUserService
from ..depends.auth import get_current_user
from ..entities.auth_info import AuthInfo

from typing import Annotated

from fastapi import Body, Depends, APIRouter
from fastapi.params import Security


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    responses={
        200: {"model": LoginOutputSuccess},
    },
)
async def login(
    credential: Annotated[LoginInput, Body()],
    user_service: Annotated[UserService, Depends(getUserService)],
) -> LoginOutputSuccess:
    """Login with email and password."""
    token = (
        await user_service.emailLogin(
            str(credential.email), credential.password.get_secret_value()
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
        200: {"model": RefreshAccessTokenOutputSuccess},
    },
)
async def refresh_token(
    request: Annotated[RefreshAccessTokenInput, Body()],
    user_service: Annotated[UserService, Depends(getUserService)],
) -> RefreshAccessTokenOutputSuccess:
    """Refresh access token using a valid refresh token."""
    token = (
        await user_service.refreshAccessToken(
            refresh_token=request.refresh_token
        )
    ).unwrap()

    return RefreshAccessTokenOutputSuccess(
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
