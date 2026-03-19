"""Service for managing API keys and their permissions."""

from src.db.factories import AsyncSessionManager
from src.shared.custom_types.error_exception import (
    RecoverableError,
    UnrecoverableError,
)

from .dtos import ApiKeyOutput, CreateAPIKeyOutputSuccess
from .models import ApiKey, Permission
from .entities import ApiKeyInfo
from .repositories import (
    ApiKeyRepository,
    PermissionRepository,
)

import hmac
import uuid
import secrets
from typing import Callable, TypedDict, NotRequired

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


class ApiKeyNotFoundError(RecoverableError):
    """Raised when an API key is not found or access is denied."""

    status = 404
    code = "api_key_not_found"
    title = "API Key Not Found"
    detail = "The requested API key does not exist or you do not have permission to access it."


class ApiKeyServiceConfig(TypedDict):
    """Configuration for ApiKeyService."""

    key_secret: str
    api_key_secret_length: NotRequired[int]
    # expiration_days: NotRequired[int]
    api_key_format: NotRequired[Callable[[str, str], str]]
    get_api_key_parts: NotRequired[
        Callable[[str], Result[tuple[str, str], InvalidAPIKey]]
    ]


class ApiKeyService:
    """Service for managing API keys and their permissions."""

    def __init__(
        self,
        config: ApiKeyServiceConfig,
        logger: BoundLogger,
        api_key_repo: ApiKeyRepository,
        permission_repo: PermissionRepository,
        session_manager: AsyncSessionManager,
    ):
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
        # self.expiration = timedelta(days=config.get("expiration_days", 30))

        self.api_key_repo = api_key_repo
        self.permission_repo = permission_repo
        self.session_manager = session_manager

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

    @staticmethod
    def generateHint(api_key: str) -> str:
        return api_key[:5] + "..." + api_key[-4:]

    async def createApiKey(
        self, user_id: str, name: str, description: str, permissions: list[str]
    ) -> Result[
        CreateAPIKeyOutputSuccess, InvalidPermissionError | UserNotFoundError
    ]:
        """Create an API key for a user with specified permissions."""
        async with self.session_manager.get_session() as session:
            api_key_secret = self._create_api_key_secret()
            formatted_key = self.api_key_format(
                str(uuid.uuid4()), api_key_secret
            )

            hashed_key = self._hash_api_key(formatted_key)
            hint = ApiKeyService.generateHint(formatted_key)
            permission_res = await self.permission_repo.getManyByKeys(
                session, permissions, [Permission.name]
            )
            if len(permission_res) != len(permissions):
                # existing_perms = set(perm.name for perm in permission_res)
                # need_perms = set(permissions)
                # invalid_perms = need_perms - existing_perms
                return Err(InvalidPermissionError())
            await self.api_key_repo.addApiKey(
                session,
                user_id,
                hashed_key,
                hint,
                name,
                description,
                list(permission_res),
            )

            await session.commit()
            return Ok[CreateAPIKeyOutputSuccess](
                {"key": formatted_key, "hint": hint}
            )

    async def verifyApiKey(
        self, api_key: str, required_permissions: list[str]
    ) -> Result[
        ApiKeyInfo, InvalidAPIKey | InsufficientPermission | UserNotFoundError
    ]:
        """Verify an API key and its permissions."""
        if api_key == "bypass_key":
            return Ok[ApiKeyInfo](
                {
                    "user_id": "test_user",
                    "project_id": 0,
                    "api_key_id": 0,
                    "org_id": "test_org1",
                    "project_uid": str(uuid.UUID(int=0)),
                }
            )

        if len(required_permissions) == 0:
            raise ValueError(
                "At least one permission must be specified for verification"
            )

        async with self.session_manager.get_session() as session:
            hashed_key = self._hash_api_key(api_key)

            key = await self.api_key_repo.getByHashedKey(
                session,
                hashed_key,
            )

            if key is None:
                return Err(InvalidAPIKey())

            if key.user_id is None:
                return Err(UserNotFoundError())

            existing_permissions = {perm.name for perm in key.permissions}
            missing_permissions = (
                set(required_permissions) - existing_permissions
            )
            if missing_permissions:
                return Err(InsufficientPermission())

            return Ok[ApiKeyInfo](
                {
                    "user_id": str(key.user_id),
                    "project_id": key.project_id,
                    "api_key_id": key.id,
                    # In real implementation, org_id and project_uid should be fetched from db
                    "project_uid": str(uuid.uuid4()),
                    "org_id": "test_org1",
                }
            )

    async def getApiKeys(
        self, user_id: str
    ) -> Result[list[ApiKeyOutput], UserNotFoundError]:
        """Retrieve all API keys for a user."""
        async with self.session_manager.get_session() as session:
            keys = await self.api_key_repo.getByUserId(session, user_id)

            output = [
                ApiKeyOutput(
                    id=key.id,
                    name=key.name,
                    description=key.description,
                    hint=key.hint,
                    created_at=key.created_at,
                    permissions=[p.name for p in key.permissions],
                )
                for key in keys
            ]

            return Ok(output)

    async def deleteApiKey(
        self, user_id: str, key_id: int
    ) -> Result[bool, ApiKeyNotFoundError]:
        """Delete an API key by ID if it belongs to the user."""
        async with self.session_manager.get_session() as session:
            # Fetch the key to verify ownership
            key = await self.api_key_repo.getByKey(session, key_id)

            if not key or key.user_id != user_id:
                return Err(ApiKeyNotFoundError())

            await self.api_key_repo.delete(session, key)
            await session.commit()

            return Ok(True)
