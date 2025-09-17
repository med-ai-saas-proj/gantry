import jwt
from datetime import datetime, timedelta
from src.consts.env import EnvConsts 


class JWTUtils:
    @staticmethod
    def create_token(user_id: str, email: str) -> str:
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(hours=24),  # 24 hour expiry
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, EnvConsts.JWT_SECRET, algorithm="HS256")
        
    @staticmethod
    def decode_token(token: str) -> dict:
        return jwt.decode(token, EnvConsts.JWT_SECRET, algorithms=["HS256"])
