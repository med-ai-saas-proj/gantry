from src.db_v2.initialize import redis as redis_client, session_manager
from src.shared.custom_types.error_exception import (
    RecoverableError,
    UnrecoverableError,
)

from ..models.users import User, UserRepo
from ..models.initialize import user_repo
from ..entities.auth_info import AuthInfo, TokenInfo, JwtPayload

from typing import TypedDict, NotRequired
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from sqlalchemy import select
from safe_result import Ok, Err, Result
from passlib.context import CryptContext
from structlog.stdlib import BoundLogger


class TooManyLoginAttemptsError(RecoverableError):
    code = "too_many_login_attempts"
    title = "Too many login attempts"
    detail = "You have exceeded the maximum number of login attempts. Please try again later."
    status = 429


class UserExistedError(RecoverableError):
    code = "user_existed"
    title = "User already exists"
    detail = (
        "The provided email was used for another account, try login instead"
    )
    status = 400


class InvalidCredentialError(RecoverableError):
    code = "invalid_credential"
    title = "Invalid email or password"
    detail = "The provided email or password is incorrect"
    status = 401


class InvalidAccessTokenError(RecoverableError):
    code = "invalid_access_token"
    title = "Invalid access token"
    detail = "Access token is not set or is invalid (expired, corrupted, ...)"
    status = 401


class InvalidRefreshTokenError(RecoverableError):
    code = "invalid_refresh_token"
    title = "Invalid refresh token"
    detail = "Refresh token is not set or is invalid (expired, corrupted, ...)"
    status = 401


class JWTEncodeError(UnrecoverableError):
    detail = "JWT encode error, we **** up, check the code. FAST!!!"


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password) -> str:
    return pwd_context.hash(password)


def createAccessToken(
    data: JwtPayload,
    secret_key: str,
    algorithm: str,
    expires_delta: timedelta | None = None,
) -> Result[str, JWTEncodeError]:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
        to_encode.update({"exp": int(expire.timestamp())})
    try:
        return Ok(jwt.encode(to_encode, secret_key, algorithm=algorithm))
    except JWTError as e:
        return Err(JWTEncodeError(e))


def getCurrentUserFromToken(
    token: str, secret_key: str, algorithm: str
) -> Result[AuthInfo, InvalidAccessTokenError]:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    except JWTError as e:
        return Err(InvalidAccessTokenError(e))
    user_id = payload.get("sub")
    user_email = payload.get("email")
    if (
        user_email is None
        or user_id is None
        or not isinstance(user_email, str)
        or not isinstance(user_id, str)
    ):
        return Err(InvalidAccessTokenError())
    return Ok[AuthInfo]({"id": user_id, "email": user_email})


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
    def __init__(self, config: UserServiceConfig, logger: BoundLogger):
        self.logger = logger
        self.access_token_secret_key = config["access_token_secret_key"]
        self.access_token_algorithm = config["access_token_algorithm"]
        self.access_token_expire = timedelta(
            minutes=config.get("access_token_expire_minutes", 60)
        )
        self.refresh_token_secret_key = config["refresh_token_secret_key"]
        self.refresh_token_algorithm = config["refresh_token_algorithm"]
        self.refresh_token_expire = timedelta(
            days=config.get("refresh_token_expire_days", 30)
        )
        self.max_login_attempts = config.get("max_login_attempts", 3)
        self.login_attempt_window = timedelta(
            minutes=config.get("login_attempt_window_minutes", 15)
        )

    async def emailRegister(
        self, username: str, email: str, password: str
    ) -> Result[User, UserExistedError]:
        async with session_manager.get_session() as session:
            existed_user = await user_repo.get_one(
                session,
                select(UserRepo.table)
                .where(
                    (UserRepo.c.username == username)
                    | (UserRepo.c.email == email)
                )
                .limit(1),
            )

            if existed_user:
                return Err(UserExistedError())

            hashed_password = get_password_hash(password)
            new_user = User(
                username=username, email=email, hashed_password=hashed_password
            )
            res: User = await user_repo.insert(session, new_user).returning()
            await session.commit()
            return Ok(res)

    async def emailLogin(
        self, email: str, password: str
    ) -> Result[
        TokenInfo,
        InvalidCredentialError | JWTEncodeError | TooManyLoginAttemptsError,
    ]:
        async with session_manager.get_session() as session:
            login_attempt = await redis_client.get(
                f"auth:login_attempt:{email}"
            )
            if login_attempt and int(login_attempt) >= self.max_login_attempts:
                return Err(TooManyLoginAttemptsError())

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
                    time=self.login_attempt_window,
                )
                return Err(InvalidCredentialError())

            access_token = createAccessToken(
                data={
                    "sub": str(user.id),
                    "email": user.email,
                },
                secret_key=self.access_token_secret_key,
                algorithm=self.access_token_algorithm,
                expires_delta=self.access_token_expire,
            ).unwrap()

            refresh_token = createAccessToken(
                data={
                    "sub": str(user.id),
                    "email": user.email,
                },
                secret_key=self.refresh_token_secret_key,
                algorithm=self.refresh_token_algorithm,
                expires_delta=self.refresh_token_expire,
            ).unwrap()

            await redis_client.delete(f"auth:login_attempt:{email}")
            await redis_client.set(
                f"auth:refresh_token:{str(user.id)}:{refresh_token}",
                "",  # value is not important
                ex=self.refresh_token_expire,
            )

            return Ok[TokenInfo](
                {
                    "access_token": access_token,
                    "token_type": "Bearer",
                    "expires_in": int(self.access_token_expire.total_seconds()),
                    "refresh_token": refresh_token,
                    "refresh_token_expires_in": int(
                        self.refresh_token_expire.total_seconds()
                    ),
                }
            )

    def getUserInfoFromAccessToken(self, token: str):
        return getCurrentUserFromToken(
            token, self.access_token_secret_key, self.access_token_algorithm
        )

    async def refreshAccessToken(
        self, refresh_token: str
    ) -> Result[
        TokenInfo,
        InvalidAccessTokenError | JWTEncodeError | InvalidRefreshTokenError,
    ]:
        self.logger.debug(
            "Refreshing access token with refresh token:", refresh_token
        )
        self.logger.debug("Secret key:", self.refresh_token_secret_key)
        self.logger.debug("Algorithm:", self.refresh_token_algorithm)
        self.logger.debug("Expire:", self.refresh_token_expire.total_seconds())
        auth_info = getCurrentUserFromToken(
            refresh_token,
            self.refresh_token_secret_key,
            self.refresh_token_algorithm,
        )
        if auth_info.error is not None:
            return auth_info

        user_id = auth_info.value["id"]
        redis_key = f"auth:refresh_token:{user_id}:{refresh_token}"
        exists = await redis_client.exists(redis_key)
        if not exists:
            return Err(InvalidRefreshTokenError())

        access_token = createAccessToken(
            data={
                "sub": str(user_id),
                "email": auth_info.value["email"],
            },
            secret_key=self.access_token_secret_key,
            algorithm=self.access_token_algorithm,
            expires_delta=self.access_token_expire,
        ).unwrap()

        return Ok[TokenInfo](
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": int(self.access_token_expire.total_seconds()),
            }
        )

    async def logout(self, auth_info: AuthInfo, refresh_token: str):
        user_id = auth_info["id"]
        pattern = f"auth:refresh_token:{user_id}:{refresh_token}"
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)
        return
