from src.dtos.register import (
    RegisterRequestDTO,
    ChangePasswordRequestDTO,
    LoginRequestDTO,
)
from src.consts.common import MessageConsts
from src.custom_types.responses import MessagedResponse, CErrorResponse
from src.initialize.services import USER_SERVICE
from src.dependencies.auth import get_current_user
from src.entities.user import User
from src.utils.password import PasswordUtils
from src.utils.jwt import JWTUtils

from typing import TypedDict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from starlette.responses import http


auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post(
    "/register",
    response_model=MessagedResponse,
    status_code=http.HTTPStatus.CREATED,
)
async def register(
    request: RegisterRequestDTO,
):
    user = await USER_SERVICE.register_user(request.email, request.password)
    response = {
        "id": user["id"],
        "email": user["email"],
        "createdAt": (
            user["created_at"].isoformat() if user.get("created_at") else None
        ),
    }

    return MessagedResponse(
        status_code=http.HTTPStatus.CREATED,
        message=MessageConsts.CREATED,
    )


@auth_router.post("/change-password", response_model=MessagedResponse)
async def change_password(
    request: ChangePasswordRequestDTO,
    current_user: User = Depends(get_current_user),
):
    result = await USER_SERVICE.change_password(
        user_id=current_user["id"],
        current_password=request.current_password,
        new_password=request.new_password,
    )

    return MessagedResponse(
        status_code=http.HTTPStatus.OK,
        message=MessageConsts.SUCCESS,
    )


class LoginResponse(TypedDict):
    token: str


@auth_router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequestDTO,
):
    user = await USER_SERVICE.get_user_by_email(request.email)
    if not user or not PasswordUtils.verify_password(
        request.password, user["password"]
    ):
        raise CErrorResponse(
            status_code=http.HTTPStatus.BAD_REQUEST,
            message=MessageConsts.INVALID_CREDENTIALS,
        )

    payload = {
        "user_id": user["id"],
        "email": user["email"],
        "exp": datetime.now(timezone.utc)
        + timedelta(hours=24),  # 24 hour expiry
        "iat": datetime.now(timezone.utc),
    }

    token = JWTUtils.create_token(payload)
    # response = Response()
    # response.set_cookie("token", token, secure=True, expires=payload["exp"])
    return LoginResponse(token=token)
