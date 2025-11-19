import os

ACCESS_TOKEN_SECRET = os.getenv(
    "ACCESS_TOKEN_SECRET", "thisisaanaccesstokensecret"
)

REFRESH_TOKEN_SECRET = os.getenv(
    "REFRESH_TOKEN_SECRET", "thisisarefreshtokensecret"
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))

LOGIN_ATTEMPT_WINDOW_MINUTES = int(
    os.getenv("LOGIN_ATTEMPT_WINDOW_MINUTES", "15")
)

API_KEY_SECRET = os.getenv("API_KEY_SECRET", "thisisasecret")

API_KEY_SECRET_LENGTH = int(os.getenv("API_KEY_SECRET_LENGTH", "32"))

API_KEY_EXPIRE_DAYS = int(os.getenv("API_KEY_EXPIRE_DAYS", "30"))
