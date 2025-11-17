import hmac
import secrets
import uuid
from datetime import datetime, timedelta
from typing import TypedDict, Callable, NotRequired

from fastapi import HTTPException
from sqlalchemy import select, insert

from src.db_v2.initialize import session_manager
from src.db_v2.repository import Repository
from ..models.api_keys import ApiKey, PermissionRepo, ApiKeyPermissionRepo
from ..models.initialize import user_repo, permission_repo, api_key_repo


class ApiKeyServiceConfig(TypedDict):
    key_secret: str
    api_key_length: NotRequired[int]
    expiration_days: NotRequired[int]
    api_key_format: NotRequired[Callable[[str, str], str]]
    get_api_key_parts: NotRequired[Callable[[str], tuple[str, str]]]


class ApiKeyService:
    def __init__(self, config: ApiKeyServiceConfig):
        self.key_secret = config["key_secret"]

        self.api_key_format = config.get(
            "api_key_format", ApiKeyService.internal_format_api_key
        )
        self.get_api_key_parts = config.get(
            "get_api_key_parts", ApiKeyService.internal_get_api_key_parts
        )

        self.api_key_length = config.get("api_key_length", 32)
        self.expiration_days = config.get("expiration_days", 30)

    def create_api_key_secret(self) -> str:
        return secrets.token_urlsafe(self.api_key_length)

    @staticmethod
    def internal_format_api_key(api_key: str, secret: str) -> str:
        return f"key_{api_key}.{secret}"

    @staticmethod
    def internal_get_api_key_parts(formatted_key: str) -> tuple[str, str]:
        try:
            prefix, rest = formatted_key.split("_", 1)
            key_id, secret = rest.split(".", 1)
            return key_id, secret
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid API key format"
            )

    def hash_api_key(self, api_key: str) -> str:
        return hmac.new(
            self.key_secret.encode(), api_key.encode(), "sha256"
        ).hexdigest()

    async def create_api_key(self, user_id: str, permissions: list[str]) -> str:
        async with session_manager.get_session() as session:
            user = await user_repo.get_by_id(session, user_id)
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")

            permission_rep = await permission_repo.get_many(
                session,
                select(PermissionRepo.table).where(
                    PermissionRepo.c.name.in_(permissions)
                ),
            )

            existing_permissions = {perm.name for perm in permission_rep}
            not_existing_permissions = set(permissions) - existing_permissions
            if not_existing_permissions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Permissions not found: {', '.join(not_existing_permissions)}",
                )

            api_key_id = uuid.uuid4()
            api_key_secret = self.create_api_key_secret()
            formatted_key = self.api_key_format(str(api_key_id), api_key_secret)

            hashed_key = self.hash_api_key(formatted_key)

            # Assuming ApiKey is a SQLAlchemy model for storing API keys
            new_api_key = ApiKey(
                id=str(api_key_id),
                owner_id=user_id,
                hashed_key=hashed_key,
                expiration_date=datetime.now()
                + timedelta(days=self.expiration_days),
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

        return formatted_key

    async def verify_api_key(
        self, api_key: str, required_permissions: list[str]
    ) -> str:
        if len(required_permissions) == 0:
            raise ValueError(
                "At least one permission must be specified for verification"
            )

        async with session_manager.get_session() as session:
            key_id, _ = self.get_api_key_parts(api_key)

            key = await api_key_repo.get_by_id(session, key_id)
            if key is None:
                raise HTTPException(status_code=401, detail="Invalid API key")

            if key.expiration_date < datetime.now():
                raise HTTPException(
                    status_code=401, detail="API key has expired"
                )

            hashed_key = self.hash_api_key(api_key)
            if not hmac.compare_digest(hashed_key, key.hashed_key):
                raise HTTPException(status_code=401, detail="Invalid API key")

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
                raise HTTPException(
                    status_code=403,
                    detail=f"Missing permissions: {', '.join(missing_permissions)}",
                )

        return key.owner_id
