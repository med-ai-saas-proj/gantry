from src.shared.consts import messages_const
from src.db.postgres.service import PostgresService
from src.shared.custom_types.responses import CErrorResponse

from ..utils import hash_password, verify_password
from ..entities.user import User
from ..repositories.users import UserRepo

from typing import Callable, Optional
from contextlib import _GeneratorContextManager


class UserService:
    def __init__(self, session_scope: Callable[..., _GeneratorContextManager]):
        self.postgres_service = PostgresService(session_scope)

    async def register_user(self, email: str, password: str):
        existing_user = await self.get_user_by_email(email)
        if existing_user:
            raise CErrorResponse(
                status_code=409,
                message=messages_const.USER_ALREADY_EXISTS,
                errors={"email": {"msg": messages_const.USER_ALREADY_EXISTS}},
            )
        hashed_password = hash_password(password)

        user_data = {"email": email, "password": hashed_password}

        user = await self.postgres_service.insert(
            repo=UserRepo, record=user_data, returning=True
        )

        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        users = await self.postgres_service.get_by_condition(
            repo=UserRepo,
            conditions={
                "logical": "and",
                "conditions": [
                    {"field": "email", "operator": "=", "value": email}
                ],
            },
        )

        if users:
            users[0]["id"] = str(users[0]["id"])
            return users[0]
        return None

    async def change_password(
        self, user_id: str, current_password: str, new_password: str
    ):
        # Get user by ID
        user = await self.get_user_by_id(user_id)
        if not user:
            raise CErrorResponse(
                status_code=404,
                message=messages_const.NOT_FOUND,
                errors={"user": ["User not found"]},
            )

        # Verify current password
        stored_password = user["password"]

        # Handle different password formats (string or bytes)
        if isinstance(stored_password, bytes):
            stored_password = stored_password.decode("utf-8")

        if not verify_password(current_password, stored_password):
            raise CErrorResponse(
                status_code=400,
                message=messages_const.INVALID_CREDENTIALS,
                errors={"msg": messages_const.INVALID_CREDENTIALS},
            )

        # Hash new password
        hashed_new_password = hash_password(new_password)

        # Update password in database
        import uuid

        # Handle both string and UUID inputs
        if isinstance(user_id, str):
            user_uuid = uuid.UUID(user_id)
        else:
            user_uuid = user_id

        update_data: User = {"id": user_uuid, "password": hashed_new_password}

        await self.postgres_service.update(
            repo=UserRepo, record=update_data, identity_columns=["id"]
        )

        return {"message": "Password changed successfully"}

    async def get_user_by_id(self, user_id) -> Optional[User]:
        import uuid

        # Handle both string and UUID inputs
        if isinstance(user_id, str):
            user_uuid = uuid.UUID(user_id)
        else:
            user_uuid = user_id

        users = await self.postgres_service.get_by_condition(
            repo=UserRepo,
            conditions={
                "logical": "and",
                "conditions": [
                    {"field": "id", "operator": "=", "value": user_uuid}
                ],
            },
        )

        return users[0] if users else None
