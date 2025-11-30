"""User service."""

from src.db_v2.initialize import redis as redis_client, session_manager
from src.auth.repositories.users import UserRepository
from src.shared.custom_types.error_exception import (
    RecoverableError,
    UnrecoverableError,
)

from ..models.users import User
from ..entities.auth_info import (
    AuthInfo,
    JwtPayload,
    LoginTokenData,
    RefreshTokenData,
)
from ...shared.utils.result import err

import uuid
from typing import TypedDict, NotRequired
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from safe_result import Ok, Err, Result
from passlib.context import CryptContext
from structlog.stdlib import BoundLogger


class TooManyLoginAttemptsError(RecoverableError):
    """Raised when too many login attempts are made in a short period."""

    code = "too_many_login_attempts"
    title = "Too many login attempts"
    detail = "You have exceeded the maximum number of login attempts. Please try again later."
    status = 429


class UserExistedError(RecoverableError):
    """Raised when trying to register a user that already exists."""

    code = "user_existed"
    title = "User already exists"
    detail = (
        "The provided email was used for another account, try login instead"
    )
    status = 400


class InvalidCredentialError(RecoverableError):
    """Raised when invalid credentials are provided."""

    code = "invalid_credential"
    title = "Invalid email or password"
    detail = "The provided email or password is incorrect"
    status = 401


class InvalidAccessTokenError(RecoverableError):
    """Raised when an invalid access token is provided."""

    code = "invalid_access_token"
    title = "Invalid access token"
    detail = "Access token is not set or is invalid (expired, corrupted, ...)"
    status = 401


class InvalidRefreshTokenError(RecoverableError):
    """Raised when an invalid refresh token is provided."""

    code = "invalid_refresh_token"
    title = "Invalid refresh token"
    detail = "Refresh token is not set or is invalid (expired, corrupted, ...)"
    status = 401


