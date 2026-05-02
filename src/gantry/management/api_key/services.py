"""Service for managing project-scoped API keys."""

from gantry.db import AsyncSessionManager
from gantry.management.project import ProjectRepository, ProjectNotFoundError
from gantry.management.organization import getOrgSettings
from gantry.management.organization.cache_keys import (
    ORG_RPM_LIMIT_CACHE_TTL_SECONDS,
    project_rpm_limit_key,
    organization_rpm_limit_key,
)
from gantry.shared.custom_types.error_exception import (
    RecoverableError,
    UnrecoverableError,
)
from gantry.management.billing.services.transaction_services import (
    TransactionService,
)

# from gantry.management.billing.services.transaction_services import (
#     TransactionService,
# )
from .dtos import (
    ApiKeyResponse,
    ApiKeyListResponse,
    ApiKeyCreateResponse,
    ApiKeyPermissionAuditResponse,
    ApiKeyPermissionCatalogResponse,
)
from .models import ApiKey
from .entities import ApiKeyInfo, ApiKeyContextRecord
from .permissions import (
    listPermissions,
    hasOnlyRegisteredPermissions,
)
from .repositories import ApiKeyRepository

import hmac
import json
import uuid
import secrets
from typing import Callable, Sequence, TypedDict, NotRequired

from pyrusult import Ok, Err, Result, ResultStatus
from redis.asyncio import Redis
from structlog.stdlib import BoundLogger


class InvalidPermissionError(RecoverableError):
    """Raised when an invalid permission is encountered."""

    status = 400
    code = "invalid_permission"
    title = "Invalid Permission"
    detail = "One or more API key permissions are invalid."


class InvalidAPIKey(RecoverableError):
    """Raised when an invalid API key is encountered."""

    status = 401
    code = "invalid_api_key"
    title = "Invalid API Key"
    detail = "API key is invalid or does not exist."

    def __init__(
        self,
        from_exception: Exception | None = None,
        message: str | None = None,
    ):
        super().__init__(from_exception)
        self.message = message


class InsufficientPermission(RecoverableError):
    """Raised when an API key lacks required permissions."""

    status = 401
    code = "insufficient_permission"
    title = "Insufficient Permission"
    detail = "API key permissions are not sufficient for this resource."


class UserNotFoundError(UnrecoverableError):
    """Raised when API key ownership data is unexpectedly missing."""

    detail = "Check the user table, there is null in there"


class ApiKeyNotFoundError(RecoverableError):
    """Raised when an API key cannot be found."""

    status = 404
    code = "api_key_not_found"
    title = "API Key Not Found"
    detail = "The requested API key does not exist."


class ApiKeyDisabledError(RecoverableError):
    """Raised when a disabled API key is used."""

    status = 401
    code = "api_key_disabled"
    title = "API Key Disabled"
    detail = "This API key is disabled."


class ApiKeyServiceConfig(TypedDict):
    """Configuration for ApiKeyService."""

    key_secret: str
    api_key_secret_length: NotRequired[int]
    api_key_format: NotRequired[Callable[[str, str], str]]
    get_api_key_parts: NotRequired[
        Callable[[str], Result[tuple[str, str], InvalidAPIKey]]
    ]
    api_key_info_cache_ttl_seconds: NotRequired[int]


