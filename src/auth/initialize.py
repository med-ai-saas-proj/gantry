from .consts import (
    ACCESS_TOKEN_SECRET,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    API_KEY_SECRET,
    API_KEY_SECRET_LENGTH,
    REFRESH_TOKEN_EXPIRE_DAYS,
    API_KEY_EXPIRE_DAYS,
    MAX_LOGIN_ATTEMPTS,
    LOGIN_ATTEMPT_WINDOW_MINUTES,
)
from .services.api_keys import ApiKeyService
from .services.users import UserService

user_service: UserService = UserService(
    config={
        "access_token_secret_key": ACCESS_TOKEN_SECRET,
        "access_token_algorithm": "HS256",
        "access_token_expire_minutes": ACCESS_TOKEN_EXPIRE_MINUTES,
        "refresh_token_secret_key": ACCESS_TOKEN_SECRET,
        "refresh_token_algorithm": "HS256",
        "refresh_token_expire_days": REFRESH_TOKEN_EXPIRE_DAYS,
        "max_login_attempts": MAX_LOGIN_ATTEMPTS,
        "login_attempt_window_minutes": LOGIN_ATTEMPT_WINDOW_MINUTES,
    }
)

api_key_service: ApiKeyService = ApiKeyService(
    config={
        "key_secret": API_KEY_SECRET,
        "api_key_secret_length": API_KEY_SECRET_LENGTH,
        "expiration_days": API_KEY_EXPIRE_DAYS,
    }
)
