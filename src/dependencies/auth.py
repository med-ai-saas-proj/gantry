from src.entities import User
from datetime import datetime
from src.utils.jwt import JWTUtils
from fastapi import Request, HTTPException, Depends
from src.dependencies.user_service import get_user_service
from src.services.user import UserService
import uuid


def get_current_user_form_apikey(api_key: str):
    now = datetime.now()
    return User(
        id="a960652d-1acc-41f2-94c9-0a92299eef9b", email="example@example.com", createdAt=now, updated_at=now
    )


def get_current_user_form_session(session: str):
    now = datetime.now()
    return User(
        id="a960652d-1acc-41f2-94c9-0a92299eef9b", email="test@example.com", createdAt=now, updated_at=now
    )

async def get_current_user(request: Request, user_service: UserService = Depends(get_user_service)):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ")
        try:
            payload = JWTUtils.decode_token(token)
            user_id = payload.get("user_id")
            user = await user_service.get_user_by_id(user_id)
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            return user
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
    raise HTTPException(status_code=401, detail="No valid authentication found")
