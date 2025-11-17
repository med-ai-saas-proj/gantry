from datetime import datetime, timedelta, timezone
from typing import TypedDict, NotRequired

from fastapi import HTTPException

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select

from src.db_v2.initialize import session_manager
from ..entities.auth_info import JwtPayload, AuthInfo, TokenInfo
from ..models.users import UserRepo, User
from ..models.initialize import user_repo

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password) -> str:
    return pwd_context.hash(password)


def create_access_token(
    data: JwtPayload,
    secret_key: str,
    algorithm: str,
    expires_delta: int | None = None,
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + timedelta(minutes=expires_delta)
        to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


def get_current_user_from_token(
    token: str, secret_key: str, algorithm: str
) -> AuthInfo:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        user_id: str = payload.get("sub")
        username: str = payload.get("name")
        if username is None or user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"id": user_id, "username": username}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


class UserServiceConfig(TypedDict):
    secret_key: str
    algorithm: NotRequired[str]
    access_token_expire_minutes: NotRequired[int]


class UserService:
    def __init__(self, config: UserServiceConfig):
        self.secret_key = config["secret_key"]
        self.algorithm = config.get("algorithm", "HS256")
        self.access_token_expire_minutes = config.get(
            "access_token_expire_minutes", 60
        )

    async def email_register(self, username: str, email: str, password: str):
        async with session_manager.get_session() as session:
            existed_user: User = await user_repo.get_one(
                session,
                select(UserRepo.table)
                .where(
                    (UserRepo.c.username == username)
                    | (UserRepo.c.email == email)
                )
                .limit(1),
            )

            if existed_user:
                raise HTTPException(
                    status_code=400,
                    detail="Username or email already registered",
                )

            hashed_password = get_password_hash(password)
            new_user = User(
                username=username, email=email, hashed_password=hashed_password
            )
            res: User = await user_repo.insert(session, new_user).returning()
            await session.commit()
            return res

    async def email_login(self, email: str, password: str) -> TokenInfo:
        async with session_manager.get_session() as session:
            user = await user_repo.get_one(
                session,
                select(UserRepo.table)
                .where(UserRepo.c.email == email)
                .limit(1),
            )

            if not user or not verify_password(password, user.hashed_password):
                raise HTTPException(
                    status_code=401, detail="Invalid email or password"
                )

            token = create_access_token(
                data={
                    "sub": str(user.id),
                    "name": user.username,
                },
                secret_key=self.secret_key,
                algorithm=self.algorithm,
                expires_delta=self.access_token_expire_minutes,
            )
            return {
                "access_token": token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60,
            }

    def get_user_info_from_token(self, token: str) -> AuthInfo:
        return get_current_user_from_token(
            token, self.secret_key, self.algorithm
        )
