from . import consts

from typing import Any

import jwt
import bcrypt


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode()

def verify_password(password: str, hashed_password) -> bool:
    if isinstance(hashed_password, memoryview):
        hashed_password = bytes(hashed_password)
    elif isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

def create_token(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, consts.JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> dict:
    return jwt.decode(token, consts.JWT_SECRET, algorithms=["HS256"])
