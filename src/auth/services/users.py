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
from ...shared.redis import redis_client

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password) -> str:
    return pwd_context.hash(password)


def create_token(
    data: JwtPayload,
    secret_key: str,
    algorithm: str,
    expires_delta: int | None = None,  # in seconds
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + timedelta(seconds=expires_delta)
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
    access_token_secret_key: str
    access_token_algorithm: str
    access_token_expire_minutes: NotRequired[int]
    refresh_token_secret_key: str
    refresh_token_algorithm: str
    refresh_token_expire_days: NotRequired[int]
    max_login_attempts: NotRequired[int]
    login_attempt_window_minutes: NotRequired[int]


class UserService:
    def __init__(self, config: UserServiceConfig):
        self.access_token_secret_key = config["access_token_secret_key"]
        self.access_token_algorithm = config["access_token_algorithm"]
        self.access_token_expire_minutes = config.get(
            "access_token_expire_minutes", 60
        )
        self.refresh_token_secret_key = config["refresh_token_secret_key"]
        self.refresh_token_algorithm = config["refresh_token_algorithm"]
        self.refresh_token_expire_days = config.get(
            "refresh_token_expire_days", 30
        )
        self.max_login_attempts = config.get("max_login_attempts", 3)
        self.login_attempt_window_minutes = config.get(
            "login_attempt_window_minutes", 15
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
            login_attempt = await redis_client.get(
                f"auth:login_attempt:{email}"
            )
            if login_attempt and int(login_attempt) >= self.max_login_attempts:
                raise HTTPException(
                    status_code=429,
                    detail="Too many login attempts. Please try again later.",
                )

            user = await user_repo.get_one(
                session,
                select(UserRepo.table)
                .where(UserRepo.c.email == email)
                .limit(1),
            )

            if not user or not verify_password(password, user.hashed_password):
                await redis_client.incr(f"auth:login_attempt:{email}", 1)
                await redis_client.expire(
                    f"auth:login_attempt:{email}",
                    time=self.login_attempt_window_minutes * 60,
                )
                raise HTTPException(
                    status_code=401, detail="Invalid email or password"
                )

            access_token = create_token(
                data={
                    "sub": str(user.id),
                    "name": user.username,
                },
                secret_key=self.access_token_secret_key,
                algorithm=self.access_token_algorithm,
                expires_delta=self.access_token_expire_minutes * 60,
            )

            refresh_token = create_token(
                data={
                    "sub": str(user.id),
                    "name": user.username,
                },
                secret_key=self.refresh_token_secret_key,
                algorithm=self.refresh_token_algorithm,
                expires_delta=self.refresh_token_expire_days * 24 * 60 * 60,
            )

            await redis_client.delete(f"auth:login_attempt:{email}")
            await redis_client.set(
                f"auth:refresh_token:{str(user.id)}:{refresh_token}",
                access_token,  # store access token for reference
                ex=self.refresh_token_expire_days * 24 * 60 * 60,
            )

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60,
                "refresh_token": refresh_token,
                "refresh_token_expires_in": self.refresh_token_expire_days
                * 24
                * 60
                * 60,
            }

    def get_user_info_from_access_token(self, token: str) -> AuthInfo:
        return get_current_user_from_token(
            token, self.access_token_secret_key, self.access_token_algorithm
        )

    async def refresh_access_token(self, refresh_token: str):
        auth_info = get_current_user_from_token(
            refresh_token,
            self.refresh_token_secret_key,
            self.refresh_token_algorithm,
        )
        user_id = auth_info["id"]
        redis_key = f"auth:refresh_token:{user_id}:{refresh_token}"
        exists = await redis_client.exists(redis_key)
        if not exists:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        access_token = create_token(
            data={
                "sub": str(user_id),
                "name": auth_info["username"],
            },
            secret_key=self.access_token_secret_key,
            algorithm=self.access_token_algorithm,
            expires_delta=self.access_token_expire_minutes * 60,
        )

        await redis_client.set(
            redis_key,
            access_token,  # update stored access token
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
        }

    async def logout(self, auth_info: AuthInfo, refresh_token: str):
        user_id = auth_info["id"]
        pattern = f"auth:refresh_token:{user_id}:{refresh_token}"
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)
        return
