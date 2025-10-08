from src.db.postgres.service import PostgresService

from ..utils import hash_password
from ..repositories.api_keys import ApiKeyRepo

import uuid
import secrets
from typing import Callable, Optional
from datetime import datetime, timedelta
from contextlib import _GeneratorContextManager


class ApiKeyServices:
    def __init__(self, session_scope: Callable[..., _GeneratorContextManager]):
        self.postgres_service = PostgresService(session_scope)

    def generate_api_key(self):
        return secrets.token_hex(16)

    async def create_api_key(
        self, user_id: str, name: str, expires_in_days: Optional[int] = None
    ) -> dict:
        plain_api_key = self.generate_api_key()

        hashed_api_key = hash_password(plain_api_key)

        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        api_key_data = {
            "user_id": uuid.UUID(user_id),
            "api_key": hashed_api_key,
            "name": name,
            "is_active": True,
            "expires_at": expires_at,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        api_key_record = await self.postgres_service.insert(
            repo=ApiKeyRepo, record=api_key_data, returning=True
        )

        return {
            "id": str(api_key_record["id"]),
            "api_key": plain_api_key,  # Return the plain key only once
            "name": api_key_record["name"],
            "is_active": api_key_record["is_active"],
            "expires_at": api_key_record["expires_at"],
            "created_at": api_key_record["created_at"],
        }

    async def get_user_api_keys(self, user_id: str) -> list[dict]:
        """Retrieves all API keys for a specific user.

        Args:
            user_id: The ID of the user

        Returns:
            list of API key records (without the actual key values)
        """
        api_keys = await self.postgres_service.get_by_condition(
            repo=ApiKeyRepo,
            conditions={
                "logical": "and",
                "conditions": [
                    {
                        "field": "user_id",
                        "operator": "=",
                        "value": uuid.UUID(user_id),
                    }
                ],
            },
        )

        # Return API keys without the hashed key value for security
        return [
            {
                "id": str(key["id"]),
                "name": key["name"],
                "is_active": key["is_active"],
                "last_used_at": key["last_used_at"],
                "expires_at": key["expires_at"],
                "created_at": key["created_at"],
                "updated_at": key["updated_at"],
            }
            for key in api_keys
        ]

    async def delete_by_id(self, user_id: str, _id: str):
        # example service delete
        return await self.postgres_service.delete_by_condition(
            ApiKeyRepo,
            {
                "logical": "and",
                "conditions": [
                    {
                        "field": "id",
                        "operator": "=",
                        "value": _id,
                    },
                    {
                        "field": "user_id",
                        "operator": "=",
                        "value": user_id,
                    },
                ],
            },
        )
