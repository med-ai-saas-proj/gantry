from fastapi import APIRouter
from fastapi.params import Depends

from ..initialize import get_user_service
from ..schemas.users import (
    EmailRegisterRequest,
    RegisterResponse,
    EmailLoginRequest,
    LoginResponse,
)
from ..services.users import UserService

router = APIRouter(prefix="/auth")


@router.post("/email-register", response_model=RegisterResponse)
async def register_user(
    request: EmailRegisterRequest,
    user_service: UserService = Depends(get_user_service),
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
    user_service: UserService = Depends(get_user_service),
):
    token = await user_service.email_login(
        email=request.username, password=request.password
    )

    return LoginResponse(
        access_token=token["access_token"],
        token_type=token["token_type"],
        expires_in=token["expires_in"],
    )
