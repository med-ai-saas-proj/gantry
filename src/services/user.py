from typing import Optional, Callable
from contextlib import _GeneratorContextManager

from src.services.postgres import PostgresService
from src.utils.password import PasswordUtils
from src.repositories.users import UserRepo
from src.custom_types.responses import CErrorResponse
from src.consts.common import MessageConsts
from src.entities.user import User


class UserService:
    def __init__(self, session_scope: Callable[..., _GeneratorContextManager]):
        self.postgres_service = PostgresService(session_scope)

    async def register_user(self, email: str, password: str):
        existing_user = await self.get_user_by_email(email)
        if existing_user:
            raise CErrorResponse(
                http_code=409,
                status_code=409,
                message=MessageConsts.USER_ALREADY_EXISTS,
                errors={"email": ["User with this email already exists"]},
            )
        hashed_password = PasswordUtils.hash_password(password)

        user_data = {"email": email, "password": hashed_password}

        user = await self.postgres_service.insert(
            repo=UserRepo, record=user_data, returning=True
        )

        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        conditions = {
            "logical": "and",
            "conditions": [{"field": "email", "operator": "=", "value": email}],
        }

        users = await self.postgres_service.get_by_condition(
            repo=UserRepo, conditions=conditions
        )

        return users[0] if users else None

    async def change_password(
        self, user_id: str, current_password: str, new_password: str
    ):
        # Get user by ID
        user = await self.get_user_by_id(user_id)
        if not user:
            raise CErrorResponse(
                http_code=404,
                status_code=404,
                message=MessageConsts.NOT_FOUND,
                errors={"user": ["User not found"]},
            )

        # Verify current password
        stored_password = user["password"]

        # Handle different password formats (string or bytes)
        if isinstance(stored_password, bytes):
            stored_password = stored_password.decode("utf-8")

        if not PasswordUtils.verify_password(current_password, stored_password):
            raise CErrorResponse(
                http_code=400,
                status_code=400,
                message="Invalid current password",
                errors={"current_password": ["Current password is incorrect"]},
            )

        # Hash new password
        hashed_new_password = PasswordUtils.hash_password(new_password)

        # Update password in database
        import uuid

        # Handle both string and UUID inputs
        if isinstance(user_id, str):
            user_uuid = uuid.UUID(user_id)
        else:
            user_uuid = user_id

        update_data = {"id": user_uuid, "password": hashed_new_password}

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

        conditions = {
            "logical": "and",
            "conditions": [
                {"field": "id", "operator": "=", "value": user_uuid}
            ],
        }

        users = await self.postgres_service.get_by_condition(
            repo=UserRepo, conditions=conditions
        )

        return users[0] if users else None
