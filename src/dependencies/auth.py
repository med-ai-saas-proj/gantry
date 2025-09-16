from src.entities import User
from datetime import datetime


def get_current_user_form_apikey(api_key: str):
    now = datetime.now()
    return User(
        id="", email="example@example.com", createdAt=now, updated_at=now
    )


def get_current_user_form_cookies(cookie: str):
    now = datetime.now()
    return User(
        id="", email="example@example.com", createdAt=now, updated_at=now
    )
