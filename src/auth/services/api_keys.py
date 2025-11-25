from src.db_v2.initialize import session_manager
from src.db_v2.repository import Repository
from src.shared.custom_types.error_exception import (
    RecoverableError,
    UnrecoverableError,
)

from ..models.api_keys import ApiKey, PermissionRepo, ApiKeyPermissionRepo
from ..models.initialize import user_repo, api_key_repo, permission_repo

import hmac
import uuid
import secrets
from typing import Callable, TypedDict, NotRequired
from datetime import datetime, timedelta

from sqlalchemy import delete, insert, select
from safe_result import Ok, Err, Result
from structlog.stdlib import BoundLogger


class InvalidPermissionError(RecoverableError):
    status = 400
    code = "invalid_permission"
    title = "Invalid permission"
    detail = "Permission requested does not exists"


class InvalidAPIKey(RecoverableError):
    status = 401
    code = "invalid_api_key"
    title = "Invalid API key"
    detail = "API key is not set or invalid (does not exists)"


class InsufficientPermission(RecoverableError):
    status = 401
    code = "insufficient_permission"
    title = "Insufficient permission"
    detail = "API key's permission is not sufficient for this resource"


class UserTableError(UnrecoverableError):
    detail = "Check the user table, there is null in there"


class ApiKeyServiceConfig(TypedDict):
    key_secret: str
    api_key_secret_length: NotRequired[int]
    expiration_days: NotRequired[int]
    api_key_format: NotRequired[Callable[[str, str], str]]
    get_api_key_parts: NotRequired[
        Callable[[str], Result[tuple[str, str], InvalidAPIKey]]
    ]


