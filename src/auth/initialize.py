from .consts import (
    JWT_SECRET,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    API_KEY_SECRET,
    API_KEY_SECRET_LENGTH,
    API_KEY_EXPIRE_DAYS,
)
from .services.api_keys import ApiKeyService
from .services.users import UserService

user_service: UserService = UserService(
    config={
        "secret_key": JWT_SECRET,
        "algorithm": "HS256",
        "access_token_expire_minutes": ACCESS_TOKEN_EXPIRE_MINUTES,
    }
)

api_key_service: ApiKeyService = ApiKeyService(
    config={
        "key_secret": API_KEY_SECRET,
        "api_key_secret_length": API_KEY_SECRET_LENGTH,
        "expiration_days": API_KEY_EXPIRE_DAYS,
    }
)