class ApiKeyService:
    """Coordinate project-scoped API key CRUD and verification."""

    def __init__(
        self,
        config: ApiKeyServiceConfig,
        logger: BoundLogger,
        api_key_repo: ApiKeyRepository,
        project_repo: ProjectRepository,
        session_manager: AsyncSessionManager,
        billing_transaction_service: TransactionService,
        redis: Redis | None = None,
    ):
        self.logger = logger
        self.key_secret = config["key_secret"]
        self.api_key_format = config.get(
            "api_key_format", ApiKeyService._internalFormatApiKey
        )
        self.get_api_key_parts = config.get(
            "get_api_key_parts", ApiKeyService._internalGetApiKeyParts
        )
        self.api_key_secret_length = config.get("api_key_secret_length", 32)
        self.api_key_info_cache_ttl_seconds = config.get(
            "api_key_info_cache_ttl_seconds", 300
        )
        self.api_key_repo = api_key_repo
        self.project_repo = project_repo
        self.session_manager = session_manager
        self.redis = redis
        self.default_org_rate_limit = getOrgSettings().default_rate_limit
        # self.billing_transaction_service = billing_transaction_service

    def _createApiKeySecret(self) -> str:
        return secrets.token_urlsafe(self.api_key_secret_length)

    @staticmethod
    def _internalFormatApiKey(api_key: str, secret: str) -> str:
        return f"sk_{api_key}.{secret}"

    @staticmethod
    def _internalGetApiKeyParts(
        formatted_key: str,
    ) -> Result[tuple[str, str], InvalidAPIKey]:
        prefix = "sk_"
        try:
            if not formatted_key.startswith(prefix):
                return Err(InvalidAPIKey())

            rest = formatted_key.removeprefix(prefix)
            key_id, secret = rest.split(".", 1)
            return Ok((key_id, secret))
        except Exception as exc:
            return Err(InvalidAPIKey(from_exception=exc))

    def _hashApiKey(self, api_key: str) -> str:
        return hmac.new(
            self.key_secret.encode(),
            api_key.encode(),
            "sha256",
        ).hexdigest()

    @staticmethod
    def _normalizeRateLimit(limit: int | None) -> int:
        return limit if limit is not None else -1

    @staticmethod
    def _normalizeScaledSpendingLimit(limit: str | int | None) -> int:
        if limit is None:
            return -1
        return int(limit)

    @staticmethod
    def _cacheKey(hashed_key: str) -> str:
        return f"apikey:context:{hashed_key}"

    async def _getCachedContext(
        self, hashed_key: str
    ) -> ApiKeyContextRecord | None:
        if self.redis is None:
            return None
        try:
            cached = await self.redis.get(self._cacheKey(hashed_key))
            if not cached:
                return None
            payload = json.loads(cached)
            return ApiKeyContextRecord(
                api_key_id=int(payload["api_key_id"]),
                user_id=str(payload["user_id"]),
                project_id=int(payload["project_id"]),
                organization_uuid=str(payload["organization_uuid"]),
                project_uuid=str(payload["project_uuid"]),
                hashed_key=str(payload["hashed_key"]),
                permissions=list(payload["permissions"]),
                disabled=bool(payload["disabled"]),
                rpm_limit_organization=int(
                    payload.get("rpm_limit_organization", -1)
                ),
                rpm_limit_project=int(payload.get("rpm_limit_project", -1)),
                spending_limit_organization=int(
                    payload.get("spending_limit_organization", -1)
                ),
                spending_limit_project=int(
                    payload.get("spending_limit_project", -1)
                ),
            )
        except Exception as exc:
            self.logger.warning(
                "api_key_context_cache_read_failed",
                hashed_key=hashed_key,
                error=str(exc),
            )
            return None

    async def _setCachedContext(self, context: ApiKeyContextRecord) -> None:
        if self.redis is None:
            return
        try:
            payload = {
                "api_key_id": context["api_key_id"],
                "user_id": context["user_id"],
                "project_id": context["project_id"],
                "organization_uuid": context["organization_uuid"],
                "project_uuid": context["project_uuid"],
                "hashed_key": context["hashed_key"],
                "permissions": list(context["permissions"]),
                "disabled": bool(context["disabled"]),
            }
            await self.redis.set(
                self._cacheKey(context["hashed_key"]),
                json.dumps(payload),
                ex=self.api_key_info_cache_ttl_seconds,
            )
        except Exception as exc:
            self.logger.warning(
                "api_key_context_cache_write_failed",
                hashed_key=context["hashed_key"],
                error=str(exc),
            )

    async def _clearCachedContext(self, hashed_key: str) -> None:
        if self.redis is None:
            return
        try:
            await self.redis.delete(self._cacheKey(hashed_key))
        except Exception as exc:
            self.logger.warning(
                "api_key_context_cache_delete_failed",
                hashed_key=hashed_key,
                error=str(exc),
            )

    async def _readCachedRpmLimit(self, key: str) -> int | None:
        if self.redis is None:
            return None
        try:
            raw = await self.redis.get(key)
        except Exception as exc:
            self.logger.warning(
                "rpm_limit_cache_read_failed",
                key=key,
                error=str(exc),
            )
            return None
        if raw is None:
            return None
        return int(raw)

    async def _writeCachedRpmLimit(self, key: str, limit: int) -> None:
        if self.redis is None:
            return
        try:
            await self.redis.set(
                key,
                limit,
                ex=ORG_RPM_LIMIT_CACHE_TTL_SECONDS,
            )
        except Exception as exc:
            self.logger.warning(
                "rpm_limit_cache_write_failed",
                key=key,
                error=str(exc),
            )

    @staticmethod
    def generateHint(api_key: str) -> str:
        return api_key[:5] + "..." + api_key[-4:]

    def _validatePermissions(
        self, permissions: list[str]
    ) -> Result[None, InvalidPermissionError]:
        if not hasOnlyRegisteredPermissions(permissions):
            return Err(InvalidPermissionError())
        return Ok(None)

    async def _getProjectByUuid(
        self, project_uuid: str
    ) -> Result[tuple[int, str, str], ProjectNotFoundError]:
        async with self.session_manager.get_session() as session:
            project = await self.project_repo.getByUuid(session, project_uuid)
            if project is None:
                return Err(ProjectNotFoundError())
            return Ok((project.id, project.organization_id, str(project.uuid)))

    async def _readCachedSpendingLimit(self, key: str) -> int:
        if self.redis is None:
            return -1
        try:
            raw = await self.redis.get(key)
        except Exception as exc:
            self.logger.warning(
                "billing_spending_limit_cache_read_failed",
                key=key,
                error=str(exc),
            )
            return -1
        return self._normalizeScaledSpendingLimit(raw)

    async def _enrichContextLimits(
        self,
        context: ApiKeyContextRecord,
    ) -> ApiKeyContextRecord:
        org_rpm_key = organization_rpm_limit_key(context["organization_uuid"])
        org_rpm_limit = await self._readCachedRpmLimit(org_rpm_key)
        if org_rpm_limit is None:
            org_rpm_limit = context["rpm_limit_organization"]
            if org_rpm_limit < 0:
                org_rpm_limit = self._normalizeRateLimit(
                    self.default_org_rate_limit
                )
            await self._writeCachedRpmLimit(org_rpm_key, org_rpm_limit)
        context["rpm_limit_organization"] = org_rpm_limit

        project_rpm_key = project_rpm_limit_key(
            context["organization_uuid"], context["project_id"]
        )
        project_rpm_limit = await self._readCachedRpmLimit(project_rpm_key)
        if project_rpm_limit is None:
            project_rpm_limit = self._normalizeRateLimit(
                context["rpm_limit_project"]
            )
            await self._writeCachedRpmLimit(project_rpm_key, project_rpm_limit)
        context["rpm_limit_project"] = project_rpm_limit

        # spending_limit = (
        #     await self.billing_transaction_service.getSpendingLimits(
        #         context["organization_uuid"], context["project_id"]
        #     )
        # ).unwrap()
        context["spending_limit_project"] = int(
            spending_limit[0] if spending_limit[0] is not None else -1
        )
        context["spending_limit_organization"] = int(
            spending_limit[1] if spending_limit[1] is not None else -1
        )
        return context

    async def _loadContextFromStorage(
        self, hashed_key: str
    ) -> ApiKeyContextRecord | None:
        async with self.session_manager.get_session() as session:
            context = await self.api_key_repo.getContextByHashedKey(
                session, hashed_key
            )

        if context is None:
            return None

        return await self._enrichContextLimits(context)

    async def _resolveApiKeyContext(
        self, api_key: str
    ) -> Result[tuple[str, ApiKeyContextRecord], InvalidAPIKey]:
        parts_res = self.get_api_key_parts(api_key)
        if parts_res.status == ResultStatus.Err:
            return parts_res.into()

        api_key_uuid, _ = parts_res.unwrap()
        hashed_key = self._hashApiKey(api_key)

        cached = await self._getCachedContext(hashed_key)
        if cached is not None:
            return Ok((api_key_uuid, await self._enrichContextLimits(cached)))

        context = await self._loadContextFromStorage(hashed_key)
        if context is None:
            return Err(InvalidAPIKey())

        await self._setCachedContext(context)
        return Ok((api_key_uuid, context))

    @staticmethod
    def _toApiKeyInfo(
        api_key_uuid: str,
        context: ApiKeyContextRecord,
    ) -> ApiKeyInfo:
        return ApiKeyInfo(
            {
                "api_key_id": context["api_key_id"],
                "api_key_uuid": api_key_uuid,
                "user_id": context["user_id"],
                "project_id": context["project_id"],
                "project_uuid": context["project_uuid"],
                "org_id": context["organization_uuid"],
                "organization_uuid": context["organization_uuid"],
                "project_uid": context["project_uuid"],
                "hashed_key": context["hashed_key"],
                "permissions": list(context["permissions"]),
                "rpm_limit_organization": context["rpm_limit_organization"],
                "rpm_limit_project": context["rpm_limit_project"],
                "spending_limit_organization": context[
                    "spending_limit_organization"
                ],
                "spending_limit_project": context["spending_limit_project"],
            }
        )

    def _snapshotApiKey(self, api_key: ApiKey) -> dict[str, object]:
        """Detach the fields needed outside the ORM session boundary."""
        return {
            "id": api_key.id,
            "project_id": api_key.project_id,
            "name": api_key.name,
            "description": api_key.description,
            "hint": api_key.hint,
            "created_at": api_key.created_at,
            "permissions": list(api_key.permissions),
            "disabled": bool(api_key.disabled),
            "hashed_key": getattr(api_key, "hashed_key", ""),
        }

    async def _getApiKeyById(
        self, api_key_id: int
    ) -> Result[dict[str, object], ApiKeyNotFoundError]:
        async with self.session_manager.get_session() as session:
            api_key = await self.api_key_repo.getByKey(session, api_key_id)
            if api_key is None:
                return Err(ApiKeyNotFoundError())
            return Ok(self._snapshotApiKey(api_key))

    async def getApiKeyProjectId(
        self, api_key_id: int
    ) -> Result[str, ApiKeyNotFoundError | ProjectNotFoundError]:
        """Resolve the project uuid that owns one API key."""
        api_key_res = await self._getApiKeyById(api_key_id)
        if api_key_res.status == ResultStatus.Err:
            return api_key_res.into()

        async with self.session_manager.get_session() as session:
            project = await self.project_repo.getByKey(
                session, int(api_key_res.unwrap()["project_id"])
            )
            if project is None:
                return Err(ProjectNotFoundError())
            return Ok(str(project.uuid))

    def _toResponse(
        self, api_key: dict[str, object], project_uuid: str
    ) -> ApiKeyResponse:
        return ApiKeyResponse(
            id=int(api_key["id"]),
            project_id=project_uuid,
            name=str(api_key["name"]),
            description=str(api_key["description"]),
            hint=str(api_key["hint"]),
            created_at=api_key["created_at"],
            permissions=list(api_key["permissions"]),
            disabled=bool(api_key["disabled"]),
        )

    def getPermissionCatalog(self) -> ApiKeyPermissionCatalogResponse:
        """Return the runtime catalog of API key permissions."""
        permissions = listPermissions()
        return ApiKeyPermissionCatalogResponse(
            total=len(permissions),
            results=permissions,
        )

    async def auditPermissions(self) -> ApiKeyPermissionAuditResponse:
        """Compare stored API key permissions with the runtime permission catalog."""
        registered_permissions = listPermissions()
        async with self.session_manager.get_session() as session:
            stored_permissions = (
                await self.api_key_repo.listDistinctPermissions(session)
            )

        registered_set = set(registered_permissions)
        stored_set = set(stored_permissions)
        return ApiKeyPermissionAuditResponse(
            registered_permissions=registered_permissions,
            stored_permissions=stored_permissions,
            stale_permissions=sorted(stored_set - registered_set),
            unused_permissions=sorted(registered_set - stored_set),
        )

    async def createApiKey(
        self,
        *,
        actor_user_id: str,
        project_uuid: str,
        name: str,
        description: str,
        permissions: list[str],
    ) -> Result[
        ApiKeyCreateResponse,
        InvalidPermissionError | ProjectNotFoundError | UserNotFoundError,
    ]:
        """Create a new API key inside one project."""
        valid_res = self._validatePermissions(permissions)
        if valid_res.status == ResultStatus.Err:
            return valid_res.into()

        project_res = await self._getProjectByUuid(project_uuid)
        if project_res.status == ResultStatus.Err:
            return project_res.into()
        project_id, _, normalized_project_uuid = project_res.unwrap()

        api_key_secret = self._createApiKeySecret()
        formatted_key = self.api_key_format(str(uuid.uuid4()), api_key_secret)
        hashed_key = self._hashApiKey(formatted_key)
        hint = self.generateHint(formatted_key)

        async with self.session_manager.get_session() as session:
            created = await self.api_key_repo.create(
                session,
                user_id=actor_user_id,
                project_id=project_id,
                hashed_key=hashed_key,
                hint=hint,
                name=name,
                description=description,
                permissions=permissions,
            )
            await session.commit()

        return Ok(
            ApiKeyCreateResponse(
                id=created.id,
                project_id=normalized_project_uuid,
                name=created.name,
                description=created.description,
                hint=created.hint,
                created_at=created.created_at,
                permissions=list(created.permissions),
                disabled=bool(created.disabled),
                key=formatted_key,
            )
        )

    async def getApiKeys(
        self,
        *,
        project_uuid: str,
    ) -> Result[ApiKeyListResponse, ProjectNotFoundError]:
        """List all API keys belonging to one project."""
        project_res = await self._getProjectByUuid(project_uuid)
        if project_res.status == ResultStatus.Err:
            return project_res.into()
        project_id, _, normalized_project_uuid = project_res.unwrap()

        async with self.session_manager.get_session() as session:
            keys = await self.api_key_repo.getByProjectId(session, project_id)
            total = await self.api_key_repo.countByProjectId(
                session, project_id
            )
            snapshots = [self._snapshotApiKey(api_key) for api_key in keys]

        return Ok(
            ApiKeyListResponse(
                total=total,
                results=[
                    self._toResponse(api_key, normalized_project_uuid)
                    for api_key in snapshots
                ],
            )
        )

    async def getApiKey(
        self, api_key_id: int
    ) -> Result[ApiKeyResponse, ApiKeyNotFoundError | ProjectNotFoundError]:
        """Get one API key by id."""
        api_key_res = await self._getApiKeyById(api_key_id)
        if api_key_res.status == ResultStatus.Err:
            return api_key_res.into()
        api_key = api_key_res.unwrap()

        async with self.session_manager.get_session() as session:
            project = await self.project_repo.getByKey(
                session, int(api_key["project_id"])
            )
            if project is None:
                return Err(ProjectNotFoundError())
            return Ok(self._toResponse(api_key, str(project.uuid)))

    async def updateApiKey(
        self,
        *,
        api_key_id: int,
        name: str,
        description: str,
        permissions: list[str],
    ) -> Result[
        ApiKeyResponse,
        InvalidPermissionError | ApiKeyNotFoundError | ProjectNotFoundError,
    ]:
        """Update mutable metadata for one API key."""
        valid_res = self._validatePermissions(permissions)
        if valid_res.status == ResultStatus.Err:
            return valid_res.into()

        api_key_res = await self._getApiKeyById(api_key_id)
        if api_key_res.status == ResultStatus.Err:
            return api_key_res.into()
        api_key = api_key_res.unwrap()

        async with self.session_manager.get_session() as session:
            updated = await self.api_key_repo.updateById(
                session,
                api_key_id,
                name=name,
                description=description,
                permissions=permissions,
            )
            if updated is None:
                return Err(ApiKeyNotFoundError())

            project = await self.project_repo.getByKey(
                session, int(api_key["project_id"])
            )
            if project is None:
                return Err(ProjectNotFoundError())

            await session.commit()
            await self._clearCachedContext(str(api_key["hashed_key"]))
            return Ok(
                self._toResponse(
                    self._snapshotApiKey(updated),
                    str(project.uuid),
                )
            )

    async def getApiKeysInfo(
        self, api_key: list[str]
    ) -> Result[Sequence[ApiKeyInfo], InvalidAPIKey]:
        async with self.session_manager.get_session() as session:
            hashed_keys_map = {self._hashApiKey(key): key for key in api_key}
            keys = await self.api_key_repo.getByHashedKeys(
                session,
                list(hashed_keys_map.keys()),
            )
            existed_hashed_keys = {key["hashed_key"] for key in keys}
            missing_hashed_keys = (
                set(hashed_keys_map.keys()) - existed_hashed_keys
            )
            if missing_hashed_keys:
                missing_keys_str = ", ".join(
                    hashed_keys_map[hk] for hk in missing_hashed_keys
                )
                return Err(
                    InvalidAPIKey(
                        message=f"API keys not found: {missing_keys_str}"
                    )
                )

            enriched_keys: list[ApiKeyInfo] = []
            for key in keys:
                raw_key = hashed_keys_map[key["hashed_key"]]
                key_parts_res = self.get_api_key_parts(raw_key)
                if key_parts_res.status == ResultStatus.Err:
                    return key_parts_res.into()
                api_key_uuid, _ = key_parts_res.unwrap()
                enriched = dict(key)
                enriched["api_key_uuid"] = api_key_uuid
                enriched_keys.append(ApiKeyInfo(enriched))

            return Ok(enriched_keys)

    async def setApiKeyDisabled(
        self,
        *,
        api_key_id: int,
        disabled: bool,
    ) -> Result[
        ApiKeyResponse,
        ApiKeyNotFoundError | ProjectNotFoundError,
    ]:
        """Enable or disable one API key."""
        api_key_res = await self._getApiKeyById(api_key_id)
        if api_key_res.status == ResultStatus.Err:
            return api_key_res.into()
        api_key = api_key_res.unwrap()

        async with self.session_manager.get_session() as session:
            updated = await self.api_key_repo.updateDisabledById(
                session,
                api_key_id,
                disabled=disabled,
            )
            if updated is None:
                return Err(ApiKeyNotFoundError())

            project = await self.project_repo.getByKey(
                session, int(api_key["project_id"])
            )
            if project is None:
                return Err(ProjectNotFoundError())

            await session.commit()
            await self._clearCachedContext(str(api_key["hashed_key"]))
            return Ok(
                self._toResponse(
                    self._snapshotApiKey(updated),
                    str(project.uuid),
                )
            )

    async def deleteApiKey(
        self, api_key_id: int
    ) -> Result[bool, ApiKeyNotFoundError]:
        """Delete one API key by id."""
        api_key_res = await self._getApiKeyById(api_key_id)
        if api_key_res.status == ResultStatus.Err:
            return api_key_res.into()
        api_key = api_key_res.unwrap()

        async with self.session_manager.get_session() as session:
            deleted = await self.api_key_repo.deleteById(session, api_key_id)
            if not deleted:
                return Err(ApiKeyNotFoundError())
            await session.commit()
            await self._clearCachedContext(str(api_key["hashed_key"]))
            return Ok(True)

    async def parseApiKey(
        self, api_key: str
    ) -> Result[
        ApiKeyInfo,
        InvalidAPIKey
        | ApiKeyDisabledError
        | InsufficientPermission
        | UserNotFoundError
        | ProjectNotFoundError,
    ]:
        """Verify an API key and resolve its project and organization context."""
        context_res = await self._resolveApiKeyContext(api_key)
        if context_res.status == ResultStatus.Err:
            return context_res.into()

        api_key_uuid, context = context_res.unwrap()
        if context["disabled"]:
            return Err(ApiKeyDisabledError())
        if not context["user_id"]:
            return Err(UserNotFoundError())

        return Ok(self._toApiKeyInfo(api_key_uuid, context))

    async def verifyApiKey(
        self, api_key: str, required_permissions: list[str]
    ) -> Result[
        ApiKeyInfo,
        InvalidAPIKey
        | ApiKeyDisabledError
        | InsufficientPermission
        | UserNotFoundError
        | ProjectNotFoundError,
    ]:
        """Verify an API key and resolve its project and organization context."""
        if len(required_permissions) == 0:
            raise ValueError(
                "At least one permission must be specified for verification"
            )
        context_res = await self._resolveApiKeyContext(api_key)
        if context_res.status == ResultStatus.Err:
            return context_res.into()

        api_key_uuid, context = context_res.unwrap()
        if context["disabled"]:
            return Err(ApiKeyDisabledError())
        if not context["user_id"]:
            return Err(UserNotFoundError())

        existing_permissions = set(context["permissions"])
        missing_permissions = set(required_permissions) - existing_permissions
        if missing_permissions:
            return Err(InsufficientPermission())

        return Ok(self._toApiKeyInfo(api_key_uuid, context))
