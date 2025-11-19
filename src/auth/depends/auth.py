from fastapi import Security, Depends
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader

from ..initialize import user_service, api_key_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def get_current_user(
    token: str = Security(oauth2_scheme),
):
    return user_service.get_user_info_from_access_token(token)


API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def required_permission(permission: list[str]):
    async def get_api_key(
        api_key: str = Security(api_key_header),
    ):
        return await api_key_service.verify_api_key(api_key, permission)

    return get_api_key
