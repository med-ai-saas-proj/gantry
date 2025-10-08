from src.shared.consts import messages_const
from src.shared.utils.logger import LOGGER
from src.shared.custom_types.responses import CErrorResponse, MessagedResponse

from .. import utils
from ..security import get_current_user
from ..initialize import USER_SERVICE
from ..dtos.register import (
    LoginRequestDTO,
    RegisterRequestDTO,
    ChangePasswordRequestDTO,
)
from ..entities.user import User

from http import HTTPStatus
from typing import TypedDict
from datetime import UTC, datetime, timezone, timedelta

from fastapi import Security, APIRouter
from fastapi.responses import JSONResponse


auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post(
    "/register",
    status_code=HTTPStatus.CREATED,
)
async def register(
    request: RegisterRequestDTO,
):
    user = await USER_SERVICE.register_user(request.email, request.password)


@auth_router.post("/change-password", status_code=HTTPStatus.OK)
async def change_password(
    request: ChangePasswordRequestDTO,
    current_user: User = Security(get_current_user),
):
    result = await USER_SERVICE.change_password(
        user_id=current_user["id"],
        current_password=request.current_password,
        new_password=request.new_password,
    )


class LoginResponse(TypedDict):
    token: str


@auth_router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequestDTO,
):
    user = await USER_SERVICE.get_user_by_email(request.email)
    if not user or not utils.verify_password(
        request.password, user["password"]
    ):
        raise CErrorResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            message=messages_const.INVALID_CREDENTIALS,
        )

    payload = {
        "user_id": user["id"],
        "email": user["email"],
        "exp": datetime.now(UTC)
        + timedelta(hours=24),  # 24 hour expiry
        "iat": datetime.now(UTC),
    }

    token = utils.create_token(payload)
    # response = Response()
    # response.set_cookie("token", token, secure=True, expires=payload["exp"])
    return LoginResponse(token=token)
