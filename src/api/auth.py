from fastapi import APIRouter, Depends
from src.services.user import UserService
from src.services.postgres import PostgresService
from src.dtos.register import RegisterRequestDTO, ChangePasswordRequestDTO, LoginRequestDTO
from src.consts.common import MessageConsts
from src.custom_types.responses import CResponse
from src.dependencies.user_service import get_user_service
from src.dependencies.auth import get_current_user
from src.entities.user import User
from src.utils.password import PasswordUtils
from src.utils.jwt import JWTUtils
from fastapi import HTTPException


auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post("/register")
async def register(request: RegisterRequestDTO, user_service: UserService = Depends(get_user_service)):
    user = await user_service.register_user(request.email, request.password)
    response = {
        "id": user["id"],
        "email": user["email"],
        "createdAt": user["created_at"].isoformat() if user.get("created_at") else None
    }

    return CResponse(
        http_code=201,
        status_code=201,
        message=MessageConsts.CREATED,
        data=response
    ).to_dict()


@auth_router.post("/change-password")
async def change_password(
    request: ChangePasswordRequestDTO, 
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user)
):
    result = await user_service.change_password(
        user_id=current_user["id"],
        current_password=request.current_password,
        new_password=request.new_password
    )
    
    return CResponse(
        http_code=200,
        status_code=200,
        message=MessageConsts.SUCCESS,
        data=result
    ).to_dict()

@auth_router.post("/login")
async def login(request: LoginRequestDTO, user_service: UserService = Depends(get_user_service)):
    user = await user_service.get_user_by_email(request.email)
    if not user or not PasswordUtils.verify_password(request.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = JWTUtils.create_token(str(user["id"]), user["email"])
    return CResponse(
        http_code=200,
        status_code=200,
        message="Login successful",
        data={"token": token, "user": {"id": user["id"], "email": user["email"]}}
    ).to_dict()