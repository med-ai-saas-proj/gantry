"""Service for managing API keys and their permissions."""

from src.db_v2.initialize import session_manager
from src.auth.entities.auth_info import APIKeyInfo
from src.auth.repositories.initialize import (
    user_repo,
    api_key_repo,
    permission_repo,
)
from src.shared.custom_types.error_exception import (
    RecoverableError,
    UnrecoverableError,
)

from ..models.api_keys import ApiKey

import hmac
import uuid
import secrets
from typing import Callable, TypedDict, NotRequired
from datetime import datetime, timedelta

from safe_result import Ok, Err, Result
from structlog.stdlib import BoundLogger


class InvalidPermissionError(RecoverableError):
    """Raised when an invalid permission is encountered."""

    status = 400
    code = "invalid_permission"
    title = "Invalid permission"
    detail = "Permission requested does not exists"


class InvalidAPIKey(RecoverableError):
    """Raised when an invalid API key is encountered."""

    status = 401
    code = "invalid_api_key"
    title = "Invalid API key"
    detail = "API key is invalid or not exists"


class InsufficientPermission(RecoverableError):
    """Raised when an insufficient permission is encountered."""

    status = 401
    code = "insufficient_permission"
    title = "Insufficient permission"
    detail = "API key's permission is not sufficient for this resource"


class UserNotFoundError(UnrecoverableError):
    """Raised when an error occurs."""

    detail = "Check the user table, there is null in there"


class ApiKeyServiceConfig(TypedDict):
    """Configuration for ApiKeyService."""

    key_secret: str
    api_key_secret_length: NotRequired[int]
    expiration_days: NotRequired[int]
    api_key_format: NotRequired[Callable[[str, str], str]]
    get_api_key_parts: NotRequired[
        Callable[[str], Result[tuple[str, str], InvalidAPIKey]]
    ]


class ApiKeyService:
    """Service for managing API keys and their permissions."""

    def __init__(self, config: ApiKeyServiceConfig, logger: BoundLogger):
        """Initialize the ApiKeyService with configuration and logger."""
        self.logger = logger
        self.key_secret = config["key_secret"]

        self.api_key_format = config.get(
            "api_key_format", ApiKeyService._internal_format_api_key
        )
        self.get_api_key_parts = config.get(
            "get_api_key_parts", ApiKeyService._internal_get_api_key_parts
        )

        self.api_key_secret_length = config.get("api_key_secret_length", 32)
        self.expiration = timedelta(days=config.get("expiration_days", 30))

    def _create_api_key_secret(self) -> str:
        return secrets.token_urlsafe(self.api_key_secret_length)

    @staticmethod
    def _internal_format_api_key(api_key: str, secret: str) -> str:
        return f"sk_{api_key}.{secret}"

    @staticmethod
    def _internal_get_api_key_parts(
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

    def _hash_api_key(self, api_key: str) -> str:
        return hmac.new(
            self.key_secret.encode(), api_key.encode(), "sha256"
        ).hexdigest()

    async def createApiKey(
        self, user_id: str, permissions: list[str]
    ) -> Result[str, InvalidPermissionError | UserNotFoundError]:
        """Create an API key for a user with specified permissions."""
        async with session_manager.get_session() as session:
            user = await user_repo.getByKey(session, uuid.UUID(user_id))
            if user is None:
                return Err(UserNotFoundError())

            permission_res = await permission_repo.getManyByKeys(
                session, permissions
            )

            existing_permissions: set[str] = {
                perm.name for perm in permission_res
            }
            # self.logger.debug(
            #     "Got perms", existing_permissions=existing_permissions
            # )
            not_existing_permissions = set(permissions) - existing_permissions
            if not_existing_permissions:
                return Err(InvalidPermissionError())
            api_key_id = uuid.uuid4()
            api_key_secret = self._create_api_key_secret()
            formatted_key = self.api_key_format(str(api_key_id), api_key_secret)

            hashed_key = self._hash_api_key(formatted_key)

            new_api_key = ApiKey(
                id=api_key_id,
                owner_id=uuid.UUID(user_id),
                hashed_key=hashed_key,
                expiration_date=datetime.now() + self.expiration,
            )
            await api_key_repo.add(session, new_api_key)
            await api_key_repo.addPermissionsToApiKey(
                session, api_key_id, permissions
            )
            await session.commit()
            return Ok(formatted_key)

    async def verifyApiKey(
        self, api_key: str, required_permissions: list[str]
    ) -> Result[
        APIKeyInfo, InvalidAPIKey | InsufficientPermission | UserNotFoundError
    ]:
        """Verify an API key and its permissions."""
        if len(required_permissions) == 0:
            raise ValueError(
                "At least one permission must be specified for verification"
            )

        async with session_manager.get_session() as session:
            key_parts_ = self.get_api_key_parts(api_key)
            if key_parts_.is_err():
                return Err(InvalidAPIKey())

            key_id, _ = key_parts_.unwrap()

            key = await api_key_repo.getByKey(session, uuid.UUID(key_id))
            if key is None:
                return Err(InvalidAPIKey())

            if key.expiration_date is None or key.owner_id is None:
                return Err(UserNotFoundError())

            if key.expiration_date < datetime.now():
                return Err(InvalidAPIKey())

            hashed_key = self._hash_api_key(api_key)
            if not hmac.compare_digest(hashed_key, key.hashed_key):
                return Err(InvalidAPIKey())

            existing_permissions = {perm.name for perm in key.permissions}
            missing_permissions = (
                set(required_permissions) - existing_permissions
            )
            if missing_permissions:
                return Err(InsufficientPermission())

            return Ok[APIKeyInfo]({"user_id": str(key.owner_id)})
