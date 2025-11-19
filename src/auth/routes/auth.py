from ..dtos import LoginInput, LoginOutputSuccess
from ..factories import UserService, getUserService

from typing import Annotated

from fastapi import Body, Depends, APIRouter
from safe_result import Ok, Err


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    responses={
        200: {"model": LoginOutputSuccess},
    },
)
async def login_user(
    credential: Annotated[LoginInput, Body()],
    user_service: Annotated[UserService, Depends(getUserService)],
) -> LoginOutputSuccess:
    token_ = await user_service.emailLogin(
        credential.email, credential.password.get_secret_value()
    )
    token = token_.unwrap()
    return {
        "token_type": "Bearer",
        "access_token": token["access_token"],
        "expire_in": token["expires_in"],
        "refresh_token": "",
    }