class JWTEncodeError(UnrecoverableError):
    """Raised when there is an error encoding a JWT."""

    detail = "JWT encode error, we **** up, check the code. FAST!!!"


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _verifyPassword(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _getPasswordHash(password) -> str:
    return pwd_context.hash(password)


def _createAccessToken(
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
        return Ok(
            jwt.encode(dict(**to_encode), secret_key, algorithm=algorithm)
        )
    except JWTError as e:
        return Err(JWTEncodeError(e))


def _getCurrentUserFromToken(
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
    """Configuration for UserService."""

    access_token_secret_key: str
    access_token_algorithm: str
    access_token_expire_minutes: NotRequired[int]
    refresh_token_secret_key: str
    refresh_token_algorithm: str
    refresh_token_expire_days: NotRequired[int]
    max_login_attempts: NotRequired[int]
    login_attempt_window_minutes: NotRequired[int]


class UserService:
    """User service."""

    def __init__(self,
                 config: UserServiceConfig,
                 logger: BoundLogger,
                 user_repo: UserRepository
                 ):
        """Initialize UserService with configuration and logger."""
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
        self.user_repo = user_repo

    async def emailRegister(
        self, username: str, email: str, password: str
    ) -> Result[User, UserExistedError]:
        """Register a new user with email and password."""
        async with session_manager.get_session() as session:
            existed_user = await self.user_repo.getByUsernameOrEmail(
                session, username, email, [User.id]
            )

            if existed_user:
                return Err(UserExistedError())

            hashed_password = _getPasswordHash(password)
            new_user = User(
                username=username, email=email, hashed_password=hashed_password
            )
            await self.user_repo.add(session, new_user)
            await session.commit()
            await session.refresh(new_user)
            return Ok(new_user)

    async def emailLogin(
        self, email: str, password: str
    ) -> Result[
        LoginTokenData,
        InvalidCredentialError | JWTEncodeError | TooManyLoginAttemptsError,
    ]:
        """Login a user with email and password."""
        async with session_manager.get_session() as session:
            redis_key_login_attempt = self._redisKeyForLoginAttempt(email)

            login_attempt = await redis_client.get(redis_key_login_attempt)
            if login_attempt and int(login_attempt) >= self.max_login_attempts:
                return Err(TooManyLoginAttemptsError())

            user = await self.user_repo.getByEmail(
                session, email, [User.id, User.email, User.hashed_password]
            )

            if not user or not _verifyPassword(password, user.hashed_password):
                await redis_client.incr(redis_key_login_attempt, 1)
                await redis_client.expire(
                    redis_key_login_attempt,
                    time=self.login_attempt_window,
                )
                return Err(InvalidCredentialError())

            access_token_ = _createAccessToken(
                data={
                    "sub": str(user.id),
                    "email": user.email,
                },
                secret_key=self.access_token_secret_key,
                algorithm=self.access_token_algorithm,
                expires_delta=self.access_token_expire,
            )
            if err(access_token_):
                return access_token_

            refresh_token_ = _createAccessToken(
                data={
                    "sub": str(user.id),
                    "email": user.email,
                },
                secret_key=self.refresh_token_secret_key,
                algorithm=self.refresh_token_algorithm,
                expires_delta=self.refresh_token_expire,
            )
            if err(refresh_token_):
                return refresh_token_

            access_token = access_token_.unwrap()
            refresh_token = refresh_token_.unwrap()

            await redis_client.delete(redis_key_login_attempt)
            await redis_client.set(
                self._redisKeyForRefreshToken(user.id, refresh_token),
                "",  # value is not important
                ex=self.refresh_token_expire,
            )

            return Ok[LoginTokenData](
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

    def _redisKeyForRefreshToken(
        self, user_id: uuid.UUID | str, refresh_token: str
    ) -> str:
        return f"auth:refresh_token:{user_id}:{refresh_token}"

    def _redisKeyForLoginAttempt(self, email: str) -> str:
        return f"auth:login_attempt:{email}"

    def getUserInfoFromAccessToken(self, token: str):
        """Get user info from access token."""
        return _getCurrentUserFromToken(
            token, self.access_token_secret_key, self.access_token_algorithm
        )

    async def refreshAccessToken(
        self, refresh_token: str
    ) -> Result[
        RefreshTokenData,
        InvalidAccessTokenError | JWTEncodeError | InvalidRefreshTokenError,
    ]:
        """Generate a new access token using the provided refresh token."""
        # self.logger.debug(
        #     "Refreshing access token with refresh token:", refresh_token
        # )
        # self.logger.debug("Secret key:", self.refresh_token_secret_key)
        # self.logger.debug("Algorithm:", self.refresh_token_algorithm)
        # self.logger.debug("Expire:", self.refresh_token_expire.total_seconds())
        auth_info_ = _getCurrentUserFromToken(
            refresh_token,
            self.refresh_token_secret_key,
            self.refresh_token_algorithm,
        )
        if err(auth_info_):
            return auth_info_

        auth_info = auth_info_.unwrap()
        user_id = auth_info["id"]
        redis_key = self._redisKeyForRefreshToken(user_id, refresh_token)
        exists = await redis_client.exists(redis_key)
        if not exists:
            return Err(InvalidRefreshTokenError())

        access_token_ = _createAccessToken(
            data={
                "sub": str(user_id),
                "email": auth_info["email"],
            },
            secret_key=self.access_token_secret_key,
            algorithm=self.access_token_algorithm,
            expires_delta=self.access_token_expire,
        )

        if err(access_token_):
            return access_token_

        access_token = access_token_.unwrap()

        return Ok[RefreshTokenData](
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": int(self.access_token_expire.total_seconds()),
            }
        )

    async def logout(self, auth_info: AuthInfo, refresh_token: str):
        """Invalidate the refresh token by deleting it from Redis."""
        user_id = auth_info["id"]
        redis_key = self._redisKeyForRefreshToken(user_id, refresh_token)
        await redis_client.delete(redis_key)
