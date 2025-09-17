from datetime import datetime
from fastapi import Request, HTTPException, Depends

from src.entities import User
from src.utils.jwt import JWTUtils
from src.initialize.services import USER_SERVICE
from src.services.user import UserService


def get_current_user_form_apikey(api_key: str):
    now = datetime.now()
    return User(
        id="a960652d-1acc-41f2-94c9-0a92299eef9b",
        email="example@example.com",
        createdAt=now,
        updated_at=now,
    )


def get_current_user_form_session(session: str):
    now = datetime.now()
    return User(
        id="a960652d-1acc-41f2-94c9-0a92299eef9b",
        email="test@example.com",
        createdAt=now,
        updated_at=now,
    )


async def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ")
        try:
            payload = JWTUtils.decode_token(token)
            user_id = payload.get("user_id")
            user = await USER_SERVICE.get_user_by_id(user_id)
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            return user
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
    raise HTTPException(status_code=401, detail="No valid authentication found")
