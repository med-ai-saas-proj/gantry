from fastapi import APIRouter, Depends

from ..depends.auth import get_current_user
from ..entities.auth_info import AuthInfo
from ..initialize import user_service
from ..schemas.users import (
    EmailRegisterRequest,
    RegisterResponse,
    EmailLoginRequest,
    RefreshTokenRequest,
    LoginResponse,
    RefreshTokenResponse,
    LogoutResponse,
)

router = APIRouter(prefix="/auth")


@router.post("/email-register", response_model=RegisterResponse)
async def register_user(
    request: EmailRegisterRequest,
):
    user = await user_service.email_register(
        email=request.email,
        password=request.password,
        username=request.username,
    )

    return RegisterResponse(user_id=str(user.id), username=user.username)


@router.post("/login", response_model=LoginResponse)
async def login_user(
    request: EmailLoginRequest,
):
    token = await user_service.email_login(
        email=request.username, password=request.password
    )

    return LoginResponse(
        access_token=token["access_token"],
        token_type=token["token_type"],
        expires_in=token["expires_in"],
        refresh_token=token["refresh_token"],
        refresh_token_expires_in=token["refresh_token_expires_in"],
    )


@router.post("/refresh-token", response_model=RefreshTokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    token = await user_service.refresh_access_token(
        refresh_token=request.refresh_token
    )

    return RefreshTokenResponse(
        access_token=token["access_token"],
        token_type=token["token_type"],
        expires_in=token["expires_in"],
    )


@router.post("/logout")
async def logout_user(
    request: LogoutResponse, auth_info: AuthInfo = Depends(get_current_user)
):
    await user_service.logout(auth_info, request.refresh_token)
