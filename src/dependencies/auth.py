from src.entities import User
from datetime import datetime
from fastapi import Request


def get_current_user_form_apikey(api_key: str):
    now = datetime.now()
    return User(
        id="", email="example@example.com", createdAt=now, updated_at=now
    )


def get_current_user_form_session(session: str):
    now = datetime.now()
    return User(
        id="", email="example@example.com", createdAt=now, updated_at=now
    )


def get_current_user(request: Request):
    api_key = request.headers.get("Authorization", "").removeprefix("Bearer ")
    session: str = request.cookies.get("session", "")
    if session:
        return get_current_user_form_session(session)
    return get_current_user_form_apikey(api_key)