class ApiKeyService:
    def __init__(self, config: ApiKeyServiceConfig, logger: BoundLogger):
        self.logger = logger
        self.key_secret = config["key_secret"]

        self.api_key_format = config.get(
            "api_key_format", ApiKeyService.internal_format_api_key
        )
        self.get_api_key_parts = config.get(
            "get_api_key_parts", ApiKeyService.internal_get_api_key_parts
        )

        self.api_key_secret_length = config.get("api_key_secret_length", 32)
        self.expiration = timedelta(days=config.get("expiration_days", 30))

    def create_api_key_secret(self) -> str:
        return secrets.token_urlsafe(self.api_key_secret_length)

    @staticmethod
    def internal_format_api_key(api_key: str, secret: str) -> str:
        return f"sk_{api_key}.{secret}"

    @staticmethod
    def internal_get_api_key_parts(
        formatted_key: str,
    ) -> Result[tuple[str, str], InvalidAPIKey]:
        prefix = "sk_"
        try:
            if not formatted_key.startswith(prefix):
                return Err(InvalidAPIKey())

            rest = formatted_key.removeprefix(prefix)
            key_id, secret = rest.split(".", 1)
            return Ok((key_id, secret))
        except Exception as e:
            return Err(InvalidAPIKey(e))

    def hash_api_key(self, api_key: str) -> str:
        return hmac.new(
            self.key_secret.encode(), api_key.encode(), "sha256"
        ).hexdigest()

    async def create_api_key(
        self, user_id: str, permissions: list[str], name: str | None = None
    ) -> Result[str, InvalidPermissionError | UserTableError]:
        async with session_manager.get_session() as session:
            user = await user_repo.get_by_id(session, user_id)
            if user is None:
                return Err(UserTableError())

            permission_rep = await permission_repo.get_many(
                session,
                select(PermissionRepo.table).where(
                    PermissionRepo.c.name.in_(permissions)
                ),
            )

            existing_permissions = {perm.name for perm in permission_rep}
            self.logger.debug(
                "Got perms", existing_permissions=existing_permissions
            )
            not_existing_permissions = set(permissions) - existing_permissions
            if not_existing_permissions:
                return Err(InvalidPermissionError())
            api_key_id = uuid.uuid4()
            api_key_secret = self.create_api_key_secret()
            formatted_key = self.api_key_format(str(api_key_id), api_key_secret)

            hashed_key = self.hash_api_key(formatted_key)

            # Assuming ApiKey is a SQLAlchemy model for storing API keys
            new_api_key = ApiKey(
                id=str(api_key_id),
                owner_id=user_id,
                name=name,
                hashed_key=hashed_key,
                is_active=True,
                expiration_date=datetime.now() + self.expiration,
            )
            await api_key_repo.insert(session, new_api_key)
            await session.execute(
                insert(ApiKeyPermissionRepo.table).values(
                    [
                        {"api_key_id": api_key_id, "permission_name": perm_name}
                        for perm_name in permissions
                    ]
                )
            )
            await session.commit()

        return Ok(formatted_key)

    async def get_user_api_keys(self, user_id: str) -> list[ApiKey]:
        async with session_manager.get_session() as session:
            stmt = select(api_key_repo.table).where(
                api_key_repo.c.owner_id == user_id
            )
            return await api_key_repo.get_many(session, stmt)

    async def update_api_key(
        self,
        user_id: str,
        key_id: str,
        name: str | None,
        is_active: bool | None,
    ) -> Result[ApiKey, InvalidAPIKey]:
        async with session_manager.get_session() as session:
            key = await api_key_repo.get_by_id(session, key_id)

            # Verify existence and ownership
            if key is None or str(key.owner_id) != user_id:
                return Err(InvalidAPIKey())

            if name is not None:
                key.name = name
            if is_active is not None:
                key.is_active = is_active

            await api_key_repo.update(session, key)
            await session.commit()
            return Ok(key)

    async def revoke_api_key(
        self, user_id: str, key_id: str
    ) -> Result[bool, InvalidAPIKey]:
        async with session_manager.get_session() as session:
            key = await api_key_repo.get_by_id(session, key_id)

            # Verify existence and ownership
            if key is None or str(key.owner_id) != user_id:
                return Err(InvalidAPIKey())

            await session.execute(
                delete(ApiKeyPermissionRepo.table).where(
                    ApiKeyPermissionRepo.c.api_key_id == key.id
                )
            )

            await api_key_repo.delete(session, key_id)
            await session.commit()
            return Ok(True)

    async def verify_api_key(
        self, api_key: str, required_permissions: list[str]
    ) -> Result[str, InvalidAPIKey | InsufficientPermission | UserTableError]:
        if len(required_permissions) == 0:
            raise ValueError(
                "At least one permission must be specified for verification"
            )

        async with session_manager.get_session() as session:
            key_parts_ = self.get_api_key_parts(api_key)
            if key_parts_.is_err():
                return Err(InvalidAPIKey())

            key_id, _ = key_parts_.unwrap()

            key = await api_key_repo.get_by_id(session, key_id)
            if key is None:
                return Err(InvalidAPIKey())

            # Check active status
            if not key.is_active:
                return Err(InvalidAPIKey())

            if key.expiration_date is None or key.owner_id is None:
                return Err(UserTableError())

            if key.expiration_date < datetime.now():
                return Err(InvalidAPIKey())

            hashed_key = self.hash_api_key(api_key)
            if not hmac.compare_digest(hashed_key, key.hashed_key):
                return Err(InvalidAPIKey())

            existing_permissions: list[str] = await Repository.select_many(
                session,
                select(ApiKeyPermissionRepo.c.permission_name).where(
                    (ApiKeyPermissionRepo.c.api_key_id == key.id)
                    & (
                        ApiKeyPermissionRepo.c.permission_name.in_(
                            required_permissions
                        )
                    )
                ),
                lambda x: x["permission_name"],
            )

            missing_permissions = set(required_permissions) - set(
                existing_permissions
            )
            if missing_permissions:
                return Err(InsufficientPermission())

        return Ok(key.owner_id)
