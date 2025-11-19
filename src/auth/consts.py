import os

JWT_SECRET = os.getenv("JWT_SECRET", "thisisasecret")

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

API_KEY_SECRET = os.getenv("API_KEY_SECRET", "thisisasecret")

API_KEY_SECRET_LENGTH = int(os.getenv("API_KEY_SECRET_LENGTH", "32"))

API_KEY_EXPIRE_DAYS = int(os.getenv("API_KEY_EXPIRE_DAYS", "30"))
