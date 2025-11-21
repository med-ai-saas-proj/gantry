from src.db_v2.initialize import session_manager
from src.shared.consts.common_const import TIME_FORMAT
from src.shared.custom_types.error_exception import RecoverableError

from ..models.users import User, UserRepo
from ..models.initialize import user_repo
from ..entities.auth_info import AuthInfo, TokenInfo, JwtPayload

from typing import Literal, TypedDict, NotRequired
from datetime import UTC, datetime, timezone, timedelta

from jose import JWTError, jwt
from fastapi import HTTPException
from sqlalchemy import select
from safe_result import Ok, Err, Result
from passlib.context import CryptContext


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
    status = 400


class InvalidTokenError(RecoverableError):
    code = "invalid_access_token"
    title = "Invalid access token"
    detail = "Access token is not set or is invalid (expired, corrupted, ...)"
    status = 400


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password) -> str:
    return pwd_context.hash(password)


class JWTEncodeError(RecoverableError):
    code = "jwt_encode"
    title = "JWT token encode error"


def generateAccessToken(
    data: JwtPayload,
    secret_key: str,
    algorithm: str,
    expires_delta: int | None = None,
) -> Result[str, JWTEncodeError]:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + timedelta(minutes=expires_delta)
        to_encode.update({"exp": expire.strftime(TIME_FORMAT)})
    try:
        return Ok(jwt.encode(to_encode, secret_key, algorithm=algorithm))
    except JWTError:
        return Err(JWTEncodeError())


def getCurrentUserFromToken(
    token: str, secret_key: str, algorithm: str
) -> Result[AuthInfo, InvalidTokenError]:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    except JWTError:
        return Err(InvalidTokenError())
    user_id = payload.get("sub")
    user_email = payload.get("email")
    if (
        user_email is None
        or user_id is None
        or not isinstance(user_email, str)
        or not isinstance(user_id, str)
    ):
        return Err(InvalidTokenError())
    return Ok[AuthInfo]({"id": user_id, "email": user_email})


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
    ):  # -> Result[TokenInfo, InvalidCredentialError | JWTEncodeError]:
        async with session_manager.get_session() as session:
            user = await user_repo.get_one(
                session,
                select(UserRepo.table)
                .where(UserRepo.c.email == email)
                .limit(1),
            )

            if not user or not verify_password(password, user.hashed_password):
                return Err(self.InvalidCredentialError())

            return generateAccessToken(
                data={
                    "sub": str(user.id),
                    "email": user.email,
                },
                secret_key=self.secret_key,
                algorithm=self.algorithm,
                expires_delta=self.access_token_expire_minutes,
            ).and_then(
                lambda token: Ok[TokenInfo](
                    {
                        "access_token": token,
                        "expires_in": self.access_token_expire_minutes * 60,
                    }
                )
            )

    def getUserInfoFromToken(self, token: str):
        return getCurrentUserFromToken(token, self.secret_key, self.algorithm)
