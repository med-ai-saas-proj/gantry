from src.consts.env import EnvConsts

import jwt
from datetime import datetime, timedelta
from typing import Any


class JWTUtils:
    @staticmethod
    def create_token(payload: dict[str, Any]) -> str:
        return jwt.encode(payload, EnvConsts.JWT_SECRET, algorithm="HS256")

    @staticmethod
    def decode_token(token: str) -> dict:
        return jwt.decode(token, EnvConsts.JWT_SECRET, algorithms=["HS256"])
