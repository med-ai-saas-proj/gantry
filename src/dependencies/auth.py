from fastapi import Request, HTTPException, Depends
from fastapi.security import OAuth2AuthorizationCodeBearer, OAuth2PasswordBearer

from src.utils.jwt import JWTUtils
from src.initialize.services import USER_SERVICE


# oauth2_auth_code = OAuth2AuthorizationCodeBearer("/login", "/login")
# oauth2_password = OAuth2PasswordBearer("/login")


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
